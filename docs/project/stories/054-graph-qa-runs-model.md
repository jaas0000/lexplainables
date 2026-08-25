# Story 054 — graph-qa: run-model (`POST /v1/runs`)

## Verhaal

Als jurist wil ik dat een beurt van de server is, niet van mijn tabblad: van gesprek wisselen,
herladen of de verbinding verliezen mag een lopend antwoord niet doden, en ik moet opnieuw kunnen
aanhaken en het resultaat alsnog zien.

## Aanleiding

Tweede story van de HTTP-laag (na 053's `/v1/chat`). `POST /v1/chat` koppelt de beurt aan de
verbinding — precies het probleem hierboven. Dit is ook de story die `stop_check` (052) eindelijk
een echte aanroeper geeft: `POST /v1/runs/{id}/cancel` zet de vlag die de graaf op de eerstvolgende
nodegrens laat stoppen.

**Vooronderzoek**: referentie `agent/runs.py` volledig gelezen (294 regels) — een in-proces
`RunRegister` met een `Condition`-gebaseerde `volg()` (geen `asyncio.Queue`, want meerdere
tabbladen kunnen tegelijk meekijken en een Queue kun je maar één keer leegdrinken), `seq` als
identiteit (niet positie — anders krijgt een aanhaker events dubbel zodra er gesnoeid is), en een
selectief cap-mechanisme dat alleen "vluchtige" events weggooit. Dat ontwerp is degelijk en uit
echte bugs voortgekomen (dubbele events, hangende SSE-streams bij een race tussen afronden en
wachten) — dit bouwt 'm over, aangepast aan lexplainables' eigen (kleinere) event-vocabulaire.

## lexplainables-specifieke afwijkingen

1. **`VLUCHTIGE_TYPES = {"token"}`**, niet `{"token", "reason", "status"}`. lexplainables' agent
   heeft nog geen `reason`-narratie of `status`-stapmeldingen (die horen bij de annotatieketen-
   route, die nog niet op `answer_stream()`/HTTP is aangesloten — zie punt 3). Alleen `token` is nu
   hoogvolume genoeg om te snoeien.
2. **Geen `agent/beurt.py`-persistentie.** De referentie schrijft aan het eind van een run naar de
   wetsanalyse-api (document/elementen/chatbericht). lexplainables heeft geen equivalent — dat
   vraagt eerst een beslissing over hoe `graph-qa` en `api` elkaar aanroepen (zie story 053
   §Afwijkingen), een aparte, latere story.
3. **`maak_stroom` roept alleen `answer_stream(question, conversation_id, ...)` aan** — geen
   `modus`/`context`/`doel` (bestaan nog niet, zie story 050/051 §Afwijkingen). Een run is dus
   altijd een QA-beurt, nooit een annotatiebeurt.
4. **`X-User-Id` optioneel, zelfde `_aanroeper`-patroon als de referentie.** lexplainables heeft
   nog geen frontend-chat/BFF die deze header zet — zonder header is `gebruiker == ""`, en een run
   zonder eigenaar is voor iedereen zichtbaar (open dev-gedrag, 1:1 met de referentie).
5. **De 409-race is op twee niveaus getest, allebei deterministisch (geen timing-gok).**
   `RunRegister` zelf unit-getest met een gecontroleerde, op een `asyncio.Event` blokkerende
   stream (`test_runs.py`); de HTTP-laag se `except RunBestaatAl → 409`-mapping apart getest met
   een kunstmatig vertraagde `_TregeLLM.create()` (`test_api.py`) — beide zonder te gokken op
   hoe snel een echte `FakeLLM` toevallig is.
6. **Cap (`MAX_EVENTS`) en bewaartermijn (`BEWAAR_NA_AFLOOP_S`) 1:1 overgenomen** (4000 resp. 600s)
   — geen reden om deze concrete, uit ervaring gekozen getallen te wijzigen.

## Wijzigingen

- `agent/runs.py` (nieuw) — poort van de referentie, met de vocabulaire-aanpassing uit punt 1:
  - `RunBestaatAl(Exception)` — draagt het actieve `run_id`.
  - `Run` (dataclass) — `run_id`/`conversation_id`/`user_id`/`vraag`/`status`
    (`loopt|klaar|gestopt|mislukt`)/`events`/`weggevallen`/`geproduceerd`/`gestart`/`eind_op`/
    `stop_gevraagd`/`taak`/`_wakker` (`asyncio.Condition`). `loopt`-property, `volgende_seq`-
    property, `samenvatting() -> dict`.
  - `RunRegister` — `get(run_id, *, user_id="")`, `actief_voor(conversation_id, *, user_id="")`,
    `start(*, conversation_id, vraag, maak_stroom, user_id="")` (raiset `RunBestaatAl` als er al
    een lopende run is op dit gesprek), `_draai`/`_rond_af`/`_voeg_toe`/`_cap` (achtergrondtaak-
    driver + selectief snoeien), `vraag_stop(run)`, `volg(run, vanaf=0)` (async generator: replay +
    live meekijken, met een `gat`-event bij een sprong in `seq`), `_ruim_op()` (verwijdert
    afgeronde runs ouder dan `BEWAAR_NA_AFLOOP_S`).
- `agent/models.py` — nieuw `RunStart` (`run_id`/`conversation_id`/`vraag`/`status`/
  `volgende_seq`/`weggevallen`), matcht `Run.samenvatting()`.
- `api/main.py`:
  - `_aanroeper(request) -> str`: leest `X-User-Id` (leeg als afwezig).
  - Module-level `runs = RunRegister()`.
  - `POST /v1/runs` (201) — start een run via `runs.start(...)`; 409 (`{"reden": "run_loopt_al",
    "run_id": ...}`) bij een actieve run op hetzelfde gesprek.
  - `GET /v1/runs/{run_id}/events?vanaf=0` — SSE via `runs.volg(...)`; 404 bij een onbekende of
    andermans run. Bewust **geen** rate-limit (zelfde reden als de referentie: meekijken/opnieuw
    aanhaken mag nooit op een limiet stuklopen).
  - `POST /v1/runs/{run_id}/cancel` (202) — `runs.vraag_stop(...)`; 404 bij onbekend/andermans.
  - `GET /v1/conversations/{conversation_id}/run` — de aanhaakbare run, of `null`.
  - `POST /v1/chat` blijft ongewijzigd bestaan (voor scripts/evals die geen run-model nodig
    hebben).

## Acceptatiecriteria

- [x] `RunRegister.start(...)` gooit `RunBestaatAl` (met het actieve `run_id`) bij een tweede
      `start()` op hetzelfde gesprek terwijl de eerste nog loopt — unit-geverifieerd met een
      gecontroleerde, blokkerende stream (`test_runs.py`), én apart op HTTP-niveau met een
      kunstmatig vertraagde `_TregeLLM` (`test_api.py`).
- [x] `RunRegister.volg(run, vanaf)` levert eerst de replay (events met `seq >= vanaf`), dan live
      nieuwe events, en sluit zodra de run niet meer loopt — geen race tussen afronden en wachten
      (de toestandscontrole staat onder dezelfde `Condition`-lock als `notify_all`).
- [x] Een `gat`-event verschijnt zodra `seq` een sprong maakt (gesnoeide events).
- [x] `_cap` gooit uitsluitend `VLUCHTIGE_TYPES`-events weg, nooit `sources`/`grounding`/`done`/
      `error`/`conversation_id`.
- [x] `_ruim_op` verwijdert een afgeronde run pas ná `BEWAAR_NA_AFLOOP_S`, niet eerder.
- [x] `POST /v1/runs` → 201 met een `RunStart`-body; `GET /v1/runs/{id}/events` replayt tot en met
      `done`; `POST /v1/runs/{id}/cancel` → 202; `GET /v1/conversations/{id}/run` → `null` zonder
      run, de samenvatting mét.
- [x] Onbekend of andermans `run_id`/`conversation_id` (verkeerde `X-User-Id`) → 404 op alle drie
      de run-specifieke endpoints.
- [x] `stop_check` (story 052) heeft nu een echte aanroeper: `cancel` gevolgd door een lopende
      beurt levert `status: "gestopt"` op, niet `"klaar"` — live geverifieerd (een `cancel` vóór
      de eerste node gaf `status: "gestopt"`, alleen `conversation_id`+`done`, geen `error`; een
      run zonder cancel liep gewoon door tot `status: "klaar"` met tokens/sources/grounding).
- [x] Bestaande 236 tests blijven groen zonder aanpassing; `POST /v1/chat` ongewijzigd.

## Buiten scope

`agent/beurt.py`-persistentie (schrijven naar `api`), annotatiebeurten via het run-model (`doel`),
CORS, rate-limiting (behalve het bewuste ontbreken op `/events`, zie §Wijzigingen), observability.

## Prioriteit / story points

Prioriteit: **high**. Story points: **5** (nieuwe module met een niet-triviale concurrency-vorm
— `Condition`-gebaseerd meekijken, selectief cappen, retentie —, vier nieuwe endpoints, een
eigenaarschapsmodel, en de eerste échte consument van `stop_check`).

## Verificatie

- `pytest -q -m "not integration"`: 251 passed (236 bestaand + 10 nieuw in `tests/test_runs.py` +
  5 nieuw in `tests/test_api.py`, geen enkele bestaande test aangepast).
- `ruff check . && ruff format --check .`: schoon (één gerichte `# noqa: B023` op de
  `wait_for`-lambda in `agent/runs.py`, met uitleg waarom de closure hier geen bug is — de
  `cursor`-waarde wordt binnen dezelfde `while`-iteratie synchroon gebruikt, geen uitgestelde
  stale-closure).
- `pytest -q -m integration`: ongewijzigd (deze story raakt de agent-laag niet, alleen de
  HTTP-laag erbovenop).
- Live: `uvicorn api.main:app` tegen de echte GraphDB + Foundry —
  - een run zonder cancel liep door tot `status: "klaar"` met echte token-/sources-/
    grounding-events (`grounding.niveau == "gegrond"`);
  - een run met een `cancel` vóór de eerste node gaf `status: "gestopt"`, met alleen
    `conversation_id`+`done` in de eventlog — bewijst dat `stop_check`/`BeurtGestopt` (story 052)
    nu daadwerkelijk via `POST /v1/runs/{id}/cancel` bereikbaar is.

## Gebouwd:

Ja (PR #92).
