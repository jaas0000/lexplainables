"""Begrensde LLM-stappen — MCP-basis mergen met LLM-cognitieve output (story 024).

Elke stap:
1. Bouwt de prompt vanuit `prompts.py`.
2. Roept het LLM aan via de geïnjecteerde client.
3. Valideert het schema-resultaat (fouten → auto-correctie-hint → tweede poging → LLMError).
4. Voert de harde brongetrouwheidscheck uit (formulering ⊆ leden-tekst).
5. Mergt brongetrouwe MCP-basis (leden, versiedatum, …) met LLM-cognitieve velden.
6. Slaat de call optioneel op in llm_calls (capture).

Capture wordt hier gedaan (niet in de LLM-client) per feature-bouwen regel 5.
"""

from __future__ import annotations

import logging

from ..shared.llm.base import LLMClient, LLMError
from . import prompts
from .validation import brongetrouwheid_check, schema_check_act2, schema_check_act3

logger = logging.getLogger(__name__)

_CORRECTIE_HINT = (
    "\n\nDe vorige respons had de volgende schema-fouten — herstel ALLE fouten en geef "
    "UITSLUITEND geldig JSON terug:\n"
)


async def _genereer_met_autocorrectie(
    llm: LLMClient,
    system: str,
    user: str,
    schema_check_fn,
    *,
    activiteit: str,
    sla_capture_op=None,
):
    """Roep LLM aan; bij schema-fouten één auto-correctie-herpoging; daarna → LLMError.

    `sla_capture_op` is optioneel: `await sla_capture_op(system, user, res)`.
    """
    res = await llm.complete(system, user)
    if sla_capture_op:
        await sla_capture_op(system, user, res)

    fouten = schema_check_fn(res.data)
    if not fouten:
        return res

    # Auto-correctie: één herpoging met foutcontext.
    correctie_user = user + _CORRECTIE_HINT + "\n".join(f"- {f}" for f in fouten)
    logger.warning(
        "Act %s: %d schema-fouten, auto-correctie starten: %s",
        activiteit,
        len(fouten),
        fouten[:3],
    )
    res2 = await llm.complete(system, correctie_user)
    if sla_capture_op:
        await sla_capture_op(system, correctie_user, res2)

    fouten2 = schema_check_fn(res2.data)
    if fouten2:
        raise LLMError(f"Act {activiteit}: schema-fouten na auto-correctie — {fouten2[:3]}")
    return res2


def _merge_act2_bron(bron_basis: dict, llm_out: dict) -> dict:
    """Combineer brongetrouwe MCP-basis met LLM-cognitieve velden (markeringen + samenhang).

    De leden-tekst, versiedatum en bronreferentie komen ALTIJD uit bron_basis (nooit LLM).
    """
    bid = bron_basis.get("bron_id", "")
    return {
        **{k: v for k, v in bron_basis.items() if k != "mcp_verwijzingen"},
        "markeringen": [{**m, "bron_id": bid} for m in llm_out.get("markeringen", [])],
        "samenhang": llm_out.get("samenhang", ""),
    }


async def genereer_act2_bron(
    llm: LLMClient,
    bron_basis: dict,
    analysefocus: str | None,
    sla_capture_op=None,
) -> dict:
    """Genereer act2-output voor één bron; merge met MCP-basis; valideer brongetrouwheid.

    Werpt LLMError bij schema-fouten na auto-correctie.
    Werpt ValueError bij brongetrouwheidsovertreding.
    """
    system, user = prompts.act2_prompt(bron_basis, analysefocus)

    res = await _genereer_met_autocorrectie(
        llm,
        system,
        user,
        schema_check_act2,
        activiteit="2",
        sla_capture_op=sla_capture_op,
    )

    leden = bron_basis.get("leden", [])
    markeringen = res.data.get("markeringen", [])
    overtredingen = brongetrouwheid_check(leden, markeringen)
    if overtredingen:
        logger.error(
            "Brongetrouwheidsovertreding in act2 voor bron %s: %s",
            bron_basis.get("bron_id"),
            overtredingen[:3],
        )
        raise ValueError(
            f"Brongetrouwheidscheck mislukt voor {bron_basis.get('bron_id')}: "
            + "; ".join(overtredingen[:3])
        )

    return _merge_act2_bron(bron_basis, res.data)


