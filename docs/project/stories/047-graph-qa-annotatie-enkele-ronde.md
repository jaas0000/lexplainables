# Story 047 — graph-qa: annotatie (enkele ronde, geen critic)

## Verhaal

Als jurist wil ik dat de agent één bepaling (artikel + eventueel lid) kan doorlezen en de
juridische elementen erin volgens het Juridisch Analyseschema (JAS) markeren en classificeren —
brongetrouw (alleen letterlijke fragmenten uit de tekst), zodat ik met een voorlopige, door de
computer voorgestelde annotatie kan beginnen in plaats van vanaf niets.

## Aanleiding

Eerste story van de **annotatieketen**-werkstroom (`docs/project/migratie-wetsanalyse.md` §Fase 4,
punt 13: "annotatie-worker" binnen de ~25-35 story-schatting voor `tools/graph-qa`). De
referentie se volledige keten is groot en zelf iteratief gebouwd ("zeven van de vijfentwintig
commits repareerden die lus", zie `tools/graph-qa/CLAUDE.md` §De annotatie-keten in de
referentie):

```
ophaal (agent ⇄ tools) → annoteer → critic₁ → patch ─┬─→ herzie → critic₂ → emit → advance
                                                     ├─→ critic₂ ──────────→ emit
                                                     └─────────────────────→ emit
```

Zelfde aanpak als de antwoord-agent-loop (stories 044-046): bouw de **kleinste zelfstandig
bewijsbare snede** eerst, zonder de rest erbij te bedenken. Voor de antwoord-loop was dat
`agent_node ⇄ tools_node → verify → finalize` — hier is dat **alleen `annoteer_node`**: één
LLM-call die een aangeleverde bepaling classificeert, met de brongetrouwheids- en
ontdubbelingsregels die al in de code zitten (niet in de prompt alleen). Kritiek/patch/herziening/
emit/advance en de graaf-wiring (supervisor kiest straks tussen de antwoord- en de
annotatie-worker) zijn allemaal latere, losse stories — zie §Buiten scope.

`annoteer_node` heeft zelf een harde randvoorwaarde die nog niet bestaat: de corpus-tekst van een
bepaling programmatisch ophalen (niet via de tool-trace van een LLM, die kan meerdere/afgekapte
resultaten door elkaar bevatten). Dat introduceert twee nieuwe, kleine modules
(`agent/graph/results.py`, `agent/artikel.py`) die deze story ook meebrengt — zonder die twee kan
`annoteer_node` niet bestaan, dus ze horen bij deze snede, niet bij een aparte story.

## Referentie-architectuur (relevante deel)

- `agent/graph/results.py`: `parse_select(tsv) -> list[dict[str, str]]` — parseert SPARQL Query
  Results TSV (het formaat dat de GraphDB-MCP voor een `SELECT` teruggeeft) naar rijen.
- `agent/artikel.py`: `artikel_corpus(bwb_id, artikel, graph, lid=None) -> str` — haalt de
  ledenteksten van één bepaling op (numeriek gesorteerd, met een `get_bepaling`-terugval voor
  decimale/circulaire-nummers) en voegt ze samen tot één corpus-string. Dezelfde functie backt in
  de referentie zowel de annotatie-corpus als `GET /v1/artikel` (documentpaneel) — hier alleen het
  eerste; het tweede is een latere API-laag-story.
- `agent/jas_klassen.py`: `JasKlasse(naam, omschrijving, vraag, uitdrukkingswijze)`-dataclass +
  `JAS_KLASSEN`-tuple (13 stuks) + `JAS_KLASSEN_VOLGORDE`/`GELDIGE_JAS_KLASSEN`, "vers afgeleid"
  van de primaire bron (niet een 1:1 kopie van de markdown-referentie — alleen de 13 canonieke
  namen + volgorde moeten matchen, bewaakt door een drift-guard-test).
- `agent/annotatie.py`: `_verwerk(llm_text, corpus, bwb_id, artikel, scope_lid=None,
  geldige_ids=None) -> (list[AnnotatieVoorstel], list[VerworpenFragment])` — het hart: parseert de
  LLM-JSON (`_parse_elementen`, met een brace-balanced salvage-pad voor afgekapte/omkaderde
  respons), valideert per element de klasse (moet in `GELDIGE_JAS_KLASSEN`) en de brongetrouwheid
  (`komt_letterlijk_voor`/genormaliseerde substring-match), ontdubbelt via `sleutel_van(tekst, lid)`
  (bewust zónder klasse — een tweede lezing met een andere klasse wordt een `alternatief`, geen
  tweede element), en berekent de `vindplaats`. Verworpen fragmenten gaan met reden terug
  (`ongeldige_klasse`/`niet_letterlijk`), niet als kale teller.
