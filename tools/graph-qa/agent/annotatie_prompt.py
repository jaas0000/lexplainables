"""
Prompt-bouw voor de annotatie-agent (enkele ronde, geen critic — werkwijze-story 047).

De systeemprompt wordt opgebouwd uit de JAS-klassen-referentie (`agent/jas_klassen.py`). De agent
markeert JAS-elementen in een aangeleverde artikeltekst en geeft ze **gestructureerd** (JSON)
terug. Brongetrouwheid is heilig: alléén letterlijke fragmenten uit de tekst.

Poort van `wetsanalyse-ai/tools/graph-qa/agent/annotatie_prompt.py`'s `annotatie_systeemprompt`/
`annotatie_userprompt`, 1:1. Bewust niet meegenomen: `critic_systeemprompt`/`critic_userprompt`/
`_stand_van`/`_vorige_ronde_blok`, `herziening_systeemprompt`/`herziening_userprompt` — die horen
bij de critic/patch/herzie-keten, een latere story.
"""

from __future__ import annotations

from .jas_klassen import JAS_KLASSEN, JAS_KLASSEN_VOLGORDE


def _klassen_referentie() -> str:
    regels = []
    for k in JAS_KLASSEN:
        regels.append(
            f"- {k.naam}\n"
            f"    omschrijving: {k.omschrijving}\n"
            f"    herken-vraag: {k.vraag}\n"
            f"    uitdrukkingswijze: {k.uitdrukkingswijze}"
        )
    return "\n".join(regels)


def annotatie_systeemprompt() -> str:
    klassen = ", ".join(JAS_KLASSEN_VOLGORDE)
    return (
        "Je bent een annotator die Nederlandse wetteksten analyseert volgens het Juridisch "
        "Analyseschema (JAS). Je markeert de juridische elementen in een aangeleverd artikel en "
        "classificeert elk in precies één van de dertien JAS-klassen.\n"
        "\n"
        "DE DERTIEN JAS-KLASSEN (gebruik exact deze namen, verzin geen andere):\n"
        f"{_klassen_referentie()}\n"
        "\n"
        "WERKWIJZE\n"
        "- Markeer de betekenisdragende formuleringen in de aangeleverde artikeltekst en "
        "classificeer elke in de meest specifieke passende JAS-klasse. Bij een tijds- of "
        "plaatsaanduiding die ook variabele/parameter zou kunnen zijn: kies de "
        "tijds-/plaatsaanduiding.\n"
        "- BRONGETROUW: het veld `tekst` is een LETTERLIJK, aaneengesloten fragment uit de "
        "aangeleverde artikeltekst — exact overgenomen (zelfde woorden, leestekens en "
        "volgorde). Verzin niets, parafraseer niet, vul niets aan. Kun je een element niet met "
        "een letterlijk fragment onderbouwen, neem het dan niet op.\n"
        "- Geef bij twijfel tussen klassen `alternatieven`: de andere kandidaat-klasse(n) met "
        "een korte motivatie. Forceer geen zekerheid die er niet is.\n"
        '- `lid`: het lidnummer waarin het fragment staat (bijv. "1"); leeg als het niet aan '
        "een lid te koppelen is.\n"
        "- `toelichting`: één beknopte zin waarom deze klasse past (herleidbaar naar de "
        "herken-vraag).\n"
        "\n"
        "UITVOER — geef UITSLUITEND geldige JSON terug, zonder omliggende tekst of "
        "code-fences, in deze vorm:\n"
        '{"elementen": [\n'
        f'  {{"klasse": "<een van: {klassen}>", "tekst": "<letterlijk fragment>", "lid": '
        '"<lidnummer of leeg>", "toelichting": "<één zin>", "alternatieven": [{"klasse": '
        '"<klasse>", "motivatie": "<korte reden>"}]}\n'
        "]}\n"
        "`alternatieven` mag een lege lijst zijn. Neem geen enkel element op waarvan `tekst` "
        "niet letterlijk in de aangeleverde artikeltekst voorkomt."
    )


def annotatie_userprompt(
    bwb_id: str, artikel: str, artikeltekst: str, lid: str | None = None
) -> str:
    plek = f"artikel {artikel}" + (f" lid {lid}" if lid else "")
    scope = f" Blijf binnen lid {lid}." if lid else ""
    return (
        f"Regeling {bwb_id}, {plek}. Markeer en classificeer de JAS-elementen in onderstaande "
        f"tekst.{scope}\n\n--- ARTIKELTEKST ---\n{artikeltekst}\n--- EINDE ARTIKELTEKST ---"
    )
