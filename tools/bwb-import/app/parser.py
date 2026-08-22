"""Parser voor de BWB toestand-XML (lxml), met optionele XSD-validatie.

Kernstructuur: ``toestand -> wetgeving -> wet-besluit/wettekst (of regeling/regeling-tekst) ->
hoofdstuk/afdeling/paragraaf (generiek genest) -> artikel -> lid``, elk met onderdelen
(genestelde ``<lijst>/<li>``), gestructureerde verwijzingen (``<intref>``/``<extref>``),
provenance-attributen, voetnoten, definities, illustraties en tabellen (story 031), en wet-niveau
brondata/aanhef/considerans/ondertekenaars (story 032). Circulaires (``circulaire/
circulaire-tekst``), bijlagen en tekstuele verwijzingsdetectie volgen in latere stories — zie
docs/project/stories/026-bwb-import-onderdelen-en-verwijzingen.md §Buiten scope.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from lxml import etree

from app.models import Artikel, Illustratie, Lid, Onderdeel, Ondertekenaar, Structuurdeel, Wet
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
            label_id=wetgeving.get("label-id"),
            vast_deel_url=root.get("bwb-ng-vast-deel"),
            **self._wet_aanhef(wetgeving),
            **self._wet_brondata(wetgeving),
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

        wet.ondertekenaars = self._parse_ondertekenaars(wetgeving)

        logger.info(
            "Parse klaar voor %s: %d structuurdelen, %d losse artikelen, %d ondertekenaars",
            bwb_id,
            len(wet.structuurdelen),
            len(wet.losse_artikelen),
            len(wet.ondertekenaars),
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
            label_id=element.get("label-id"),
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
        excl = " and not(ancestor::lid) and not(ancestor::li)"
        artikel = Artikel(
            id=self._knoop_id(bwb_id, element),
            nummer=self._tekst(kop.find("nr")) if kop is not None else "",
            label=element.get("label", ""),
            tekst=self._lichaamstekst(element, binnen_lid=False),
            jci=self._element_jci(element),
            label_id=element.get("label-id"),
            inwerking=element.get("inwerking"),
            bron=element.get("bron"),
            effect=element.get("effect"),
            status=element.get("status"),
            terugwerkend_tot=self._terugwerkend(element),
            wijzigingsbronnen=self._wijzigingsbronnen(element),
            verwijzingen=extract_references(element, eigen_bwb_id=bwb_id, extra_excl=excl),
            onderdelen=self._parse_onderdelen(element, bwb_id),
            voetnoten=self._noten(element, excl),
            illustraties=self._illustraties(element, extra_excl=excl),
        )
        for lid in element.iterfind("lid"):
            artikel.leden.append(self._parse_lid(lid, bwb_id))
        return artikel

    def _parse_lid(self, element: etree._Element, bwb_id: str) -> Lid:
        excl = " and not(ancestor::li)"
        return Lid(
            id=self._knoop_id(bwb_id, element),
            nummer=self._tekst(element.find("lidnr")),
            tekst=self._lichaamstekst(element, binnen_lid=True),
            jci=self._element_jci(element),
            terugwerkend_tot=self._terugwerkend(element),
            verwijzingen=extract_references(element, eigen_bwb_id=bwb_id, extra_excl=excl),
            onderdelen=self._parse_onderdelen(element, bwb_id),
            voetnoten=self._noten(element, excl),
            definieert_begrippen=self._definities(element),
            illustraties=self._illustraties(element, extra_excl=excl),
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
            voetnoten=[self._noot_tekst(noot) for noot in li.xpath("./al//noot")],
            definieert_begrippen=self._definities(li),
            illustraties=self._illustraties(li, base="./al//illustratie"),
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
    def _terugwerkend(element: etree._Element) -> str | None:
        """Retroactieve ingangsdatum uit het eigen meta-data-blok
        (`brondata/inwerkingtreding/terugwerkend.datum`), indien aanwezig."""
        for datum in element.xpath(
            "./meta-data/brondata/inwerkingtreding/terugwerkend.datum/@isodatum"
        ):
            if datum:
                return datum
        return None

    @staticmethod
    def _wijzigingsbronnen(element: etree._Element) -> list[str]:
        """Stb-bronnen waarmee dit tekstdeel is gewijzigd (uit `<juncto>`)."""
        bronnen: list[str] = []
        for pub in element.xpath("./meta-data//juncto/publicatie"):
            jaar = pub.findtext("publicatiejaar")
            nr = pub.findtext("publicatienr")
            if jaar and nr:
                bronnen.append(f"{pub.get('soort', 'Stb')}.{jaar}-{nr}")
        return bronnen

    @staticmethod
    def _noten(element: etree._Element, extra_excl: str) -> list[str]:
        """Voetnoten binnen het tekstbereik van deze node (zelfde exclusies als de lopende
        tekst, zodat noot en tekst op hetzelfde niveau landen)."""
        xpath = f".//noot[not(ancestor::meta-data){extra_excl}]"
        return [ToestandParser._noot_tekst(noot) for noot in element.xpath(xpath)]

    @staticmethod
    def _noot_tekst(noot: etree._Element) -> str:
        delen = noot.xpath(".//text()[not(ancestor::meta-data)]")
        return re.sub(r"\s+", " ", "".join(delen)).strip()

    @staticmethod
    def _definities(element: etree._Element) -> list[str]:
        """Gedefinieerde begrippen: cursieve termen (`nadruk type="cur"`) die op een dubbele
        punt eindigen, aan het begin van een definitie."""
        begrippen: list[str] = []
        for term in element.xpath("./al/nadruk[@type='cur']/text()"):
            genormaliseerd = term.strip()
            if genormaliseerd.endswith(":"):
                begrippen.append(genormaliseerd.rstrip(":").strip())
        return begrippen

    @staticmethod
    def _illustraties(
        element: etree._Element,
        *,
        base: str = ".//illustratie",
        extra_excl: str = "",
    ) -> list[Illustratie]:
        """Illustraties binnen `element` (uit `<plaatje>/<illustratie>`), beperkt via `base` +
        exclusies zoals de tekst-scope, zodat een illustratie bij de meest specifieke
        tekstdrager landt."""
        out: list[Illustratie] = []
        for il in element.xpath(f"{base}[not(ancestor::meta-data){extra_excl}]"):
            out.append(
                Illustratie(
                    id=il.get("id") or il.get("naam") or "",
                    naam=il.get("naam"),
                    formaat=il.get("formaat"),
                    breedte=il.get("breedte"),
                    hoogte=il.get("hoogte"),
                    alt=il.get("alt"),
                )
            )
        return out

    def _parse_ondertekenaars(self, wetgeving: etree._Element) -> list[Ondertekenaar]:
        """Ondertekenaars uit de `<ondertekening>`-blokken van de regeling.

        Een ondertekening bevat een `<functie>` en een `<naam>` (met `<voornaam>`/
        `<achternaam>`). Ontdubbelt op (functie, naam, achternaam)."""
        gezien: set[tuple[str, str, str]] = set()
        out: list[Ondertekenaar] = []
        for ondt in wetgeving.iter("ondertekening"):
            naam_el = ondt.find("naam")
            functie = self._tekst(ondt.find("functie")) or None
            voornaam = self._tekst(naam_el.find("voornaam")) if naam_el is not None else ""
            achternaam = self._tekst(naam_el.find("achternaam")) if naam_el is not None else ""
            naam = self._tekst(naam_el) if naam_el is not None else ""
            if not (functie or naam):
                continue
            sleutel = (functie or "", naam, achternaam)
            if sleutel in gezien:
                continue
            gezien.add(sleutel)
            out.append(
                Ondertekenaar(
                    functie=functie,
                    naam=naam or None,
                    voornaam=voornaam or None,
                    achternaam=achternaam or None,
                    plaats=self._tekst(ondt.find("plaats")) or None,
                    datum=None,
                )
            )
        return out

    def _wet_aanhef(self, wetgeving: etree._Element) -> dict[str, str | None]:
        """Aanhef en considerans (`wet-besluit/aanhef` of `regeling/aanhef`)."""
        aanhef_el = wetgeving.find("wet-besluit/aanhef")
        if aanhef_el is None:
            aanhef_el = wetgeving.find("regeling/aanhef")
        if aanhef_el is None:
            return {"aanhef": None, "considerans": None}
        aanhef_delen = [
            # Wetten/besluiten openen met <wij>, ministeriële regelingen met <wie>.
            self._tekst(aanhef_el.find("wij")),
            self._tekst(aanhef_el.find("wie")),
            self._tekst(aanhef_el.find("afkondiging")),
        ]
        aanhef = " ".join(d for d in aanhef_delen if d).strip() or None
        considerans_delen = [
            "".join(al.xpath(".//text()[not(ancestor::noot)]"))
            for al in aanhef_el.xpath("./considerans/considerans.al")
        ]
        considerans = re.sub(r"\s+", " ", " ".join(considerans_delen)).strip() or None
        return {"aanhef": aanhef, "considerans": considerans}

    @staticmethod
    def _wet_brondata(wetgeving: etree._Element) -> dict[str, str | None]:
        """Brondata van de oorspronkelijke regeling (wetgeving/meta-data/brondata)."""
        pub = wetgeving.find("meta-data/brondata/oorspronkelijk/publicatie")
        if pub is None:
            return {
                "publicatiejaar": None,
                "publicatienr": None,
                "ondertekeningsdatum": None,
                "uitgiftedatum": None,
                "dossier": None,
            }
        ondt = pub.find("ondertekeningsdatum")
        uitg = pub.find("uitgiftedatum")
        doss = pub.find("dossierref")
        return {
            "publicatiejaar": pub.findtext("publicatiejaar"),
            "publicatienr": pub.findtext("publicatienr"),
            "ondertekeningsdatum": ondt.get("isodatum") if ondt is not None else None,
            "uitgiftedatum": uitg.get("isodatum") if uitg is not None else None,
            "dossier": doss.get("dossier") if doss is not None else None,
        }

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
        `<lid>` hoort — anders dubbelt de artikeltekst met zijn eigen leden. Tabellen (CALS)
        worden buiten de alinea's om als leesbare rijen ná de lopende tekst toegevoegd
        (`_tabel_tekst`), zodat niets stilzwijgend verdwijnt."""
        if binnen_lid:
            scope = "not(ancestor::li) and not(ancestor::meta-data)"
        else:
            scope = "not(ancestor::lid) and not(ancestor::li) and not(ancestor::meta-data)"
        delen = [
            "".join(al.xpath(".//text()[not(ancestor::noot)]"))
            for al in element.xpath(f".//al[{scope} and not(ancestor::table)]")
        ]
        tekst = re.sub(r"\s+", " ", " ".join(delen)).strip()
        tabellen = [_tabel_tekst(t) for t in element.xpath(f".//table[{scope}]")]
        tabellen = [t for t in tabellen if t]
        if tabellen:
            tekst = "\n".join([tekst, *tabellen]).strip()
        return tekst


def _tabel_tekst(table: etree._Element) -> str:
    """Leesbare weergave van een CALS-tabel: cellen per rij met `|` gescheiden.

    De structuur (kolombreedtes, spans) gaat verloren; doel is dat geen tekst stilzwijgend
    verdwijnt en de inhoud full-text-doorzoekbaar is.
    """
    rijen: list[str] = []
    for row in table.xpath(".//row"):
        cellen: list[str] = []
        for entry in row.xpath("./entry"):
            delen = entry.xpath(".//text()[not(ancestor::meta-data) and not(ancestor::noot)]")
            cellen.append(re.sub(r"\s+", " ", "".join(delen)).strip())
        rij = " | ".join(cellen).strip()
        if rij.strip("| "):
            rijen.append(rij)
    return "\n".join(rijen)
