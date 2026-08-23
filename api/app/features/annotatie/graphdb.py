"""SPARQL-leesclient voor wetsartikeltekst (story 037, uitgebreid na vergelijking met
`wetsanalyse-ai/tools/graph-qa/agent/artikel.py`+`graph/queries.py` — het doel is dat de
werkplek-weergave hetzelfde toont als de referentie-app, ook al zit die logica daar in de
losse `graph-qa`-agent (nog niet gebouwd in dit project) en hier rechtstreeks in `api/`).

Vraagt rechtstreeks de artikeltekst (+ leden + onderdelen) op bij GraphDB voor de
werkplek-detailpagina. Geen import van `tools/bwb-import` (ADR-0002 — geen gedeelde import over
een servicegrens): de artikel-IRI wordt hier zelf opgebouwd, volgens exact hetzelfde schema als
`tools/bwb-import/app/rdf_vocab.py::Vocab.by_ref_key`/`_iri` (canonieke vorm
`urn:bwb:{bwb_id}:artikel:{artikelnummer}`, URN-segmenten `:`-gescheiden, elk segment
percent-encoded). Wijzigt dat schema daar, dan moet het hier mee veranderen.

Twee dingen die de referentie-app óók expliciet oplost en die hier bewust zijn overgenomen:
- **Onderdelen onder een lid** (`bwb:heeftOnderdeel+`, property-path — lexplainables nestelt
  onderdelen recursief via hetzelfde predicaat i.p.v. de platte `bwb:bevat`-kopie die de
  referentie gebruikt, dus een property-path volstaat hier zonder schemawijziging). Zonder dit
  is een definitieartikel (bv. Invorderingswet art. 2 lid 1) vrijwel leeg: alleen "Deze wet
  verstaat onder:", zonder de a-t.-onderdelen die de eigenlijke definities dragen.
- **Numerieke lid-sortering** — SPARQL's `ORDER BY` op een string-literal is lexicaal
  (1, 10, 11, 2, …). `_lidsleutel` (poort van de referentie's gelijknamige functie) sorteert op
  het numerieke voorvoegsel.

Bewust NIET overgenomen: de referentie's `OngeldigeVindplaats`-validatie (typo vs. leeg) — dat
is een API-consumentendetail voor de agent-tool-laag, geen verschil dat een jurist in de
werkplek-UI ziet (beide gevallen tonen daar toch "niet gevonden").

Geen `shared/`-module: precies één consument (feature-bouwen regel 8). `api/app/shared/
wettenbank.py` lost een vergelijkbaar probleem op voor een andere functie (citeertitel via
JSON-RPC tegen een niet-bestaande Wettenbank-MCP) — die module is niet hergebruikt, want de
transportlaag is volledig anders en `wettenbank.py` staat zelf al gepland voor vervanging door
precies dit soort directe SPARQL-toegang.

Secrets volgen werkwijze-ADR-0006 (`GRAPHDB_PASSWORD_FILE`, geen platte env-var). Zelfde
env-var-namen/-defaults als `tools/bwb-import/app/config.py`, zodat één GraphDB-instance met
dezelfde configuratie door beide services bereikt wordt.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import quote

import httpx

from .models import Wetsartikel, WetsartikelLid, WetsartikelOnderdeel

GRAPHDB_URL = os.environ.get("GRAPHDB_URL", "http://graphdb:7200")
GRAPHDB_REPOSITORY = os.environ.get("GRAPHDB_REPOSITORY", "inning")
GRAPHDB_USER = os.environ.get("GRAPHDB_USER") or None


def _lees_graphdb_password() -> str | None:
    pad = os.environ.get("GRAPHDB_PASSWORD_FILE")
    if pad is None:
        return None
    return Path(pad).read_text(encoding="utf-8").strip()


# Eén keer bij module-load gelezen, zelfde als GRAPHDB_URL/REPOSITORY/USER hierboven — niet
# opnieuw van disk lezen bij elke aanvraag.
GRAPHDB_PASSWORD = _lees_graphdb_password()

_TIMEOUT = 15.0

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Proces-brede client, lazily aangemaakt — zelfde patroon als `db.py::get_engine`."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_TIMEOUT)
    return _client


# `?lid`/`?onderdeel` zijn hier bewust bound (geen losse IRI-projectie): de groepering in Python
# hieronder gebruikt hun waarde als sleutel om rijen bij het juiste lid te clusteren.
_QUERY_ARTIKEL = """
PREFIX bwb: <urn:bwb-ns:>
SELECT ?opschrift ?tekst ?lid ?lidNummer ?lidTekst ?onderdeel ?onderdeelNummer ?onderdeelTekst
WHERE {{
  GRAPH ?g {{
    <{iri}> a bwb:Artikel .
    OPTIONAL {{ <{iri}> bwb:tekst ?tekst }}
    OPTIONAL {{ <{iri}> bwb:opschrift ?opschrift }}
    OPTIONAL {{
      <{iri}> bwb:heeftLid ?lid .
      OPTIONAL {{ ?lid bwb:nummer ?lidNummer }}
      OPTIONAL {{ ?lid bwb:tekst ?lidTekst }}
      OPTIONAL {{
        ?lid bwb:heeftOnderdeel+ ?onderdeel .
        OPTIONAL {{ ?onderdeel bwb:nummer ?onderdeelNummer }}
        OPTIONAL {{ ?onderdeel bwb:tekst ?onderdeelTekst }}
      }}
    }}
  }}
}}
"""

# Fallback voor een artikel zonder leden dat wél direct onderdelen draagt (a/b/c rechtstreeks
# onder het artikel) — alleen aangeroepen als `_QUERY_ARTIKEL` geen leden opleverde.
_QUERY_ARTIKEL_ONDERDELEN = """
PREFIX bwb: <urn:bwb-ns:>
SELECT ?onderdeel ?onderdeelNummer ?onderdeelTekst WHERE {{
  GRAPH ?g {{
    <{iri}> bwb:heeftOnderdeel+ ?onderdeel .
    OPTIONAL {{ ?onderdeel bwb:nummer ?onderdeelNummer }}
    OPTIONAL {{ ?onderdeel bwb:tekst ?onderdeelTekst }}
  }}
}}
"""

# Fallback voor bepalingen die niet het artikel/lid-IRI-patroon volgen: decimale nummers uit
# circulaires/beleidsregels (bv. "9.1", zie story 034/`Divisie`) — gezocht op `bwb:nummer`
# binnen de eigen regeling, net als de referentie's `get_bepaling`.
_QUERY_BEPALING = """
PREFIX bwb: <urn:bwb-ns:>
SELECT ?tekst ?opschrift WHERE {{
  GRAPH ?g {{
    ?node bwb:nummer {nummer} ; bwb:tekst ?tekst .
    FILTER(STRSTARTS(STR(?node), {basis}))
    OPTIONAL {{ ?node bwb:opschrift ?opschrift }}
  }}
}} LIMIT 1
"""


class GraphDbFout(RuntimeError):
    """Ophalen mislukte — geen bruikbare wetsartikeltekst."""


class GraphDbNietBereikbaar(GraphDbFout):
    """Netwerk-/HTTP-fout — GraphDB zelf antwoordt niet."""


class WetsartikelNietGevonden(GraphDbFout):
    """GraphDB antwoordt, maar het artikel staat niet (meer) in de graaf."""


def _artikel_iri(bwb_id: str, artikel: str) -> str:
    """`urn:bwb:{bwb_id}:artikel:{artikel}` — zelfde vorm als `Vocab.by_ref_key` in bwb-import."""
    return "urn:bwb:" + ":".join(quote(s, safe="") for s in (bwb_id, "artikel", artikel))


def _lit(tekst: str) -> str:
    """Veilige SPARQL-stringliteral (poort van de referentie's `queries._lit`)."""
    escaped = tekst.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
    return f'"{escaped}"'


_LEIDEND_NUMMER = re.compile(r"\d+")


def _sorteersleutel(nummer: str | None) -> tuple[int, str]:
    """Numeriek sorteren op een lid-/onderdeelnummer (poort van de referentie's `_lidsleutel`):
    SPARQL's `ORDER BY` op de string is lexicaal (1, 10, 11, 2, …), dit sorteert '10' ná '2'."""
    match = _LEIDEND_NUMMER.search(nummer or "")
    return (int(match.group()) if match else 10**9, nummer or "")


def _waarde(binding: dict, sleutel: str) -> str | None:
    return binding.get(sleutel, {}).get("value")


async def _select(query: str, client: httpx.AsyncClient, *, foutcontext: str) -> list[dict]:
    """POST één SPARQL-SELECT en geef de result-bindings terug. Werpt `GraphDbNietBereikbaar`
    bij netwerk-/HTTP-fouten — geen onderscheid tussen de queries hierboven, ze delen dezelfde
    repository/auth/foutafhandeling."""
    auth = (GRAPHDB_USER, GRAPHDB_PASSWORD) if GRAPHDB_USER else None
    try:
        resp = await client.post(
            f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPOSITORY}",
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            auth=auth,
        )
    except (
        httpx.ConnectError,
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.ProtocolError,
    ) as exc:
        raise GraphDbNietBereikbaar(f"GraphDB niet bereikbaar voor {foutcontext}: {exc}") from exc

    if not resp.is_success:
        raise GraphDbNietBereikbaar(f"GraphDB HTTP {resp.status_code} voor {foutcontext}")
    return resp.json().get("results", {}).get("bindings", [])