- `agent/annotatie_prompt.py`: `annotatie_systeemprompt()` (de 13 JAS-klassen, brongetrouwheids-
  regel, strikt-JSON-uitvoerformaat) + `annotatie_userprompt(bwb_id, artikel, artikeltekst, lid)`.
- `orchestrator.py`'s `annoteer_node` (referentie, regels 854-954): haalt de corpus op (of
  hergebruikt wat de ophaal-agent al ophaalde), doet één `llm.create()`-call, verwerkt het
  resultaat via `_verwerk()`. In de referentie ook: kandidaten/ONDERWERP-afhandeling,
  jurist-marking-merge, SSE-events — allemaal buiten scope hier (zie hieronder).

## lexplainables-specifieke afwijkingen (bewust, met reden)

1. **Geen ophaal-agent, geen graaf-wiring.** De referentie routeert via de supervisor naar een
   ophaal-agent (`agent_node` als `retrieval`-specialist) die zelf een bepaling opzoekt, en dan
   pas naar `annoteer_node`. Deze story neemt aan dat de bepaling al bekend is (`doel`:
   bwbId/artikel/lid, rechtstreeks meegegeven) — `annoteer_node` is een losstaande, direct
   aanroepbare functie, **niet** in `build_graph`/de supervisor-routing gewired. Zelfde patroon
   als stories 029/039-041: de bouwstenen bestaan eerst zelfstandig, story 044 was pas de eerste
   die ze daadwerkelijk aan een graaf knoopte. Hoe annotatie straks bij de supervisor terechtkomt
   (een nieuwe workerkeuze naast `antwoord`?) is een eigen, latere architectuurbeslissing — dat nu
   meenemen zou deze al grote story verder opblazen.
2. **Geen critic/patch/herzie/emit/advance.** `annoteer_node` levert ruwe, gegronde voorstellen —
   geen kwaliteitsoordeel, geen correctieronde, geen SSE-emissie, geen worker-doorschakeling. Elk
   van die vijf is een eigen vervolgstory (zie §Buiten scope).
3. **Geen kandidaten/ONDERWERP-afhandeling.** De referentie herkent een vage "onderwerp"-opdracht
   (i.p.v. een concrete bepaling) en levert dan een kandidatenlijst i.p.v. te annoteren. Dat vraagt
   UI-interactie (de jurist kiest een kandidaat) die hier nog niet bestaat — `annoteer_node`
   verwacht een concreet `doel`.
4. **Geen jurist-marking-merge (`van_jurist`).** Die stap voegt bestaande, door de jurist gemaakte
   markeringen (uit `api/annotatie`) toe als bevroren voorstellen. Dat vraagt de contractgrens
   tussen `tools/graph-qa` en `api` (ADR-0002) op te lossen — een latere integratiestory, niet iets
   om hier terloops te doen. Zie ook punt 6.
5. **`artikel.py`: alleen `artikel_corpus`, niet `haal_artikel_sync`.** Dat laatste backt de
   referentie se `GET /v1/artikel` (documentpaneel-weergave) — die endpoint bestaat hier nog niet
   (API-laag is een latere story). Bouw 'm niet vooruitlopend; `_leden_en_corpus` (het gedeelde
   binnenste) blijft wél intern herbruikbaar zodra die endpoint er komt.
6. **Geen integratie met `api/app/features/annotatie`.** Dat bestaande contract (`AnnotatieElement`
   met `levenscyclus`/`span`/`herkomst`/`beslissingen`/`diff`, `aandacht: Aandacht | None`) verschilt
   bewust van `AnnotatieVoorstel` (`aandacht: str = ""`, geen `levenscyclus`/`span`) — exact het
   soort contractgrens-mismatch dat de referentie se eigen `CLAUDE.md` beschrijft
   ("`naar_contract`... geen typefout maar een 422 op de PUT"). Deze story vertaalt niets aan die
   grens; dat gebeurt pas in de story die de twee daadwerkelijk aan elkaar knoopt.

## Wijzigingen

