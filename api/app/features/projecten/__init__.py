"""Projecten (analyses).

Wat: analisten maken analyses aan met één of meer bronnen (bwb_id + artikel + lid); een
background-job orkestreert act2/act3 via `engine/orchestrator`; SSE geeft live status;
rapport-endpoint levert eindresultaat + Markdown-download; LLM-calls-log koppelt aan
`llm_calls`.
Waarom: eigen domein voor analyse-orkestratie — status-machine, background-task-lifecycle,
SSE-stream, human-in-the-loop akkoord/afwijzen. Los van annotatie (dat is post-analyse
werkplek) en van de engine zelf (dat is stateless orkestratie-code).
Grens: het rekenwerk zit in `engine/orchestrator.py`, niet hier; de analyse-status en
tussenresultaten worden hier bewaard; annotatie op individuele elementen woont in
`annotatie/`.

Tabellen:
  - analyses: id + naam + client_id + status (actief/wacht_op_review/klaar/fout) + fase +
    bronnen (JSON) + begrippenlijst (JSON, optioneel) + human_in_the_loop + resultaat
    (JSON) + timestamps.

Beslissingen:
  - ADR-0007 (store-abstractie): router leunt op `AnalyseStore` Protocol; rolfilter (analist
    vs. beheerder) zit in de store, niet in de router (story 012 §Auth).
  - ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
  - Story 012 §Human-in-the-loop: default `true`; `akkoord` zet status terug op `actief`
    (job pikt op via polling), `afwijzen` zet status op `fout` (job stopt).
  - Story 024: echte LLM-orkestratie via `engine/orchestrator.voer_analyse_uit`, geen mock.

Interacties:
  - engine/orchestrator.py: `voer_analyse_uit` is de background-task; roept LLM aan via
    `engine/`, schrijft naar `llm_calls`.
  - shared/auth.py: `huidige_beheerder` op alle endpoints (BFF geeft rol door via
    X-User-Id).
  - llm_calls/dependencies.py: `get_llm_calls_store` voor de log-per-analyse-route.
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
"""
