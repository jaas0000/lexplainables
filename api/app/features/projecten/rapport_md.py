"""Markdown-renderer voor het analyserapport (story 013).

Zet een rapport-dict (zoals opgeslagen door de engine) om naar een Markdown-document.
Alle veld-accesses zijn defensief: ontbrekende sleutels leveren lege strings of lege lijsten.
"""

from __future__ import annotations


def naar_markdown(rapport: dict, analyse_id: str) -> str:
    """Genereer Markdown uit een rapport-dict."""
    delen: list[str] = []

    # ── Titel ────────────────────────────────────────────────────────────────────
    naam = rapport.get("naam") or f"Rapport {analyse_id}"
    delen.append(f"# {naam}\n")

    # ── Werkgebied (optioneel geneste dict) ──────────────────────────────────────
    werkgebied = rapport.get("werkgebied")
    if isinstance(werkgebied, dict):
        omschrijving = werkgebied.get("omschrijving") or ""
        analysefocus = werkgebied.get("analysefocus") or ""
        if omschrijving or analysefocus:
            delen.append("## Werkgebied\n")
            if omschrijving:
                delen.append(omschrijving)
            if analysefocus:
                delen.append(f"\nAnalysefocus: {analysefocus}")
            delen.append("")

    # ── Bronnen ──────────────────────────────────────────────────────────────────
    bronnen: list[dict] = rapport.get("bronnen") or []
    if bronnen:
        delen.append("## Bronnen\n")
        for bron in bronnen:
            label = bron.get("label") or bron.get("wet") or ""
            artikel = bron.get("artikel") or ""
            kop = f"### {label}"
            if artikel:
                kop += f" (art. {artikel})"
            delen.append(kop + "\n")

            samenhang = bron.get("samenhang") or ""
            if samenhang:
                delen.append(samenhang + "\n")

            markeringen: list[dict] = bron.get("markeringen") or []
            if markeringen:
                delen.append("**Markeringen:**\n")
                for m in markeringen:
                    tekst = m.get("tekst") or m.get("formulering") or ""
                    if tekst:
                        delen.append(f"- {tekst}")
                delen.append("")

    # ── Begrippen ────────────────────────────────────────────────────────────────
    begrippen: list[dict] = rapport.get("begrippen") or []
    if begrippen:
        delen.append("## Begrippen\n")
        delen.append("| ID | Naam | Definitie |")
        delen.append("|---|---|---|")
        for b in begrippen:
            bid = b.get("id") or ""
            naam_b = b.get("naam") or ""
            definitie = (b.get("definitie") or "").replace("|", "\\|").replace("\n", " ")
            delen.append(f"| {bid} | {naam_b} | {definitie} |")
        delen.append("")

    # ── Afleidingsregels ─────────────────────────────────────────────────────────
    regels: list[dict] = rapport.get("afleidingsregels") or []
    if regels:
        delen.append("## Afleidingsregels\n")
        for i, regel in enumerate(regels, start=1):
            regel_naam = regel.get("naam") or f"Regel {i}"
            delen.append(f"### {regel_naam}\n")
            omschrijving = regel.get("omschrijving") or ""
            if omschrijving:
                delen.append(omschrijving + "\n")

    return "\n".join(delen)
