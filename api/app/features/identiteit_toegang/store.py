"""Credential-verificatie en gebruikersbeheer."""

from __future__ import annotations

import secrets

import bcrypt
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.future import select
from sqlmodel.ext.asyncio.session import AsyncSession

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


def _naar_read(g: Gebruiker) -> GebruikerRead:
    return GebruikerRead(
        gebruikersnaam=g.gebruikersnaam,
        rol=g.rol,
        actief=g.actief,
        aangemaakt_op=g.aangemaakt_op,
    )


def _hash_wachtwoord(wachtwoord: str) -> str:
    """Bcrypt-hash met verse salt (cost = library-default)."""
    return bcrypt.hashpw(wachtwoord.encode(), bcrypt.gensalt()).decode()


async def _zoek_op_naam(sess: AsyncSession, gebruikersnaam: str) -> Gebruiker | None:
    result = await sess.execute(select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam))
    return result.scalar_one_or_none()


async def _valideer_niet_laatste_beheerder(sess: AsyncSession, g: Gebruiker) -> None:
    """Gooit LaatsteBeheerder als `g` de enige actieve beheerder is.

    Roep dit alleen aan wanneer `g` een actie ondergaat die die status zou wegnemen
    (deactiveren of degraderen of verwijderen). Alleen relevant als `g` op dit moment
    zelf een actieve beheerder is.
    """
    if not (g.actief and g.rol == "beheerder"):
        return
    result = await sess.execute(
        select(func.count())
        .select_from(Gebruiker)
        .where(
            Gebruiker.rol == "beheerder",
            Gebruiker.actief == True,  # noqa: E712
        )
    )
    if result.scalar_one() <= 1:
        raise LaatsteBeheerder(g.gebruikersnaam)


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

        gebruiker = Gebruiker(
            gebruikersnaam=gebruikersnaam,
            email=email,
            wachtwoord_hash=_hash_wachtwoord(wachtwoord),
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
    engine: AsyncEngine, gebruikersnaam: str, wachtwoord: str
) -> VerifyResult:
    async with AsyncSession(engine) as sess:
        gebruiker = await _zoek_op_naam(sess, gebruikersnaam)

    if gebruiker is None or not gebruiker.actief:
        # Altijd bcrypt-vergelijking uitvoeren om timing-oracle te voorkomen.
        bcrypt.checkpw(wachtwoord.encode(), _DUMMY_HASH)
        return VerifyResult(ok=False)

    if not bcrypt.checkpw(wachtwoord.encode(), gebruiker.wachtwoord_hash.encode()):
        return VerifyResult(ok=False)

    return VerifyResult(ok=True, gebruikersnaam=gebruiker.gebruikersnaam, rol=gebruiker.rol)


async def maak_gebruiker(
    engine: AsyncEngine,
    gebruikersnaam: str,
    wachtwoord: str,
    rol: str = "beheerder",
    email: str = "",
) -> Gebruiker:
    gebruiker = Gebruiker(
        gebruikersnaam=gebruikersnaam,
        email=email,
        wachtwoord_hash=_hash_wachtwoord(wachtwoord),
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
    """Maakt de gebruiker aan als die nog niet bestaat. Geeft True terug als aangemaakt.

    Gebruikt de atomische admin-variant zodat check-en-insert in één transactie lopen.
    """
    try:
        await maak_gebruiker_admin(engine, gebruikersnaam, wachtwoord, rol)
    except GebruikersnaamAlInGebruik:
        return False
    return True


async def haal_gebruiker(engine: AsyncEngine, gebruikersnaam: str) -> MijnProfiel:
    """Haalt het eigen profiel op. Gooit GebruikerNietActief als account ontbreekt of inactief."""
    async with AsyncSession(engine) as sess:
        gebruiker = await _zoek_op_naam(sess, gebruikersnaam)

    if gebruiker is None or not gebruiker.actief:
        raise GebruikerNietActief(gebruikersnaam)

    return MijnProfiel(
        naam=gebruiker.gebruikersnaam,
        gebruikersnaam=gebruiker.gebruikersnaam,
        rol=gebruiker.rol,
        totp_ingeschakeld=False,
    )


async def wijzig_eigen_wachtwoord(
    engine: AsyncEngine,
    gebruikersnaam: str,
    huidig_wachtwoord: str,
    nieuw_wachtwoord: str,
) -> None:
    """Wijzigt het wachtwoord. Gooit GebruikerNietActief of WachtwoordOnjuist bij fouten."""
    async with AsyncSession(engine) as sess:
        gebruiker = await _zoek_op_naam(sess, gebruikersnaam)

    if gebruiker is None or not gebruiker.actief:
        raise GebruikerNietActief(gebruikersnaam)

    # bcrypt buiten de sessie: CPU-gebonden operatie, DB-verbinding hoeft niet open te blijven.
    if not bcrypt.checkpw(huidig_wachtwoord.encode(), gebruiker.wachtwoord_hash.encode()):
        raise WachtwoordOnjuist()

    nieuw_hash = _hash_wachtwoord(nieuw_wachtwoord)

    async with AsyncSession(engine) as sess:
        gebruiker = await _zoek_op_naam(sess, gebruikersnaam)
        assert gebruiker is not None  # bestond zojuist nog; race is zeldzaam en niet-fataal
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
        if await _zoek_op_naam(sess, gebruikersnaam) is not None:
            raise GebruikersnaamAlInGebruik(gebruikersnaam)
        g = Gebruiker(
            gebruikersnaam=gebruikersnaam,
            wachtwoord_hash=_hash_wachtwoord(wachtwoord),
            rol=rol,
        )
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
        g = await _zoek_op_naam(sess, gebruikersnaam)
        if g is None:
            raise GebruikerNietGevonden(gebruikersnaam)

        # Alleen als de actie de gebruiker deactiveert of degradeert kan de invariant breken.
        if actief is False or rol == "analist":
            await _valideer_niet_laatste_beheerder(sess, g)

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
    """Verwijdert gebruiker. Gooit LaatsteBeheerder als dit de laatste actieve beheerder is.

    `ingelogd_als` wordt bewaard voor toekomstige uitbreiding (bv. audit-log).
    """
    async with AsyncSession(engine) as sess:
        g = await _zoek_op_naam(sess, gebruikersnaam)
        if g is None:
            raise GebruikerNietGevonden(gebruikersnaam)

        await _valideer_niet_laatste_beheerder(sess, g)

        await sess.delete(g)
        await sess.commit()


async def reset_wachtwoord(
    engine: AsyncEngine,
    gebruikersnaam: str,
) -> TijdelijkWachtwoord:
    """Genereert een veilig tijdelijk wachtwoord, slaat de hash op, geeft plaintext terug."""
    async with AsyncSession(engine) as sess:
        g = await _zoek_op_naam(sess, gebruikersnaam)
        if g is None:
            raise GebruikerNietGevonden(gebruikersnaam)

        tijdelijk = secrets.token_urlsafe(12)
        g.wachtwoord_hash = _hash_wachtwoord(tijdelijk)
        sess.add(g)
        await sess.commit()

    return TijdelijkWachtwoord(gebruikersnaam=gebruikersnaam, tijdelijk_wachtwoord=tijdelijk)
