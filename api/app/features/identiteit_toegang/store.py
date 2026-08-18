"""Credential-verificatie en gebruikersbeheer."""

from __future__ import annotations

import secrets

import bcrypt
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.future import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import Gebruiker, GebruikerRead, MijnProfiel, TijdelijkWachtwoord, VerifyResult

GELDIGE_ROLLEN = {"beheerder", "analist"}


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


# Vaste dummy-hash voor timing-oracle-beveiliging bij onbekende gebruiker.
# Hardcoded constante (cost=12) zodat module-import geen bcrypt-ronde kost op elke cold start.
_DUMMY_HASH = b"$2b$12$aPK8gqAEWjX6MHVbvpshbeUk9q3j2hMZBhg1kx2Gm9ptWc0HvYCZe"


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
) -> Gebruiker:
    wachtwoord_hash = bcrypt.hashpw(wachtwoord.encode(), bcrypt.gensalt()).decode()
    gebruiker = Gebruiker(gebruikersnaam=gebruikersnaam, wachtwoord_hash=wachtwoord_hash, rol=rol)
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
