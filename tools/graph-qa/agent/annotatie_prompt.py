"""
Prompt-bouw voor de annotatie-agent: de annotator (werkwijze-story 047) en de Critic (werkwijze-
story 048).

De systeemprompt wordt opgebouwd uit de JAS-klassen-referentie (`agent/jas_klassen.py`). De agent
markeert JAS-elementen in een aangeleverde artikeltekst en geeft ze **gestructureerd** (JSON)
terug. Brongetrouwheid is heilig: alléén letterlijke fragmenten uit de tekst.

Poort van `wetsanalyse-ai/tools/graph-qa/agent/annotatie_prompt.py`'s `annotatie_systeemprompt`/
`annotatie_userprompt`/`critic_systeemprompt`/`critic_userprompt`/`_stand_van`/
`_vorige_ronde_blok`, 1:1. Bewust niet meegenomen: `herziening_systeemprompt`/
`herziening_userprompt` — die horen bij de herzieningsstap, een latere story.
"""

from __future__ import annotations

from typing import Any

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


def critic_systeemprompt() -> str:
    klassen = ", ".join(JAS_KLASSEN_VOLGORDE)
    return (
        "Je bent een kritische reviewer (Critic) die JAS-annotatievoorstellen controleert "
        "VÓÓRDAT een jurist ze beoordeelt. Je maakt de annotaties zelf NIET; je beoordeelt de "
        "kwaliteit ervan en signaleert waar de jurist extra op moet letten.\n"
        "\n"
        "DE DERTIEN JAS-KLASSEN (gebruik exact deze namen, verzin geen andere):\n"
        f"{_klassen_referentie()}\n"
        "\n"
        "WAAR JE OP LET (per voorgesteld element):\n"
        "- Verkeerde of te grove klasse (past een andere JAS-klasse beter?).\n"
        "- Zwak of onvolledig gemarkeerd fragment (te lang/te kort, verkeerde grens).\n"
        "- Echte twijfel tussen klassen (dan hoort er disambiguatie te zijn).\n"
        "\n"
        "AANDACHT-NIVEAU per element — géén verzonnen zekerheidscijfer, maar een oordeel op "
        "bovenstaande signalen:\n"
        '- "groen": klasse en fragment zijn helder en juist; geen bezwaar.\n'
        '- "geel": twijfel of een aandachtspunt — jurist moet even kijken (bv. plausibel '
        "alternatief, grensgeval).\n"
        '- "rood": waarschijnlijk fout — verkeerde klasse of niet-onderbouwd fragment.\n'
        "\n"
        "HET NIVEAU ZEGT HOE ZEKER JE BENT; DE ACTIE ZEGT WAT ERMEE MOET. Dat zijn twee "
        "verschillende dingen en\n"
        'je vult ze allebei in. Denk je aan een betere klasse, noem die dan — óók bij "geel". '
        "Een oordeel als\n"
        '"het zou ook een Voorwaarde kunnen zijn" zonder `voorstel_klasse` laat de jurist met '
        "precies dezelfde\n"
        "vraag zitten als waarmee hij begon.\n"
        "\n"
        "ONTBREKEND: benoem JAS-klassen die waarschijnlijk óók in de tekst voorkomen maar niet "
        "zijn gemarkeerd.\n"
        "- Geef ALTIJD het `tekst`-veld met het LETTERLIJKE fragment uit de artikeltekst dat "
        "gemarkeerd zou moeten worden — woord voor woord, zonder aanhalingstekens eromheen. "
        "Zonder fragment kan niemand er iets mee: de annotator kan het niet toevoegen (elk "
        "element moet letterlijk te vinden zijn) en de jurist moet het zelf gaan zoeken.\n"
        "- Lukt dat echt niet omdat het element alleen impliciet aanwezig is (bv. een subject "
        'dat de tekst niet noemt), laat `tekst` dan leeg en begin de `reden` met "impliciet:". '
        "Zeg dus dát je het niet kunt aanwijzen in plaats van het te omschrijven alsof het er "
        "staat.\n"
        "- Verzin niets buiten de aangeleverde tekst.\n"
        "\n"
        "ACTIE per element — niet alleen wát er mis is, maar wat ermee moet gebeuren:\n"
        '- "behoud": je hebt geen betere klasse of afbakening in gedachten. Gebruik dit als je '
        "alleen iets wilt\n"
        "  signaleren waar de jurist zelf over moet oordelen — niet als verlegenheidskeuze "
        "omdat je twijfelt.\n"
        '- "vervang": er is een betere klasse en/of een beter begrensd fragment. Geef die dan '
        "ook op in\n"
        "  `voorstel_klasse` en/of `voorstel_tekst`; een `voorstel_tekst` MOET letterlijk in de "
        "artikeltekst staan.\n"
        '- "verwijder": dit hoort helemaal geen JAS-element te zijn. Alleen bij "rood".\n'
        "\n"
        "WAT ER MET JE VOORSTEL GEBEURT — dat hangt af van het niveau, dus kies dat "
        "zorgvuldig:\n"
        '- "rood" + "vervang" → de correctie wordt DIRECT UITGEVOERD. Er komt geen tweede '
        "beoordelaar meer\n"
        "  tussen. Kies rood alleen als je er zeker van bent dat het huidige voorstel fout is.\n"
        '- "geel" + "vervang" → je voorkeur wordt NIET uitgevoerd, maar als alternatief aan de '
        "jurist getoond;\n"
        '  die neemt hem met één klik over. Dit is de plek voor "ik denk dat het beter '
        "Voorwaarde kan zijn,\n"
        '  maar oordeel zelf" — en dus geen reden om je voorstel voor je te houden.\n'
        "\n"
        "UITVOER — geef UITSLUITEND geldige JSON terug, zonder omliggende tekst of "
        "code-fences, in deze vorm:\n"
        '{"oordelen": [\n'
        '  {"id": "<het id van het element>", "aandacht": "<groen|geel|rood>", "motivatie": '
        '"<één korte zin>",\n'
        '    "actie": "<behoud|vervang|verwijder>", "voorstel_klasse": "<optioneel, een van de '
        'dertien>",\n'
        '    "voorstel_tekst": "<optioneel, letterlijk fragment>"}\n'
        '], "ontbrekend": [\n'
        f'  {{"klasse": "<een van: {klassen}>", "reden": "<korte reden>", "tekst": '
        '"<optioneel, letterlijk fragment>"}\n'
        "]}\n"
        "Geef voor ELK aangeleverd element precies één oordeel, met het `id` zoals het is "
        "aangeleverd. `ontbrekend` mag leeg zijn.\n"
        "\n"
        "De MOTIVATIE leest een jurist letterlijk op zijn reviewkaart. Schrijf hem dus voor die "
        "jurist: geen ids (ook niet tussen haakjes) — verwijs naar een ander element met zijn "
        'fragment tussen aanhalingstekens. En schrijf niet óver de beoordeling ("herhaal '
        'niet", "jurist hoeft dit niet opnieuw te bekijken"); schrijf wat er aan de hand is.\n'
        "\n"
        "NIET DE EERSTE RONDE? Dan staat er onder de voorstellen wat je vórige ronde vond en "
        "wat de annotator daarmee heeft gedaan.\n"
        '- Is een punt opgelost? Zeg dat: `aandacht: "groen"`, `actie: "behoud"`. Dat is een '
        "uitkomst, geen zwakte.\n"
        "- Heeft de annotator jouw voorstel bewust laten liggen? Dan is dat een gemotiveerd "
        'meningsverschil. Herhaal het niet — zet het hooguit op "geel" zodat de jurist het '
        "ziet, en ga verder.\n"
        "- Herhaal geen punten die je al maakte, en meld bij ONTBREKEND alleen elementen die je "
        "nog niet eerder hebt genoemd. Is er niets meer over? Zeg dat met groene oordelen en "
        "een lege `ontbrekend`.\n"
        "\n"
        'ELEMENTEN GEMARKEERD MET "DOOR DE JURIST" heeft een mens zelf aangebracht. Beoordeel '
        "ze net zo eerlijk, maar weet dat je oordeel daar een SUGGESTIE is die de jurist naast "
        'zich neer mag leggen: gebruik `actie: "behoud"` tenzij je echt denkt dat er iets mis '
        "is, en formuleer de motivatie als een vraag of overweging, niet als een correctie."
    )


