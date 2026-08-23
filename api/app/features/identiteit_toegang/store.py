"""Credential-verificatie en gebruikersbeheer (werkwijze-ADR-0011, SQLAlchemy Core)."""

from __future__ import annotations

import secrets
from urllib.parse import quote

import bcrypt
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared import crypto
from ...shared.tijd import nu
from .models import (
    GebruikerInfo,
    GebruikerRead,
    MijnProfiel,
    TijdelijkWachtwoord,
    VerifyResult,
    _GebruikerRij,
    gebruiker_uit_rij,
    gebruikers,
    naar_mijn_profiel,
    naar_read,
)

GELDIGE_ROLLEN = {"beheerder", "analist"}


class GebruikerFout(Exception):
    """Domeinuitzondering voor ongeldig gebruikersbeheer (409 / ongeldige invoer)."""


class GebruikerNietGevonden(Exception):
    pass


class LaatsteBeheerder(Exception):
    """Raised wanneer een actie de laatste actieve beheerder zou verwijderen of degraderen."""

    pass


class GebruikersnaamAlInGebruik(Exception):
    pass


class GebruikerNietActief(LookupError):
    """Gebruiker bestaat niet of is inactief."""


class WachtwoordOnjuist(ValueError):
    """Huidig wachtwoord klopt niet."""


class TotpFout(Exception):
    """TOTP-code ongeldig of TOTP-setup ongeldig (bv. geen pending secret)."""


# Vaste dummy-hash voor timing-oracle-beveiliging bij onbekende gebruiker.
# Hardcoded constante (cost=12) zodat module-import geen bcrypt-ronde kost op elke cold start.
_DUMMY_HASH = b"$2b$12$aPK8gqAEWjX6MHVbvpshbeUk9q3j2hMZBhg1kx2Gm9ptWc0HvYCZe"


async def _haal_rij_op(engine: AsyncEngine, gebruikersnaam: str) -> _GebruikerRij | None:
    async with engine.connect() as conn:
        rij = (
            await conn.execute(
                select(gebruikers).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            )
        ).first()
    return gebruiker_uit_rij(rij) if rij is not None else None


async def tabel_leeg(engine: AsyncEngine) -> bool:
    """Geeft True terug als de gebruikers-tabel geen enkel record bevat."""
    async with engine.connect() as conn:
        rij = (await conn.execute(select(gebruikers.c.id).limit(1))).first()
    return rij is None


async def maak_eerste_beheerder(
    engine: AsyncEngine,
    gebruikersnaam: str,
    email: str,
    wachtwoord: str,
) -> GebruikerInfo:
    """Maakt de eerste beheerder aan.

    Gooit `GebruikerFout` als de tabel al niet leeg is of de gebruikersnaam al bestaat.
    """
    async with engine.begin() as conn:
        bestaand = (await conn.execute(select(gebruikers.c.id).limit(1))).first()
        if bestaand is not None:
            raise GebruikerFout("Setup al voltooid.")

        wachtwoord_hash = bcrypt.hashpw(wachtwoord.encode(), bcrypt.gensalt()).decode()
        await conn.execute(
            gebruikers.insert().values(
                gebruikersnaam=gebruikersnaam,
                email=email,
                wachtwoord_hash=wachtwoord_hash,
                rol="beheerder",
                actief=True,
                aangemaakt_op=nu(),
            )
        )

    return GebruikerInfo(gebruikersnaam=gebruikersnaam, email=email, rol="beheerder")


async def verifieer_credentials(
    engine: AsyncEngine, gebruikersnaam: str, wachtwoord: str, totp: str | None = None
) -> VerifyResult:
    gebruiker = await _haal_rij_op(engine, gebruikersnaam)

    if gebruiker is None or not gebruiker.actief:
        # Altijd bcrypt-vergelijking uitvoeren om timing-oracle te voorkomen.
        bcrypt.checkpw(wachtwoord.encode(), _DUMMY_HASH)
        return VerifyResult(ok=False, code="invalid")

    if not bcrypt.checkpw(wachtwoord.encode(), gebruiker.wachtwoord_hash.encode()):
        return VerifyResult(ok=False, code="invalid")

    # Wachtwoord klopt. Als 2FA aan staat moet ook `totp` matchen. Zonder meegestuurde totp
    # signaleren we `totp_required` zodat de BFF het tweede scherm kan tonen; met verkeerde
    # totp maskeren we het als `invalid` om de status niet via de foutmelding te lekken.
    if gebruiker.totp_ingeschakeld:
        if not totp:
            return VerifyResult(ok=False, code="totp_required")
        if not _totp_geldig(gebruiker.totp_secret_enc, totp):
            return VerifyResult(ok=False, code="invalid")

    return VerifyResult(ok=True, gebruikersnaam=gebruiker.gebruikersnaam, rol=gebruiker.rol)


