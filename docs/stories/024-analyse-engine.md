# Story 024 — Analyse-engine (echte LLM-orkestratie)

**Status:** gebouwd (PR #17)  
**Epic:** lexplainables core — analyse  
**Branch:** story-024-analyse-engine

## Doel

Vervang de PoC-`BackgroundTask` (`_voer_analyse_uit`) in `projecten/router.py` door een echte
LLM-orkestratie: activiteit 2 (JAS-markeringen per bron, via Wettenbank-MCP) en activiteit 3
(begrippen + afleidingsregels, werkgebied-breed), met human-in-the-loop review, auto-correctie,
brongetrouwheidscheck en LLM-call-capture.

## Acceptatiecriteria

1. `POST /v1/projecten` start de achtergrond-job met de echte engine.
2. Per bron: wettekst opgehaald uit de Wettenbank-MCP (deterministisch); LLM genereert alleen
   markeringen + samenhang.
3. Elke `formulering`-markering is een letterlijk substring van de gecombineerde leden-tekst
   (harde brongetrouwheidscheck).
4. Auto-correctie: één herpoging bij JSON-parse-fout of schema-validatiefout; daarna → `fout`.
5. Bij `human_in_the_loop=True`: status `review` na act2, poll tot akkoord (→ actief, verder
   naar act3) of afwijzen (→ fout). Max 24 uur wachten.
6. `POST /v1/projecten/{id}/akkoord` en `POST /v1/projecten/{id}/afwijzen` beschikbaar.
7. Act3 genereert begrippen (3a) + afleidingsregels (3b), rapport opgeslagen in `analyses.rapport`.
8. Status `klaar` na succesvolle afronding.
9. Foutmeldingen gesaniteerd (interne fout → logger.error; opgeslagen foutmelding = vaste zin).
10. LLM-calls opgeslagen in `llm_calls` tabel als `capture_llm_calls=True` in runtime_config.

## Schema-wijzigingen (migratie 0009)

- `analyses.rapport JSON nullable` — het eindrapport na act3.
- Nieuwe tabel `llm_calls` — vastgelegd LLM-verkeer (id, analyse_id, activiteit, bron_id,
  system_prompt, user_prompt, ruwe_respons, model, tokens_in, tokens_out, aangemaakt).

## Vereenvoudigingen t.o.v. wetsanalyse-ai

- Geen RegelSpraak fase, geen cross-referenties (stap 1b), geen meerdere review-rondes.
- Geen lease/heartbeat/CAS (SQLite + BackgroundTask, geen horizontale schaling).
- Geen OTel/observability spans, geen rate limiting, geen verwijzingen-inventaris.
- LiteLLM client: geen json_object response_format, geen prompt_caching-toggle, geen throttle.