def _stand_van(voorstel: dict[str, Any], laatste_ronde: dict[str, Any]) -> str:
    """Wat er met je vorige oordeel is gebeurd — in de bewoording die klopt.

    Zonder dit onderscheid leest een uitgevoerde correctie als "ongewijzigd gelaten", en omdat
    de prompt dat als een gemotiveerd meningsverschil interpreteert, zou de Critic zijn eigen
    al-uitgevoerde oordeel weer ter discussie stellen.

    Alles hier is afgeleid uit het spoor zelf; er is geen extra state voor nodig.
    """
    if laatste_ronde.get("toegepast"):
        return "UITGEVOERD zoals je vroeg — dit is de nieuwe versie, beoordeel die"
    voorstel_klasse = str(laatste_ronde.get("voorstel_klasse", "")).strip()
    if voorstel_klasse and any(
        str(a.get("klasse")) == voorstel_klasse for a in (voorstel.get("alternatieven") or [])
    ):
        return "als ALTERNATIEF aan de jurist voorgelegd — die kiest; herhaal het niet"
    # Geel verandert nooit iets, maar het is wél afgehandeld: de motivatie staat als
    # kanttekening op de kaart van de jurist. Zonder deze regel viel een geel voorstel dat géén
    # klasse noemde terug op "ongewijzigd gelaten", en herhaalde de Critic zijn advies opnieuw.
    if str(laatste_ronde.get("aandacht", "")) == "geel" and laatste_ronde.get("actie") != "behoud":
        return "als kanttekening aan de jurist gemeld — die weegt het; herhaal het niet"
    if voorstel.get("aangepast_na_kritiek"):
        return "de annotator heeft dit AANGEPAST"
    return "ongewijzigd gelaten"


