# Vervolgpunten

Niet-blocking bevindingen uit code-reviews die een follow-up verdienen.

---

## PR #68 — werkplek: echte wetsartikeltekst via GraphDB (story 037) ✅ opgelost in PR #69

`httpx.AsyncClient` per aanroep in `annotatie/graphdb.py` — opgelost via een proces-brede,
lazily aangemaakte client (`_get_client()`, zelfde patroon als `db.py::get_engine`), tijdens de
retroactieve simplify-sweep over stories 030-037. De vergelijkbare gevallen bij PR #15/#17
(`shared/wettenbank.py`) zijn inmiddels ook opgelost, in PR #71.

---

## Fase 2 story 5 — 2FA e2e-test ✅ opgelost in fase 2b.2 (PR #48)

Root cause: `signIn(..., { totp: undefined })` serialiseerde `undefined` naar de string
`"undefined"`; api zag dat als een ongeldige code i.p.v. ontbrekende. Fix: spread-guard in
`LoginFormulier.tsx`. Tweede probleem was `TotpRequired`-subclass die niet stabiel
overrulde onder Turbopack — vervangen door `new CredentialsSignin(); err.code = "TotpRequired"`.
Playwright artifacts on-failure (screenshot + trace + video) staan sinds PR #47 aan.

## Fase 2 story 4 — Auth.js live-rol-check ✅ opgelost in fase 2b.3

JWT-callback ververst rol/actief-status via `GET /v1/auth/me` elke `SESSION_CHECK_TTL_MS`
(default 5 min). 401 of `actief=false` maakt de sessie ongeldig.

---

## Fase 3 — Rijkshuisstijl (sidebar-migratie)

- **`AppSidebar.tsx` is een skelet, nog geen gesprekkenlijst**: de bron-app (`wetsanalyse-ai`)
  heeft de sidebar verweven met de chatgeschiedenis-feature (nieuw-gesprek-knop, scrollende
  gesprekkenlijst, hernoemen/verwijderen — zie `GesprekSidebar.tsx`). Die functionaliteit bestaat
  in lexplainables nog niet; komt pas met de analyse-werkplek in fase 4. Nu staat er alleen de
  vorm (logo, statische nav-links Projecten/Werkplek/Beheer, gebruikersblok, mobiele drawer).
  Fase 4 vult 'm met de echte gesprekkenlijst i.p.v. opnieuw op te zetten.
- **Rijkshuisstijl-vorm gewijzigd**: de horizontale, gecentreerde logobalk (lint op de
  middenas, Rijkshuisstijl-regel) is vervangen door een sidebar met het logo linksboven, conform
  `wetsanalyse-ai`'s huidige aanpak (`layout.tsx`-comment daar: "de oude logobalk + navigatiebalk
  + footer zijn weg"). Dit wijkt af van de klassieke RH-lintregel; bewust gekozen om gelijk te
  lopen met de bron-app. Als dit ooit een RH-toetsing moet doorstaan, is dit het punt om op terug
  te komen.
- **Geen rol-gating op de "Beheer"-link**: `AppSidebar` toont "Beheer" aan elke ingelogde
  gebruiker, ongeacht rol — onderdeel van het bredere BFF-rolautorisatie-gat, zie
  "BFF-rolautorisatie ontbreekt project-breed" verderop in dit bestand.
- **Geen generieke `Dialog`-abstractie**: de mobiele drawer in `AppSidebar.tsx` is een eigen,
  eenvoudige implementatie (backdrop + paneel, geen focus-trap), niet de 5-varianten-`Dialog` uit
  `wetsanalyse-ai/components/ui/Dialog.tsx`. Voldoende voor nu (één variant nodig); overwegen zodra
  een tweede modal-usecase komt (bv. een uitgebreidere feedback-dialoog of een artefact-paneel in
  fase 4).
