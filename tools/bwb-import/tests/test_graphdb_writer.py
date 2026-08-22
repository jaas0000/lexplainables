from __future__ import annotations

import os
from pathlib import Path

import pytest
from rdflib import OWL, RDF, RDFS, URIRef

from app.graphdb_writer import GraphDbWriter
from app.models import Artikel, Bijlage, Illustratie, Lid, Ondertekenaar, Wet
from app.parser import ToestandParser
from app.rdf_vocab import Vocab

FIXTURE = Path(__file__).parent / "fixtures" / "sample_toestand.xml"


def _writer() -> GraphDbWriter:
    return GraphDbWriter(url="http://localhost:7200", repository="inning", vocab=Vocab())


def test_build_graph_regeling_triples() -> None:
    wet = ToestandParser().parse(FIXTURE)
    g, summary = _writer().build_graph(wet)

    wet_iri = URIRef("urn:bwb:BWBR0004770")
    labels = list(g.objects(wet_iri, RDFS.label))
    assert str(labels[0]) == "Invorderingswet 1990"
    assert (wet_iri, OWL.sameAs, URIRef("https://wetten.overheid.nl/BWBR0004770")) in g
    assert summary.artikelen == 2


def test_build_graph_artikel_iri_uit_jci_ref_key() -> None:
    wet = ToestandParser().parse(FIXTURE)
    g, _ = _writer().build_graph(wet)

    artikel1 = URIRef("urn:bwb:BWBR0004770:artikel:1")
    assert (artikel1, RDF.type, URIRef("urn:bwb-ns:Artikel")) in g
    assert (artikel1, RDF.type, URIRef("urn:bwb-ns:Citeerbaar")) in g


def test_build_graph_structuurrelatie() -> None:
    wet = ToestandParser().parse(FIXTURE)
    g, _ = _writer().build_graph(wet)

    hoofdstuk_pred = URIRef("urn:bwb-ns:heeftHoofdstuk")
    artikel_pred = URIRef("urn:bwb-ns:heeftArtikel")
    assert (URIRef("urn:bwb:BWBR0004770"), hoofdstuk_pred, None) in g
    hoofdstukken = list(g.objects(URIRef("urn:bwb:BWBR0004770"), hoofdstuk_pred))
    assert len(hoofdstukken) == 1
    artikelen = list(g.objects(hoofdstukken[0], artikel_pred))
    assert len(artikelen) == 2


def test_build_graph_verwijzing_naar_niet_geimporteerde_wet() -> None:
    wet = ToestandParser().parse(FIXTURE)
    g, summary = _writer().build_graph(wet)

    lid2 = URIRef("urn:bwb:BWBR0004770:artikel:1:lid:2")
    doel = URIRef("urn:bwb:BWBR0005537:artikel:3%3A40")
    verwijst_naar = URIRef("urn:bwb-ns:verwijstNaar")
    assert (lid2, verwijst_naar, doel) in g
    # Het doel bestaat nog niet als eigen node (open-world), maar krijgt wel een leesbaar label.
    assert (doel, RDFS.label, None) in g
    assert summary.relaties > 0


def test_build_graph_verwijzing_naar_wet_zonder_artikel() -> None:
    """Een jci-doc zonder &artikel= (bv. titeldeel) valt terug op het wet-niveau."""
    wet = ToestandParser().parse(FIXTURE)
    g, _ = _writer().build_graph(wet)

    lid2 = URIRef("urn:bwb:BWBR0004770:artikel:1:lid:2")
    verwijst_naar = URIRef("urn:bwb-ns:verwijstNaar")
    assert (lid2, verwijst_naar, URIRef("urn:bwb:BWBR0005537")) in g


def test_build_graph_artikel_zonder_jci_valt_terug_op_id() -> None:
    """Zonder jci krijgt een artikel nog steeds een ref_key (id-fallback, zie collect.py), dus
    nog steeds een Citeerbaar-type en een by_ref_key-IRI — alleen zonder owl:sameAs (het
    `#id=`-formaat is niet jci-adresseerbaar, zie Vocab.canonieke_url)."""
    wet = Wet(
        bwb_id="BWBR9999",
        citeertitel="Test",
        opschrift="Test",
        soort="wet",
        losse_artikelen=[
            Artikel(
                id="BWBR9999/Art1",
                nummer="1",
                label="Artikel 1",
                tekst="tekst",
                leden=[Lid(id="BWBR9999/Art1/Lid1", nummer="1", tekst="lid-tekst")],
            )
        ],
    )
    g, _ = _writer().build_graph(wet)

    artikel_iri = URIRef("urn:bwb:BWBR9999:id:BWBR9999%2FArt1")
    assert (artikel_iri, RDF.type, URIRef("urn:bwb-ns:Artikel")) in g
    assert (artikel_iri, RDF.type, URIRef("urn:bwb-ns:Citeerbaar")) in g
    assert (artikel_iri, OWL.sameAs, None) not in g


