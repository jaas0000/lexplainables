# Story 049 — graph-qa: annotatieketen afronden (patch, herziening, emit, graaf-wiring)

## Verhaal

Als jurist wil ik dat een aangewezen bepaling volledig geannoteerd wordt — inclusief het
automatisch doorvoeren van zekere Critic-correcties, het herstellen van bijna-goede citaten en het
toevoegen van gemiste elementen — zodat ik één afgeronde, gecorrigeerde set voorstellen krijg in
plaats van zelf elke Critic-opmerking te moeten verwerken.

## Aanleiding

Slotstory van de annotatieketen-werkstroom (stories 047-048 bouwden `annoteer_node`/`critic_node`
los van elkaar). Deze story rondt de keten af in één keer — bewust een grotere snede dan
044-048 (elk één node): de resterende stukken (patch/herziening/emit/routing) horen inhoudelijk
bij elkaar (ze vormen samen precies één correctiecyclus) en hebben geen zelfstandige waarde apart.

Referentie-topologie (lineair, geen cyclus):
```
annoteer → critic₁ → patch ─┬─→ herzie → critic₂ → emit
                            ├─→ critic₂ ──────────→ emit
                            └─────────────────────→ emit
```

## lexplainables-specifieke afwijkingen

1. **Geen `advance_node`/worker-chaining.** Er is hier maar één worker (annotatie); na `emit` gaat
   de graaf direct naar `END`. `advance_node`'s hele bestaansreden (tussen meerdere workers
   schakelen) is niet van toepassing — zelfde redenering als stories 045/046 voor eerdere
   ontbrekende machinerie.
2. **Geen SSE-events.** `emit_node` stuurt in de referentie `run`/`element`/`suggestie`/
   `ontbrekend`/`token`-events. Zonder streaming-laag levert `emit_node` hier in plaats daarvan één
   keer een finale structuur terug in de state: de definitieve `voorstellen`, `suggesties`
   (via `openstaand_voorstel`) en `ontbrekend`, plus een samenvattende `answer`-tekst. Geen
   `AgentRun`/`run`-event (provenance zonder export-consument, nog niet nodig).
3. **Supervisor-routing via `doel`, niet via een NL-vraag.** De referentie kan via een
   `WORKERS:`-allowlist ook uit een vrije tekstvraag ("annoteer artikel 5") afleiden dat het om
   annotatie gaat. Hier bestaat nog geen API/UI die zo'n vraag zou kunnen produceren — de enige
   realistische aanroeper (tot nu toe: mijn eigen tests) geeft `state["doel"]` al direct mee. Route
   daarom simpel op aanwezigheid van `doel`: is die gezet, dan gaat de graaf rechtstreeks naar
   `annoteer` (geen supervisor-LLM-call nodig — er valt niets te kiezen als het doel al vaststaat).
   Zonder `doel` werkt de supervisor exact als voorheen (QA-routing, ongewijzigd). Dit is dezelfde
   soort bewuste, beargumenteerde afbakening als stories 045/047 al toepasten op ontbrekende
   machinerie — geen halve implementatie van de NL-route, maar een expliciete keuze om hem nog niet
   te bouwen totdat er een aanroeper is die hem nodig heeft.
4. **`herzie_node` leest `state["doel"]`/`state["corpus"]` direct**, geen `_bepaal_doel`/`_corpus`-
   afleiding (die bestaan in de referentie voor scenario's die hier niet voorkomen — zelfde
   vereenvoudiging als `critic_node` al toepaste in story 048).
5. **Bugfix tijdens het porten**: de referentie se `herzie_node` retourneert de sleutel
   `"verworpen_fragmenten"` twee keer in dezelfde dict-literal (een kennelijke restant van een
   eerdere bewerking) — geport met de sleutel één keer, met de laatst-bedoelde waarde
   (`conditioneel op gewijzigd`).
6. **`Settings.critic_max_rondes: int = 1`** (env `CRITIC_MAX_RONDES`) — nieuw veld, 1:1 uit de
   referentie: `0` = uit (annoteer → critic → emit, geen patch/herziening ooit), `>0` = aan.

## Wijzigingen

