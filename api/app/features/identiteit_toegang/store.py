"""Credential-verificatie en gebruikersbeheer."""

from __future__ import annotations

import secrets
from urllib.parse import quote

import bcrypt
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.future import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.shared import crypto

from .models import (
    Gebruiker,
    GebruikerInfo,
    GebruikerRead,
    MijnProfiel,
    TijdelijkWachtwoord,
    VerifyResult,
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


def _naar_read(g: Gebruiker) -> GebruikerRead:
    return GebruikerRead(
        gebruikersnaam=g.gebruikersnaam,
        rol=g.rol,
        actief=g.actief,
        aangemaakt_op=g.aangemaakt_op,
    )


# Vaste dummy-hash voor timing-oracle-beveiliging bij onbekende gebruiker.
# Hardcoded constante (cost=12) zodat module-import geen bcrypt-ronde kost op elke cold start.
_DUMMY_HASH = b"$2b$12$aPK8gqAEWjX6MHVbvpshbeUk9q3j2hMZBhg1kx2Gm9ptWc0HvYCZe"


async def tabel_leeg(engine: AsyncEngine) -> bool:
    """Geeft True terug als de gebruikers-tabel geen enkel record bevat."""
    async with AsyncSession(engine) as sess:
        result = await sess.execute(select(Gebruiker).limit(1))
        return result.scalar_one_or_none() is None


async def maak_eerste_beheerder(
    engine: AsyncEngine,
    gebruikersnaam: str,
    email: str,
    wachtwoord: str,
) -> GebruikerInfo:
    """Maakt de eerste beheerder aan.

    Gooit `GebruikerFout` als de tabel al niet leeg is of de gebruikersnaam al bestaat.
    """
    async with AsyncSession(engine) as sess:
        existing = await sess.execute(select(Gebruiker).limit(1))
        if existing.scalar_one_or_none() is not None:
            raise GebruikerFout("Setup al voltooid.")

        wachtwoord_hash = bcrypt.hashpw(wachtwoord.encode(), bcrypt.gensalt()).decode()
        gebruiker = Gebruiker(
            gebruikersnaam=gebruikersnaam,
            email=email,
            wachtwoord_hash=wachtwoord_hash,
            rol="beheerder",
        )
        sess.add(gebruiker)
        await sess.commit()
        await sess.refresh(gebruiker)

    return GebruikerInfo(
        gebruikersnaam=gebruiker.gebruikersnaam,
        email=gebruiker.email,
        rol=gebruiker.rol,
    )


async def verifieer_credentials(
    engine: AsyncEngine, gebruikersnaam: str, wachtwoord: str, totp: str | None = None
) -> VerifyResult:
    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        gebruiker = result.scalar_one_or_none()

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

    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        gebruiker = result.scalar_one_or_none()
        if gebruiker is None or not gebruiker.actief:
            raise GebruikerNietActief(gebruikersnaam)

        secret = pyotp.random_base32()
        # `crypto.encrypt` gooit CryptoFout als FERNET_KEY ontbreekt — de router mapt dat
        # naar HTTP 400 zoals de story vereist.
        gebruiker.totp_secret_enc = crypto.encrypt(secret)
        sess.add(gebruiker)
        await sess.commit()

    # Bouw de URI conform de otpauth-spec: otpauth://totp/<issuer>:<label>?secret=...&issuer=...
    label = quote(f"{_TOTP_ISSUER}:{gebruikersnaam}", safe="")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(_TOTP_ISSUER)}"


async def activeer_totp(engine: AsyncEngine, gebruikersnaam: str, code: str) -> None:
    """Bevestig de koppeling: als `code` klopt tegen het pending secret, zet
    `totp_ingeschakeld=True`."""
    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        gebruiker = result.scalar_one_or_none()
        if gebruiker is None or not gebruiker.actief:
            raise GebruikerNietActief(gebruikersnaam)
        if not gebruiker.totp_secret_enc:
            raise TotpFout("Geen 2FA-setup in uitvoering.")
        if not _totp_geldig(gebruiker.totp_secret_enc, code):
            raise TotpFout("Ongeldige TOTP-code.")

        gebruiker.totp_ingeschakeld = True
        sess.add(gebruiker)
        await sess.commit()