# ---- 2FA / TOTP -----------------------------------------------------------


_TOTP_ISSUER = "lexplainables"


def _totp_geldig(secret_enc: str | None, code: str) -> bool:
    """Verifieer een TOTP-code tegen een versleuteld secret. `valid_window=1` geeft ±30s
    tolerantie voor clock-skew tussen server en authenticator-app."""
    import pyotp

    if not secret_enc:
        return False
    try:
        secret = crypto.decrypt(secret_enc)
    except crypto.CryptoFout:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


async def begin_totp_koppeling(engine: AsyncEngine, gebruikersnaam: str) -> str:
    """Genereer een nieuw TOTP-secret voor deze gebruiker en retourneer de `otpauth://`-URI.

    Bestaande secret wordt overschreven — als de gebruiker een half-afgemaakte koppeling
    heeft laten liggen, begint hij met deze aanroep vers. `totp_ingeschakeld` blijft
    onaangeroerd (die zet pas `activeer` op True), zodat een tweede `begin`-aanroep op een
    actief-2FA-account de bestaande koppeling niet stilzwijgend vervangt zonder pass-check.
    """
    import pyotp

    async with engine.begin() as conn:
        rij = (
            await conn.execute(
                select(gebruikers).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            )
        ).first()
        gebruiker = gebruiker_uit_rij(rij) if rij is not None else None
        if gebruiker is None or not gebruiker.actief:
            raise GebruikerNietActief(gebruikersnaam)

        secret = pyotp.random_base32()
        # `crypto.encrypt` gooit CryptoFout als FERNET_KEY_FILE ontbreekt — de router mapt dat
        # naar HTTP 400 zoals de story vereist.
        await conn.execute(
            update(gebruikers)
            .where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            .values(totp_secret_enc=crypto.encrypt(secret))
        )

    # Bouw de URI conform de otpauth-spec: otpauth://totp/<issuer>:<label>?secret=...&issuer=...
    label = quote(f"{_TOTP_ISSUER}:{gebruikersnaam}", safe="")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(_TOTP_ISSUER)}"


async def activeer_totp(engine: AsyncEngine, gebruikersnaam: str, code: str) -> None:
    """Bevestig de koppeling: als `code` klopt tegen het pending secret, zet
    `totp_ingeschakeld=True`."""
    async with engine.begin() as conn:
        rij = (
            await conn.execute(
                select(gebruikers).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            )
        ).first()
        gebruiker = gebruiker_uit_rij(rij) if rij is not None else None
        if gebruiker is None or not gebruiker.actief:
            raise GebruikerNietActief(gebruikersnaam)
        if not gebruiker.totp_secret_enc:
            raise TotpFout("Geen 2FA-setup in uitvoering.")
        if not _totp_geldig(gebruiker.totp_secret_enc, code):
            raise TotpFout("Ongeldige TOTP-code.")

        await conn.execute(
            update(gebruikers)
            .where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            .values(totp_ingeschakeld=True)
        )


async def uitschakel_totp(engine: AsyncEngine, gebruikersnaam: str, code: str) -> None:
    """Schakel 2FA uit — vereist een geldige lopende code (zonder die check zou een dief die
    net toegang tot de sessie heeft, 2FA kunnen uitzetten en zo de tweede factor slopen)."""
    async with engine.begin() as conn:
        rij = (
            await conn.execute(
                select(gebruikers).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            )
        ).first()
        gebruiker = gebruiker_uit_rij(rij) if rij is not None else None
        if gebruiker is None or not gebruiker.actief:
            raise GebruikerNietActief(gebruikersnaam)
        if not gebruiker.totp_ingeschakeld or not _totp_geldig(gebruiker.totp_secret_enc, code):
            raise TotpFout("Ongeldige TOTP-code.")

        await conn.execute(
            update(gebruikers)
            .where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            .values(totp_secret_enc=None, totp_ingeschakeld=False)
        )