def _onderdelen_uit_bindings(
    bindings: list[dict], *, iri_key: str, nummer_key: str, tekst_key: str
) -> list[WetsartikelOnderdeel]:
    """Groepeer rijen tot onderdelen op de IRI-sleutel (elke onderdeel-IRI kan door de
    `heeftOnderdeel+`-property-path meerdere keren voorkomen als er meerdere paden naar dezelfde
    node zijn — ontdubbelen op IRI voorkomt duplicaten in de weergave)."""
    gezien: dict[str, WetsartikelOnderdeel] = {}
    for binding in bindings:
        iri = _waarde(binding, iri_key)
        tekst = _waarde(binding, tekst_key)
        if iri is None or tekst is None or iri in gezien:
            continue
        gezien[iri] = WetsartikelOnderdeel(nummer=_waarde(binding, nummer_key), tekst=tekst)
    return sorted(gezien.values(), key=lambda o: _sorteersleutel(o.nummer))


async def haal_wetsartikel_op(
    bwb_id: str, artikel: str, *, client: httpx.AsyncClient | None = None
) -> Wetsartikel:
    """Haal de tekst van één artikel (+ leden + onderdelen) op uit GraphDB.

    Werpt `GraphDbNietBereikbaar` bij netwerk-/HTTP-fouten en `WetsartikelNietGevonden` als het
    artikel/de bepaling niet (meer) in de graaf staat. `client` is een DI-punt voor tests
    (zelfde patroon als bwb-import's injecteerbare `requests.Session`) — zonder wordt de
    proces-brede, lazily aangemaakte client uit `_get_client()` gebruikt.
    """
    http = client or _get_client()
    iri = _artikel_iri(bwb_id, artikel)
    foutcontext = f"{bwb_id} art. {artikel}"

    bindings = await _select(_QUERY_ARTIKEL.format(iri=iri), http, foutcontext=foutcontext)
    if not bindings:
        return await _haal_bepaling_op(bwb_id, artikel, http, foutcontext=foutcontext)

    leden_volgorde: list[str] = []
    leden_bij_iri: dict[str, dict] = {}
    onderdelen_bindings_per_lid: dict[str, list[dict]] = {}
    for binding in bindings:
        lid_iri = _waarde(binding, "lid")
        if lid_iri is None:
            continue
        if lid_iri not in leden_bij_iri:
            leden_volgorde.append(lid_iri)
            leden_bij_iri[lid_iri] = {
                "nummer": _waarde(binding, "lidNummer"),
                "tekst": _waarde(binding, "lidTekst") or "",
            }
            onderdelen_bindings_per_lid[lid_iri] = []
        onderdelen_bindings_per_lid[lid_iri].append(binding)

    leden = [
        WetsartikelLid(
            nummer=leden_bij_iri[lid_iri]["nummer"],
            tekst=leden_bij_iri[lid_iri]["tekst"],
            onderdelen=_onderdelen_uit_bindings(
                onderdelen_bindings_per_lid[lid_iri],
                iri_key="onderdeel",
                nummer_key="onderdeelNummer",
                tekst_key="onderdeelTekst",
            ),
        )
        for lid_iri in leden_volgorde
    ]
    leden.sort(key=lambda lid: _sorteersleutel(lid.nummer))

    onderdelen: list[WetsartikelOnderdeel] = []
    if not leden:
        onderdelen_bindings = await _select(
            _QUERY_ARTIKEL_ONDERDELEN.format(iri=iri), http, foutcontext=foutcontext
        )
        onderdelen = _onderdelen_uit_bindings(
            onderdelen_bindings,
            iri_key="onderdeel",
            nummer_key="onderdeelNummer",
            tekst_key="onderdeelTekst",
        )

    return Wetsartikel(
        bwb_id=bwb_id,
        artikel=artikel,
        opschrift=_waarde(bindings[0], "opschrift"),
        tekst=_waarde(bindings[0], "tekst") or "",
        onderdelen=onderdelen,
        leden=leden,
    )


async def _haal_bepaling_op(
    bwb_id: str, artikel: str, client: httpx.AsyncClient, *, foutcontext: str
) -> Wetsartikel:
    """Fallback als er geen `bwb:Artikel`-resource op het IRI-patroon bestaat: zoek op
    `bwb:nummer` binnen de regeling (decimale bepalingnummers uit circulaires/beleidsregels)."""
    query = _QUERY_BEPALING.format(nummer=_lit(artikel), basis=_lit(f"urn:bwb:{bwb_id}"))
    bindings = await _select(query, client, foutcontext=foutcontext)
    if not bindings:
        raise WetsartikelNietGevonden(
            f"Artikel {artikel} van {bwb_id} niet gevonden in de kennisgraaf."
        )
    return Wetsartikel(
        bwb_id=bwb_id,
        artikel=artikel,
        opschrift=_waarde(bindings[0], "opschrift"),
        tekst=_waarde(bindings[0], "tekst") or "",
        onderdelen=[],
        leden=[],
    )
