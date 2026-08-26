"""Documentexport voor het annotatie-domein: PDF/CSV/JSON van één annotatiedocument.

Poort van wetsanalyse-ai's `api/app/annotatie_export.py` (586r), versmald tot de kern: de
markeringen als tabel, gesorteerd op JAS-klasse (`jas_sorteersleutel`), plus het volledige
auditspoor. Werkt in elke fase — een document dat nog in review is exporteert gewoon, met de
telling "te beoordelen" in de kop, zodat een concept nooit als eindproduct kan worden gelezen.

Anders dan de referentie: `bouw_export()` krijgt de wettekst als `Wetsartikel | None` mee
(opgehaald door de router via `graphdb.py`, story 037) i.p.v. dat de client 'm meestuurt — het
`api`-domein heeft hier al een graafverbinding die de referentie niet had.
"""

from __future__ import annotations

import csv
import io
import json
from enum import StrEnum

from fastapi import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ...shared.validation import JAS_KLASSE_KLEUREN, JAS_TEKSTKLEUR, jas_sorteersleutel
from .models import AnnotatieDocument, AuditRegel, Wetsartikel


class Exportformaat(StrEnum):
    pdf = "pdf"
    csv = "csv"
    json = "json"


def _bestandsnaam(doc: AnnotatieDocument, formaat: Exportformaat) -> str:
    lid = f"-lid-{doc.lid}" if doc.lid else ""
    return f"annotatie-{doc.bwb_id}-art-{doc.artikel}{lid}.{formaat.value}"


def _gesorteerde_elementen(doc: AnnotatieDocument) -> list:
    return sorted(doc.elementen, key=lambda e: (jas_sorteersleutel(e.klasse), e.lid))


def bouw_export(
    doc: AnnotatieDocument,
    audit: list[AuditRegel],
    wetsartikel: Wetsartikel | None,
    *,
    formaat: Exportformaat,
) -> Response:
    bestandsnaam = _bestandsnaam(doc, formaat)
    headers = {"Content-Disposition": f'attachment; filename="{bestandsnaam}"'}
    if formaat is Exportformaat.json:
        return Response(
            content=json.dumps(
                {
                    "document": doc.model_dump(),
                    "audit": [a.model_dump() for a in audit],
                },
                ensure_ascii=False,
                indent=2,
            ),
            media_type="application/json",
            headers=headers,
        )
    if formaat is Exportformaat.csv:
        return Response(
            content=_bouw_csv(doc),
            media_type="text/csv",
            headers=headers,
        )
    return Response(
        content=_bouw_pdf(doc, wetsartikel),
        media_type="application/pdf",
        headers=headers,
    )


def _bouw_csv(doc: AnnotatieDocument) -> str:
    buffer = io.StringIO()
    schrijver = csv.writer(buffer)
    schrijver.writerow(["klasse", "tekst", "lid", "levenscyclus", "toelichting", "vindplaats"])
    for el in _gesorteerde_elementen(doc):
        schrijver.writerow(
            [el.klasse, el.tekst, el.lid, el.levenscyclus.value, el.toelichting, el.vindplaats]
        )
    return buffer.getvalue()


def _bouw_pdf(doc: AnnotatieDocument, wetsartikel: Wetsartikel | None) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    stijlen = getSampleStyleSheet()
    tekststijl = ParagraphStyle("cel", parent=stijlen["Normal"], fontSize=9, leading=12)

    lid = f" lid {doc.lid}" if doc.lid else ""
    titel = f"Annotatie {doc.bwb_id} art. {doc.artikel}{lid}"
    te_beoordelen = sum(1 for e in doc.elementen if e.levenscyclus.value == "voorgesteld")

    onderdelen = [
        Paragraph(titel, stijlen["Title"]),
        Paragraph(
            f"Status: {doc.status.value} — {len(doc.elementen)} markeringen, "
            f"{te_beoordelen} nog te beoordelen.",
            stijlen["Normal"],
        ),
        Spacer(1, 0.5 * cm),
    ]

    if wetsartikel is not None:
        onderdelen.append(Paragraph("Wetsartikel", stijlen["Heading2"]))
        onderdelen.append(Paragraph(wetsartikel.tekst.replace("\n", "<br/>"), tekststijl))
        onderdelen.append(Spacer(1, 0.5 * cm))

    onderdelen.append(Paragraph("Markeringen", stijlen["Heading2"]))
    rijen = [["Klasse", "Tekst", "Lid", "Levenscyclus"]]
    achtergronden = []
    for i, el in enumerate(_gesorteerde_elementen(doc), start=1):
        rijen.append(
            [
                Paragraph(el.klasse, tekststijl),
                Paragraph(el.tekst, tekststijl),
                el.lid,
                el.levenscyclus.value,
            ]
        )
        achtergrond, _rand = JAS_KLASSE_KLEUREN.get(el.klasse, ("#ffffff", "#cccccc"))
        achtergronden.append(("BACKGROUND", (0, i), (0, i), colors.HexColor(achtergrond)))
        achtergronden.append(("TEXTCOLOR", (0, i), (0, i), colors.HexColor(JAS_TEKSTKLEUR)))

    tabel = Table(rijen, colWidths=[4 * cm, 8 * cm, 1.5 * cm, 3.5 * cm], repeatRows=1)
    tabel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e5e5")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                *achtergronden,
            ]
        )
    )
    onderdelen.append(tabel)

    document.build(onderdelen)
    return buffer.getvalue()