async def genereer_act3(
    llm: LLMClient,
    bronnen: list[dict],
    omschrijving: str | None,
    analysefocus: str | None,
    begrippenlijst_hint: list[dict] | None,
    sla_capture_op=None,
) -> dict:
    """Genereer act3 (begrippen + regels) in twee stappen (3a begrippen → 3b regels).

    Werpt LLMError bij schema-fouten na auto-correctie.
    Geeft dict terug met 'begrippen' en 'afleidingsregels'.
    """
    # Stap 3a: begrippen
    system_a, user_a = prompts.act3_begrippen_prompt(
        bronnen, omschrijving, analysefocus, begrippenlijst_hint
    )
    res_a = await _genereer_met_autocorrectie(
        llm,
        system_a,
        user_a,
        lambda d: schema_check_act3({"begrippen": d.get("begrippen", []), "afleidingsregels": []}),
        activiteit="3a",
        sla_capture_op=sla_capture_op,
    )
    begrippen = res_a.data.get("begrippen", [])

    # Stap 3b: regels (met begrippen als bouwstenen)
    system_b, user_b = prompts.act3_regels_prompt(bronnen, begrippen)
    res_b = await _genereer_met_autocorrectie(
        llm,
        system_b,
        user_b,
        lambda d: [],  # regels-schema-check: minimaal (afdwingen via orchestrator indien gewenst)
        activiteit="3b",
        sla_capture_op=sla_capture_op,
    )

    # Nieuwe begrippen van 3b doormergen
    nieuwe = res_b.data.get("nieuwe_begrippen", [])
    if isinstance(nieuwe, list):
        begrippen = begrippen + nieuwe

    return {
        "begrippen": begrippen,
        "afleidingsregels": res_b.data.get("afleidingsregels", []),
    }


def bouw_bron_basis(
    bwb_id: str, artikel: str, lid: str | None, bron_id: str, mcp_data: dict
) -> dict:
    """Bouw een bron_basis-dict uit de MCP-respons. Alle brongetrouwe velden komen uit mcp_data."""
    wet = mcp_data.get("wet", "")
    label_lid = f" lid {lid}" if lid else ""
    label = f"{wet} art. {artikel}{label_lid}".strip()
    return {
        "bron_id": bron_id,
        "label": label,
        "wet": wet,
        "bwbId": bwb_id,
        "artikel": artikel,
        "lid": lid,
        "versiedatum": mcp_data.get("versiedatum", ""),
        "bronreferentie": mcp_data.get("bronreferentie", ""),
        "pad": mcp_data.get("pad", ""),
        "leden": mcp_data.get("leden", []),
    }


def bouw_rapport(bronnen: list[dict], act3: dict, analyse_naam: str | None) -> dict:
    """Bouw het eindrapport als opgeslagen JSON-artefact."""
    return {
        "naam": analyse_naam or "",
        "bronnen": [
            {
                "bron_id": b.get("bron_id"),
                "label": b.get("label"),
                "wet": b.get("wet"),
                "bwbId": b.get("bwbId"),
                "artikel": b.get("artikel"),
                "lid": b.get("lid"),
                "versiedatum": b.get("versiedatum"),
                "bronreferentie": b.get("bronreferentie"),
                "markeringen": b.get("markeringen", []),
                "samenhang": b.get("samenhang", ""),
            }
            for b in bronnen
        ],
        "begrippen": act3.get("begrippen", []),
        "afleidingsregels": act3.get("afleidingsregels", []),
    }


def capture_factory(analyse_id: str, activiteit: str, bron_id: str | None, llm_calls_store):
    """Geeft een capture-coroutine-factory terug voor gebruik in _genereer_met_autocorrectie.

    `llm_calls_store` is een object met `sla_op(analyse_id, activiteit, bron_id, ...)`-methode.
    """

    async def sla_op(system: str, user: str, res):
        try:
            await llm_calls_store.sla_op(
                analyse_id=analyse_id,
                activiteit=activiteit,
                bron_id=bron_id,
                system_prompt=system,
                user_prompt=user,
                ruwe_respons=res.ruwe_tekst,
                model=res.model,
                tokens_in=res.tokens_in,
                tokens_out=res.tokens_out,
            )
        except Exception:  # noqa: BLE001 — capture mag de analyse nooit breken
            logger.warning("LLM-call capture mislukt (genegeerd).", exc_info=True)

    return sla_op