async def maak_gebruiker(
    engine: AsyncEngine,
    gebruikersnaam: str,
    wachtwoord: str,
    rol: str = "beheerder",
    email: str = "",
) -> _GebruikerRij:
    wachtwoord_hash = bcrypt.hashpw(wachtwoord.encode(), bcrypt.gensalt()).decode()
    async with engine.begin() as conn:
        await conn.execute(
            gebruikers.insert().values(
                gebruikersnaam=gebruikersnaam,
                email=email,
                wachtwoord_hash=wachtwoord_hash,
                rol=rol,
                actief=True,
                aangemaakt_op=nu(),
            )
        )
        rij = (
            await conn.execute(
                select(gebruikers).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            )
        ).first()
    return gebruiker_uit_rij(rij)


async def maak_gebruiker_indien_ontbreekt(
    engine: AsyncEngine,
    gebruikersnaam: str,
    wachtwoord: str,
    rol: str = "beheerder",
) -> bool:
    """Maakt de gebruiker aan als die nog niet bestaat. Geeft True terug als aangemaakt."""
    if await _haal_rij_op(engine, gebruikersnaam) is not None:
        return False
    await maak_gebruiker(engine, gebruikersnaam, wachtwoord, rol)
    return True


async def haal_gebruiker(engine: AsyncEngine, gebruikersnaam: str) -> MijnProfiel:
    """Haalt het eigen profiel op. Gooit GebruikerNietActief als account ontbreekt of inactief."""
    gebruiker = await _haal_rij_op(engine, gebruikersnaam)

    if gebruiker is None or not gebruiker.actief:
        raise GebruikerNietActief(gebruikersnaam)

    return naar_mijn_profiel(gebruiker)


async def wijzig_eigen_wachtwoord(
    engine: AsyncEngine,
    gebruikersnaam: str,
    huidig_wachtwoord: str,
    nieuw_wachtwoord: str,
) -> None:
    """Wijzigt het wachtwoord. Gooit GebruikerNietActief of WachtwoordOnjuist bij fouten."""
    gebruiker = await _haal_rij_op(engine, gebruikersnaam)

    if gebruiker is None or not gebruiker.actief:
        raise GebruikerNietActief(gebruikersnaam)

    # bcrypt buiten de sessie: CPU-gebonden operatie, DB-verbinding hoeft niet open te blijven.
    # Bewuste keuze (twee korte round-trips i.p.v. één sessie die openblijft tijdens de
    # bcrypt-hash) — zie vervolgpunten.md voor de afweging.
    if not bcrypt.checkpw(huidig_wachtwoord.encode(), gebruiker.wachtwoord_hash.encode()):
        raise WachtwoordOnjuist()

    nieuw_hash = bcrypt.hashpw(nieuw_wachtwoord.encode(), bcrypt.gensalt()).decode()

    async with engine.begin() as conn:
        await conn.execute(
            update(gebruikers)
            .where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            .values(wachtwoord_hash=nieuw_hash)
        )


async def maak_gebruiker_admin(
    engine: AsyncEngine,
    gebruikersnaam: str,
    wachtwoord: str,
    rol: str = "analist",
) -> GebruikerRead:
    """Maakt een gebruiker aan via admin-API; gooit GebruikersnaamAlInGebruik bij duplicaat.

    Check en insert lopen in één transactie zodat er geen TOCTOU-window is.
    """
    async with engine.begin() as conn:
        bestaand = (
            await conn.execute(
                select(gebruikers.c.id).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            )
        ).first()
        if bestaand is not None:
            raise GebruikersnaamAlInGebruik(gebruikersnaam)
        wachtwoord_hash = bcrypt.hashpw(wachtwoord.encode(), bcrypt.gensalt()).decode()
        await conn.execute(
            gebruikers.insert().values(
                gebruikersnaam=gebruikersnaam,
                wachtwoord_hash=wachtwoord_hash,
                rol=rol,
                actief=True,
                aangemaakt_op=nu(),
            )
        )
        rij = (
            await conn.execute(
                select(gebruikers).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            )
        ).first()
        return naar_read(gebruiker_uit_rij(rij))


