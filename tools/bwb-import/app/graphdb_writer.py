"""Wegschrijven van het BWB-model naar GraphDB (RDF/SPARQL).

Consumeert de `Batch` (app/collect.py) en vertaalt die naar triples volgens het custom
vocabulaire (app/rdf_vocab.py). Elke wet komt in een eigen named graph; bij (her)import wordt die
graaf integraal vervangen (RDF4J Graph Store PUT) → idempotent.

Cross-referenties (`verwijstNaar`) wijzen naar de ref_key-afgeleide doel-IRI. Die doel-IRI hoeft
nog niet te bestaan: RDF is open-world, dus de node krijgt vanzelf inhoud zodra de doelwet later
wordt geïmporteerd.

WTI-verrijking (story 030) en wet-brondata/ondertekenaars (story 032) schrijven mee in dezelfde
named graph als de wet, dus worden atomair mee-vervangen bij her-import. De Lucene-FTS-connector
is nog niet gebouwd — zie docs/project/stories/027-bwb-import-graphdb-writer.md §Buiten scope.
"""

from __future__ import annotations

import logging

import requests
from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef

from app.collect import collect
from app.models import ImportSummary, Ondertekenaar, Wet
from app.ontology import build_ontology
from app.rdf_vocab import Vocab
from app.wti_parser import WtiInfo

