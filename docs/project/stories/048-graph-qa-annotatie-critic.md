# Story 048 — graph-qa: annotatie-critic (kwaliteitsoordeel over voorstellen)

## Verhaal

Als jurist wil ik dat de agent zijn eigen JAS-voorstellen laat controleren vóórdat ik ze te zien
krijg — een tweede blik die aangeeft welke markeringen zeker zijn (groen), welke twijfelachtig
zijn en waarom (geel), en welke waarschijnlijk fout zijn (rood) — zodat ik weet waar ik extra
aandacht aan moet besteden in plaats van elk voorstel even kritisch te moeten doorlezen.

## Aanleiding

Tweede story van de annotatieketen-werkstroom, vervolg op story 047 (`annoteer_node`, enkele
ronde zonder critic). Deze story voegt de **Critic** toe: één LLM-call die elk voorstel uit
`annoteer_node` beoordeelt op een aandacht-niveau (groen/geel/rood) + een actie
(behoud/vervang/verwijder), en waarschijnlijk gemiste elementen signaleert. Nog steeds **geen**
patch (het uitvoeren van de rode+vervang-instructies), **geen** herziening, **geen** emit/advance,
en **geen** graaf-wiring — zie §Buiten scope.

## Referentie-architectuur (relevante deel)

`orchestrator.py`'s `critic_node` (regels 956-1064): één `llm.create`-call (`max_tokens=2048`,
geen tools) met `critic_systeemprompt()`/`critic_userprompt()`, verwerkt via `_verwerk_critic()`.
Zet per voorstel `aandacht`/`critic` (motivatie, met interne ids vervangen door een kort citaat via
`vervang_ids_door_citaat`), voegt een `CriticRonde`-trail-entry toe. Bij ronde ≥2 dempt
`demp_zelfweerspreking()` een eindoordeel dat de eigen, al uitgevoerde correctie terugdraait. Faalt
de call, dan breekt de keten niet: voorstellen blijven ongemoeid, `critic_gefaald=True`.

`agent/annotatie.py`: `_verwerk_critic(llm_text, ids) -> (dict[id, CriticOordeel],
list[OntbrekendItem])` — koppelt op `id` met `index`-fallback, normaliseert ongeldige waarden
(onbekende `aandacht` → genegeerd; `verwijder` zonder `rood` → `vervang`; `vervang` zonder
`voorstel_klasse`/`voorstel_tekst` → `behoud`; een verzonnen `voorstel_klasse` buiten de 13 → leeg).
`demp_zelfweerspreking(voorstellen) -> int` en `vervang_ids_door_citaat(motivatie, voorstellen) ->
str` (interne hex-ids in de motivatie vervangen door een kort citaat van het bedoelde element).