- `agent/config.py` — `critic_max_rondes: int = 1`.
- `agent/annotatie.py` — `PatchTelling`, `pas_critic_toe`, `openstaand_voorstel`,
  `_markeer_toegepast` toegevoegd (1:1 poort, laatste geport-uit-de-lijst-functies).
- `agent/annotatie_prompt.py` — `herziening_systeemprompt`/`herziening_userprompt` toegevoegd (1:1
  poort). Alle vier annotatie-prompt-functies nu compleet.
- `agent/orchestrator.py` —
  - Nieuwe pure functie `_heeft_doel(state) -> str` ("annoteer" | "supervisor").
  - `patch_node(state)` — code-only, roept `pas_critic_toe` aan.
  - `route_na_critic(state, *, settings)` / `route_na_patch(state)` — pure routing, 1:1 poort
    (lineair: geen cyclus).
  - `herzie_node(state, *, settings, llm)` — één LLM-call, `herziening_systeemprompt`/
    `herziening_userprompt`, verwerkt via `annotatie._verwerk(..., geldige_ids=...)`.
  - `emit_node(state)` — bouwt de finale structuur (zie afwijking 2), geen SSE.
  - `build_graph`: `START` routeert via `_heeft_doel` naar `annoteer` of `supervisor` (voor beide
    `enable_decomposition`-varianten); nieuwe edges `annoteer→critic→(patch|emit)→
    (herzie|critic|emit)→herzie→critic`, `emit→END`.

## Acceptatiecriteria

- [x] Een rood+vervang-Critic-instructie wordt door `patch_node` automatisch doorgevoerd (klasse
      en/of tekst aangepast, `toegepast=True`), zonder LLM-call. Unit + live (4× toegepast).
- [x] Een geel-instructie verandert nooit de hoofdklasse — wordt een alternatief; een markering van
      de jurist (`van_jurist`) blijft altijd ongemoeid. Unit-geverifieerd.
- [x] Na een patch die iets wijzigde, volgt een tweede Critic-beoordeling vóór `emit` (niet
      rechtstreeks); na een patch zonder wijziging gaat het direct naar `emit`. Unit + live
      (`critic_ronde: 2` in de live-run).
- [x] `herzie_node` herstelt een verworpen fragment of voegt een gemeld ontbrekend element toe,
      behoudt bestaande id's/critic-geschiedenis/alternatieven bij een inhoudelijk ongewijzigd
      element, en een mislukte herziening laat de vorige voorstellen ongemoeid. Unit-geverifieerd.
- [x] `emit_node` levert een finale structuur met de laatste voorstellen, openstaande suggesties
      (uit een niet-uitgevoerde eindronde-instructie) en de ontbrekend-lijst. Unit + live (2
      suggesties, 1 ontbrekend in de live-run).
- [x] `build_graph(...).invoke({"doel": {...}})` doorloopt de volledige keten tot `emit` zonder de
      supervisor aan te roepen; zonder `doel` werkt de bestaande QA-routing ongewijzigd (alle 195
      bestaande tests bleven ongewijzigd slagen).
- [x] Live-geverifieerd: een volledige annotatie-run op artikel 1 IW 1990 — 5 voorstellen, 4
      correcties toegepast, 2 open suggesties, geen crash.

## Buiten scope

`advance_node`/worker-chaining, SSE-events, jurist-marking-merge, NL-vraag-gebaseerde
annotatie-routing via de supervisor, checkpointer/streaming, API-laag — zie §Afwijkingen.

## Prioriteit / story points

Prioriteit: **high**. Story points: **5** (grootste story van deze werkstroom: 4 nieuwe/
uitgebreide functies + graaf-wiring die twee bestaande topologieën raakt).

## Verificatie

- `pytest -q -m "not integration"`: 213 passed (195 bestaand ongewijzigd + 18 nieuw).
- `ruff check . && ruff format --check .`: schoon.
- `pytest -q -m integration`: 9 passed.
- Live sanity-check op `build_graph(...).invoke({"doel": {...}})` (artikel 1 IW 1990):
  `critic_ronde=2`, `patch_toegepast=4`, `suggesties=2`, antwoord "Ik heb 5 JAS-elementen
  voorgesteld; 4 met aandacht; 1 mogelijk ontbrekend." — de patch/herzie/emit-keten draait
  daadwerkelijk, niet alleen in tests.

## Gebouwd:

Ja (PR #87).