DCTERMS = Namespace("http://purl.org/dc/terms/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

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

    def build_graph(self, wet: Wet, wti: WtiInfo | None = None) -> tuple[Graph, ImportSummary]:
        """Bouw de RDF-graaf voor één wet uit de `Batch` (geen HTTP)."""
        batch, summary = collect(wet)
        v = self._vocab
        g = Graph()
        g.bind("bwb", v.ns)
        g.bind("dcterms", DCTERMS)
        g.bind("skos", SKOS)

        # 1) Nodes -> klassen + literals; onthoud id -> IRI voor de relaties.
        iri_by_id: dict[str, URIRef] = {}
        # label-id -> IRI, voor het koppelen van WTI-regelingelementen aan hun node.
        label_iri: dict[str, URIRef] = {}
        for entiteit, rows in batch.nodes.items():
            klasse = v.klasse(entiteit)
            for row in rows:
                ref_key = row.get("ref_key")
                iri = v.by_ref_key(ref_key) if ref_key else v.by_id(wet.bwb_id, row["id"])
                iri_by_id[row["id"]] = iri
                if row.get("label_id"):
                    label_iri[row["label_id"]] = iri
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

        # WTI-verrijking (citeertitels, thesaurustermen, grondslagen) — in dezelfde named graph,
        # dus atomair mee-vervangen bij her-import.
        if wti is not None:
            self._wti_verrijking(g, v.wet(wet.bwb_id), wti)
            self._wti_element_relaties(g, label_iri, wti)

        # Toestand-identiteit (versie) op wetten.overheid.nl: ander FRBR-niveau dan de wet zelf,
        # dus een eigen property i.p.v. owl:sameAs.
        if wet.vast_deel_url:
            g.add((v.wet(wet.bwb_id), v.ns.toestandUrl, URIRef(wet.vast_deel_url)))

        self._ondertekenaars(g, v.wet(wet.bwb_id), wet.ondertekenaars)

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

    def _wti_verrijking(self, g: Graph, wet_iri: URIRef, wti: WtiInfo) -> None:
        """WTI-triples op de wet-node: titels, thesaurustermen, grondslagen."""
        v = self._vocab
        for titel in wti.citeertitels:
            g.add((wet_iri, v.ns.citeertitel, Literal(titel, lang="nl")))
        for titel in wti.niet_officiele_titels:
            g.add((wet_iri, v.ns.alternatieveTitel, Literal(titel, lang="nl")))
        for afkorting in wti.afkortingen:
            g.add((wet_iri, v.ns.afkorting, Literal(afkorting)))
        if wti.eerstverantwoordelijke:
            g.add((wet_iri, v.ns.eerstverantwoordelijke, Literal(wti.eerstverantwoordelijke)))
        if wti.authority:
            # Verantwoordelijke organisatie als wet-overstijgende node (dezelfde organisatie
            # valt over regelingen heen samen op de slug-IRI).
            org = v.entiteit("organisatie", wti.authority)
            g.add((org, RDF.type, v.klasse("Organisatie")))
            g.add((org, RDFS.label, Literal(wti.authority, lang="nl")))
            g.add((org, v.ns.naam, Literal(wti.authority, lang="nl")))
            g.add((wet_iri, v.ns.uitgegevenDoor, org))
        for bwb_id in wti.wetsfamilie:
            g.add((wet_iri, v.ns.inFamilie, v.wet(bwb_id)))
        for hoofd, specifiek in wti.rechtsgebieden:
            hoofd_iri = self._begrip(g, hoofd)
            g.add((wet_iri, DCTERMS.subject, hoofd_iri))
            if specifiek:
                specifiek_iri = self._begrip(g, specifiek)
                g.add((specifiek_iri, SKOS.broader, hoofd_iri))
                g.add((wet_iri, DCTERMS.subject, specifiek_iri))
        for domein in wti.overheidsdomeinen:
            g.add((wet_iri, DCTERMS.subject, self._begrip(g, domein)))
        for bwb_id in wti.grondslagen:
            g.add((wet_iri, v.ns.heeftGrondslag, v.wet(bwb_id)))

    def _wti_element_relaties(self, g: Graph, label_iri: dict[str, URIRef], wti: WtiInfo) -> None:
        """Per-regelingelement uitgaande relaties uit de WTI: koppel het tekstdeel (via
        `label-id`) aan de regelingen waarvoor het grondslag/bevoegdheid is, of die ernaar
        verwijzen. Doelen zijn open-world wet-IRI's."""
        v = self._vocab
        for label_id, rel in wti.element_relaties.items():
            bron = label_iri.get(label_id)
            if bron is None:
                continue  # geen node met dit label-id in deze wet
            for pred, bwb_ids in (
                (v.ns.grondslagVoor, rel.grondslag_voor),
                (v.ns.bevoegdheidVoor, rel.bevoegdheid_voor),
                (v.ns.verwijzingDoor, rel.verwijzing_door),
            ):
                for bwb_id in bwb_ids:
                    g.add((bron, pred, v.wet(bwb_id)))

    def _begrip(self, g: Graph, label: str) -> URIRef:
        """skos:Concept voor een thesaurusterm; convergeert open-world op slug-IRI."""
        iri = self._vocab.begrip(label)
        g.add((iri, RDF.type, SKOS.Concept))
        g.add((iri, SKOS.prefLabel, Literal(label, lang="nl")))
        g.add((iri, RDFS.label, Literal(label, lang="nl")))
        return iri

    def _ondertekenaars(
        self, g: Graph, wet_iri: URIRef, ondertekenaars: list[Ondertekenaar]
    ) -> None:
        """Ondertekenaars als wet-overstijgende nodes (dezelfde persoon valt over regelingen
        heen samen op de slug-IRI, zelfde open-world-patroon als de WTI-Organisatie-node)."""
        v = self._vocab
        for ondt in ondertekenaars:
            sleutel = f"{ondt.functie or ''}|{ondt.naam or ''}"
            iri = v.entiteit("ondertekenaar", sleutel)
            g.add((iri, RDF.type, v.klasse("Ondertekenaar")))
            label = ondt.naam or ondt.functie or "Ondertekenaar"
            g.add((iri, RDFS.label, Literal(label, lang="nl")))
            for prop, value in (
                (v.ns.naam, ondt.naam),
                (v.ns.functie, ondt.functie),
                (v.ns.voornaam, ondt.voornaam),
                (v.ns.achternaam, ondt.achternaam),
                (v.ns.plaats, ondt.plaats),
            ):
                if value:
                    g.add((iri, prop, Literal(value, lang="nl")))
            g.add((wet_iri, v.ns.ondertekendDoor, iri))

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

    def write_wet(self, wet: Wet, wti: WtiInfo | None = None) -> ImportSummary:
        """Bouw de graaf en vervang de named graph van deze wet in GraphDB."""
        graph, summary = self.build_graph(wet, wti=wti)
        self._put_graph(self._vocab.graph(wet.bwb_id), graph)
        logger.info("Wet %s naar GraphDB geschreven: %s", wet.bwb_id, summary.as_dict())
        return summary
