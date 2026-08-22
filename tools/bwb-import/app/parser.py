"""Parser voor de BWB toestand-XML (lxml), met optionele XSD-validatie.

Kernstructuur: ``toestand -> wetgeving -> wet-besluit/wettekst (of regeling/regeling-tekst) ->
hoofdstuk/afdeling/paragraaf (generiek genest) -> artikel -> lid``, elk met onderdelen
(genestelde ``<lijst>/<li>``) en gestructureerde verwijzingen (``<intref>``/``<extref>``).
Circulaires (``circulaire/circulaire-tekst``) en de rijkere velden van de referentie-parser
(illustraties, voetnoten, tabellen, ondertekenaars, bijlagen, tekstuele verwijzingsdetectie)
volgen in latere stories — zie
docs/project/stories/026-bwb-import-onderdelen-en-verwijzingen.md §Buiten scope.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from lxml import etree

from app.models import Artikel, Lid, Onderdeel, Structuurdeel, Wet
from app.references import extract_references

logger = logging.getLogger(__name__)

# Tags die als structuurdeel worden behandeld (generieke recursie, willekeurige nestingdiepte).
_STRUCTUUR_TAGS = {"hoofdstuk", "titeldeel", "afdeling", "paragraaf"}


class ParseError(RuntimeError):
    """De XML kon niet als geldige (ondersteunde) toestand worden geïnterpreteerd."""


class ToestandParser:
    """Zet een toestand-XML om naar het `Wet`-model (kernstructuur, zie module-docstring)."""

    def __init__(self, schema_path: Path | None = None) -> None:
        self._schema_path = schema_path
        self._schema: etree.XMLSchema | None = None

    # ------------------------------------------------------------- validatie
    def validate(self, xml_path: Path) -> bool:
        """Valideer tegen het XSD. Niet-blokkerend: faalt zacht met waarschuwing.

        Geeft `True` bij geldig, `False` bij ongeldig of als het schema niet beschikbaar is.
        Validatie is een kwaliteitssignaal, geen harde poort — `parse()` gaat door ongeacht het
        resultaat hier.
        """
        if self._schema_path is None:
            logger.warning("Geen XSD opgegeven; validatie overgeslagen")
            return False
        try:
            schema = self._load_schema()
            doc = etree.parse(str(xml_path))
            schema.assertValid(doc)
            logger.info("XSD-validatie geslaagd voor %s", xml_path.name)
            return True
        except etree.DocumentInvalid as exc:
            logger.warning("XSD-validatie mislukt voor %s: %s", xml_path.name, exc)
            return False
        except (etree.XMLSchemaParseError, OSError) as exc:
            logger.warning("XSD kon niet worden geladen (%s); validatie overgeslagen", exc)
            return False

    def _load_schema(self) -> etree.XMLSchema:
        if self._schema is None:
            assert self._schema_path is not None
            self._schema = etree.XMLSchema(etree.parse(str(self._schema_path)))
        return self._schema

    # ----------------------------------------------------------------- parse
    def parse(self, xml_path: Path) -> Wet:
        """Parse de toestand-XML naar een `Wet` (kernstructuur)."""
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        if root.tag != "toestand":
            raise ParseError(f"Onverwacht root-element: {root.tag!r} (verwacht 'toestand')")

        bwb_id = root.get("bwb-id") or ""
        wetgeving = root.find("wetgeving")
        if wetgeving is None:
            raise ParseError(f"Geen <wetgeving>-element gevonden voor {bwb_id}")

        wet = Wet(
            bwb_id=bwb_id,
            citeertitel=self._tekst(wetgeving.find("citeertitel")),
            opschrift=self._tekst(wetgeving.find("intitule")),
            soort=wetgeving.get("soort", ""),
            geldig_vanaf=root.get("inwerkingtreding"),
        )

        # Ministeriële regelingen dragen dezelfde bouwstenen als een wettekst, maar onder
        # <regeling>/<regeling-tekst>.
        wettekst = wetgeving.find("wet-besluit/wettekst")
        if wettekst is None:
            wettekst = wetgeving.find("regeling/regeling-tekst")
        if wettekst is None:
            raise ParseError(
                f"Geen <wet-besluit>/<wettekst> of <regeling>/<regeling-tekst> gevonden voor "
                f"{bwb_id} (circulaires zijn nog niet ondersteund, zie story 025 §Buiten scope)"
            )

        for child in wettekst:
            tag = child.tag if isinstance(child.tag, str) else ""
            if tag in _STRUCTUUR_TAGS:
                wet.structuurdelen.append(self._parse_structuurdeel(child, bwb_id))
            elif tag == "artikel":
                wet.losse_artikelen.append(self._parse_artikel(child, bwb_id))

        logger.info(
            "Parse klaar voor %s: %d structuurdelen, %d losse artikelen",
            bwb_id,
            len(wet.structuurdelen),
            len(wet.losse_artikelen),
        )
        return wet

    # ------------------------------------------------------------- structuur
    def _parse_structuurdeel(self, element: etree._Element, bwb_id: str) -> Structuurdeel:
        kop = element.find("kop")
        deel = Structuurdeel(
            id=self._knoop_id(bwb_id, element),
            soort=element.tag,
            nummer=self._tekst(kop.find("nr")) if kop is not None else "",
            label=self._tekst(kop.find("label")) if kop is not None else "",
            titel=self._tekst(kop.find("titel")) if kop is not None else "",
            jci=self._element_jci(element),
        )
        for child in element:
            tag = child.tag if isinstance(child.tag, str) else ""
            if tag in _STRUCTUUR_TAGS:
                deel.subdelen.append(self._parse_structuurdeel(child, bwb_id))
            elif tag == "artikel":
                deel.artikelen.append(self._parse_artikel(child, bwb_id))
        return deel

    def _parse_artikel(self, element: etree._Element, bwb_id: str) -> Artikel:
        kop = element.find("kop")
        artikel = Artikel(
            id=self._knoop_id(bwb_id, element),
            nummer=self._tekst(kop.find("nr")) if kop is not None else "",
            label=element.get("label", ""),
            tekst=self._lichaamstekst(element, binnen_lid=False),
            jci=self._element_jci(element),
            verwijzingen=extract_references(
                element,
                eigen_bwb_id=bwb_id,
                extra_excl=" and not(ancestor::lid) and not(ancestor::li)",
            ),
            onderdelen=self._parse_onderdelen(element, bwb_id),
        )
        for lid in element.iterfind("lid"):
            artikel.leden.append(self._parse_lid(lid, bwb_id))
        return artikel

    def _parse_lid(self, element: etree._Element, bwb_id: str) -> Lid:
        return Lid(
            id=self._knoop_id(bwb_id, element),
            nummer=self._tekst(element.find("lidnr")),
            tekst=self._lichaamstekst(element, binnen_lid=True),
            jci=self._element_jci(element),
            verwijzingen=extract_references(
                element, eigen_bwb_id=bwb_id, extra_excl=" and not(ancestor::li)"
            ),
            onderdelen=self._parse_onderdelen(element, bwb_id),
        )

    # --------------------------------------------------------------- onderdelen
    def _parse_onderdelen(self, element: etree._Element, bwb_id: str) -> list[Onderdeel]:
        """Onderdelen uit direct geneste `<lijst>/<li>` (niet uit een genest lid — die heeft zijn
        eigen `_parse_lid`-aanroep)."""
        onderdelen: list[Onderdeel] = []
        for lijst in element.findall("lijst"):
            for li in lijst.findall("li"):
                onderdelen.append(self._parse_onderdeel(li, bwb_id))
        return onderdelen

    def _parse_onderdeel(self, li: etree._Element, bwb_id: str) -> Onderdeel:
        nr = li.find("li.nr")
        tekst_delen = [
            "".join(al.xpath(".//text()[not(ancestor::noot)]")) for al in li.xpath("./al")
        ]
        return Onderdeel(
            id=self._knoop_id(bwb_id, li),
            nummer=self._tekst(nr) if nr is not None else "",
            tekst=re.sub(r"\s+", " ", " ".join(tekst_delen)).strip(),
            jci=self._element_jci(li),
            verwijzingen=extract_references(li, eigen_bwb_id=bwb_id, base="./al//*"),
            subonderdelen=self._parse_onderdelen(li, bwb_id),
        )

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _knoop_id(bwb_id: str, element: etree._Element) -> str:
        """Stabiele sleutel uit `bwb-ng-variabel-deel` (valt terug op tag) — nodig zodra de
        GraphDB-writer stabiele IRI's per node moet genereren (latere story)."""
        pad = element.get("bwb-ng-variabel-deel")
        return f"{bwb_id}{pad}" if pad else f"{bwb_id}/{element.tag}"

    @staticmethod
    def _element_jci(element: etree._Element) -> str | None:
        """De canonieke `jci1.3`-verwijzing van een node uit zijn eigen `meta-data`."""
        for jci in element.xpath("./meta-data/jcis/jci/@verwijzing"):
            if jci.startswith("jci1.3:"):
                return jci
        return None

    @staticmethod
    def _tekst(element: etree._Element | None) -> str:
        """Genormaliseerde tekst van een element, exclusief meta-data-subtrees (jci/brondata)."""
        if element is None:
            return ""
        delen = element.xpath(".//text()[not(ancestor::meta-data)]")
        return re.sub(r"\s+", " ", "".join(delen)).strip()

    @staticmethod
    def _lichaamstekst(element: etree._Element, *, binnen_lid: bool) -> str:
        """Verzamel de lopende `<al>`-tekst van een element, exclusief meta-data, exclusief
        onderdeel-tekst (`<lijst>/<li>` — die hoort bij zijn eigen `Onderdeel`-node, zie
        `_parse_onderdeel`) en (voor een artikel met leden) exclusief de tekst die al bij een
        `<lid>` hoort — anders dubbelt de artikeltekst met zijn eigen leden. Tabellen worden nog
        niet gerenderd (zie §Buiten scope); wél uitgesloten van de lopende tekst zodat tabelcellen
        niet als kale, ongestructureerde tekst lekken."""
        if binnen_lid:
            scope = "not(ancestor::li) and not(ancestor::meta-data)"
        else:
            scope = "not(ancestor::lid) and not(ancestor::li) and not(ancestor::meta-data)"
        delen = [
            "".join(al.xpath(".//text()[not(ancestor::noot)]"))
            for al in element.xpath(f".//al[{scope} and not(ancestor::table)]")
        ]
        return re.sub(r"\s+", " ", " ".join(delen)).strip()