def _vorige_ronde_blok(voorstellen: list[dict[str, Any]], gemeld_ontbrekend: list[str]) -> str:
    """Wat de Critic vorige ronde zei, en wat de annotator ermee deed.

    Zonder dit blok beoordeelt de Critic elke ronde met een schone lei: hij weet niet wat hij
    zelf al vond, dus bevestigt hij nooit dat iets is opgelost en bedenkt hij elke ronde opnieuw
    wat er ontbreekt.
    """
    regels = []
    for v in voorstellen:
        rondes = v.get("critic_rondes") or []
        if not rondes:
            continue
        laatste = rondes[-1]
        kop = (
            f"[{v.get('id', '')}] {laatste.get('aandacht', '')} · {laatste.get('actie', 'behoud')}"
        )
        if laatste.get("voorstel_klasse"):
            kop += f" → {laatste['voorstel_klasse']}"
        stand = _stand_van(v, laatste)
        regels.append(f"{kop}\n       {stand}")

    if not regels and not gemeld_ontbrekend:
        return ""
    blok = ["", "--- WAT JE VORIGE RONDE ZEI ---", *regels]
    if gemeld_ontbrekend:
        blok.append("Al gemeld als ontbrekend: " + "; ".join(gemeld_ontbrekend))
    blok.append("--- EINDE ---")
    return "\n".join(blok)


def critic_userprompt(
    voorstellen: list[dict[str, Any]],
    artikeltekst: str,
    gemeld_ontbrekend: list[str] | None = None,
) -> str:
    regels = []
    for i, v in enumerate(voorstellen):
        alt = ", ".join(a.get("klasse", "") for a in v.get("alternatieven", []) if a.get("klasse"))
        alt_tekst = f" | alternatieven: {alt}" if alt else ""
        # Zowel het id (waarop het oordeel wordt gekoppeld) als de positie: valt het id weg in
        # de respons, dan is er nog een terugval. Zie `_verwerk_critic`.
        eigen_id = v.get("id", "") or f"pos-{i}"
        # Markeringen van de jurist krijgen een label: de Critic mag er iets van vinden, maar
        # zijn oordeel wordt daar een SUGGESTIE — de mens heeft het laatste woord.
        merk = " | DOOR DE JURIST" if v.get("van_jurist") else ""
        regels.append(
            f"[{i}] id={eigen_id} | klasse={v.get('klasse', '')} | "
            f'tekst="{v.get("tekst", "")}"{alt_tekst}{merk}'
        )
    lijst = "\n".join(regels) if regels else "(geen voorstellen)"
    return (
        "Beoordeel de onderstaande voorgestelde JAS-elementen tegen de artikeltekst. Geef per "
        "element een aandacht-niveau, een motivatie en een actie, en noem waarschijnlijk "
        "ontbrekende elementen.\n\n"
        f"--- VOORSTELLEN ---\n{lijst}\n--- EINDE VOORSTELLEN ---\n"
        f"{_vorige_ronde_blok(voorstellen, gemeld_ontbrekend or [])}\n"
        f"\n--- ARTIKELTEKST ---\n{artikeltekst}\n--- EINDE ARTIKELTEKST ---"
    )