def test_build_graph_onderdeel_zonder_nummer_geen_ref_key() -> None:
    """Het enige geval waarin een node écht geen ref_key krijgt: een onderdeel zonder nummer."""
    from app.models import Onderdeel

    wet = Wet(
        bwb_id="BWBR9999",
        citeertitel="Test",
        opschrift="Test",
        soort="wet",
        losse_artikelen=[
            Artikel(
                id="BWBR9999/Art1",
                nummer="1",
                label="Artikel 1",
                tekst="",
                onderdelen=[Onderdeel(id="BWBR9999/Art1/O1", nummer="", tekst="een punt")],
            )
        ],
    )
    g, _ = _writer().build_graph(wet)

    onderdeel_iri = URIRef("urn:bwb:BWBR9999:id:BWBR9999%2FArt1%2FO1")
    assert (onderdeel_iri, RDF.type, URIRef("urn:bwb-ns:Onderdeel")) in g
    assert (onderdeel_iri, RDF.type, URIRef("urn:bwb-ns:Citeerbaar")) not in g


def test_build_graph_toestand_url_en_brondata_uit_fixture() -> None:
    wet = ToestandParser().parse(FIXTURE)
    g, _ = _writer().build_graph(wet)

    wet_iri = URIRef("urn:bwb:BWBR0004770")
    toestand_url = URIRef("http://wetten.overheid.nl/id/BWBR0004770/2026-01-01/0")
    assert (wet_iri, URIRef("urn:bwb-ns:toestandUrl"), toestand_url) in g
    assert (wet_iri, URIRef("urn:bwb-ns:publicatiejaar"), None) in g
    assert (wet_iri, URIRef("urn:bwb-ns:dossier"), None) in g


def test_build_graph_zonder_vast_deel_url_geen_toestand_url_triple() -> None:
    wet = Wet(bwb_id="BWBR9999", citeertitel="Test", opschrift="Test", soort="wet")
    g, _ = _writer().build_graph(wet)

    assert (None, URIRef("urn:bwb-ns:toestandUrl"), None) not in g


def test_build_graph_ondertekenaar_node_en_relatie() -> None:
    wet = Wet(
        bwb_id="BWBR9999",
        citeertitel="Test",
        opschrift="Test",
        soort="wet",
        ondertekenaars=[Ondertekenaar(functie="De Minister", achternaam="Jansen")],
    )
    g, _ = _writer().build_graph(wet)

    wet_iri = URIRef("urn:bwb:BWBR9999")
    ondertekend_door = URIRef("urn:bwb-ns:ondertekendDoor")
    doelen = list(g.objects(wet_iri, ondertekend_door))
    assert len(doelen) == 1
    ondt_iri = doelen[0]
    assert (ondt_iri, RDF.type, URIRef("urn:bwb-ns:Ondertekenaar")) in g
    assert (ondt_iri, URIRef("urn:bwb-ns:functie"), None) in g


def test_build_graph_ondertekenaar_dedupliceert_over_wetten() -> None:
    """Dezelfde ondertekenaar in twee wetten valt open-world samen op één IRI."""
    ondertekenaar = Ondertekenaar(functie="De Minister", achternaam="Jansen")
    wet1 = Wet(
        bwb_id="BWBR0001",
        citeertitel="Wet 1",
        opschrift="Wet 1",
        soort="wet",
        ondertekenaars=[ondertekenaar],
    )
    wet2 = Wet(
        bwb_id="BWBR0002",
        citeertitel="Wet 2",
        opschrift="Wet 2",
        soort="wet",
        ondertekenaars=[ondertekenaar],
    )
    g1, _ = _writer().build_graph(wet1)
    g2, _ = _writer().build_graph(wet2)

    ondt_iri1 = next(g1.objects(URIRef("urn:bwb:BWBR0001"), URIRef("urn:bwb-ns:ondertekendDoor")))
    ondt_iri2 = next(g2.objects(URIRef("urn:bwb:BWBR0002"), URIRef("urn:bwb-ns:ondertekendDoor")))
    assert ondt_iri1 == ondt_iri2