- `agent/graph/results.py` (nieuw) — `parse_select()`, 1:1 poort.
- `agent/artikel.py` (nieuw) — `artikel_corpus()` + `_leden_en_corpus`/`_bepaling_fallback`/
  `_controleer_vindplaats`/`_lidsleutel`/`_match_lid`/`OngeldigeVindplaats`, 1:1 poort minus
  `haal_artikel_sync` (zie §Afwijkingen punt 5). Gebruikt `agent/graph/queries.py`'s al bestaande
  `get_artikel`/`get_bepaling`/`get_regeling_info`/`regeling_iri`/`_art`/`_num`/`_nummer_vrij`
  (story 041) — geen nieuwe SPARQL-bouwers nodig, zie daar.
- `agent/jas_klassen.py` (nieuw) — `JasKlasse`-dataclass + `JAS_KLASSEN`/`JAS_KLASSEN_VOLGORDE`/
  `GELDIGE_JAS_KLASSEN`, 1:1 poort (13 klassen, "vers afgeleid" net als de referentie).
- `agent/models.py` (aangepast) — `AnnotatieVoorstel`, `AnnotatieAlternatief`, `VerworpenFragment`
  toegevoegd (velden 1:1 uit de referentie, zie §Referentie-architectuur). Bewust **niet**
  toegevoegd: `CriticRonde`, `CriticOordeel`, `OntbrekendItem`, `AgentRun` (horen bij latere
  stories).
- `agent/annotatie.py` (nieuw) — `_normaliseer`, `komt_letterlijk_voor`, `sleutel_van`,
  `_balanced_objecten`, `_parse_elementen`, `_voeg_alternatief_toe`, `_verwerk`, 1:1 poort. Bewust
  niet meegenomen: `pas_critic_toe`, `demp_zelfweerspreking`, `vervang_ids_door_citaat`,
  `openstaand_voorstel`, `_markeer_toegepast`, `_verwerk_critic`, `PatchTelling`.
- `agent/annotatie_prompt.py` (nieuw) — `annotatie_systeemprompt()`/`annotatie_userprompt()`, 1:1
  poort. Bewust niet meegenomen: `critic_systeemprompt`/`critic_userprompt`/`_stand_van`/
  `_vorige_ronde_blok`, `herziening_systeemprompt`/`herziening_userprompt`.
- `agent/orchestrator.py` (aangepast) —
  - `State`: `doel: dict[str, str]`, `corpus: str`, `voorstellen: list[dict[str, Any]]`,
    `verworpen_fragmenten: list[dict[str, Any]]` erbij (velden, geen nieuwe nodes/edges).
  - Nieuwe, **losstaande** functie `annoteer_node(state, *, settings, llm, graph)`: haalt de
    corpus op via `artikel.artikel_corpus(doel["bwbId"], doel["artikel"], graph, doel.get("lid"))`,
    doet één `llm.create()`-call (`system=annotatie_systeemprompt()`, `tools=[]`,
    `max_tokens=8192`, matcht de referentie), verwerkt het resultaat via `_verwerk()`. Return
    `{"voorstellen": [...], "verworpen_fragmenten": [...], "corpus": corpus}`. **Niet** toegevoegd
    aan `build_graph` — rechtstreeks aanroepbaar/testbaar, geen supervisor-routing.

## Acceptatiecriteria

- [x] Gegeven een `doel` (bwbId/artikel/lid), haalt `annoteer_node` de corpus-tekst gericht op via
      `artikel.artikel_corpus` (niet uit een tool-trace). Unit- én live-geverifieerd.
- [x] De classificatie levert alleen `AnnotatieVoorstel`s met een geldige JAS-klasse en een
      fragment dat letterlijk in de opgehaalde corpus voorkomt; een ongeldige klasse of een
      niet-letterlijk fragment wordt geweigerd en komt terug als `VerworpenFragment` met de juiste
      reden (`ongeldige_klasse`/`niet_letterlijk`). Unit-geverifieerd
      (`test_verwerk_verwerpt_ongeldige_klasse`, `test_verwerk_verwerpt_niet_letterlijk_fragment`).
- [x] Twee voorstellen met hetzelfde fragment+lid ontdubbelen tot één element; hetzelfde fragment
      onder een andere klasse wordt een `alternatief` op het eerste element, geen tweede element.
      Unit-geverifieerd, en zichtbaar live (zie §Verificatie: "invordering van rijksbelastingen"
      kreeg terecht een alternatief in plaats van een tweede element).
- [x] Een door het model meegegeven `id` wordt behouden (voorbereidend op een latere
      revisieronde); zonder `id` wordt er één toegekend. Unit-geverifieerd.
