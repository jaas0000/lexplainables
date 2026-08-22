"""SPARQL-leesclient voor wetsartikeltekst (story 037).

Vraagt rechtstreeks de artikeltekst (+ leden) op bij GraphDB voor de werkplek-detailpagina.
Geen import van `tools/bwb-import` (ADR-0002 — geen gedeelde import over een servicegrens): de
artikel-IRI wordt hier zelf opgebouwd, volgens exact hetzelfde schema als
`tools/bwb-import/app/rdf_vocab.py::Vocab.by_ref_key`/`_iri` (canonieke vorm
`urn:bwb:{bwb_id}:artikel:{artikelnummer}`, URN-segmenten `:`-gescheiden, elk segment
percent-encoded). Wijzigt dat schema daar, dan moet het hier mee veranderen.

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
from pathlib import Path
from urllib.parse import quote

import httpx

from .models import Wetsartikel, WetsartikelLid

GRAPHDB_URL = os.environ.get("GRAPHDB_URL", "http://graphdb:7200")
GRAPHDB_REPOSITORY = os.environ.get("GRAPHDB_REPOSITORY", "inning")
GRAPHDB_USER = os.environ.get("GRAPHDB_USER") or None

_TIMEOUT = 15.0

_QUERY_TEMPLATE = """
PREFIX bwb: <urn:bwb-ns:>
SELECT ?opschrift ?tekst ?lidNummer ?lidTekst WHERE {{
  GRAPH ?g {{
    <{iri}> a bwb:Artikel .
    OPTIONAL {{ <{iri}> bwb:tekst ?tekst }}
    OPTIONAL {{ <{iri}> bwb:opschrift ?opschrift }}
    OPTIONAL {{
      <{iri}> bwb:heeftLid ?lid .
      ?lid bwb:tekst ?lidTekst .
      OPTIONAL {{ ?lid bwb:nummer ?lidNummer }}
    }}
  }}
}}
"""


class GraphDbFout(RuntimeError):
    """Ophalen mislukte — geen bruikbare wetsartikeltekst."""


class GraphDbNietBereikbaar(GraphDbFout):
    """Netwerk-/HTTP-fout — GraphDB zelf antwoordt niet."""


class WetsartikelNietGevonden(GraphDbFout):
    """GraphDB antwoordt, maar het artikel staat niet (meer) in de graaf."""


def _graphdb_password() -> str | None:
    pad = os.environ.get("GRAPHDB_PASSWORD_FILE")
    if pad is None:
        return None
    return Path(pad).read_text(encoding="utf-8").strip()


def _artikel_iri(bwb_id: str, artikel: str) -> str:
    """`urn:bwb:{bwb_id}:artikel:{artikel}` — zelfde vorm als `Vocab.by_ref_key` in bwb-import."""
    return "urn:bwb:" + ":".join(quote(s, safe="") for s in (bwb_id, "artikel", artikel))


def _waarde(binding: dict, sleutel: str) -> str | None:
    return binding.get(sleutel, {}).get("value")


async def haal_wetsartikel_op(
    bwb_id: str, artikel: str, *, client: httpx.AsyncClient | None = None
) -> Wetsartikel:
    """Haal de tekst van één artikel (+ leden) op uit GraphDB.

    Werpt `GraphDbNietBereikbaar` bij netwerk-/HTTP-fouten en `WetsartikelNietGevonden` als het
    artikel niet (meer) in de graaf staat. `client` is een DI-punt voor tests (zelfde patroon
    als bwb-import's injecteerbare `requests.Session`) — zonder wordt een kortlevende
    `httpx.AsyncClient` gebruikt.
    """
    iri = _artikel_iri(bwb_id, artikel)
    query = _QUERY_TEMPLATE.format(iri=iri)
    auth = (GRAPHDB_USER, _graphdb_password()) if GRAPHDB_USER else None

    eigen_client = client is None
    http = client or httpx.AsyncClient(timeout=_TIMEOUT)
    try:
        resp = await http.post(
            f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPOSITORY}",
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            auth=auth,
        )
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
        raise GraphDbNietBereikbaar(
            f"GraphDB niet bereikbaar voor {bwb_id} art. {artikel}: {exc}"
        ) from exc
    finally:
        if eigen_client:
            await http.aclose()

    if not resp.is_success:
        raise GraphDbNietBereikbaar(f"GraphDB HTTP {resp.status_code} voor {bwb_id} art. {artikel}")

    bindings = resp.json().get("results", {}).get("bindings", [])
    if not bindings:
        raise WetsartikelNietGevonden(
            f"Artikel {artikel} van {bwb_id} niet gevonden in de kennisgraaf."
        )

    leden: list[WetsartikelLid] = []
    for binding in bindings:
        lid_tekst = _waarde(binding, "lidTekst")
        if lid_tekst is None:
            continue
        leden.append(WetsartikelLid(nummer=_waarde(binding, "lidNummer"), tekst=lid_tekst))

    return Wetsartikel(
        bwb_id=bwb_id,
        artikel=artikel,
        opschrift=_waarde(bindings[0], "opschrift"),
        tekst=_waarde(bindings[0], "tekst") or "",
        leden=leden,
    )