- **Sidebar altijd gemount, ook onzichtbaar op mobiel** (Simplify-bevinding, bewust niet gefixt):
  `AppSidebar.tsx`'s `<aside>` wordt met CSS verborgen op mobiel (`hidden lg:block`), niet
  conditioneel gerenderd — en mount dus altijd, inclusief zijn eigen `BerichtenPopover` met een
  60s-polling-interval. Zodra de mobiele drawer opengaat, mount een *tweede* instantie ernaast, wat
  tijdelijk dubbele polling geeft. Dit patroon is 1:1 overgenomen van `wetsanalyse-ai`'s eigen
  `AppSidebar.tsx` (identieke structuur: altijd-gemounte `<aside>` + los gemounte `Dialog` bij
  `drawerOpen`) — dus geen regressie t.o.v. de bron-app, maar wel een generieke inefficiëntie die
  in beide codebases zou opgaan. Fix (indien ooit nodig): één `SidebarInhoud`-instantie die van
  container wisselt i.p.v. twee aparte mounts, of de aside niet-conditioneel maken achter een
  JS-media-query-hook.

---

## Simplify-sweep story 005 — auth-login

- ✅ opgelost — `app/api/auth/setup-status/route.ts` was inderdaad nergens meer bereikt
  (`haalSetupStatus` praat rechtstreeks met de API, niet via deze BFF-route) en is verwijderd.
- **Header-bundel duplicatie in `lib/api-client.ts`**: `publiekApiProxy` bouwt zijn eigen header-object dat 90% overlapt met `buildBackendHeaders` — alleen `X-User-Id` verschilt. Uniticeren via `buildBackendHeaders(gebruikersnaam?: string)` met optionele user. Gevonden tijdens de architecturale review van PR #32; buiten scope van die PR (auth-login-005).

---

## PR #22 — Werkplek annotatie-UI (story 023)

- **`projecten/page.tsx` — dubbele `formatDatum`**: `lib/datum.ts` is aangemaakt en `werkplek/page.tsx` importeert correct uit die lib, maar `frontend/app/projecten/page.tsx` heeft nog zijn eigen lokale kopie (regel 21). Vervang de lokale definitie door `import { formatDatum } from "@/lib/datum"`.
- **`use(params)` voor slug-/id-resolutie**: `app/werkplek/[slug]/page.tsx` en `app/projecten/[id]/page.tsx` lossen `params` nog op via een `useEffect` + `useState`-combinatie. React is inmiddels 19 (was het blokkerende punt) — `use(params)` als éénregelige vervanging kan nu.
- **Design-tokens voor aandacht-kleuren ontbreken in `globals.css`**: `ElementenKolom.tsx` gebruikt hardcoded hex-waarden (`#fef2f2`, `#fca5a5`, `#dc2626` etc.). Verplaatsen naar CSS-variabelen in `globals.css` zodra dark-mode wordt toegevoegd.

---

## PR #20 — LLM-calls log (story 021)

- **Ontbrekende kolommen t.o.v. originele spec**: De originele story 021-spec had `ronde`, `poging`, `fase`, `provider`, `ok`, `fout` als kolommen — story 024 vereenvoudigde het schema. Als die velden later toch nodig zijn, vereist dat een nieuwe Alembic-migratie.
- **`SqlAlchemyLlmCallsStore` zonder Protocol-abstractie**: De router bindt direct aan de concrete klasse (`SqlAlchemyLlmCallsStore`), terwijl `SqlAlchemyAnalyseStore` het `AnalyseStore`-Protocol implementeert. Voeg een `LlmCallsStore`-Protocol toe zodra er een tweede implementatie of gebruiker bijkomt.

---

## Architectuur-audit — 2026-08-19 (ronde 2)

_Historische snapshot — `api/app/engine/` bestaat sinds PR #36 niet meer (zie "PR #17 —
analyse-engine" hierboven); de tekst hieronder blijft ongewijzigd als tijdsopname._

Audit gedraaid op stand na PRs #21 (annotatie-backend) en #22 (annotatie-UI). Focus: `api/app/features/`, `api/app/shared/`, `api/app/engine/`, `db.py`, `main.py`. Vier bevindingen — geen ervan is een projectbrede keuze die een ADR verdient (engine als derde mapniveau staat al in `stack-profiel.md` §Feature-eenheid; geen wijziging in dat beeld). Alles staat hieronder als vervolgpunt; niets is deze ronde direct gerefactord omdat elke aanpassing meerdere features raakt.