async def lijst_gebruikers(engine: AsyncEngine) -> list[GebruikerRead]:
    async with engine.connect() as conn:
        rijen = (await conn.execute(select(gebruikers).order_by(gebruikers.c.aangemaakt_op))).all()
    return [naar_read(gebruiker_uit_rij(r)) for r in rijen]


async def _is_laatste_actieve_beheerder(conn) -> bool:
    """Zou het degraderen/deactiveren van de aanroepende gebruiker de laatste actieve
    beheerder wegnemen? Telt via `COUNT(*)` i.p.v. alle rijen op te halen."""
    aantal = await conn.scalar(
        select(func.count())
        .select_from(gebruikers)
        .where(gebruikers.c.rol == "beheerder", gebruikers.c.actief.is_(True))
    )
    return aantal <= 1


async def wijzig_gebruiker(
    engine: AsyncEngine,
    gebruikersnaam: str,
    *,
    rol: str | None,
    actief: bool | None,
) -> GebruikerRead:
    """Wijzigt rol en/of actief-status. Gooit LaatsteBeheerder als invariant geschonden."""
    async with engine.begin() as conn:
        rij = (
            await conn.execute(
                select(gebruikers).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            )
        ).first()
        g = gebruiker_uit_rij(rij) if rij is not None else None
        if g is None:
            raise GebruikerNietGevonden(gebruikersnaam)

        # Controleer de invariant als de actie de gebruiker zou deactiveren of degraderen.
        zou_deactiveren = actief is False and g.actief
        zou_degraderen = rol == "analist" and g.rol == "beheerder"
        if (
            (zou_deactiveren or zou_degraderen)
            and g.actief
            and g.rol == "beheerder"
            and await _is_laatste_actieve_beheerder(conn)
        ):
            raise LaatsteBeheerder(gebruikersnaam)

        waarden = {}
        if rol is not None:
            waarden["rol"] = rol
        if actief is not None:
            waarden["actief"] = actief
        if waarden:
            await conn.execute(
                update(gebruikers)
                .where(gebruikers.c.gebruikersnaam == gebruikersnaam)
                .values(**waarden)
            )
            rij = (
                await conn.execute(
                    select(gebruikers).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
                )
            ).first()
            g = gebruiker_uit_rij(rij)
        return naar_read(g)


async def verwijder_gebruiker(
    engine: AsyncEngine,
    gebruikersnaam: str,
    *,
    ingelogd_als: str,
) -> None:
    """Verwijdert gebruiker. Gooit LaatsteBeheerder als dit de laatste actieve beheerder is."""
    async with engine.begin() as conn:
        rij = (
            await conn.execute(
                select(gebruikers).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            )
        ).first()
        g = gebruiker_uit_rij(rij) if rij is not None else None
        if g is None:
            raise GebruikerNietGevonden(gebruikersnaam)

        # Eigen account verwijderen is toegestaan zolang de invariant-check hieronder doorkomt
        # (ingelogd_als wordt bewaard voor toekomstige uitbreiding, b.v. audit-log).
        if g.actief and g.rol == "beheerder" and await _is_laatste_actieve_beheerder(conn):
            raise LaatsteBeheerder(gebruikersnaam)

        await conn.execute(gebruikers.delete().where(gebruikers.c.gebruikersnaam == gebruikersnaam))


async def reset_wachtwoord(
    engine: AsyncEngine,
    gebruikersnaam: str,
) -> TijdelijkWachtwoord:
    """Genereert een veilig tijdelijk wachtwoord, slaat de hash op, geeft plaintext terug."""
    async with engine.begin() as conn:
        rij = (
            await conn.execute(
                select(gebruikers.c.id).where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            )
        ).first()
        if rij is None:
            raise GebruikerNietGevonden(gebruikersnaam)

        tijdelijk = secrets.token_urlsafe(12)
        nieuw_hash = bcrypt.hashpw(tijdelijk.encode(), bcrypt.gensalt()).decode()
        await conn.execute(
            update(gebruikers)
            .where(gebruikers.c.gebruikersnaam == gebruikersnaam)
            .values(wachtwoord_hash=nieuw_hash)
        )

    return TijdelijkWachtwoord(gebruikersnaam=gebruikersnaam, tijdelijk_wachtwoord=tijdelijk)