- [x] Een afgekapte, omkaderde of met proza omhulde LLM-respons wordt toch (deels) geparsed via de
      balanced-braces-salvage, zolang er complete `{klasse, tekst, ...}`-objecten in zitten.
      Unit-geverifieerd (4 varianten: volledig, code-fence, omringend proza, afgekapt).
- [x] Live-geverifieerd: een echte bepaling uit de Invorderingswet-fixture met duidelijke
      normatieve inhoud (niet een pure definitie-opsomming) levert brongetrouwe, herkenbaar
      correcte JAS-classificaties op. Zie §Verificatie.

## Buiten scope

Ophaal-agent + graaf-wiring (supervisor-routing naar een annotatie-worker), critic-ronde,
patch-toepassing, herziening, emit (SSE), advance (worker-doorschakeling), kandidaten/ONDERWERP-
afhandeling, jurist-marking-merge, `GET /v1/artikel`/`haal_artikel_sync`, integratie met
`api/app/features/annotatie` — zie §Afwijkingen voor de reden per punt. Elk van deze is een eigen,
latere story.

## Prioriteit / story points

Prioriteit: **high** (eerste story van de annotatieketen-werkstroom, expliciet genoemd in
`docs/project/migratie-wetsanalyse.md` §Fase 4).
Story points: **5** — grootste story van deze werkstroom tot nu toe: twee nieuwe voorwaardelijke
modules (`results.py`/`artikel.py`) plus de kernannotatielogica, meerdere nieuwe entiteiten
(`AnnotatieVoorstel`/`VerworpenFragment`/`JasKlasse`), meerdere niet-triviale businessregels met
randgevallen (brongetrouwheid, ontdubbeling-vs-alternatief, id-behoud, salvage-parsing bij een
kapotte respons).

## Verificatie

- `uv run --extra dev pytest -q -m "not integration"` — **176 passed, 6 deselected** (144
  bestaand, ongewijzigd + 32 nieuw: 7 `test_results.py` + 5 `test_jas_klassen.py` + 7
  `test_artikel.py` + 12 `test_annotatie.py` + 1 `test_orchestrator.py`-aanvulling).
- `uv run ruff check . && uv run ruff format --check .` — schoon (meerdere E501's in geport
  proza/docstrings gefixt zonder de geport logica of prompt-tekst te wijzigen — de herschreven
  `annotatie_systeemprompt()` is byte-voor-byte geverifieerd identiek aan de triple-quoted
  bronvorm; 1 SIM102 in `_balanced_objecten` opgelost, gedrag ongewijzigd).
- `uv run --extra dev pytest -q -m integration` (tegen de lokale `deploy/graphdb`-stack + Azure
  Foundry) — **7 passed** (de bestaande 6 + de nieuwe live-annotatietest).
- Handmatig doorgelicht: `annoteer_node` op **artikel 1** van de Invorderingswet 1990 (gekozen
  boven artikel 2 — dat is een pure definitie-opsomming; artikel 1 heeft een echte
  toepassingsbereik- en uitzonderingsbepaling, betere JAS-proef) leverde 5 grounded voorstellen,
  0 verworpen fragmenten:
  - `[Rechtsobject] "rijksbelastingen"`, `[Rechtsfeit] "invordering van rijksbelastingen"` (met
    een `Voorwaarde`-alternatief — genuine dubbelzinnigheid, correct als alternatief i.p.v. een
    tweede element), `[Voorwaarde] "bij de invordering van rijksbelastingen"` (met een
    `Rechtsfeit`-alternatief — dezelfde ontdubbeling in de andere richting).
  - `[Brondefinitie] "artikel 3:40, ... afdeling 10.2.1 van de Algemene wet bestuursrecht"`,
    `[Rechtsbetrekking] "niet van toepassing"` voor lid 2's Awb-uitzondering.
  - Alle fragmenten letterlijk in de opgehaalde corpus geverifieerd (de dedup/grounding-
    mechaniek werkt correct). De `Brondefinitie`-classificatie van de Awb-opsomming is
    inhoudelijk discutabel (eerder een opsomming binnen een uitzonderingsbepaling dan een
    JAS-brondefinitie) — precies het soort beoordelingsfout dat de critic-ronde (een latere
    story) hoort te signaleren, geen gebrek in de hier geport grounding/ontdubbelings-logica.

## Gebouwd:

Ja (PR #84).