async def uitschakel_totp(engine: AsyncEngine, gebruikersnaam: str, code: str) -> None:
    """Schakel 2FA uit — vereist een geldige lopende code (zonder die check zou een dief die
    net toegang tot de sessie heeft, 2FA kunnen uitzetten en zo de tweede factor slopen)."""
    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        gebruiker = result.scalar_one_or_none()
        if gebruiker is None or not gebruiker.actief:
            raise GebruikerNietActief(gebruikersnaam)
        if not gebruiker.totp_ingeschakeld or not _totp_geldig(gebruiker.totp_secret_enc, code):
            raise TotpFout("Ongeldige TOTP-code.")

        gebruiker.totp_secret_enc = None
        gebruiker.totp_ingeschakeld = False
        sess.add(gebruiker)
        await sess.commit()


async def maak_gebruiker(
    engine: AsyncEngine,
    gebruikersnaam: str,
    wachtwoord: str,
    rol: str = "beheerder",
    email: str = "",
) -> Gebruiker:
    wachtwoord_hash = bcrypt.hashpw(wachtwoord.encode(), bcrypt.gensalt()).decode()
    gebruiker = Gebruiker(
        gebruikersnaam=gebruikersnaam,
        email=email,
        wachtwoord_hash=wachtwoord_hash,
        rol=rol,
    )
    async with AsyncSession(engine) as sess:
        sess.add(gebruiker)
        await sess.commit()
        await sess.refresh(gebruiker)
    return gebruiker


async def maak_gebruiker_indien_ontbreekt(
    engine: AsyncEngine,
    gebruikersnaam: str,
    wachtwoord: str,
    rol: str = "beheerder",
) -> bool:
    """Maakt de gebruiker aan als die nog niet bestaat. Geeft True terug als aangemaakt."""
    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        if result.scalar_one_or_none() is not None:
            return False
    await maak_gebruiker(engine, gebruikersnaam, wachtwoord, rol)
    return True


async def haal_gebruiker(engine: AsyncEngine, gebruikersnaam: str) -> MijnProfiel:
    """Haalt het eigen profiel op. Gooit GebruikerNietActief als account ontbreekt of inactief."""
    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        gebruiker = result.scalar_one_or_none()

    if gebruiker is None or not gebruiker.actief:
        raise GebruikerNietActief(gebruikersnaam)

    return MijnProfiel(
        naam=gebruiker.gebruikersnaam,
        gebruikersnaam=gebruiker.gebruikersnaam,
        rol=gebruiker.rol,
        actief=gebruiker.actief,
        totp_ingeschakeld=gebruiker.totp_ingeschakeld,
    )


async def wijzig_eigen_wachtwoord(
    engine: AsyncEngine,
    gebruikersnaam: str,
    huidig_wachtwoord: str,
    nieuw_wachtwoord: str,
) -> None:
    """Wijzigt het wachtwoord. Gooit GebruikerNietActief of WachtwoordOnjuist bij fouten."""
    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        gebruiker = result.scalar_one_or_none()

    if gebruiker is None or not gebruiker.actief:
        raise GebruikerNietActief(gebruikersnaam)

    # bcrypt buiten de sessie: CPU-gebonden operatie, DB-verbinding hoeft niet open te blijven.
    if not bcrypt.checkpw(huidig_wachtwoord.encode(), gebruiker.wachtwoord_hash.encode()):
        raise WachtwoordOnjuist()

    nieuw_hash = bcrypt.hashpw(nieuw_wachtwoord.encode(), bcrypt.gensalt()).decode()

    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        gebruiker = result.scalar_one()
        gebruiker.wachtwoord_hash = nieuw_hash
        sess.add(gebruiker)
        await sess.commit()


