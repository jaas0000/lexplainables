"""Store-abstractie voor het llm_profielen-domein (werkwijze-ADR-0007).

`LlmProfielenStore` beschrijft de operaties die router.py nodig heeft. `SqlAlchemyLlmProfielenStore`
is de enige huidige implementatie. Tests draaien 'm tegen een eigen kortlevende SQLite-engine.

Businessregels die hier worden gehandhaafd:
- Fernet-encryptie van `api_sleutel` bij schrijven; bij lezen: `sleutel_ingesteld` (bool).
- Bij `is_standaard=True`: alle andere profielen worden tegelijk op False gezet (één transactie).
- `api_sleutel` leeg bij bijwerken → bestaande versleutelde sleutel ongewijzigd laten.
- Verwijderen van het enige profiel → `EnigeProfielFout`.
- Naam-conflict bij aanmaken → `NaamConflictFout`.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared.crypto import encrypt
from ...shared.tijd import nu
from .models import LlmProfielRead, llm_profiel_uit_rij, llm_profielen


class ProfielNietGevonden(LookupError):
    """Onbekende profielnaam bij bijwerken of verwijderen."""


class NaamConflictFout(ValueError):
    """Naam bestaat al bij aanmaken van een nieuw profiel."""


class EnigeProfielFout(ValueError):
    """Verwijderen geweigerd: dit is het enige profiel."""


class LlmProfielenStore(Protocol):
    async def lijst(self) -> list[LlmProfielRead]: ...

    async def maak(
        self,
        naam: str,
        provider: str,
        model: str,
        api_base: str,
        api_versie: str | None,
        temperatuur: float,
        api_sleutel: str | None,
        is_standaard: bool,
    ) -> LlmProfielRead: ...

    async def bewerk(
        self,
        naam: str,
        provider: str,
        model: str,
        api_base: str,
        api_versie: str | None,
        temperatuur: float,
        api_sleutel: str | None,
        is_standaard: bool,
    ) -> LlmProfielRead: ...

    async def verwijder(self, naam: str) -> None: ...


class SqlAlchemyLlmProfielenStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def lijst(self) -> list[LlmProfielRead]:
        stmt = select(llm_profielen).order_by(llm_profielen.c.naam)
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [llm_profiel_uit_rij(rij) for rij in rijen]

    async def maak(
        self,
        naam: str,
        provider: str,
        model: str,
        api_base: str,
        api_versie: str | None,
        temperatuur: float,
        api_sleutel: str | None,
        is_standaard: bool,
    ) -> LlmProfielRead:
        enc = _encrypt_optioneel(api_sleutel)
        moment = nu()
        async with self._engine.begin() as conn:
            # Controleer naam-uniciteit atomair in dezelfde transactie.
            bestaand = await conn.scalar(
                select(llm_profielen.c.naam).where(llm_profielen.c.naam == naam)
            )
            if bestaand is not None:
                raise NaamConflictFout(f"Profielnaam '{naam}' bestaat al.")

            if is_standaard:
                await conn.execute(update(llm_profielen).values(is_standaard=False))

            result = await conn.execute(
                insert(llm_profielen)
                .values(
                    naam=naam,
                    provider=provider,
                    model=model,
                    api_base=api_base,
                    api_versie=api_versie or None,
                    temperatuur=temperatuur,
                    api_sleutel_enc=enc,
                    is_standaard=is_standaard,
                    updated=moment,
                )
                .returning(llm_profielen)
            )
            rij = result.one()
        return llm_profiel_uit_rij(rij)

    async def bewerk(
        self,
        naam: str,
        provider: str,
        model: str,
        api_base: str,
        api_versie: str | None,
        temperatuur: float,
        api_sleutel: str | None,
        is_standaard: bool,
    ) -> LlmProfielRead:
        async with self._engine.begin() as conn:
            # Haal de bestaande rij op voor de huidige versleutelde sleutel.
            huidig = await conn.execute(select(llm_profielen).where(llm_profielen.c.naam == naam))
            rij = huidig.first()
            if rij is None:
                raise ProfielNietGevonden(f"Profiel '{naam}' bestaat niet.")

            # api_sleutel leeg → ongewijzigd laten.
            nieuw_enc = _encrypt_optioneel(api_sleutel) if api_sleutel else rij.api_sleutel_enc

            if is_standaard:
                await conn.execute(
                    update(llm_profielen)
                    .where(llm_profielen.c.naam != naam)
                    .values(is_standaard=False)
                )

            result = await conn.execute(
                update(llm_profielen)
                .where(llm_profielen.c.naam == naam)
                .values(
                    provider=provider,
                    model=model,
                    api_base=api_base,
                    api_versie=api_versie or None,
                    temperatuur=temperatuur,
                    api_sleutel_enc=nieuw_enc,
                    is_standaard=is_standaard,
                    updated=nu(),
                )
                .returning(llm_profielen)
            )
            bijgewerkt = result.first()
        if bijgewerkt is None:
            raise ProfielNietGevonden(f"Profiel '{naam}' bestaat niet.")
        return llm_profiel_uit_rij(bijgewerkt)

    async def verwijder(self, naam: str) -> None:
        from sqlalchemy import func

        async with self._engine.begin() as conn:
            telling = await conn.scalar(select(func.count()).select_from(llm_profielen))
            if int(telling or 0) <= 1:
                # Controleer eerst of het profiel bestaat.
                bestaand = await conn.scalar(
                    select(llm_profielen.c.naam).where(llm_profielen.c.naam == naam)
                )
                if bestaand is None:
                    raise ProfielNietGevonden(f"Profiel '{naam}' bestaat niet.")
                raise EnigeProfielFout(
                    f"Profiel '{naam}' is het enige profiel en kan niet worden verwijderd."
                )

            result = await conn.execute(
                delete(llm_profielen)
                .where(llm_profielen.c.naam == naam)
                .returning(llm_profielen.c.naam)
            )
            if result.first() is None:
                raise ProfielNietGevonden(f"Profiel '{naam}' bestaat niet.")

    async def haal_rij_op_naam(self, naam: str):
        """Geef de ruwe databaserij terug voor een profiel op naam (inclusief api_sleutel_enc).

        Geeft None terug als het profiel niet bestaat. Gebruikt door de orchestrator om het
        LLM-profiel op te halen (inclusief de versleutelde API-sleutel — feature-bouwen regel 8).
        """
        async with self._engine.connect() as conn:
            rij = await conn.execute(select(llm_profielen).where(llm_profielen.c.naam == naam))
            return rij.first()

    async def haal_standaard_rij(self):
        """Geef de ruwe databaserij voor het standaard-profiel terug (inclusief api_sleutel_enc).

        Geeft None terug als er geen standaard-profiel is.
        """
        async with self._engine.connect() as conn:
            rij = await conn.execute(
                select(llm_profielen).where(llm_profielen.c.is_standaard.is_(True))
            )
            return rij.first()


def _encrypt_optioneel(sleutel: str | None) -> str | None:
    """Versleutel de API-sleutel als die aanwezig is; geeft None terug als `sleutel` leeg is.
    Gooit `CryptoFout` als FERNET_KEY_FILE ontbreekt maar wel een sleutel meegegeven wordt."""
    if not sleutel:
        return None
    return encrypt(sleutel)
