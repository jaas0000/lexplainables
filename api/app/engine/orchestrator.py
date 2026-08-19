"""De analyse-orchestrator — state machine voor act2/act3 (story 024).

Vereenvoudigd t.o.v. wetsanalyse-ai: geen lease/CAS, geen OTel, geen rate limiting.
Draait als FastAPI BackgroundTask (asyncio, één SQLite-connectie, geen horizontale schaling).

Garanties:
  - Harde brongetrouwheid mislukt → status 'fout', nooit stil 'klaar'.
  - Schema-fouten → auto-correctie (één herpoging); daarna → 'fout'.
  - Foutmeldingen gesaniteerd: interne fout naar logger.error, opgeslagen foutmelding = vaste zin.
  - Human-in-the-loop: na act2 poll max 43200×2s (24 uur) op status-wijziging.
"""

from __future__ import annotations

import asyncio
import logging

from ..features.llm_calls.store import SqlAlchemyLlmCallsStore
from ..features.llm_profielen.store import SqlAlchemyLlmProfielenStore
from ..features.runtime_config.store import RuntimeConfigStore
from ..shared.crypto import decrypt
from ..shared.llm.base import LLMError
from ..shared.llm.client import LlmConfig, bouw_llm_client
from ..shared.wettenbank import WettenbankFout, haal_artikel_op
from .retry import met_retry
from .steps import bouw_bron_basis, bouw_rapport, capture_factory, genereer_act2_bron, genereer_act3

logger = logging.getLogger(__name__)

_POLL_INTERVAL_S = 2.0
_MAX_POLL = 43200  # 24 uur


async def voer_analyse_uit(analyse_id: str, store, engine) -> None:
    """Hoofdfunctie voor de background-job — voert de volledige analyse uit.

    `store` is een SqlAlchemyAnalyseStore-instantie (de concrete implementatie).
    `engine` is de async SQLAlchemy-engine (voor llm_profielen- en runtime_config-stores).
    """
    try:
        await _run(analyse_id, store, engine)
    except Exception as exc:  # noqa: BLE001 — vang alles zodat de status altijd wordt bijgewerkt
        logger.error("Onverwachte fout in analyse %s: %s", analyse_id, exc, exc_info=True)
        try:
            await store.zet_status(
                analyse_id, "fout", foutmelding="Analyse mislukt — onverwachte fout."
            )
        except Exception:  # noqa: BLE001
            logger.error("Kon status niet bijwerken na crash voor analyse %s.", analyse_id)