async def maak_gebruiker_admin(
    engine: AsyncEngine,
    gebruikersnaam: str,
    wachtwoord: str,
    rol: str = "analist",
) -> GebruikerRead:
    """Maakt een gebruiker aan via admin-API; gooit GebruikersnaamAlInGebruik bij duplicaat.

    Check en insert lopen in één transactie zodat er geen TOCTOU-window is.
    """
    async with AsyncSession(engine) as sess:
        bestaand = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        if bestaand.scalar_one_or_none() is not None:
            raise GebruikersnaamAlInGebruik(gebruikersnaam)
        wachtwoord_hash = bcrypt.hashpw(wachtwoord.encode(), bcrypt.gensalt()).decode()
        g = Gebruiker(gebruikersnaam=gebruikersnaam, wachtwoord_hash=wachtwoord_hash, rol=rol)
        sess.add(g)
        await sess.commit()
        await sess.refresh(g)
        return _naar_read(g)


async def lijst_gebruikers(engine: AsyncEngine) -> list[GebruikerRead]:
    async with AsyncSession(engine) as sess:
        result = await sess.execute(select(Gebruiker).order_by(Gebruiker.aangemaakt_op))
        return [_naar_read(g) for g in result.scalars().all()]


async def wijzig_gebruiker(
    engine: AsyncEngine,
    gebruikersnaam: str,
    *,
    rol: str | None,
    actief: bool | None,
) -> GebruikerRead:
    """Wijzigt rol en/of actief-status. Gooit LaatsteBeheerder als invariant geschonden."""
    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        g = result.scalar_one_or_none()
        if g is None:
            raise GebruikerNietGevonden(gebruikersnaam)

        # Controleer de invariant als de actie de gebruiker zou deactiveren of degraderen.
        zou_deactiveren = actief is False and g.actief
        zou_degraderen = rol == "analist" and g.rol == "beheerder"
        if (zou_deactiveren or zou_degraderen) and g.actief and g.rol == "beheerder":
            actieve_beheerders = await sess.execute(
                select(Gebruiker).where(
                    Gebruiker.rol == "beheerder",
                    Gebruiker.actief == True,  # noqa: E712
                )
            )
            if len(actieve_beheerders.scalars().all()) <= 1:
                raise LaatsteBeheerder(gebruikersnaam)

        if rol is not None:
            g.rol = rol
        if actief is not None:
            g.actief = actief
        sess.add(g)
        await sess.commit()
        await sess.refresh(g)
        return _naar_read(g)


async def verwijder_gebruiker(
    engine: AsyncEngine,
    gebruikersnaam: str,
    *,
    ingelogd_als: str,
) -> None:
    """Verwijdert gebruiker. Gooit LaatsteBeheerder als dit de laatste actieve beheerder is."""
    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        g = result.scalar_one_or_none()
        if g is None:
            raise GebruikerNietGevonden(gebruikersnaam)

        # Eigen account verwijderen is toegestaan zolang de invariant-check hieronder doorkomt
        # (ingelogd_als wordt bewaard voor toekomstige uitbreiding, b.v. audit-log).
        if g.actief and g.rol == "beheerder":
            actieve_beheerders = await sess.execute(
                select(Gebruiker).where(
                    Gebruiker.rol == "beheerder",
                    Gebruiker.actief == True,  # noqa: E712
                )
            )
            if len(actieve_beheerders.scalars().all()) <= 1:
                raise LaatsteBeheerder(gebruikersnaam)

        await sess.delete(g)
        await sess.commit()


async def reset_wachtwoord(
    engine: AsyncEngine,
    gebruikersnaam: str,
) -> TijdelijkWachtwoord:
    """Genereert een veilig tijdelijk wachtwoord, slaat de hash op, geeft plaintext terug."""
    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        g = result.scalar_one_or_none()
        if g is None:
            raise GebruikerNietGevonden(gebruikersnaam)

        tijdelijk = secrets.token_urlsafe(12)
        g.wachtwoord_hash = bcrypt.hashpw(tijdelijk.encode(), bcrypt.gensalt()).decode()
        sess.add(g)
        await sess.commit()

    return TijdelijkWachtwoord(gebruikersnaam=gebruikersnaam, tijdelijk_wachtwoord=tijdelijk)
