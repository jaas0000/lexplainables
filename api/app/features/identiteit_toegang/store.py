"""Credential-verificatie en gebruikersbeheer."""

from __future__ import annotations

import bcrypt
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.future import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import Gebruiker, GebruikerInfo, MijnProfiel, VerifyResult

# Vaste dummy-hash voor timing-oracle-beveiliging bij onbekende gebruiker.
# Hardcoded constante (cost=12) zodat module-import geen bcrypt-ronde kost op elke cold start.
_DUMMY_HASH = b"$2b$12$aPK8gqAEWjX6MHVbvpshbeUk9q3j2hMZBhg1kx2Gm9ptWc0HvYCZe"


class GebruikerFout(Exception):
    """Domeinuitzondering voor ongeldig gebruikersbeheer (409 / ongeldige invoer)."""


class GebruikerNietActief(LookupError):
    """Gebruiker bestaat niet of is inactief."""


class WachtwoordOnjuist(ValueError):
    """Huidig wachtwoord klopt niet."""


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

        # De tabel is hier bewezen leeg, dus een gebruikersnaam-duplicaat is niet mogelijk.
        # De UNIQUE-constraint op gebruikersnaam (migratie 0003) vangt toekomstige
        # race-conditions op databaseniveau op.
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
    engine: AsyncEngine, gebruikersnaam: str, wachtwoord: str
) -> VerifyResult:
    async with AsyncSession(engine) as sess:
        result = await sess.execute(
            select(Gebruiker).where(Gebruiker.gebruikersnaam == gebruikersnaam)
        )
        gebruiker = result.scalar_one_or_none()

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
