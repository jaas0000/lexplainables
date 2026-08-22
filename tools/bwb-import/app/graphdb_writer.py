"""Wegschrijven van het BWB-model naar GraphDB (RDF/SPARQL).

Consumeert de `Batch` (app/collect.py) en vertaalt die naar triples volgens het custom
vocabulaire (app/rdf_vocab.py). Elke wet komt in een eigen named graph; bij (her)import wordt die
graaf integraal vervangen (RDF4J Graph Store PUT) → idempotent.

Cross-referenties (`verwijstNaar`) wijzen naar de ref_key-afgeleide doel-IRI. Die doel-IRI hoeft
nog niet te bestaan: RDF is open-world, dus de node krijgt vanzelf inhoud zodra de doelwet later
wordt geïmporteerd.

WTI-verrijking en de Lucene-FTS-connector zijn nog niet gebouwd — zie
docs/project/stories/027-bwb-import-graphdb-writer.md §Buiten scope.
"""

from __future__ import annotations

import logging

import requests
from rdflib import OWL, RDF, RDFS, Graph, Literal, URIRef

from app.collect import collect
from app.models import ImportSummary, Wet
from app.ontology import build_ontology
from app.rdf_vocab import Vocab

logger = logging.getLogger(__name__)

_STRUCTUUR = {"Hoofdstuk", "Titeldeel", "Afdeling", "Paragraaf"}

# bwb:soort (letterlijke bronwaarde) -> subklasse van bwb:Regeling. Onbekende soorten krijgen
# alleen het generieke type bwb:Regeling.
_SOORT_KLASSE = {
    "wet": "Wet",
    "AMvB": "AMvB",
    "KB": "KoninklijkBesluit",
    "ministeriele-regeling": "MinisterieleRegeling",
    "beleidsregel": "Beleidsregel",
    "circulaire": "Circulaire",
}

_REPO_CONFIG_TTL = """\
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix rep: <http://www.openrdf.org/config/repository#>.
@prefix sr: <http://www.openrdf.org/config/repository/sail#>.
@prefix sail: <http://www.openrdf.org/config/sail#>.
@prefix graphdb: <http://www.ontotext.com/config/graphdb#>.

[] a rep:Repository ;
    rep:repositoryID "{repo}" ;
    rdfs:label "{repo}" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        sr:sailImpl [
            sail:sailType "graphdb:Sail" ;
            graphdb:ruleset "rdfsplus-optimized" ;
            graphdb:base-URL "http://example.org/{repo}#" ;
            graphdb:repository-type "file-repository" ;
            graphdb:storage-folder "storage" ;
            graphdb:enable-context-index "true" ;
            graphdb:enablePredicateList "true" ;
            graphdb:enable-literal-index "true" ;
        ]
    ].
"""


def _rdfs_label(entiteit: str, props: dict) -> str:
    """Leesbaar label per node (voor GraphDB's Visual Graph)."""
    nummer = props.get("nummer")
    if entiteit == "Regeling":
        return (
            props.get("citeertitel") or props.get("opschrift") or props.get("bwb_id") or "Regeling"
        )
    if entiteit in _STRUCTUUR:
        basis = props.get("label") or entiteit
        if nummer:
            basis = f"{basis} {nummer}"
        titel = props.get("titel")
        return f"{basis} — {titel}" if titel else basis
    if entiteit == "Artikel":
        return props.get("label") or (f"Artikel {nummer}" if nummer else "Artikel")
    if entiteit == "Lid":
        return f"Lid {nummer}" if nummer else "Lid"
    if entiteit == "Onderdeel":
        return f"Onderdeel {nummer}" if nummer else "Onderdeel"
    return props.get("label") or props.get("titel") or entiteit


def _doel_label(row: dict) -> str | None:
    """Leesbaar fallback-label voor een (nog) niet-geïmporteerd verwijsdoel."""
    soort, bwb = row.get("doel_soort"), row.get("to_bwb")
    if not bwb:
        return None
    if soort == "wet":
        return bwb
    return f"{soort} ({bwb})" if soort else bwb