def test_build_graph_illustratie_en_provenance_triples() -> None:
    wet = Wet(
        bwb_id="BWBR9999",
        citeertitel="Test",
        opschrift="Test",
        soort="wet",
        losse_artikelen=[
            Artikel(
                id="BWBR9999/Art1",
                nummer="1",
                label="Artikel 1",
                tekst="tekst",
                bron="Stb.2020-1",
                effect="wijziging",
                illustraties=[Illustratie(id="IL1", naam="foto.png")],
            )
        ],
    )
    g, _ = _writer().build_graph(wet)

    artikel_iri = URIRef("urn:bwb:BWBR9999:id:BWBR9999%2FArt1")
    illustratie_iri = URIRef("urn:bwb:BWBR9999:id:IL1")
    bevat_illustratie = URIRef("urn:bwb-ns:bevatIllustratie")
    assert (artikel_iri, URIRef("urn:bwb-ns:bron"), None) in g
    assert (artikel_iri, URIRef("urn:bwb-ns:effect"), None) in g
    assert (artikel_iri, bevat_illustratie, illustratie_iri) in g
    assert (illustratie_iri, RDF.type, URIRef("urn:bwb-ns:Illustratie")) in g
    assert (illustratie_iri, URIRef("urn:bwb-ns:naam"), None) in g


def test_build_graph_bijlage_citeerbaar_en_relaties() -> None:
    wet = Wet(
        bwb_id="BWBR9999",
        citeertitel="Test",
        opschrift="Test",
        soort="wet",
        bijlagen=[
            Bijlage(
                id="BWBR9999/Bijlage1",
                nummer="1",
                label="Bijlage 1",
                titel="Tabel",
                tekst="inhoud",
                artikelen=[
                    Artikel(id="BWBR9999/Bijlage1/ArtA", nummer="A", label="A", tekst="tekst")
                ],
            )
        ],
    )
    g, _ = _writer().build_graph(wet)

    bijlage_iri = URIRef("urn:bwb:BWBR9999:id:BWBR9999%2FBijlage1")
    wet_iri = URIRef("urn:bwb:BWBR9999")
    heeft_bijlage = URIRef("urn:bwb-ns:heeftBijlage")
    assert (bijlage_iri, RDF.type, URIRef("urn:bwb-ns:Bijlage")) in g
    assert (bijlage_iri, RDF.type, URIRef("urn:bwb-ns:Citeerbaar")) in g
    assert (wet_iri, heeft_bijlage, bijlage_iri) in g
    # Het geneste artikel is een aparte, citeerbare Artikel-node onder de bijlage.
    artikel_iri = URIRef("urn:bwb:BWBR9999:id:BWBR9999%2FBijlage1%2FArtA")
    heeft_artikel = URIRef("urn:bwb-ns:heeftArtikel")
    assert (bijlage_iri, heeft_artikel, artikel_iri) in g


def test_build_graph_twee_bijlagen_volgt_op_camelcase() -> None:
    wet = Wet(
        bwb_id="BWBR9999",
        citeertitel="Test",
        opschrift="Test",
        soort="wet",
        bijlagen=[
            Bijlage(id="B1", nummer="1", label="B1", titel="Eerste", tekst=""),
            Bijlage(id="B2", nummer="2", label="B2", titel="Tweede", tekst=""),
        ],
    )
    g, _ = _writer().build_graph(wet)

    volgt_op = URIRef("urn:bwb-ns:volgtOp")
    b1_iri = URIRef("urn:bwb:BWBR9999:id:B1")
    b2_iri = URIRef("urn:bwb:BWBR9999:id:B2")
    assert (b2_iri, volgt_op, b1_iri) in g


def test_build_graph_onbekende_soort_geen_subklasse() -> None:
    wet = Wet(bwb_id="BWBR9999", citeertitel="Test", opschrift="Test", soort="onbekende-soort")
    g, _ = _writer().build_graph(wet)

    wet_iri = URIRef("urn:bwb:BWBR9999")
    types = set(g.objects(wet_iri, RDF.type))
    verwachte_types = {URIRef("urn:bwb-ns:Regeling"), URIRef("urn:bwb-ns:Citeerbaar")}
    assert types == verwachte_types


# ------------------------------------------------------------------------- integration


@pytest.mark.integration
def test_write_wet_en_terugvragen() -> None:
    """Schrijft daadwerkelijk naar de lokale deploy/graphdb-stack en leest terug.

    Vereist: `podman compose up -d` in deploy/graphdb/, repository `inning` aangemaakt (zie
    deploy/graphdb/README.md). Standaard geskipt (zie pyproject.toml markers).
    """
    url = os.environ.get("GRAPHDB_URL", "http://localhost:7200")
    user = os.environ.get("GRAPHDB_SVC_USER", "lex")
    password = os.environ.get("GRAPHDB_SVC_PASSWORD", "lex-dev-wachtwoord")

    writer = GraphDbWriter(
        url=url, repository="inning", vocab=Vocab(), user=user, password=password
    )
    writer.ensure_constraints()
    writer.write_ontology()

    wet = ToestandParser().parse(FIXTURE)
    eerste = writer.write_wet(wet)
    # Her-import: de named graph wordt integraal vervangen (idempotent), geen dubbele triples.
    tweede = writer.write_wet(wet)
    assert eerste.artikelen == tweede.artikelen == 2
