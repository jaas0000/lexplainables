# Story 046 — graph-qa: decompositie (multi-hop)

## Verhaal

Als jurist wil ik dat de agent een vraag die uit meerdere losse onderdelen bestaat ("wat is een
belastingschuldige, en welk artikel regelt de aansprakelijkheid van een bestuurder?") in delen
opsplitst en elk deel apart onderzoekt — in plaats van dat één tool-lus moet uitzoeken welke van
de twee onderwerpen als eerste aan bod komt en het risico loopt het tweede onderdeel te missen.

## Aanleiding

Vervolg op story 045 (supervisor: specialist-routing + afwijzen). De referentie se
`enable_decomposition`-toggle vertakt de graaf naar een multi-hop-stroom: **decompose → solve →
synthesize → verify → (resynth) → finalize**, die de bestaande `agent_node ⇄ tools_node`-lus voor
de antwoord-worker vervangt. Staat de toggle uit, dan is de bestaande stroom (stories 044-045)
byte voor byte ongewijzigd — dat is ook hier het uitgangspunt: deze story voegt een graaf-variant
tóé, ze vervangt niets van wat er al staat.

## Referentie-architectuur (relevante deel)

`orchestrator.py`: `decompose_node` (één `llm.create`-call, splitst in genummerde deelvragen,
`max_subquestions`-cap, fallback naar de hele vraag als één deelvraag bij een onherkenbaar
antwoord); `solve_node` (per deelvraag een eigen agent⇄tools-lus met lokale scratch-messages,
`sub_max_turns`-cap, gedeelde `source_trace`; bij precies één deelvraag is de tool-loze
eindbeurt meteen het eindantwoord — synthese wordt overgeslagen); `route_after_solve` (1 deelvraag
→ `verify`, anders → `synthesize`); `synthesize_node` (één `llm.create`-call die de
deelbevindingen samenvoegt tot één antwoord; bij een eerdere afkeuring met `unsupported` krijgt
het systeemblok een correctie-instructie mee); `resynth_node` (zet `corrected: True`/`answer: ""`
en routeert terug naar `synthesize`, in plaats van `correct_node`'s terugkeer naar `agent`).

## lexplainables-specifieke afwijkingen (bewust, met reden)

1. **Geen `_memory_context(state)`.** Die functie leest gespreksgeheugen uit een checkpointer, die
   hier nog niet bestaat (aparte, latere story — zie CLAUDE.md §Volgende stap). `decompose_node`
   en `solve_node` krijgen dus geen geheugen-context mee; dat komt erbij zodra de checkpointer er
   is, zonder dat deze story's structuur hoeft te veranderen.
2. **Geen streaming/`get_stream_writer`/`reason`-events.** Er is nog geen SSE-/API-laag om naar te
   streamen (zelfde afwijking als stories 044-045). `solve_node` gebruikt `llm.create()` in een
   lus (zoals `agent_node` al doet), niet `llm.stream()`; `synthesize_node` doet één `llm.create()`
   in plaats van een gestreamde call.
3. **Geen `_stap`/statusregel-narratie.** Die hoort bij de SSE-laag (`writer(...)`-aanroepen) die
   hier nog niet bestaat.
4. **`solve_node` gebruikt wél de `[stabiel, variabel]`-cachingsplit** (`ports.Systeem`), in
   tegenstelling tot stories 044-045, die daar bewust vanaf zagen. Reden: 044/045 hebben nooit
   meer dan één `llm.create`-call met hetzelfde systeemblok binnen één graafinvocatie — caching
   heeft daar niets om op te herhalen. `solve_node` roept de LLM wél herhaald aan met een stabiele
   `base_system` (identiteit + specialist-addendum) en een groeiend variabel deel (deelbevindingen
   van eerdere deelvragen) — precies het scenario waar de al bestaande, tot nu toe ongebruikte
   caching-laag in `adapters/anthropic_llm.py` (story 039) voor gebouwd is. Dit is dus geen nieuwe
   afwijking maar de eerste keer dat een al bestaande mogelijkheid daadwerkelijk baat heeft.
5. **`resynth`/`synthesize_node`'s correctie-instructie dekt ook `niet_letterlijk`, niet alleen
   `unsupported`.** De referentie corrigeert bij een herkansing alleen niet-onderbouwde
   vindplaatsen; lexplainables' eigen `correct_node` (story 044) documenteert expliciet waarom dat
   een bug is ("een antwoord dat enkel op citaten struikelde kreeg dan een correctie-call met een
   lege opsomming") en behandelt `unsupported` én `niet_letterlijk` als twee aparte, allebei te
   benoemen categorieën. Deze story past die al aanwezige, bewuste correctie ook toe op
   `synthesize_node`'s herkansingsinstructie — anders zou dezelfde bugklasse hier terugkeren.
6. **Geen annotatie-tak in de routing-map.** De referentie se `entrymap` bevat ook `"annoteer"`
   (de annotatie-worker bestaat hier niet — zelfde afwijking als story 045 §Afwijkingen punt 1).
   `route_after_supervisor` blijft ongewijzigd (`"afwijzen"`/`"agent"`); de decompositie-graaf
   hergebruikt 'm met een andere edge-map (`"agent"` → node `"decompose"` i.p.v. node `"agent"`).

## Wijzigingen

- `agent/config.py` — nieuwe velden: `enable_decomposition: bool = False`,
  `max_subquestions: int = 5`, `sub_max_turns: int = 8` (env: `ENABLE_DECOMPOSITION`,
  `MAX_SUBQUESTIONS`, `SUB_MAX_TURNS`).
- `agent/orchestrator.py` (aangepast) —
  - `State`: `sub_questions: list[str]`, `sub_findings: list[dict[str, str]]` erbij.
  - Nieuwe prompts `_DECOMPOSE_SYSTEM`/`_SYNTHESE_SYSTEM` (module-niveau constanten, zoals de
    referentie ze ook niet in `prompts.py` zet).
  - Nieuwe pure, testbare functie `_parse_subquestions(text, cap) -> list[str]` (zelfde patroon
    als `supervisor.parse_supervisor` uit story 045: de parseerlogica los van de node zelf).
  - Nieuwe nodes: `decompose_node`, `solve_node`, `synthesize_node`, `resynth_node`.
  - Nieuwe routing: `route_after_solve(state) -> "verify" | "synthesize"`.
  - `build_graph`: vertakt op `settings.enable_decomposition` naar de bestaande graaf (ongewijzigd)
    of de nieuwe multi-hop-graaf, die `verify_node`/`finalize_node`/`afwijs_node` en
    `route_after_supervisor`/`route_after_verify` hergebruikt met een andere edge-map.
  - `finalize_node`: kleine aanvulling — in de decompositie-stroom zet hij het eindantwoord ook in
    `messages` (state-vorm-consistentie voor een latere checkpointer, zelfde soort fix als
    `afwijs_node` in story 045; de referentie doet dit ook, met dezelfde reden).

Nieuwe topologie (alleen actief bij `enable_decomposition=True`):
```
START → supervisor_node → (afwijs_node → END)
                         → decompose_node → solve_node
                           → (verify_node, als 1 deelvraag)
                           → (synthesize_node → verify_node, als >1 deelvraag)
                         → verify_node → (resynth_node → synthesize_node | finalize_node) → END
```

## Acceptatiecriteria

- [x] `enable_decomposition=False` (default): de graaf en elk bestaand gedrag uit stories 044-045
      blijven ongewijzigd — alle 136 bestaande tests in `test_orchestrator.py` slagen zonder
      wijziging (regressie-bewijs, geen enkele bestaande test aangeraakt).
- [x] Een enkelvoudige vraag met `enable_decomposition=True` levert precies één deelvraag (gelijk
      aan de oorspronkelijke vraag), slaat `synthesize_node` over, en het antwoord komt rechtstreeks
      uit `solve_node`. Unit-geverifieerd (`test_decompositie_enkelvoudige_vraag_slaat_synthese_over`).
- [x] Een samengestelde vraag met `enable_decomposition=True` wordt in ≥2 deelvragen gesplitst, elke
      deelvraag krijgt een eigen agent⇄tools-lus, de `source_trace` accumuleert over alle
      deelvragen, en `synthesize_node` combineert de bevindingen tot één antwoord. Unit- én
      live-geverifieerd (zie §Verificatie).
- [x] Een ongegronde synthese krijgt precies één herkansing via `resynth_node` →
      `synthesize_node` (niet terug naar `decompose`/`solve`), met een correctie-instructie die
      zowel `unsupported` als `niet_letterlijk` benoemt. Unit-geverifieerd
      (`test_decompositie_ongegronde_synthese_krijgt_precies_een_herkansing`).
- [x] `max_subquestions` begrenst het aantal deelvragen; een onherkenbaar/leeg
      decompositie-antwoord valt terug op één deelvraag (de oorspronkelijke vraag), nooit een crash.
      Unit-geverifieerd (`parse_subquestions`-tests + `test_decompositie_*`).
- [x] Live-geverifieerd: een echte samengestelde vraag tegen de lokale GraphDB + Foundry levert
      zichtbaar meerdere deelvragen, een gedeelde bronnenlijst en één samenhangend eindantwoord.
      Zie §Verificatie voor de handmatig doorgelichte respons.

## Buiten scope

Checkpointer/gespreksgeheugen (`_memory_context`), streaming/SSE/statusregel-narratie,
annotatieketen, API-laag — zie §Afwijkingen voor de reden per punt.

## Prioriteit / story points

Prioriteit: **high** (derde story van de agent-loop-werkstroom, direct vervolg op 045).
Story points: **4** — nieuwe graaf-topologie-variant met vier nieuwe nodes en een nieuwe
routing-functie, hergebruikt bestaande verify/finalize/afwijzen-infrastructuur, geen auth/rollen,
blijft binnen één module (`orchestrator.py` + drie nieuwe `config.py`-velden).

## Verificatie

- `uv run --extra dev pytest -q -m "not integration"` — **144 passed, 5 deselected** (136
  bestaande + 8 nieuwe: 3 `parse_subquestions`-tests + 5 graaf-niveau-tests).
- `uv run ruff check . && uv run ruff format --check .` — schoon (3 regels E501 in de nieuwe
  prompt-constanten onderweg gefixt, 2 bestanden door `ruff format` herschikt).
- `uv run --extra dev pytest -q -m integration` (tegen de lokale `deploy/graphdb`-stack + Azure
  Foundry) — **6 passed** (de 3 bestaande + de nieuwe `test_live_decompositie_splitst_een_
  samengestelde_vraag`).
- Handmatig doorgelicht: *"Wat is een belastingschuldige, en wat is een belastingaanslag, volgens
  de Invorderingswet 1990?"* met `enable_decomposition=True` → gesplitst in exact de twee
  verwachte deelvragen, elk correct beantwoord tegen een ander onderdeel van artikel 2 lid 1
  (belastingschuldige → onderdeel k, belastingaanslag → onderdeel m), 27 bronnen verzameld,
  `grounding_niveau: gegrond`, en één samenhangend, correct gestructureerd eindantwoord met
  letterlijke citaten uit beide onderdelen.

## Gebouwd:

Ja (PR #83).
