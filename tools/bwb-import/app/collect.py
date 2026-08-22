"""Opslag-agnostische traversal van het BWB-model naar een platte `Batch`.

Loopt één keer door een `Wet` en verzamelt nodes, relaties en verwijzingen in een neutrale
representatie. De GraphDB-writer consumeert die `Batch`, zodat de ref_key-/verwijzing-logica
(incl. de telling in `ImportSummary`) op één plek staat, los van de HTTP-laag.

Elke node die JuriConnect-adresseerbaar is (structuurdeel, artikel, lid, onderdeel) draagt naast
zijn XML-`id` een `ref_key`: jci eerst (canoniek), anders een nummer/id-fallback — zelfde
volgorde als de referentie-app, zie docs/project/stories/027-bwb-import-graphdb-writer.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import (
    Artikel,
    Bijlage,
    Illustratie,
    ImportSummary,
    Onderdeel,
    Structuurdeel,
    Verwijzing,
    Wet,
)
from app.references import jci_doel_ref_key, jci_to_ref_key

STRUCT_REL = {
    "hoofdstuk": "HEEFT_HOOFDSTUK",
    "titeldeel": "HEEFT_TITELDEEL",
    "afdeling": "HEEFT_AFDELING",
    "paragraaf": "HEEFT_PARAGRAAF",
}
STRUCT_LABEL = {
    "hoofdstuk": "Hoofdstuk",
    "titeldeel": "Titeldeel",
    "afdeling": "Afdeling",
    "paragraaf": "Paragraaf",
}
_STRUCT_TELLER = {
    "hoofdstuk": "hoofdstukken",
    "titeldeel": "titeldelen",
    "afdeling": "afdelingen",
    "paragraaf": "paragrafen",
}


@dataclass
class Batch:
    """Verzamelde nodes en relaties, klaar om naar RDF vertaald te worden.

    - `nodes`: entiteit -> lijst prop-dicts (elk met `id`; nodes met een JuriConnect-identiteit
      dragen ook `ref_key`).
    - `rels`: `(src_ent, rel_type, dst_ent)` -> rijen `{"from": id, "to": id}`.
    - `verwijzingen`: rijen met `from`/`to` als *ref_key* plus soort/doc/doel-metadata.
    """

    nodes: dict[str, list[dict]] = field(default_factory=dict)
    rels: dict[tuple[str, str, str], list[dict]] = field(default_factory=dict)
    verwijzingen: list[dict] = field(default_factory=list)

    def node(self, entiteit: str, props: dict) -> None:
        self.nodes.setdefault(entiteit, []).append(props)

    def rel(self, src: str, rel_type: str, dst: str, from_id: str, to_id: str) -> None:
        self.rels.setdefault((src, rel_type, dst), []).append({"from": from_id, "to": to_id})


class _Collector:
    """Bouwt een `Batch` uit een `Wet` (één traversal)."""

    def __init__(self, wet: Wet) -> None:
        self._bwb = wet.bwb_id
        self.batch = Batch()
        self.summary = ImportSummary(bwb_id=wet.bwb_id, wetten=1)

    def run(self, wet: Wet) -> None:
        self.batch.node(
            "Regeling",
            {
                "id": wet.bwb_id,
                "bwb_id": wet.bwb_id,
                "ref_key": wet.bwb_id,
                "citeertitel": wet.citeertitel,
                "opschrift": wet.opschrift,
                "soort": wet.soort,
                "geldig_vanaf": wet.geldig_vanaf,
                "label_id": wet.label_id,
                "aanhef": wet.aanhef,
                "considerans": wet.considerans,
                "publicatiejaar": wet.publicatiejaar,
                "publicatienr": wet.publicatienr,
                "ondertekeningsdatum": wet.ondertekeningsdatum,
                "uitgiftedatum": wet.uitgiftedatum,
                "dossier": wet.dossier,
            },
        )
        for deel in wet.structuurdelen:
            self._structuur(deel, wet.bwb_id, "Regeling")
        self._artikelen(wet.losse_artikelen, wet.bwb_id, "Regeling")
        self._bijlagen(wet.bijlagen, wet.bwb_id, "Regeling")

    def _structuur(self, deel: Structuurdeel, ouder_id: str, ouder_ent: str) -> None:
        entiteit = STRUCT_LABEL[deel.soort]
        ref_key = jci_doel_ref_key(deel.jci)[0]
        if ref_key is None and deel.nummer:
            ref_key = f"{self._bwb}#{deel.soort}={deel.nummer}"
        self.batch.node(
            entiteit,
            {
                "id": deel.id,
                "ref_key": ref_key,
                "nummer": deel.nummer,
                "label": deel.label,
                "titel": deel.titel,
                "label_id": deel.label_id,
            },
        )
        self.batch.rel(ouder_ent, STRUCT_REL[deel.soort], entiteit, ouder_id, deel.id)
        teller = _STRUCT_TELLER[deel.soort]
        setattr(self.summary, teller, getattr(self.summary, teller) + 1)
        for sub in deel.subdelen:
            self._structuur(sub, deel.id, entiteit)
        self._artikelen(deel.artikelen, deel.id, entiteit)

    def _artikelen(self, artikelen: list[Artikel], ouder_id: str, ouder_ent: str) -> None:
        for artikel in artikelen:
            ref_key = jci_to_ref_key(artikel.jci) or f"{self._bwb}#id={artikel.id}"
            self.batch.node(
                "Artikel",
                {
                    "id": artikel.id,
                    "ref_key": ref_key,
                    "nummer": artikel.nummer,
                    "label": artikel.label,
                    "tekst": artikel.tekst,
                    "label_id": artikel.label_id,
                    "inwerking": artikel.inwerking,
                    "bron": artikel.bron,
                    "effect": artikel.effect,
                    "status": artikel.status,
                    "terugwerkend_tot": artikel.terugwerkend_tot,
                    "wijzigingsbronnen": artikel.wijzigingsbronnen,
                    "voetnoot": artikel.voetnoten,
                },
            )
            self.batch.rel(ouder_ent, "HEEFT_ARTIKEL", "Artikel", ouder_id, artikel.id)
            self.summary.artikelen += 1
            self._illustraties("Artikel", artikel.id, artikel.illustraties)
            self._verwijzingen(ref_key, artikel.verwijzingen)
            self._leden(artikel, ref_key)
            self._onderdelen(artikel.onderdelen, artikel.id, "Artikel", ref_key)

    def _bijlagen(self, bijlagen: list[Bijlage], ouder_id: str, ouder_ent: str) -> None:
        vorige_bijlage: str | None = None
        for bijlage in bijlagen:
            ref_key = jci_to_ref_key(bijlage.jci) or f"{self._bwb}#id={bijlage.id}"
            self.batch.node(
                "Bijlage",
                {
                    "id": bijlage.id,
                    "ref_key": ref_key,
                    "nummer": bijlage.nummer,
                    "label": bijlage.label,
                    "titel": bijlage.titel,
                    "tekst": bijlage.tekst,
                    "inwerking": bijlage.inwerking,
                    "bron": bijlage.bron,
                    "effect": bijlage.effect,
                    "status": bijlage.status,
                    "terugwerkend_tot": bijlage.terugwerkend_tot,
                    "wijzigingsbronnen": bijlage.wijzigingsbronnen,
                    "voetnoot": bijlage.voetnoten,
                },
            )
            self.batch.rel(ouder_ent, "HEEFT_BIJLAGE", "Bijlage", ouder_id, bijlage.id)
            self.summary.bijlagen += 1
            if vorige_bijlage is not None:
                self.batch.rel("Bijlage", "VOLGT_OP", "Bijlage", bijlage.id, vorige_bijlage)
            vorige_bijlage = bijlage.id

            self._illustraties("Bijlage", bijlage.id, bijlage.illustraties)
            self._verwijzingen(ref_key, bijlage.verwijzingen)
            self._onderdelen(bijlage.onderdelen, bijlage.id, "Bijlage", ref_key)
            # Een bijlage kan eigen artikelen bevatten (aparte Artikel-nodes, hergebruikt).
            self._artikelen(bijlage.artikelen, bijlage.id, "Bijlage")

    def _leden(self, artikel: Artikel, artikel_ref_key: str) -> None:
        for lid in artikel.leden:
            lid_ref = jci_doel_ref_key(lid.jci)[0] if lid.jci else None
            if lid_ref is None and lid.nummer:
                lid_ref = f"{artikel_ref_key}#lid={lid.nummer}"
            self.batch.node(
                "Lid",
                {
                    "id": lid.id,
                    "ref_key": lid_ref,
                    "nummer": lid.nummer,
                    "tekst": lid.tekst,
                    "terugwerkend_tot": lid.terugwerkend_tot,
                    "voetnoot": lid.voetnoten,
                    "definieert_begrip": lid.definieert_begrippen,
                },
            )
            self.batch.rel("Artikel", "HEEFT_LID", "Lid", artikel.id, lid.id)
            self.summary.leden += 1
            self._illustraties("Lid", lid.id, lid.illustraties)
            bron = lid_ref or artikel_ref_key
            self._verwijzingen(bron, lid.verwijzingen)
            self._onderdelen(lid.onderdelen, lid.id, "Lid", bron)

    def _onderdelen(
        self, onderdelen: list[Onderdeel], ouder_id: str, ouder_ent: str, erf_ref_key: str
    ) -> None:
        for onderdeel in onderdelen:
            ref_key = f"{erf_ref_key}#o={onderdeel.nummer}" if onderdeel.nummer else None
            self.batch.node(
                "Onderdeel",
                {
                    "id": onderdeel.id,
                    "ref_key": ref_key,
                    "nummer": onderdeel.nummer,
                    "tekst": onderdeel.tekst,
                    "voetnoot": onderdeel.voetnoten,
                    "definieert_begrip": onderdeel.definieert_begrippen,
                },
            )
            self.batch.rel(ouder_ent, "HEEFT_ONDERDEEL", "Onderdeel", ouder_id, onderdeel.id)
            self.summary.onderdelen += 1
            self._illustraties("Onderdeel", onderdeel.id, onderdeel.illustraties)
            bron = ref_key or erf_ref_key
            self._verwijzingen(bron, onderdeel.verwijzingen)
            self._onderdelen(onderdeel.subonderdelen, onderdeel.id, "Onderdeel", bron)

    def _illustraties(self, ouder_ent: str, ouder_id: str, illustraties: list[Illustratie]) -> None:
        for illustratie in illustraties:
            self.batch.node(
                "Illustratie",
                {
                    "id": illustratie.id,
                    "naam": illustratie.naam,
                    "formaat": illustratie.formaat,
                    "breedte": illustratie.breedte,
                    "hoogte": illustratie.hoogte,
                    "alt": illustratie.alt,
                },
            )
            self.batch.rel(ouder_ent, "BEVAT_ILLUSTRATIE", "Illustratie", ouder_id, illustratie.id)
            self.summary.illustraties += 1

    def _verwijzingen(self, bron_ref_key: str, verwijzingen: list[Verwijzing]) -> None:
        """Elke verwijzing met een jci-`doc` wordt een graafrelatie. Zonder `doc` (bv. een
        `<intref>` zonder jci-metadata) is er geen betrouwbare manier om het doel te resolven —
        wordt overgeslagen, niet gegokt (brongetrouwheid). Zie story 027 §Buiten scope."""
        for verwijzing in verwijzingen:
            doel_ref_key, doel_soort = jci_doel_ref_key(verwijzing.doc)
            if doel_ref_key is None:
                continue
            self.batch.verwijzingen.append(
                {
                    "from": bron_ref_key,
                    "to": doel_ref_key,
                    "to_bwb": verwijzing.doel_bwb_id,
                    "soort": verwijzing.soort.value,
                    "doc": verwijzing.doc,
                    "doel_soort": doel_soort,
                    "doel_pad": verwijzing.doel_pad,
                    "verwijzing_id": verwijzing.verwijzing_id,
                    "anker_tekst": verwijzing.tekst,
                }
            )


def collect(wet: Wet) -> tuple[Batch, ImportSummary]:
    """Bouw de `Batch` + `ImportSummary` voor één `Wet` (geen HTTP, geen I/O)."""
    collector = _Collector(wet)
    collector.run(wet)
    return collector.batch, collector.summary
