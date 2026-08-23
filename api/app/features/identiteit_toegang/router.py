"""Auth-router en admin-router voor gebruikersbeheer.

auth-router: credential-verificatie en accountbeheer achter API_TOKEN-gate.
admin_router: beheerder-only CRUD voor gebruikersaccounts (werkwijze-ADR-0003).
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_engine
from app.shared.auth import GebruikerContext, huidige_beheerder, vereist_api_token
from app.shared.crypto import CryptoFout
from app.shared.rate_limit import probeer_toestaan

from .models import (
    GebruikerCreate,
    GebruikerInfo,
    GebruikerPatch,
    GebruikerRead,
    MijnProfiel,
    SetupStatus,
    SetupVerzoek,
    TijdelijkWachtwoord,
    TotpBeginResultaat,
    TotpCodeVerzoek,
    VerifyRequest,
    VerifyResult,
    WachtwoordWijzigenVerzoek,
)
from .store import (
    GELDIGE_ROLLEN,
    GebruikerFout,
    GebruikerNietActief,
    GebruikerNietGevonden,
    GebruikersnaamAlInGebruik,
    LaatsteBeheerder,
    TotpFout,
    WachtwoordOnjuist,
    activeer_totp,
    begin_totp_koppeling,
    haal_gebruiker,
    lijst_gebruikers,
    maak_eerste_beheerder,
    maak_gebruiker_admin,
    reset_wachtwoord,
    tabel_leeg,
    uitschakel_totp,
    verifieer_credentials,
    verwijder_gebruiker,
    wijzig_eigen_wachtwoord,
    wijzig_gebruiker,
)

# Brute-force-rem op /verify: per-userid + globaal (tegen password-spraying). In-process
# (per replica) → defense-in-depth, echte bescherming hoort op de proxy/WAF. 0 = uit.
_LOGIN_MAX = int(os.environ.get("LOGIN_RATE_LIMIT_MAX", "10"))
_LOGIN_WINDOW = float(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_S", "60"))
_LOGIN_GLOBAL_FACTOR = 20

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin/gebruikers", tags=["gebruikers-admin"])


@router.get(
    "/setup-status",
    response_model=SetupStatus,
    dependencies=[Depends(vereist_api_token)],
)
async def setup_status(engine=Depends(get_engine)) -> SetupStatus:
    """Geeft aan of er al een beheerder bestaat (needs_setup = False als inrichtbaar)."""
    leeg = await tabel_leeg(engine)
    return SetupStatus(needs_setup=leeg)


@router.post(
    "/setup",
    response_model=GebruikerInfo,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(vereist_api_token)],
)
async def setup(body: SetupVerzoek, engine=Depends(get_engine)) -> GebruikerInfo:
    """Maakt de eerste beheerder aan. Retourneert 409 als de tabel al niet leeg is."""
    try:
        return await maak_eerste_beheerder(engine, body.gebruikersnaam, body.email, body.wachtwoord)
    except GebruikerFout as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/verify", response_model=VerifyResult, dependencies=[Depends(vereist_api_token)])
async def verify(request: VerifyRequest, engine=Depends(get_engine)) -> VerifyResult:
    # Brute-force-rem: per-userid ÉN globaal (tegen password-spraying over veel userids). Beide
    # moeten passeren; anders 429. Rem uit als LOGIN_RATE_LIMIT_MAX=0.
    userid = request.gebruikersnaam.strip().lower()
    per_userid_ok = probeer_toestaan(f"login:{userid}", _LOGIN_MAX, _LOGIN_WINDOW)
    globaal_ok = probeer_toestaan(
        "login:__globaal__", _LOGIN_MAX * _LOGIN_GLOBAL_FACTOR, _LOGIN_WINDOW
    )
    if not (per_userid_ok and globaal_ok):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Te veel inlogpogingen; probeer later opnieuw.",
            headers={"Retry-After": str(int(_LOGIN_WINDOW))},
        )
    return await verifieer_credentials(
        engine, request.gebruikersnaam, request.wachtwoord, request.totp
    )


@router.post(
    "/2fa/begin",
    response_model=TotpBeginResultaat,
    dependencies=[Depends(vereist_api_token)],
)
async def start_totp_koppeling(
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> TotpBeginResultaat:
    """Start een 2FA-koppeling — genereert een nieuw secret en geeft de `otpauth://`-URI
    terug (die de frontend als QR-code toont)."""
    try:
        uri = await begin_totp_koppeling(engine, gebruiker.gebruikersnaam)
    except CryptoFout as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geen FERNET_KEY_FILE geconfigureerd; 2FA kan niet worden opgeslagen.",
        ) from exc
    except GebruikerNietActief as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account niet (meer) actief.",
        ) from exc
    return TotpBeginResultaat(otpauth_uri=uri)


@router.post(
    "/2fa/activeer",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(vereist_api_token)],
)
async def activeer_totp_koppeling(
    body: TotpCodeVerzoek,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> None:
    """Bevestig 2FA-koppeling met een geldige code uit de authenticator-app."""
    try:
        await activeer_totp(engine, gebruiker.gebruikersnaam, body.totp)
    except GebruikerNietActief as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account niet (meer) actief.",
        ) from exc
    except TotpFout as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/2fa/uitschakel",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(vereist_api_token)],
)
async def uitschakel_totp_koppeling(
    body: TotpCodeVerzoek,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> None:
    """Schakel 2FA uit — vereist een geldige lopende code zodat een dief met sessie-toegang
    2FA niet stilzwijgend kan opheffen."""
    try:
        await uitschakel_totp(engine, gebruiker.gebruikersnaam, body.totp)
    except GebruikerNietActief as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account niet (meer) actief.",
        ) from exc
    except TotpFout as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/me", response_model=MijnProfiel)
async def me(
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> MijnProfiel:
    """Geeft de eigen accountgegevens terug van de ingelogde gebruiker."""
    try:
        return await haal_gebruiker(engine, gebruiker.gebruikersnaam)
    except GebruikerNietActief as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account niet (meer) actief.",
        ) from exc


@router.post("/wijzig-wachtwoord", status_code=status.HTTP_204_NO_CONTENT)
async def wijzig_wachtwoord(
    verzoek: WachtwoordWijzigenVerzoek,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> None:
    """Wijzigt het eigen wachtwoord. Geeft 400 als het huidige wachtwoord onjuist is."""
    try:
        await wijzig_eigen_wachtwoord(
            engine,
            gebruiker.gebruikersnaam,
            verzoek.huidig_wachtwoord,
            verzoek.nieuw_wachtwoord,
        )
    except GebruikerNietActief as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account niet (meer) actief.",
        ) from exc
    except WachtwoordOnjuist as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Huidig wachtwoord klopt niet.",
        ) from exc


# ---- Admin-endpoints -------------------------------------------------------


@admin_router.get("", response_model=list[GebruikerRead])
async def haal_gebruikers_op(
    _ctx: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> list[GebruikerRead]:
    return await lijst_gebruikers(engine)


@admin_router.post("", response_model=GebruikerRead, status_code=status.HTTP_201_CREATED)
async def maak_gebruiker_aan(
    body: GebruikerCreate,
    _ctx: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> GebruikerRead:
    if body.rol not in GELDIGE_ROLLEN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ongeldige rol '{body.rol}'. Kies uit: {sorted(GELDIGE_ROLLEN)}.",
        )
    try:
        return await maak_gebruiker_admin(engine, body.gebruikersnaam, body.wachtwoord, body.rol)
    except GebruikersnaamAlInGebruik as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Gebruikersnaam '{body.gebruikersnaam}' is al in gebruik.",
        ) from exc


@admin_router.patch("/{gebruikersnaam}", response_model=GebruikerRead)
async def wijzig_gebruiker_endpoint(
    gebruikersnaam: str,
    body: GebruikerPatch,
    _ctx: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> GebruikerRead:
    if body.rol is not None and body.rol not in GELDIGE_ROLLEN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ongeldige rol '{body.rol}'. Kies uit: {sorted(GELDIGE_ROLLEN)}.",
        )
    try:
        return await wijzig_gebruiker(engine, gebruikersnaam, rol=body.rol, actief=body.actief)
    except GebruikerNietGevonden as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gebruiker niet gevonden."
        ) from exc
    except LaatsteBeheerder as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kan de laatste actieve beheerder niet deactiveren of degraderen.",
        ) from exc


@admin_router.post("/{gebruikersnaam}/reset-wachtwoord", response_model=TijdelijkWachtwoord)
async def reset_wachtwoord_endpoint(
    gebruikersnaam: str,
    _ctx: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> TijdelijkWachtwoord:
    try:
        return await reset_wachtwoord(engine, gebruikersnaam)
    except GebruikerNietGevonden as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gebruiker niet gevonden."
        ) from exc


@admin_router.delete("/{gebruikersnaam}", status_code=status.HTTP_204_NO_CONTENT)
async def verwijder_gebruiker_endpoint(
    gebruikersnaam: str,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> None:
    try:
        await verwijder_gebruiker(engine, gebruikersnaam, ingelogd_als=ctx.gebruikersnaam)
    except GebruikerNietGevonden as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gebruiker niet gevonden."
        ) from exc
    except LaatsteBeheerder as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kan de laatste actieve beheerder niet verwijderen.",
        ) from exc
