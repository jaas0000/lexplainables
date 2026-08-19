"""Validatie voor de analyse-engine.

Twee soorten:
  - SCHEMA: structuur-/volledigheidscheck op LLM-output (markeringen, begrippen, regels).
    Fouten worden teruggegeven als lijst; de orchestrator doet auto-correctie of zet op 'fout'.
  - HARD (brongetrouwheid): elk 'formulering'-citaat MOET een substring zijn van de
    gecombineerde leden-tekst (na NFKC-normalisatie). Nooit stil doorgaan bij een mismatch.

De 13 JAS-klassen zijn de enige toegestane klassen (jas-klassen-referentie.md).
"""

from __future__ import annotations

import unicodedata

# De 13 JAS-klassen uit jas-klassen-referentie.md (enige toegestane waarden).
GELDIGE_JAS_KLASSEN: frozenset[str] = frozenset(
    {
        "Rechtssubject",
        "Rechtsobject",
        "Rechtsbetrekking",
        "Rechtsfeit",
        "Voorwaarde",
        "Afleidingsregel",
        "Variabele en variabelewaarde",
        "Parameter en parameterwaarde",
        "Operator",
        "Tijdsaanduiding",
        "Plaatsaanduiding",
        "Delegatiebevoegdheid en delegatie-invulling",
        "Brondefinitie",
    }
)


def _normaliseer(tekst: str) -> str:
    return unicodedata.normalize("NFKC", tekst)


def schema_check_act2(data: dict) -> list[str]:
    """Structuurcheck op act2-output. Geeft lijst van foutbeschrijvingen terug (leeg = OK)."""
    fouten: list[str] = []
    markeringen = data.get("markeringen")
    if not isinstance(markeringen, list):
        fouten.append("'markeringen' ontbreekt of is geen lijst.")
        return fouten

    gebruikte_ids: set[str] = set()
    for i, m in enumerate(markeringen):
        prefix = f"Markering {i + 1}"
        if not isinstance(m, dict):
            fouten.append(f"{prefix}: geen object.")
            continue
        for veld in ("id", "formulering", "klasse", "vindplaats"):
            if not m.get(veld):
                fouten.append(f"{prefix}: veld '{veld}' ontbreekt of leeg.")
        klasse = m.get("klasse", "")
        if klasse and klasse not in GELDIGE_JAS_KLASSEN:
            fouten.append(
                f"{prefix}: klasse '{klasse}' is geen geldige JAS-klasse. "
                f"Gebruik één van: {', '.join(sorted(GELDIGE_JAS_KLASSEN))}."
            )
        mid = m.get("id", "")
        if mid:
            if mid in gebruikte_ids:
                fouten.append(f"{prefix}: id '{mid}' wordt meerdere keren gebruikt.")
            gebruikte_ids.add(mid)

    if not data.get("samenhang"):
        fouten.append("'samenhang' ontbreekt of leeg.")
    return fouten


def schema_check_act3(data: dict) -> list[str]:
    """Structuurcheck op act3-output (begrippen + regels). Geeft foutlijst terug (leeg = OK)."""
    fouten: list[str] = []
    begrippen = data.get("begrippen")
    if not isinstance(begrippen, list):
        fouten.append("'begrippen' ontbreekt of is geen lijst.")
    else:
        begrip_ids: set[str] = set()
        for i, b in enumerate(begrippen):
            prefix = f"Begrip {i + 1}"
            if not isinstance(b, dict):
                fouten.append(f"{prefix}: geen object.")
                continue
            for veld in ("id", "naam", "klasse", "definitie"):
                if not b.get(veld):
                    fouten.append(f"{prefix}: veld '{veld}' ontbreekt of leeg.")
            klasse = b.get("klasse", "")
            if klasse and klasse not in GELDIGE_JAS_KLASSEN:
                fouten.append(f"{prefix}: klasse '{klasse}' is geen geldige JAS-klasse.")
            bid = b.get("id", "")
            if bid:
                if bid in begrip_ids:
                    fouten.append(f"{prefix}: id '{bid}' wordt meerdere keren gebruikt.")
                begrip_ids.add(bid)

    afleidingsregels = data.get("afleidingsregels")
    if not isinstance(afleidingsregels, list):
        fouten.append("'afleidingsregels' ontbreekt of is geen lijst.")

    return fouten


def brongetrouwheid_check(leden: list[dict], markeringen: list[dict]) -> list[str]:
    """Harde brongetrouwheidscheck: elke 'formulering' moet een substring zijn van de leden-tekst.

    Geeft lijst van overtredingen terug. Leeg = volledig brongetrouw.
    Alle vergelijkingen verlopen via NFKC-normalisatie (unicode-whitespace, ligaturen e.d.).
    """
    gecombineerd = _normaliseer(
        " ".join(lid.get("tekst", "") for lid in leden if isinstance(lid, dict))
    )
    overtredingen: list[str] = []
    for m in markeringen:
        if not isinstance(m, dict):
            continue
        formulering = m.get("formulering", "")
        if not formulering:
            continue
        if _normaliseer(formulering) not in gecombineerd:
            mid = m.get("id", "?")
            kort = formulering[:60] + "…" if len(formulering) > 60 else formulering
            overtredingen.append(
                f"Markering {mid}: formulering '{kort}' is geen letterlijk citaat "
                "uit de leden-tekst."
            )
    return overtredingen