`agent/annotatie_prompt.py`: `critic_systeemprompt()` + `critic_userprompt(voorstellen,
artikeltekst, gemeld_ontbrekend)`, met `_stand_van`/`_vorige_ronde_blok` (het "wat zei je vorige
ronde"-geheugenblok, nodig zodat de Critic bij een tweede pas niet blind herhaalt).

## lexplainables-specifieke afwijkingen (bewust, met reden)

1. **Nog steeds losstaand, niet in `build_graph` gewired.** Zelfde patroon als `annoteer_node`
   (story 047 §Afwijkingen punt 1) — de graaf-wiring (supervisor kiest tussen antwoord-/
   annotatie-worker, `annoteer → critic → …`-edges) is een eigen, latere story.
2. **Geen SSE/statusregel-narratie** (`_stap`, `_critic_melding`, `get_stream_writer`) — er is nog
   geen streaming-laag (zelfde afwijking als alle voorgaande stories in deze werkstroom).
3. **Geen `_corpus(state)`-helper.** De referentie heeft die omdat de corpus soms vers wordt
   opgehaald en soms uit state komt; hier zet `annoteer_node` (story 047) `state["corpus"]` altijd
   — `critic_node` leest dat rechtstreeks.
4. **Geen `openstaand_voorstel`/`_markeer_toegepast`.** Die horen bij `patch_node`/`emit_node`
   (een latere story) — `critic_node` levert alleen het oordeel, voert niets uit.
5. **`van_jurist`/`aangepast_na_kritiek`-dictsleutels** die de prompt-helpers raadplegen
   (`v.get("van_jurist")`, `voorstel.get("aangepast_na_kritiek")`) bestaan hier nog niet op een
   voorstel (geen jurist-marking-merge, story 047 §Afwijkingen punt 4) — ze evalueren simpelweg
   falsy/afwezig, wat correct gedrag oplevert zonder speciale behandeling.
6. **`_ontbrekend_sleutel`** (dedup-sleutel voor gemelde ontbrekende elementen) verhuist van
   `orchestrator.py` (waar de referentie 'm plaatst) naar dezelfde plek hier — geen inhoudelijke
   wijziging, alleen waar de functie staat.

## Wijzigingen

- `agent/models.py` (aangepast) — `CriticOordeel`, `OntbrekendItem`, `CriticRonde` toegevoegd (1:1
  velden uit de referentie). `AnnotatieVoorstel` krijgt nu ook `aandacht: str = ""`,
  `critic: str = ""`, `critic_rondes: list[CriticRonde] = []` (in story 047 bewust weggelaten
  "geen consument nog" — deze story is die consument).
- `agent/annotatie.py` (aangepast) — `_AANDACHT`/`_ACTIES`-constanten, `_verwerk_critic`,
  `demp_zelfweerspreking`, `vervang_ids_door_citaat` (+ `_ELEMENT_ID`-regex) toegevoegd, 1:1 poort.
  Nog niet meegenomen: `PatchTelling`, `pas_critic_toe`, `openstaand_voorstel`,
  `_markeer_toegepast`.
- `agent/annotatie_prompt.py` (aangepast) — `critic_systeemprompt()`, `critic_userprompt()`,
  `_stand_van()`, `_vorige_ronde_blok()` toegevoegd, 1:1 poort. Nog niet meegenomen:
  `herziening_systeemprompt`/`herziening_userprompt`.
- `agent/orchestrator.py` (aangepast) —
  - `State`: `critic_feedback: list[dict[str, Any]]`, `critic_ontbrekend: list[dict[str, Any]]`,
    `critic_gefaald: bool`, `critic_ronde: int`, `nieuw_ontbrekend: list[dict[str, Any]]`,
    `gemeld_ontbrekend: list[str]` erbij.
  - Nieuwe pure functie `_ontbrekend_sleutel(item) -> str` (dedup-sleutel: klasse + genormaliseerd
    fragment).
  - Nieuwe, **losstaande** functie `critic_node(state, *, settings, llm)`: bouwt de prompt uit
    `state["voorstellen"]`/`state["corpus"]`/`state.get("gemeld_ontbrekend")`, één `llm.create()`
    (`max_tokens=2048`, geen tools), verwerkt via `annotatie._verwerk_critic`. Zet per voorstel
    `aandacht`/`critic` (via `vervang_ids_door_citaat`), voegt een `CriticRonde`-entry toe aan
    `critic_rondes`. Berekent `nieuw_ontbrekend`/`gemeld_ontbrekend` via `_ontbrekend_sleutel`.
    Bij `critic_ronde >= 2` (na verhoging) roept `annotatie.demp_zelfweerspreking`. Faalt de call
    (brede `except Exception`, zoals de referentie — de Critic mag de keten nooit breken): geeft
    `voorstellen` ongemoeid terug met `critic_gefaald=True`. **Niet** toegevoegd aan `build_graph`.

## Acceptatiecriteria

- [x] `critic_node` beoordeelt elk voorstel met precies één aandacht-niveau
      (groen/geel/rood) + motivatie + actie (behoud/vervang/verwijder), gekoppeld op `id` met
      `index`-terugval als het id in de respons ontbreekt. Unit-geverifieerd
      (`test_verwerk_critic_koppelt_op_id`, `test_verwerk_critic_index_terugval_bij_ontbrekend_id`).
- [x] Ongeldige/onbekende waarden worden genormaliseerd volgens de referentie-regels: een
      onbekende `aandacht`-waarde levert geen oordeel voor dat element op; `verwijder` zonder
      `aandacht="rood"` degradeert naar `vervang`; `vervang` zonder `voorstel_klasse`/
      `voorstel_tekst` degradeert naar `behoud`; een verzonnen `voorstel_klasse` buiten de 13
      geldige klassen wordt leeggemaakt. Unit-geverifieerd (6 tests in `test_annotatie.py`).
- [x] Interne element-ids die de Critic in zijn motivatie noemt, worden vervangen door een kort
      citaat van het bedoelde element (`vervang_ids_door_citaat`) — nooit een hexcode in de
      motivatie. Unit- én live-geverifieerd (zie §Verificatie — geen enkele hexcode in de live
      motivaties; index-referenties als "element [0]" blijven terecht onaangeraakt, dat zijn geen
      interne ids).
- [x] Bij een tweede beoordelingsronde (`critic_ronde >= 2`) dempt `critic_node` een eindoordeel
      dat de eigen, al uitgevoerde correctie terugdraait: het niveau zakt van rood naar geel en de
      teruggedraaide klasse komt als alternatief te staan. Unit-geverifieerd
      (`test_critic_node_ronde_twee_dempt_zelfweerspreking`).
- [x] Nieuw gemelde ontbrekende elementen worden onderscheiden van al eerder gemelde
      (`gemeld_ontbrekend`/`nieuw_ontbrekend`, dedup via `_ontbrekend_sleutel`). Unit-geverifieerd.
- [x] Een mislukte Critic-call breekt de keten niet: de voorstellen blijven ongewijzigd staan,
      `critic_gefaald=True`, geen exception naar de aanroeper. Unit-geverifieerd
      (`test_critic_node_faalpad_laat_voorstellen_ongemoeid`).
- [x] Live-geverifieerd: `critic_node` op echte voorstellen (uit een live `annoteer_node`-run)
      levert herkenbaar zinnige aandacht-niveaus en motivaties op. Zie §Verificatie.

## Buiten scope

Patch (het uitvoeren van rode+vervang-instructies), herziening, emit (SSE), advance
(worker-doorschakeling), graaf-wiring naar een annotatie-worker, `openstaand_voorstel`/
`_markeer_toegepast`, jurist-marking-merge — zie §Afwijkingen voor de reden per punt. Elk van deze
is een eigen, latere story.

## Prioriteit / story points

Prioriteit: **high** (tweede story van de annotatieketen-werkstroom, direct vervolg op 047).
Story points: **4** — drie nieuwe entiteiten (`CriticOordeel`/`OntbrekendItem`/`CriticRonde`),
meerdere niet-triviale businessregels met randgevallen (normalisatie, id-vervanging,
zelfweerspreking-demping, ontbrekend-dedup), geen nieuwe infra-modules nodig (hergebruikt story
047's `artikel.py`/`results.py`/`jas_klassen.py` volledig).

## Verificatie

- `uv run --extra dev pytest -q -m "not integration"` — **195 passed, 7 deselected** (176
  bestaand, ongewijzigd + 19 nieuw: 14 in `test_annotatie.py` + 5 `critic_node`-tests in
  `test_orchestrator.py`).
- `uv run ruff check . && uv run ruff format --check .` — schoon (`critic_systeemprompt()`
  byte-voor-byte tegen de oorspronkelijke triple-quoted vorm geverifieerd, net als
  `annotatie_systeemprompt()` in story 047).
- `uv run --extra dev pytest -q -m integration` (tegen de lokale `deploy/graphdb`-stack + Azure
  Foundry) — **8 passed** (de bestaande 7 + de nieuwe live-critic-test).
- Handmatig doorgelicht: `annoteer_node` gevolgd door `critic_node` op artikel 1 van de
  Invorderingswet 1990. De Critic ving een **echte misclassificatie**: deze live-run
  classificeerde "rijksbelastingen" als `Plaatsaanduiding` (fout — geen geografisch gebied), en
  de Critic gaf daar terecht `rood` met een concrete correctie (`Rechtsobject`). Twee andere
  elementen kregen `geel` met zinnige overwegingen (overlap tussen twee voorstellen, een kort
  fragment dat de relatie niet volledig draagt). 2 ontbrekende elementen gemeld
  (`Rechtssubject` impliciet, `Rechtsbetrekking` bij "geldt"), beide met een bruikbare reden.
  Geen enkele hexcode in de motivaties — index-referenties als "element [0]" (uit de
  prompt-eigen nummering) blijven terecht onaangeraakt door `vervang_ids_door_citaat`, dat alleen
  echte 12-hex-teken interne ids vervangt.

## Gebouwd:

Ja (PR #86).