**Stabiel bevonden:**
`db.py` (30 r) en `main.py` (58 r) blijven strak dun. Feature-structuur (`models.py`/`store.py`/`router.py`/`tests/`) is consistent voor alle negen domeinen. Elke feature heeft een eigen `MetaData()`-instantie — bewuste isolatie, geen probleem (Alembic beheert het schema, niet `metadata.create_all()`). `shared/tijd.py`, `shared/crypto.py`, `shared/validation.py`, `shared/wettenbank.py`, `shared/llm/` zitten op de juiste plek en hebben elk ≥2 consumenten. De engine-module is nog steeds gedocumenteerd in `stack-profiel.md` §Feature-eenheid; geen tweede LLM-orkestratie-consument in zicht, dus verplaatsingsvraag nog niet actief. `engine/steps.py` (237 r) en `engine/prompts.py` (224 r) zijn de grootste modules in `engine/`, maar elk één natuurlijk concern — cohesie nog gezond.

---

## Architectuur-audit — 2026-08-19 (ronde 1)

_Historische snapshot — `api/app/engine/` bestaat sinds PR #36 niet meer._

Audit gedraaid op stand na PRs #17 (analyse-engine), #18 (api-tokens, open), #19 (rapport, open), #20 (llm-calls log, open). Drie bevindingen — twee direct opgelost, één als vervolgpunt:

**Direct opgelost (commit in deze ronde):**
- **`llm_calls_metadata` → `metadata`** ✓: `projecten/models.py` gebruikte een aparte `MetaData()`-instantie voor de `llm_calls`-tabel, los van de `metadata`-instantie voor `analyses`. Nu beide tabellen onder dezelfde `metadata`, zodat `metadata.create_all()` volledig is. Imports in `test_orchestrator.py` bijgewerkt.
- **`shared/validation.py` → `engine/validation.py`** ✓: `validation.py` stond in `shared/` maar had uitsluitend gebruikers in `engine/` (steps.py, prompts.py, tests/test_validation.py). Verplaatst naar `engine/validation.py`; imports in alle drie bijgewerkt. Per werkwijze-regel: `shared/` is voor ≥2 gebruikers.

**Stabiel bevonden:**
`main.py` en `db.py` zijn correct dun; feature-structuur (models/store/router/tests) is consistent voor alle domeinen; `shared/auth.py`, `shared/crypto.py`, `shared/tijd.py`, `shared/llm/` en `shared/wettenbank.py` staan op de juiste plek; `engine/` is gedocumenteerd als derde mapniveau in `stack-profiel.md` §Feature-eenheid.

---

## Werkwijze

- **"Ingelogd blijven"-checkbox functioneel maken**: de checkbox staat visueel op de loginpagina maar doet nog niets. Zodra de sessieduur-logica gebouwd wordt (story nog aan te maken), hier de `remember`-vlag doorgeven aan de Auth.js Credentials-provider (zoals wetsanalyse dat doet met `rememberMe` in de JWT-callback).
- **Mockup-stap in `frontend-bouwen` verbeterd en vastgelegd** ✓: dev-server als canvas, `/mockup/<feature>/`-pad, interactieve nepdata-component, badge, promotie naar definitief pad. Vastgelegd in `werkwijze-v2-multi-service/werkwijze/.claude/skills/frontend-bouwen/SKILL.md` (regels 2-4 + §Mockup-structuur).

---

## PR #3 — huisstijl-frontend (story 004)

