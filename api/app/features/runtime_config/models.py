"""De ene bron voor het runtime_config-domein (werkwijze-ADR-0011).

Sleutel-waarde-tabel `app_instellingen` — elke instelling is een rij met een JSON-geëncodeerde
waarde. Nieuwe instellingen zijn een nieuw veld op `AppInstellingen` en een nieuw `sleutel`-record
in de database; geen migratie nodig voor elke nieuwe instelling.
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, MetaData, Table, Text

metadata = MetaData()
logger = logging.getLogger(__name__)

app_instellingen = Table(
    "app_instellingen",
    metadata,
    Column("sleutel", Text(), primary_key=True),
    Column("waarde", Text(), nullable=False),
    Column("bijgewerkt", DateTime(timezone=True), nullable=False),
)

# Alle bekende sleutels — uitbreidbaar zonder migratie.
SLEUTEL_CAPTURE_LLM_CALLS = "capture_llm_calls"


class AppInstellingen(BaseModel):
    """Huidige waarden van alle runtime-instellingen."""

    capture_llm_calls: bool = False


class AppInstellingenPatch(BaseModel):
    """Gedeeltelijke update — weggelaten velden blijven ongewijzigd."""

    capture_llm_calls: bool | None = None


def _str_naar_bool(waarde: str, standaard: bool) -> bool:
    """Parseer een JSON-geëncodeerde boolean-string; valt terug op `standaard` bij een fout."""
    try:
        parsed = json.loads(waarde)
        if isinstance(parsed, bool):
            return parsed
        return standaard
    except Exception:
        logger.warning(
            "Ongeldige JSON in app_instellingen voor waarde %r; gebruik standaard %r.",
            waarde,
            standaard,
        )
        return standaard
