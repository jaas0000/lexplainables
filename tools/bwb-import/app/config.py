"""Configuratie voor bwb-import, geladen uit de omgeving.

Geen globale state: `Settings.from_env()` bouwt een onveranderlijk configuratie-object dat
expliciet wordt doorgegeven aan de componenten (zelfde patroon als de referentie-app).

Secrets volgen werkwijze-ADR-0006: het GraphDB-wachtwoord komt uit een bestand
(`GRAPHDB_PASSWORD_FILE`), nooit rechtstreeks uit een env-var-waarde. Dit wijkt bewust af van de
referentie-app (die `GRAPHDB_PASSWORD` als platte env-var leest) — nieuwe lexplainables-code volgt
de geaccepteerde ADR, ook waar bestaande code dat nog niet doet (zie vervolgpunten.md).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Wortel van het project (bwb-import/), onafhankelijk van de werkdirectory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Officieel SRU-endpoint van het Basiswettenbestand (geverifieerd tegen de referentie-app).
DEFAULT_SRU_BASE_URL = "https://zoekservice.overheid.nl/sru/Search"


def _read_secret(env_var_file: str, *, default: str | None = None) -> str | None:
    """Lees een geheim uit het bestand waarnaar `<NAAM>_FILE` verwijst (werkwijze-ADR-0006).

    Geeft `default` terug als de env-var niet gezet is (bv. lokale dev zonder GraphDB-schrijf-
    toegang in deze story). Een gezette env-var die naar een ontbrekend bestand wijst is een
    configuratiefout en hoort te crashen, niet stil te falen.
    """
    pad = os.environ.get(env_var_file)
    if pad is None:
        return default
    return Path(pad).read_text(encoding="utf-8").strip()


@dataclass(frozen=True, slots=True)
class Settings:
    """Onveranderlijke runtime-configuratie."""

    data_dir: Path
    schemas_dir: Path
    sru_base_url: str
    validate_xsd: bool
    import_wti: bool
    detect_tekstuele_refs: bool
    graphdb_url: str
    graphdb_repository: str
    graphdb_user: str | None
    graphdb_password: str | None
    service_api_key: str | None

    @classmethod
    def from_env(cls) -> Settings:
        """Laad instellingen uit de omgeving."""
        return cls(
            data_dir=Path(os.environ.get("BWB_DATA_DIR", str(PROJECT_ROOT / "data"))),
            schemas_dir=Path(os.environ.get("BWB_SCHEMAS_DIR", str(PROJECT_ROOT / "schemas"))),
            sru_base_url=os.environ.get("BWB_SRU_URL", DEFAULT_SRU_BASE_URL),
            validate_xsd=os.environ.get("BWB_VALIDATE_XSD", "true").strip().lower()
            not in {"0", "false", "nee", "no"},
            import_wti=os.environ.get("BWB_IMPORT_WTI", "false").strip().lower()
            not in {"0", "false", "nee", "no"},
            detect_tekstuele_refs=os.environ.get("BWB_DETECT_TEKSTUELE_REFS", "true")
            .strip()
            .lower()
            not in {"0", "false", "nee", "no"},
            graphdb_url=os.environ.get("GRAPHDB_URL", "http://graphdb:7200"),
            graphdb_repository=os.environ.get("GRAPHDB_REPOSITORY", "inning"),
            graphdb_user=os.environ.get("GRAPHDB_USER") or None,
            graphdb_password=_read_secret("GRAPHDB_PASSWORD_FILE"),
            service_api_key=_read_secret("BWB_SERVICE_API_KEY_FILE"),
        )