- **MEDIUM** — Geen `<h1>` op de pagina (opgelost in `app/beheer/page.tsx` en `app/berichten/page.tsx`; nog open voor de mockup-pagina's).

---

## PR #7 — disclaimer + PoC-strip (story 008)

- **LAAG** — `disclaimer_geaccepteerd`-cookie mist `secure: process.env.NODE_ENV === "production"` (zie `app/api/disclaimer/accepteer/route.ts:20`). De sessie-cookie in `auth.config.ts` heeft dit al — zelfde patroon toevoegen bij een volgende ronde.
- **LAAG** — `setTimeout(() => setOpgeslagen(false), 3000)` in `beheer/page.tsx` wordt niet gecleanupt bij unmount; kan een setState-after-unmount triggeren als de gebruiker binnen 3 seconden wegnavigeert.

---

## Architectuur-audit — 2026-08-14

Audit gedraaid op stand na PR #7. Drie bevindingen — direct opgelost (commit `be2bfa7`):

- **Naamconflict opgelost** ✓: `frontend/lib/proxy.ts` (BFF HTTP-client) hernoemd naar `lib/api-client.ts`. NB: `proxy.ts` in de root is correct — in Next.js 16 is dit de officiële bestandsconventie (`middleware.ts` is deprecated).
- **`BerichtenPopover.tsx` verplaatst** ✓: naar `components/berichten/BerichtenPopover.tsx`, naast `TypeBadge.tsx`.
- **BFF auth-guard geëxtraheerd** ✓: `lib/bff-auth.ts` met `requireSession()` — alle 6 routes importeren nu alleen nog `requireSession()` en `apiProxy()`.

Wat stabiel is: `main.py` en `db.py` zijn correct dun; feature-structuur (models/store/router) is consistent voor alle drie domeinen; `shared/auth.py` en `shared/tijd.py` zijn op de juiste plek; `TYPE_META`/`TypeBadge`/`SectieHeader` zijn na PR #7 gededupliceerd; de BFF-proxy is éénmalig gedefinieerd in `lib/proxy.ts`.

---

## PR #8 — feedback-frontend (story 009)

- **LAAG** — `setTimeout` na succesvol verzenden in `components/feedback/FeedbackKnop.tsx:59` wordt niet gecleanupt bij unmount. Zelfde patroon als bestaand punt voor `beheer/page.tsx` hieronder.
- **LAAG** — `tests/e2e/feedback.spec.ts:54` — dubbel-verwijder test klikt op `.first()` in de lijst; bij pre-existing feedback-data staat het nieuw aangemaakte item mogelijk niet bovenaan en is de test flaky.

---

## PR #13 — setup-flow (story 015)

- **Race condition in `maak_eerste_beheerder`** (prioritair, nu actueel — Postgres is sinds
  ADR-0003 de enige DB, dit is niet meer "vóór productie-inzet" maar de huidige stand): SELECT +
  INSERT zijn niet atomair (`api/app/features/identiteit_toegang/store.py`). Twee gelijktijdige
  POST /setup-requests met verschillende gebruikersnamen kunnen allebei slagen en zo twee
  beheerders aanmaken. Kans in de praktijk nihil (intern endpoint, eenmalige first-run), maar de
  invariant "precies één admin na setup" is niet gegarandeerd. Fix: serializable transactie of
  `SELECT FOR UPDATE`. Zelfde soort ontbrekende locking als de LaatsteBeheerder-check bij
  "PR #14 — gebruikersbeheer uitbreiden" — allebei verdienen dezelfde, bewuste oplossing i.p.v.
  twee losse patches.
- **OpenAPI-spec mist 409-response** voor `POST /v1/auth/setup` (`api/generated/openapi.json`). De frontend handelt 409 correct af, maar het contract beschrijft het niet. Toevoegen bij de volgende contractronde.
- **`SetupVerzoek.email` heeft geen format-validatie** op de backend (`api/app/features/identiteit_toegang/models.py`). Elke string ≤ 320 tekens passeert. Voeg `EmailStr` (pydantic) of een `field_validator` toe zodra email-validatie elders in gebruik komt.
- **`async_eng` niet disposed** in de `client`-fixture van `test_setup.py` (regel ~88-100). Voeg `async_eng.dispose()` toe via een sync finalizer of maak de fixture async.
- **E2E foutpad-test is niet-deterministisch** (`frontend/tests/e2e/setup.spec.ts`, regels 37-59): accepteert zowel `/login` als `/setup` als correct resultaat. Aanscherpen zodra de CI-infrastructuur een lege vs. gevulde database garandeert.
- **`API_TOKEN` op twee plekken onafhankelijk uitgelezen**: `frontend/lib/setup-status.ts` leest `process.env.API_TOKEN` opnieuw i.p.v. te importeren uit `api-client.ts`. Exporteer `API_TOKEN` uit `api-client.ts`.
- **`publiekApiProxy` dupliceert response-shaping van `apiProxy`** (`frontend/lib/api-client.ts`). Extraheer de body-lees/Response-bouw logica naar een private helper of maak `gebruikersnaam` optioneel in `apiProxy`.
- **`maak_eerste_beheerder` herhaalt user-aanmaaklogica** die al in `maak_gebruiker` zit (`api/app/features/identiteit_toegang/store.py`). Vervang door aanroep naar `maak_gebruiker` na de leeg-check.
- **Schema-aanmaaklogica gedupliceerd** in `async_engine`- en `client`-fixtures in `test_setup.py`. Laat `client` de `async_engine`-fixture hergebruiken of extraheer naar een eigen fixture.

---

## PR #15 — wettenbank-beheer (story 020)

- ✅ opgelost — Crash in BewerkenFormulier na verwijder-terwijl-bewerkt: `setBewerkt(null)`
  toegevoegd in de `verwijder`-functie. Regressietest toegevoegd
  (`tests/e2e/wetten-beheer.spec.ts` — deze pagina had nog helemaal geen e2e-dekking).
- **MEDIUM** — Geen index op `naam`-kolom: alle lijstqueries sorteren op naam, maar de migratie maakt geen index aan. Voeg `ix_wet_catalogus_naam` toe in een volgende migratie (`api/alembic/versions/0007_wet_catalogus_tabel.py`).
- **MEDIUM** — ✅ opgelost (in het bestand dat de resolve-aanroep sindsdien echt bevat): zie het
  vervolgpunt bij PR #17 en PR #71.
- **MEDIUM** — `structuur()` geeft lege artikelenlijst zonder fout als `bwb_id` wel in de DB staat
  maar niet in `_STRUCTUUR`, en `_STRUCTUUR` is nog steeds een hardgecodeerde placeholder (zie de
  docstring in `store.py`: "wordt vervangen door een directe SPARQL-query op GraphDB"). Die
  voorwaarde is nu wél vervuld — `deploy/graphdb` + `tools/bwb-import` bestaan en zijn gevuld
  (zie CLAUDE.md) — dus dit is niet langer een kleine patch maar een echte story: `structuur()`
  op GraphDB-SPARQL laten leunen, zelfde patroon als story 037's `annotatie/graphdb.py`. Niet in
  deze sweep gedaan (te groot voor een sweep-fix), wel genoteerd als de eigenlijke, nu haalbare
  oplossing i.p.v. de kleinere losse `WetNietGevonden`-patch.
- ✅ opgelost — `WetCreate.bwb_id` (nooit gelezen, stond stil te negeren bij een mismatch) is
  verwijderd uit het model; de URL-path-`bwb_id` is en blijft de enige bron. Frontend meegewerkt
  (`beheer/wetten/page.tsx`): stuurt `bwb_id` niet langer mee in de PUT-body (toevoeg- én
  bewerkformulier), het toevoegformulier gebruikt nu een eigen lokaal `NieuweWetFormulier`-type
  i.p.v. het (nu smallere) gegenereerde `WetCreate`-contract te hergebruiken voor iets dat meer
  velden nodig heeft dan de body.
- ✅ opgelost — `httpx.ProtocolError` toegevoegd aan de except-tuples in `wettenbank.py` én
  `annotatie/graphdb.py`.
- ✅ opgelost — dode else-tak in `wet_uit_rij` verwijderd (`DateTime(timezone=True)` garandeert
  al een `datetime`, geen `str`-fallback nodig).
- **LAAG** — `_wet_bestaat` heeft geen hergebruik en kan ingelind worden in `structuur()` — bewust laten staan: een kleine, duidelijk genoemde private helper is prima leesbaar, en dit hangt sowieso samen met de grotere `structuur()`-herziening hierboven.
- ✅ al opgelost vóór deze sweep — geen duplicaat-import meer in `lege_client` (bestand was al
  ververst).
- **LAAG** — `beheer/page.tsx` haalt de volledige wettenlijst op enkel voor de teller naast "Wetten →". Count-endpoint toevoegen of bewust accepteren als tech debt (`frontend/app/beheer/page.tsx:85-92`).

---

## PR #12 — account-pagina (story 016)

- ✅ opgelost — de stale comment in `test_me_met_geldig_token_geeft_profiel` is gecorrigeerd
  (zie de "Zwakke HTTP-routetest"-regel hieronder, dat was dezelfde plek).
- **Dubbele DB-fetch** in `wijzig_eigen_wachtwoord` — bekeken en bewust laten staan: de twee
  aparte `AsyncSession`-blokken zijn een deliberate keuze (zie de comment erboven in de code —
  "bcrypt buiten de sessie: CPU-gebonden operatie, DB-verbinding hoeft niet open te blijven"),
  niet losse duplicatie. Samenvoegen tot één sessie zou de DB-connectie openhouden tijdens de
  bcrypt-hash (tientallen tot honderden ms CPU-werk), wat onder load eerder de connection-pool
  belast dan de huidige twee korte round-trips. Geen duidelijke winst, dus niet aangepast.
- **Zwakke HTTP-routetest** voor `GET /v1/auth/me` — comment gecorrigeerd (verwees ten onrechte
  naar SQLite, is Postgres-only sinds ADR-0003). De onderliggende suggestie (een seed toevoegen
  voor de 200-tak) staat nog open: vereist dat `client`- en `db_engine`-fixtures dezelfde
  test-engine delen (nu allebei een eigen `drop_all`/`create_all`-ronde), niet triviaal zonder
  fixture-herstructurering.

---

## PR #14 — gebruikersbeheer uitbreiden (story 014)

- ✅ opgelost — LaatsteBeheerder-invariantquery gedupliceerd in `wijzig_gebruiker` en
  `verwijder_gebruiker`: geëxtraheerd naar een private `_is_laatste_actieve_beheerder(sess, g)`.
- **store.py**: LaatsteBeheerder-check en write zijn in één transactie maar zonder `SELECT … FOR UPDATE`; nu relevant sinds ADR-0003 (Postgres-only, was eerder "met SQLite geen acuut risico" — die aanname geldt niet meer). Zelfde soort race als `maak_eerste_beheerder` hieronder bij "PR #13 — setup-flow"; allebei verdienen dezelfde oplossing (serializable transactie of `SELECT FOR UPDATE`), niet losstaand bekijken.
- ✅ opgelost (PR #75) — `adminProxy()` in `lib/api-client.ts` combineert `requireBeheerder()` +
  `apiProxy()`; alle 19 admin-route-bestanden gemigreerd, samen met de rol-check zelf.
- **page.tsx**: `onReset` cast de API-response naar een inline type i.p.v. `components["schemas"]["TijdelijkWachtwoord"]` (beschikbaar in `generated/types.ts`); consisent maken met de andere casts.
- ✅ opgelost — `GebruikerCreate.rol`/`GebruikerPatch.rol` zijn nu
  `Literal["beheerder", "analist"]` (Pydantic valideert automatisch, de handmatige 422-check in
  de router is weg); `GebruikerPatch` heeft nu een `model_validator` die een volledig lege body
  weigert (422, test toegevoegd).
- **openapi.json**: 401-response is niet gedocumenteerd voor de vijf admin-endpoints (GET, POST, PATCH, DELETE, reset-wachtwoord); toevoegen voor volledigheid van het contract.
- **store.py**: `lijst_gebruikers` heeft geen LIMIT — bewust niet gefixt met een simpele `.limit(N)`: dit is een admin-beheerscherm waar volledigheid ("zie ik echt alle gebruikers") het punt is, dus een LIMIT zou stilzwijgend gebruikers verbergen in plaats van het probleem op te lossen. Een echte fix is paginering, niet een sweep-regel.
- **scope**: GET + POST `/v1/admin/gebruikers` vallen buiten story 014-spec (afhankelijkheid story 006); functioneel noodzakelijk voor de UI maar niet formeel vastgelegd in de story.
- ✅ opgelost (PR #74) — `identiteit_toegang` is gemigreerd van SQLModel ORM naar SQLAlchemy
  Core + Pydantic (ADR-0011), zelfde patroon als `api_tokens`. Geen gedragswijziging; `sqlmodel`
  is nu nergens meer een dependency van `api/`.

---

## PR #16 — app-instellingen / runtime-config (story 019)

- **MEDIUM** — `frontend/app/api/admin/instellingen/route.ts` r13-14: `req.text()` + vaste `Content-Type: application/json` in `buildBackendHeaders` — nu correct (browser stuurt JSON), maar impliciete aanname die breekt als een caller een andere Content-Type gebruikt.
- ✅ opgelost — `_cache: dict[str, object]` vervangen door een getypeerde `_CacheEntry`-dataclass
  (geen `isinstance`-check/`# type: ignore` meer nodig).
- ✅ opgelost — `json`/`logging` zijn nu module-niveau imports in `models.py`, met
  `logger = logging.getLogger(__name__)` als module-constante.
- **LAAG** — `api/app/features/runtime_config/store.py` r88-90: na elke schrijfactie cache wissen + nieuwe `SELECT *` — bewust niet gefixt: er is precies één instelling vandaag, dus de round-trip kost niets meetbaars; pas oppakken zodra er meerdere instellingen zijn en dit patroon zich herhaalt.
- **LAAG** — `api/app/features/runtime_config/store.py` r78-87: per-sleutel upsert in loop — nu 1 query, bij méér instellingen N sequentiële queries binnen één transactie.
- **LAAG** — `frontend/app/beheer/instellingen/page.tsx` r18-29: `useEffect` zonder `AbortController` — geen lek in React 18, maar netwerk-request loopt onnodig door na unmount.
- **LAAG** — `frontend/app/beheer/instellingen/page.tsx`: 197 regels inline styles voor één kaart — kaart-layout en status-badge herhalen patronen die extraction verdienen (zie `SectieHeader` als precedent). ✅ opgelost in fase 3 (Rijkshuisstijl): kaart-wrapper → `.card`, status-tag → `.badge`/`.badge-gepubliceerd`/`.badge-concept`, knop → `.btn`, foutmelding → `.melding melding-fout`.
---

## PR #17 — analyse-engine (story 024) ✅ vervallen — module verwijderd in PR #36

`api/app/engine/` (orchestrator, prompts, steps, retry, validation) en de rapport-/SSE-flow
zijn volledig opgeruimd in PR #36 ("opruimen story 013 + 024", migratie 0012) — de JAS-
orkestratie (act2/act3, review-flow, rapport) is legacy; annotatie is de enige overgebleven
analyse-stap (zie `docs/project/migratie-wetsanalyse.md`). De twee resterende bevindingen hier
(act3b-schema-validatie, human-in-the-loop-poll-backoff) vervielen daarmee. De
`httpx.AsyncClient`-bevinding is apart opgelost in PR #71 (zat inmiddels in
`shared/wettenbank.py::_jsonrpc_call`, niet meer in `engine/`).

---

## PR #18 — API-tokens (story 018) ✅ opgelost

`ApiTokenAanmakenVerzoek.label` heeft nu `Field(default="", max_length=128)` — een te lange
`label` geeft 422 i.p.v. een stilzwijgend afgeknipte 201.

---

## PR #19 — rapport bekijken (story 013) ✅ vervallen — feature verwijderd in PR #36

De hele rapport-bekijken-feature (endpoint, story-doc, frontend-pagina) is opgeruimd in PR #36
— de story-doc-URL-drift die hier stond is daarmee niet meer van toepassing (het bestand
bestaat niet meer).

---

## Frontend — berichten fase 2 (rolautorisatie — zie ook de bredere versie hieronder)

- **E2E-tests voor `/beheer` en `/berichten`**: ontbreken nog (`frontend-bouwen` regel 6). Aanmaken vóór de feature in productie gaat.

---

## BFF-rolautorisatie ontbreekt project-breed (PR #5 t/m nu)

- ✅ opgelost (PR #75, story 038) — nieuwe `requireBeheerder()`/`adminProxy()` in de BFF-laag
  (`lib/bff-auth.ts`/`lib/api-client.ts`) controleren nu `session.user.rol` op alle 19
  admin-route-bestanden (401 bij geen sessie, 403 bij een sessie zonder beheerder-rol —
  bewust onderscheiden na een regressie die dat eerst plat sloeg tot 403, zie de story-doc);
  `auth.config.ts` redirect een analist die `/beheer` bezoekt naar `/`; `AppSidebar.tsx` toont
  de "Beheer"-link alleen aan een beheerder. Lost tegelijk het DRY-vervolgpunt op dat hieronder
  (regel "requireSession + apiProxy-patroon is nu gedupliceerd...") stond.

Drie eerdere, losse vermeldingen van dit punt (PR #5 story 006, Frontend-berichten-fase-2,
Fase-3-sidebar) samengevoegd — het is één en hetzelfde, project-brede gat, niet drie losse.

`huidige_beheerder` in `api/app/shared/auth.py` verifieert alleen het machine-`API_TOKEN` +
een `X-User-Id`-header; het retourneert altijd `rol="beheerder"`, ongeacht wie er werkelijk
achter die gebruikersnaam zit (zie de docstring: "sterk vereenvoudigde stand-in"). De
architectuur (story 006) legt rolautorisatie bewust bij de BFF — dat is precies waar PR #75
'm nu daadwerkelijk afdwingt; `huidige_beheerder` zelf blijft ongewijzigd (bewuste architectuur,
geen gat meer nu de BFF-laag het afdwingt).

---

## Gevonden tijdens story 024 (bwb-import setup)

- ✅ opgelost — `crypto.py` leest nu `FERNET_KEY_FILE` (werkwijze-ADR-0006), niet meer een
  platte `FERNET_KEY`-env-var. Geraakt: `crypto.py` zelf, foutmeldingen in
  `identiteit_toegang/router.py`+`store.py` en `llm_profielen/store.py`, story 017's doc, de
  test-fixtures in `test_2fa.py`/`test_llm_profielen.py` (schrijven nu een tmp-bestand i.p.v.
  de key als platte env-var-waarde te zetten), en `frontend-ci.yml`'s `test-frontend-e2e`-job
  (schrijft de CI-testkey naar `/tmp/fernet_key` vóórdat de API-server start).

---

## Gevonden tijdens story 027 (bwb-import GraphDB-writer) ✅ opgelost 2026-08-22

GraphDB ≥ 11.x vereist een licentie voor elke schrijfactie ("No license was set", 500 op elke
PUT/SPARQL-update). Root cause + juridische afweging vastgelegd in
`ai-notes/licenties-en-juridisch.md`. Gebruiker heeft een GraphDB Free-licentie geregistreerd
(Licensee: Belastingdienst) en aangeleverd; geladen via `deploy/graphdb/docker-compose.override.yml`
(gitignored, licentiebestand buiten de repo in `/root/.secrets/`). Twee checks bevestigen dat de
schrijfpijplijn nu volledig werkt:
- `test_write_wet_en_terugvragen` (`@pytest.mark.integration`) slaagt tegen de echte lokale
  GraphDB.
- Live `python -m app.main BWBR0004770` tegen de actuele Invorderingswet 1990
  (geldig vanaf 2026-07-01, rechtstreeks van `repository.officiele-overheidspublicaties.nl`)
  schreef 9.686 triples weg: 133 artikelen, 385 leden, 232 onderdelen, 1.284 relaties — geverifieerd
  via SPARQL.

Let op: GraphDB Free is alleen toegestaan voor dev/test (zie `ai-notes/licenties-en-juridisch.md`);
een productie-deploy (fase 5) vereist een betaalde licentie.

---

## Gevonden tijdens story 034 (bwb-import circulaires) ✅ opgelost

`tools/bwb-import/CLAUDE.md`'s twee stale verwijzingen naar "de nog te bouwen GraphDB-writer"
zijn bijgewerkt.