class GraphDbWriter:
    """Schrijft een `Wet` als RDF naar een GraphDB-repository."""

    def __init__(
        self,
        *,
        url: str,
        repository: str,
        vocab: Vocab,
        user: str | None = None,
        password: str | None = None,
        session: requests.Session | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._repo = repository
        self._vocab = vocab
        self._auth = (user, password) if user else None
        self._http = session or requests.Session()
        self._timeout = timeout

    @property
    def _statements(self) -> str:
        return f"{self._url}/repositories/{self._repo}/statements"

    @property
    def _graph_store(self) -> str:
        return f"{self._url}/repositories/{self._repo}/rdf-graphs/service"

    def ensure_constraints(self) -> None:
        """Zorg dat de repository bestaat (maak 'm anders aan)."""
        resp = self._http.get(
            f"{self._url}/rest/repositories", auth=self._auth, timeout=self._timeout
        )
        resp.raise_for_status()
        bestaand = {r.get("id") for r in resp.json()}
        if self._repo in bestaand:
            logger.info("GraphDB-repository %s bestaat al", self._repo)
            return
        config = _REPO_CONFIG_TTL.format(repo=self._repo)
        create = self._http.post(
            f"{self._url}/rest/repositories",
            files={"config": (f"{self._repo}.ttl", config, "text/turtle")},
            auth=self._auth,
            timeout=self._timeout,
        )
        create.raise_for_status()
        logger.info("GraphDB-repository %s aangemaakt", self._repo)

    def build_graph(self, wet: Wet) -> tuple[Graph, ImportSummary]:
        """Bouw de RDF-graaf voor één wet uit de `Batch` (geen HTTP)."""
        batch, summary = collect(wet)
        v = self._vocab
        g = Graph()
        g.bind("bwb", v.ns)

        # 1) Nodes -> klassen + literals; onthoud id -> IRI voor de relaties.
        iri_by_id: dict[str, URIRef] = {}
        for entiteit, rows in batch.nodes.items():
            klasse = v.klasse(entiteit)
            for row in rows:
                ref_key = row.get("ref_key")
                iri = v.by_ref_key(ref_key) if ref_key else v.by_id(wet.bwb_id, row["id"])
                iri_by_id[row["id"]] = iri
                g.add((iri, RDF.type, klasse))
                if entiteit == "Regeling":
                    subklasse = _SOORT_KLASSE.get(row.get("soort") or "")
                    if subklasse:
                        g.add((iri, RDF.type, v.klasse(subklasse)))
                if ref_key:
                    g.add((iri, RDF.type, v.klasse("Citeerbaar")))
                    canoniek = v.canonieke_url(ref_key)
                    if canoniek is not None:
                        g.add((iri, OWL.sameAs, canoniek))
                g.add((iri, RDFS.label, Literal(_rdfs_label(entiteit, row), lang="nl")))
                for key, value in row.items():
                    if v.skip_prop(key) or value is None or value == "":
                        continue
                    g.add((iri, v.predicaat_prop(key), v.literal(key, value)))

        # 2) Structuur- en volgrelaties.
        for (_src, rel_type, _dst), rows in batch.rels.items():
            pred = v.predicaat_rel(rel_type)
            for row in rows:
                a, b = iri_by_id.get(row["from"]), iri_by_id.get(row["to"])
                if a is None or b is None:
                    continue
                g.add((a, pred, b))
            summary.relaties += len(rows)

        # 3) Verwijzingen: directe edge + tussenresource met doel-metadata.
        node_iris = set(iri_by_id.values())
        for row in batch.verwijzingen:
            bron = v.by_ref_key(row["from"])
            doel = v.by_ref_key(row["to"])
            label = _doel_label(row) if doel not in node_iris else None
            if label:
                g.add((doel, RDFS.label, Literal(label, lang="nl")))
            g.add((bron, v.ns.verwijstNaar, doel))
            vw = v.verwijzing(bron, doel, row["soort"])
            g.add((bron, v.ns.heeftVerwijzing, vw))
            g.add((vw, RDF.type, v.klasse("Verwijzing")))
            g.add((vw, v.ns.naar, doel))
            g.add((vw, v.ns.soort, Literal(row["soort"])))
            for key, prop in (
                ("doc", v.ns.doc),
                ("doel_pad", v.ns.doelPad),
                ("verwijzing_id", v.ns.verwijzingId),
            ):
                if row.get(key):
                    g.add((vw, prop, Literal(row[key])))
            if row.get("anker_tekst"):
                g.add((vw, v.ns.ankerTekst, Literal(row["anker_tekst"], lang="nl")))
            summary.relaties += 1

        return g, summary

    def write_ontology(self) -> None:
        """Vervang de ontologie-graaf (T-Box) in GraphDB (PUT = idempotent)."""
        graph = build_ontology(self._vocab)
        self._put_graph(self._vocab.ontology_graph(), graph)
        logger.info("Ontologie naar GraphDB geschreven (%d triples)", len(graph))

    def _put_graph(self, graph_iri: URIRef, graph: Graph) -> None:
        """RDF4J Graph Store PUT: vervang één named graph integraal."""
        resp = self._http.put(
            self._graph_store,
            params={"graph": str(graph_iri)},
            data=graph.serialize(format="turtle").encode("utf-8"),
            headers={"Content-Type": "text/turtle"},
            auth=self._auth,
            timeout=self._timeout,
        )
        resp.raise_for_status()

    def write_wet(self, wet: Wet) -> ImportSummary:
        """Bouw de graaf en vervang de named graph van deze wet in GraphDB."""
        graph, summary = self.build_graph(wet)
        self._put_graph(self._vocab.graph(wet.bwb_id), graph)
        logger.info("Wet %s naar GraphDB geschreven: %s", wet.bwb_id, summary.as_dict())
        return summary
