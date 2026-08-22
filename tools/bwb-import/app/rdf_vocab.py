"""Custom RDF-vocabulaire + IRI-schema voor het BWB-model.

Modelleert het BWB-model in RDF: elke entiteit wordt een klasse, elke relatie een predicaat. Eén
`Vocab` bundelt de twee configureerbare namespaces (resources vs. ontologie) en levert
deterministische IRI's.

De artikel-IRI wordt afgeleid van de `ref_key` (JuriConnect-sleutel), zodat een `verwijstNaar`
naar een nog niet geïmporteerde wet naar exact dezelfde IRI wijst — de doel-IRI krijgt vanzelf
inhoud zodra die wet later wordt geïmporteerd (RDF open-world; geen stub-nodes nodig).

Dit is niet een vrij gekozen ontwerp: `graph-qa` (nog te bouwen) verwacht ditzelfde IRI-schema
(provenance-detectie prefixt op de documentbasis `urn:bwb:`) — zie
docs/project/stories/027-bwb-import-graphdb-writer.md.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import quote

from rdflib import XSD, Literal, Namespace, URIRef

# Bewust een URN en geen http-IRI: een domeinnaam in het datamodel bindt de data aan wie dat
# domein toevallig bezit, en verhuizen kost dan een herimport van alles. Elke citeerbare node
# krijgt een `owl:sameAs` naar WETTEN_BASE — dát is de publieke, klikbare vindplaats.
DEFAULT_BASE_IRI = "urn:bwb:"
# De vocabulaireruimte moet **disjunct** zijn van de documentruimte (niet `urn:bwb:ns:`), anders
# herkent graph-qa's provenance-detectie (die op de documentbasis prefixt) elk predicaat als
# vindplaats.
DEFAULT_ONTOLOGY_IRI = "urn:bwb-ns:"

WETTEN_BASE = "https://wetten.overheid.nl/"

_BWB_ID = re.compile(r"BWB[RV]\d+")

# Node-prop-sleutels die niet als literal worden weggeschreven (zitten in de IRI of intern).
# `label_id` is de WTI-join-sleutel (story 030): puur intern voor het opbouwen van de
# label_id->IRI-map tijdens het schrijven, geen zinvolle data op zichzelf zodra de WTI-relaties
# als eigen predicaten (grondslagVoor/bevoegdheidVoor/verwijzingDoor) gematerialiseerd zijn.
_SKIP_PROPS = {"id", "ref_key", "jci", "label_id"}

_PROP_DATATYPES: dict[str, URIRef] = {
    "geldig_vanaf": XSD.date,
    "geldig_tot": XSD.date,
}

_PROP_TAAL_NL = {"tekst", "titel", "opschrift", "citeertitel"}

_ISO_DATUM = re.compile(r"\d{4}-\d{2}-\d{2}")


def _camel(snake: str) -> str:
    """`heeft_artikel` / `geldig_vanaf` -> camelCase."""
    delen = snake.lower().split("_")
    return delen[0] + "".join(p.capitalize() for p in delen[1:])


@dataclass(frozen=True)
class Vocab:
    """IRI-fabriek + termen voor één configuratie van namespaces."""

    base: str = DEFAULT_BASE_IRI
    ontology: str = DEFAULT_ONTOLOGY_IRI

    @property
    def ns(self) -> Namespace:
        return Namespace(self.ontology)

    @property
    def _sep(self) -> str:
        """URN-ruimtes scheiden hun segmenten met `:`, http-IRI's met `/`."""
        return ":" if self.base.startswith("urn:") else "/"

    def _iri(self, *segmenten: str) -> URIRef:
        """Samengestelde IRI onder de basis; elk segment volledig ge-escaped (`safe=''` is
        wezenlijk: bij een URN moet een `:` in een waarde percent-escaped worden, anders leest
        hij als een extra segment)."""
        return URIRef(self.base + self._sep.join(quote(s, safe="") for s in segmenten))

    # ------------------------------------------------------------- resource-IRI's
    def wet(self, bwb_id: str) -> URIRef:
        return self._iri(bwb_id)

    def graph(self, bwb_id: str) -> URIRef:
        """Named-graph-IRI voor één wet (idempotente re-import per graaf)."""
        return self._iri("graph", bwb_id)

    def ontology_graph(self) -> URIRef:
        return self._iri("graph", "ontologie")

    @property
    def ontology_resource(self) -> URIRef:
        return URIRef(self.ontology.rstrip("#/:"))

    def canonieke_url(self, ref_key: str) -> URIRef | None:
        """Canonieke wetten.overheid.nl-URL voor een ref_key (`owl:sameAs`-doel).

        `{bwb}`                 -> `{WETTEN_BASE}{bwb}`
        `{bwb}#artikel={nr}[…]` -> `{WETTEN_BASE}jci1.3:c:{bwb}&artikel={nr}[…]`
        `{bwb}#id={id}`         -> `None` (geen jci-adresseerbare vorm).
        """
        bwb, _, rest = ref_key.partition("#")
        if not _BWB_ID.fullmatch(bwb):
            return None
        if not rest:
            return URIRef(f"{WETTEN_BASE}{bwb}")
        delen: list[str] = []
        for segment in rest.split("#"):
            sleutel, _, waarde = segment.partition("=")
            if sleutel == "id" or not waarde:
                return None
            delen.append(f"&{sleutel}={quote(waarde, safe=':.')}")
        return URIRef(f"{WETTEN_BASE}jci1.3:c:{bwb}{''.join(delen)}")

    def by_id(self, bwb_id: str, xml_id: str) -> URIRef:
        """IRI voor een niet-citeerbare node (hoofdstuk/afdeling/lid/onderdeel zonder jci)."""
        return self._iri(bwb_id, "id", xml_id)

    def by_ref_key(self, ref_key: str) -> URIRef:
        """IRI voor een citeerbare node/verwijs-doel, afgeleid van de ref_key.

        `{bwb}`               -> `BASE{bwb}` (de wet zelf)
        `{bwb}#artikel={nr}`  -> `BASE{bwb}:artikel:{nr}`
        `{bwb}#id={id}`       -> `BASE{bwb}:id:{id}`
        (valt terug op een gehashte IRI als het formaat onbekend is).
        """
        bwb, _, rest = ref_key.partition("#")
        if bwb and not rest:
            return self.wet(bwb)
        segmenten: list[str] = []
        for segment in rest.split("#"):
            sleutel, _, waarde = segment.partition("=")
            if not bwb or not sleutel or not waarde:
                digest = hashlib.sha1(ref_key.encode("utf-8")).hexdigest()[:16]
                return self._iri("ref", digest)
            segmenten.extend((sleutel, waarde))
        return self._iri(bwb, *segmenten)

    def begrip(self, label: str) -> URIRef:
        """IRI voor een thesaurusterm (rechtsgebied/overheidsdomein uit de WTI) op slug."""
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        return self._iri("begrip", slug)

    def entiteit(self, soort: str, sleutel: str) -> URIRef:
        """Deterministische, wet-overstijgende IRI voor een gedeelde entiteit (bv. de
        WTI-verantwoordelijke organisatie) op slug.

        Zo valt dezelfde organisatie over wetten heen samen tot één node (open-world; elke
        wet-graaf her-assert de node, net als thesaurustermen).
        """
        slug = re.sub(r"[^a-z0-9]+", "-", sleutel.lower()).strip("-")
        return self._iri(soort, slug)

    def verwijzing(self, bron: URIRef, doel: URIRef, soort: str) -> URIRef:
        """Deterministische IRI voor de tussenresource van één verwijzing."""
        sleutel = f"{bron}|{doel}|{soort}".encode()
        digest = hashlib.sha1(sleutel).hexdigest()[:16]
        return self._iri("verwijzing", digest)

    # ---------------------------------------------------------------------- termen
    def klasse(self, entiteit: str) -> URIRef:
        return self.ns[entiteit]

    def predicaat_rel(self, rel_type: str) -> URIRef:
        """`HEEFT_ARTIKEL` -> `bwb:heeftArtikel`."""
        return self.ns[_camel(rel_type)]

    def predicaat_prop(self, prop_key: str) -> URIRef:
        """`bwb_id` -> `bwb:bwbId`, `geldig_vanaf` -> `bwb:geldigVanaf`."""
        return self.ns[_camel(prop_key)]

    @staticmethod
    def skip_prop(prop_key: str) -> bool:
        return prop_key in _SKIP_PROPS

    # -------------------------------------------------------------------- literals
    @staticmethod
    def literal(prop_key: str, value: object) -> Literal:
        """Getypeerde literal voor een prop: `xsd:date` waar dat kan, `@nl` op
        Nederlandstalige tekst, anders platte string."""
        tekst = str(value)
        datatype = _PROP_DATATYPES.get(prop_key)
        if datatype == XSD.date and _ISO_DATUM.fullmatch(tekst):
            return Literal(tekst, datatype=XSD.date)
        if prop_key in _PROP_TAAL_NL:
            return Literal(tekst, lang="nl")
        return Literal(tekst)