async def _run(analyse_id: str, store, engine) -> None:
    """De eigenlijke analysestroom — mag exceptions gooien; voer_analyse_uit vangt ze."""
    # ── 0. Laad analyse-configuratie ──────────────────────────────────────────
    rij = await store.haal_rij_op_id(analyse_id)
    if rij is None:
        logger.error("Analyse %s niet gevonden bij start background-job.", analyse_id)
        return

    bronnen_config = rij.bronnen or []  # list[{bwb_id, artikel, lid}]
    model_profiel = rij.model_profiel
    human_in_the_loop = rij.human_in_the_loop
    omschrijving = rij.omschrijving
    analysefocus = rij.analysefocus
    naam = rij.naam
    begrippenlijst_hint = rij.begrippenlijst  # list[{naam, definitie}] | None

    # ── 1. Bouw LLM-client ────────────────────────────────────────────────────
    try:
        llm_config = await _lees_llm_config(model_profiel, engine)
    except Exception as exc:
        logger.error(
            "LLM-profiel ophalen mislukt voor analyse %s: %s", analyse_id, exc, exc_info=True
        )
        await store.zet_status(
            analyse_id, "fout", foutmelding="Analyse mislukt — LLM-profiel niet beschikbaar."
        )
        return

    llm = bouw_llm_client(llm_config)

    # ── 2. Runtime config (capture-toggle) ────────────────────────────────────
    runtime_store = RuntimeConfigStore(engine)
    try:
        config = await runtime_store.lees_alle()
        capture_aan = config.capture_llm_calls
    except Exception:  # noqa: BLE001 — capture-fout mag de analyse niet stoppen
        capture_aan = False

    # llm_calls store (altijd aanmaken; stores zijn goedkoop)
    llm_calls_store = SqlAlchemyLlmCallsStore(engine)

    # ── 3. Act 2: per bron ophalen + analyseren ───────────────────────────────
    await store.zet_status(analyse_id, "actief", "Bronnen ophalen")

    act2_bronnen: list[dict] = []
    for i, bron_cfg in enumerate(bronnen_config):
        bwb_id = bron_cfg.get("bwb_id", "")
        artikel = bron_cfg.get("artikel", "")
        lid = bron_cfg.get("lid")
        bron_id = f"br{i + 1}"

        await store.zet_status(
            analyse_id,
            "actief",
            f"Ophalen: {bwb_id} art. {artikel}" + (f" lid {lid}" if lid else ""),
        )

        try:
            mcp_data = await met_retry(
                lambda bw=bwb_id, ar=artikel, li=lid: haal_artikel_op(bw, ar, li),
                max_retries=3,
                backoff=2.0,
            )
        except WettenbankFout as exc:
            logger.error(
                "Wettekst ophalen mislukt voor analyse %s bron %s: %s", analyse_id, bron_id, exc
            )
            await store.zet_status(
                analyse_id,
                "fout",
                foutmelding="Analyse mislukt — wettekst niet ophaalbaar.",
            )
            return

        bron_basis = bouw_bron_basis(bwb_id, artikel, lid, bron_id, mcp_data)

        await store.zet_status(
            analyse_id,
            "actief",
            f"Analyseren: {bron_basis['wet']} art. {artikel}",
        )

        capture_fn = (
            capture_factory(analyse_id, "act2", bron_id, llm_calls_store) if capture_aan else None
        )

        try:
            bron_result = await met_retry(
                lambda bb=bron_basis, af=analysefocus, cf=capture_fn: genereer_act2_bron(
                    llm, bb, af, sla_capture_op=cf
                ),
                max_retries=2,
                backoff=5.0,
            )
        except LLMError as exc:
            logger.error("LLM-fout in act2 voor analyse %s bron %s: %s", analyse_id, bron_id, exc)
            await store.zet_status(
                analyse_id,
                "fout",
                foutmelding="Analyse mislukt — LLM-fout in act 2.",
            )
            return
        except ValueError as exc:
            # brongetrouwheidsovertreding
            logger.error(
                "Brongetrouwheidsovertreding in act2 voor analyse %s bron %s: %s",
                analyse_id,
                bron_id,
                exc,
            )
            await store.zet_status(
                analyse_id,
                "fout",
                foutmelding="Analyse mislukt — brongetrouwheidscheck mislukt in act 2.",
            )
            return

        act2_bronnen.append(bron_result)

    # ── 4. Human-in-the-loop review ───────────────────────────────────────────
    if human_in_the_loop:
        await store.zet_status(analyse_id, "review", "Wacht op goedkeuring")

        for _ in range(_MAX_POLL):
            await asyncio.sleep(_POLL_INTERVAL_S)
            huidige_status = await store.haal_status(analyse_id)
            if huidige_status == "actief":
                # Akkoord gegeven door gebruiker
                break
            if huidige_status == "fout":
                # Afgewezen door gebruiker
                logger.info("Analyse %s afgewezen door gebruiker.", analyse_id)
                return
            # huidige_status == "review" → blijven wachten
        else:
            # Timeout bereikt (24 uur)
            logger.warning("Analyse %s: human-in-the-loop timeout na 24 uur.", analyse_id)
            await store.zet_status(
                analyse_id,
                "fout",
                foutmelding="Analyse mislukt — human-in-the-loop timeout (24 uur).",
            )
            return

    # ── 5. Act 3: begrippen + afleidingsregels ────────────────────────────────
    await store.zet_status(analyse_id, "actief", "Begrippen en regels afleiden")

    capture_fn3 = (
        capture_factory(analyse_id, "act3", None, llm_calls_store) if capture_aan else None
    )

    try:
        act3_result = await met_retry(
            lambda: genereer_act3(
                llm,
                act2_bronnen,
                omschrijving,
                analysefocus,
                begrippenlijst_hint,
                sla_capture_op=capture_fn3,
            ),
            max_retries=2,
            backoff=5.0,
        )
    except LLMError as exc:
        logger.error("LLM-fout in act3 voor analyse %s: %s", analyse_id, exc)
        await store.zet_status(
            analyse_id,
            "fout",
            foutmelding="Analyse mislukt — LLM-fout in act 3.",
        )
        return

    # ── 6. Rapport opslaan + status klaar ────────────────────────────────────
    await store.zet_status(analyse_id, "actief", "Rapport samenstellen")
    rapport = bouw_rapport(act2_bronnen, act3_result, naam)
    await store.sla_rapport_op(analyse_id, rapport)
    await store.zet_status(analyse_id, "klaar")


async def _lees_llm_config(model_profiel: str | None, engine) -> LlmConfig:
    """Lees het LLM-profiel uit de database en ontsleutel de API-sleutel.

    Als `model_profiel` ontbreekt: gebruik het standaard-profiel.
    Werpt RuntimeError als er geen profiel beschikbaar is.
    """
    profiel_store = SqlAlchemyLlmProfielenStore(engine)
    rij = await profiel_store.haal_rij_op_naam(model_profiel) if model_profiel else None

    if rij is None:
        # Probeer het standaard-profiel
        rij = await profiel_store.haal_standaard_rij()

    if rij is None:
        raise RuntimeError(
            "Geen LLM-profiel beschikbaar (standaard of gevraagd profiel ontbreekt)."
        )

    api_sleutel: str | None = None
    if rij.api_sleutel_enc:
        try:
            api_sleutel = decrypt(rij.api_sleutel_enc)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"API-sleutel ontsleutelen mislukt: {exc}") from exc

    return LlmConfig(
        provider=rij.provider,
        model=rij.model,
        api_base=rij.api_base,
        api_key=api_sleutel,
        api_version=rij.api_versie,
        temperature=rij.temperatuur,
    )
