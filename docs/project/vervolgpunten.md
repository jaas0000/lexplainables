# Vervolgpunten

Niet-blocking bevindingen uit code-reviews die een follow-up verdienen.

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
- **Geen rol-gating op de "Beheer"-link**: zowel de oude `NavigatieHeader` als de nieuwe
  `AppSidebar` tonen "Beheer" aan elke ingelogde gebruiker, ongeacht `session.user.rol`. Bestaand
  gedrag, niet gewijzigd in fase 3 (zuiver visuele scope) — wel inconsistent met
  `GesprekSidebar.tsx` in de bron-app, die "Beheer" alleen aan `beheerder`-rol toont. Zie ook het
  bestaande vervolgpunt onder "PR #5 — auth-eigen-gebruikers": BFF-routes controleren
  `session.user.rol` sowieso nog niet.
- **`tailwind.config.ts` was géén volledige match met `wetsanalyse-ai`**: het fase-3-plan
  claimde "identiek", maar `borderRadius.kaart`, `boxShadow.zacht`/`.kaart`, de `.focus-ring`-CSS-
  klasse en de `coarse:`-Tailwind-variant ontbraken. Toegevoegd in deze PR (nodig voor de sidebar-
  vormtaal); geverifieerd dat verder niets anders was.
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

- **Onbenutte BFF-route `app/api/auth/setup-status/route.ts`**: mogelijk dead code — de frontend gebruikt alleen `haalSetupStatus` (server-side). Onderzoeken en verwijderen indien nergens meer bereikt. Gevonden tijdens simplify-sweep (story 005, PR #32); buiten simplify-scope want gedragsverandering.
- **Header-bundel duplicatie in `lib/api-client.ts`**: `publiekApiProxy` bouwt zijn eigen header-object dat 90% overlapt met `buildBackendHeaders` — alleen `X-User-Id` verschilt. Uniticeren via `buildBackendHeaders(gebruikersnaam?: string)` met optionele user. Gevonden tijdens de architecturale review van PR #32; buiten scope van die PR (auth-login-005).

---

## PR #22 — Werkplek annotatie-UI (story 023)

- **`projecten/page.tsx` — dubbele `formatDatum`**: `lib/datum.ts` is aangemaakt en `werkplek/page.tsx` importeert correct uit die lib, maar `frontend/app/projecten/page.tsx` heeft nog zijn eigen lokale kopie (regel 21). Vervang de lokale definitie door `import { formatDatum } from "@/lib/datum"`.
- **Story 023 staat nog op "Gebouwd: nee"**: `docs/stories/023-werkplek-annotatie-ui.md` bijwerken naar `Gebouwd: ja`.
- **Wetsartikeltekst is een placeholder**: de linkerkolom toont "De volledige wetsartikeltekst is beschikbaar via de Wettenbank-koppeling (nog niet ingebouwd)". Koppeling met Wettenbank-MCP (`GET /v1/wetten/{bwb_id}/structuur`) vereist een apart BFF-endpoint en een client-component; aparte story of vervolgspurt.
- **`use(params)` voor slug-resolutie**: `app/werkplek/[slug]/page.tsx` lost `params` op via een `useEffect` + `useState`-combinatie (Next.js 16). React 19 biedt `use(params)` als éénregelige vervanging — consistent toepassen samen met `projecten/[id]/page.tsx` zodra de codebase naar React 19 gaat.
- **Design-tokens voor aandacht-kleuren ontbreken in `globals.css`**: `ElementenKolom.tsx` gebruikt hardcoded hex-waarden (`#fef2f2`, `#fca5a5`, `#dc2626` etc.). Verplaatsen naar CSS-variabelen in `globals.css` zodra dark-mode wordt toegevoegd.

---

## PR #20 — LLM-calls log (story 021)

- **Frontend CI structureel kapot op push-events**: `frontend-ci.yml` faalt bij elke push met "workflow file issue" (0s, geen job output). Hierdoor draaien `check-generated-types`, `check-ts-style` en `test-frontend-e2e` niet op PRs. Los op als apart vervolgpunt (raakt alle frontend-PRs, niet specifiek deze).
- **Ontbrekende kolommen t.o.v. originele spec**: De originele story 021-spec had `ronde`, `poging`, `fase`, `provider`, `ok`, `fout` als kolommen — story 024 vereenvoudigde het schema. Als die velden later toch nodig zijn, vereist dat een nieuwe Alembic-migratie.
- **`SqlAlchemyLlmCallsStore` zonder Protocol-abstractie**: De router bindt direct aan de concrete klasse (`SqlAlchemyLlmCallsStore`), terwijl `SqlAlchemyAnalyseStore` het `AnalyseStore`-Protocol implementeert. Voeg een `LlmCallsStore`-Protocol toe zodra er een tweede implementatie of gebruiker bijkomt.

---

## Architectuur-audit — 2026-08-19 (ronde 2)

Audit gedraaid op stand na PRs #21 (annotatie-backend) en #22 (annotatie-UI). Focus: `api/app/features/`, `api/app/shared/`, `api/app/engine/`, `db.py`, `main.py`. Vier bevindingen — geen ervan is een projectbrede keuze die een ADR verdient (engine als derde mapniveau staat al in `stack-profiel.md` §Feature-eenheid; geen wijziging in dat beeld). Alles staat hieronder als vervolgpunt; niets is deze ronde direct gerefactord omdat elke aanpassing meerdere features raakt.

**Stabiel bevonden:**
`db.py` (30 r) en `main.py` (58 r) blijven strak dun. Feature-structuur (`models.py`/`store.py`/`router.py`/`tests/`) is consistent voor alle negen domeinen. Elke feature heeft een eigen `MetaData()`-instantie — bewuste isolatie, geen probleem (Alembic beheert het schema, niet `metadata.create_all()`). `shared/tijd.py`, `shared/crypto.py`, `shared/validation.py`, `shared/wettenbank.py`, `shared/llm/` zitten op de juiste plek en hebben elk ≥2 consumenten. De engine-module is nog steeds gedocumenteerd in `stack-profiel.md` §Feature-eenheid; geen tweede LLM-orkestratie-consument in zicht, dus verplaatsingsvraag nog niet actief. `engine/steps.py` (237 r) en `engine/prompts.py` (224 r) zijn de grootste modules in `engine/`, maar elk één natuurlijk concern — cohesie nog gezond.

---

## Architectuur-audit — 2026-08-19 (ronde 1)

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

## PR #5 — auth-eigen-gebruikers (story 006)

- BFF-routes controleren `session.user.rol` niet — momenteel geen `analist`-gebruikers, maar de architectuur (story 006) zegt dat de BFF de rolautorisatie draagt. Toevoegen zodra meerdere rollen in gebruik komen.

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

## PR #10 — llm-profielen (story 011)

- **Story 011 "Gebouwd: nee"**: `docs/stories/011-llm-profielen.md` heeft onderaan nog `**Gebouwd:** nee` staan. Bijwerken naar `ja` bij de eerste volgende commit op die story.

---

## PR #11 — analyse aanmaken & volgen (story 012)

- **Story 012 "Gebouwd: nee"**: `docs/stories/012-analyse-aanmaken.md` heeft onderaan nog `**Gebouwd:** nee` staan. Bijwerken naar `ja`.

---

## PR #13 — setup-flow (story 015)

- **Race condition in `maak_eerste_beheerder`** (prioritair): SELECT + INSERT zijn niet atomair (`api/app/features/identiteit_toegang/store.py`). Twee gelijktijdige POST /setup-requests met verschillende gebruikersnamen kunnen allebei slagen en zo twee beheerders aanmaken. Kans in de praktijk nihil (intern endpoint, eenmalige first-run), maar de invariant "precies één admin na setup" is niet gegarandeerd. Fix: serializable transactie of `SELECT FOR UPDATE` (let op: SQLite negeert FOR UPDATE — database-specifiek aanpakken). Aandacht vereist vóór productie-inzet met PostgreSQL.
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

- **MEDIUM** — Crash in BewerkenFormulier na verwijder-terwijl-bewerkt: `wetten.find(...)!` geeft `undefined` als een rij verwijderd wordt terwijl het bewerkformulier al open staat. `setBewerkt(null)` toevoegen in de `verwijder`-functie (`frontend/app/beheer/wetten/page.tsx:279`).
- **MEDIUM** — Geen index op `naam`-kolom: alle lijstqueries sorteren op naam, maar de migratie maakt geen index aan. Voeg `ix_wet_catalogus_naam` toe in een volgende migratie (`api/alembic/versions/0007_wet_catalogus_tabel.py`).
- **MEDIUM** — Nieuwe `httpx.AsyncClient` per resolve-aanroep: maakt elke keer een nieuwe TCP-verbinding. Maak één lifespan-scoped client aan via FastAPI `lifespan` (`api/app/features/wetcatalogus/router.py:126`).
- **MEDIUM** — `structuur()` geeft lege artikelenlijst zonder fout als `bwb_id` wel in de DB staat maar niet in `_STRUCTUUR`. Expliciete `WetNietGevonden` gooien of het gedrag documenteren (`api/app/features/wetcatalogus/store.py:117-128`).
- **LAAG** — `WetCreate.bwb_id` stilzwijgend genegeerd bij mismatch met URL-pad: verwijder het veld uit `WetCreate` of voeg een 422-validatie toe (`api/app/features/wetcatalogus/router.py:80`).
- **LAAG** — `httpx.ProtocolError` niet afgevangen: bij misvormde MCP-respons propageert als 500 in plaats van 502. Toevoegen aan de except-tuple (`api/app/features/wetcatalogus/router.py:132`).
- **LAAG** — Dode else-tak in `wet_uit_rij`: `else: str(bijgewerkt)` is onbereikbaar bij `DateTime(timezone=True)` (`api/app/features/wetcatalogus/models.py:74-86`).
- **LAAG** — `_wet_bestaat` heeft geen hergebruik en kan ingelind worden in `structuur()` (`api/app/features/wetcatalogus/store.py:130-135`).
- **LAAG** — Duplicaat import `create_engine` in `lege_client` fixture (`api/app/features/wetcatalogus/tests/conftest.py:75`).
- **LAAG** — `beheer/page.tsx` haalt de volledige wettenlijst op enkel voor de teller naast "Wetten →". Count-endpoint toevoegen of bewust accepteren als tech debt (`frontend/app/beheer/page.tsx:85-92`).

---

## PR #12 — account-pagina (story 016)

- **Stale comment** in `test_me_met_geldig_token_geeft_profiel`: zegt "TestClient gebruikt de echte app-db" maar de fixture gebruikt na de fix een tmp SQLite. Bijwerken bij de volgende aanraking van dit testbestand.
- **Dubbele DB-fetch** in `wijzig_eigen_wachtwoord` (`api/app/features/identiteit_toegang/store.py`): twee `AsyncSession`-blokken — één om te lezen + bcrypt te checken, één om te schrijven. Samenvoegen in één sessie (lees → hash → schrijf) voor minder DB-roundtrips en een kleiner TOCTOU-window.
- **Zwakke HTTP-routetest** voor `GET /v1/auth/me`: `test_me_met_geldig_token_geeft_profiel` assert `in (200, 401)` maar raakt de 200-tak nooit (geen seed-gebruiker). De store-laag is wél goed gedekt via `test_haal_gebruiker_profiel`. Overweeg een seed in de test voor de 200-tak.

---

## PR #14 — gebruikersbeheer uitbreiden (story 014)

- **store.py**: LaatsteBeheerder-invariantquery staat verbatim gedupliceerd in `wijzig_gebruiker` en `verwijder_gebruiker`; extraheer naar een private `_tel_actieve_beheerders(sess)` helper.
- **store.py**: LaatsteBeheerder-check en write zijn in één transactie maar zonder `SELECT … FOR UPDATE`; bij een toekomstige PostgreSQL-migratie opnieuw evalueren (met SQLite zijn writes geserialiseerd, dus nu geen acuut risico).
- **BFF**: `requireSession` + `apiProxy`-patroon is nu gedupliceerd in berichten-, profielen- én gebruikers-routes; een gedeelde `adminProxy(req, url, opts)`-utility elimineert de boilerplate.
- **models.py**: `GebruikerCreate.rol` en `GebruikerPatch.rol` zijn getypeerd als `str` i.p.v. `Literal["beheerder", "analist"]`; met een Literal-type valideert FastAPI/Pydantic dit automatisch en verdwijnt de handmatige check in de router.
- **page.tsx**: `onReset` cast de API-response naar een inline type i.p.v. `components["schemas"]["TijdelijkWachtwoord"]` (beschikbaar in `generated/types.ts`); consisent maken met de andere casts.
- **models.py**: `GebruikerPatch` accepteert een volledig lege body (`{"rol": null, "actief": null}`) als silent no-op; een model-validator die ten minste één non-null veld eist zou dit explicieter maken.
- **openapi.json**: 401-response is niet gedocumenteerd voor de vijf admin-endpoints (GET, POST, PATCH, DELETE, reset-wachtwoord); toevoegen voor volledigheid van het contract.
- **store.py**: `lijst_gebruikers` heeft geen LIMIT; inconsistent met berichten-store. Op de huidige schaal geen probleem, maar bewaken bij groei.
- **scope**: GET + POST `/v1/admin/gebruikers` vallen buiten story 014-spec (afhankelijkheid story 006); functioneel noodzakelijk voor de UI maar niet formeel vastgelegd in de story.
- **ADR-0011**: `identiteit_toegang` staat nog op SQLModel ORM (niet SQLAlchemy Core + Pydantic zoals ADR-0011 voorschrijft en de implementatienoot aanbeval). Aparte story aanmaken voor de migratie.

---

## PR #16 — app-instellingen / runtime-config (story 019)

- **MEDIUM** — `frontend/app/api/admin/instellingen/route.ts` r13-14: `req.text()` + vaste `Content-Type: application/json` in `buildBackendHeaders` — nu correct (browser stuurt JSON), maar impliciete aanname die breekt als een caller een andere Content-Type gebruikt.
- **MEDIUM** — `api/app/features/runtime_config/store.py` r34, r50-52: `_cache: dict[str, object]` dwingt een `isinstance`-check en twee `# type: ignore` af. Een `@dataclass`-entry of `_CacheEntry | None`-variabele maakt dit weg.
- **MEDIUM** — `api/app/features/runtime_config/models.py` r89, r95: `json` en `logging` als inline imports in `_str_naar_bool` — horen op module-niveau; `logger = logging.getLogger(__name__)` als module-constante.
- **LAAG** — `api/app/features/runtime_config/store.py` r88-90: na elke schrijfactie cache wissen + nieuwe `SELECT *` — de geschreven waarden zijn al bekend, round-trip overbodig.
- **LAAG** — `api/app/features/runtime_config/store.py` r78-87: per-sleutel upsert in loop — nu 1 query, bij méér instellingen N sequentiële queries binnen één transactie.
- **LAAG** — `frontend/app/beheer/instellingen/page.tsx` r18-29: `useEffect` zonder `AbortController` — geen lek in React 18, maar netwerk-request loopt onnodig door na unmount.
- **LAAG** — `frontend/app/beheer/instellingen/page.tsx`: 197 regels inline styles voor één kaart — kaart-layout en status-badge herhalen patronen die extraction verdienen (zie `SectieHeader` als precedent). ✅ opgelost in fase 3 (Rijkshuisstijl): kaart-wrapper → `.card`, status-tag → `.badge`/`.badge-gepubliceerd`/`.badge-concept`, knop → `.btn`, foutmelding → `.melding melding-fout`.
---

## PR #17 — analyse-engine (story 024)

- **Act3b schema-validatie is een no-op**: `schema_check_act3b` in `api/app/engine/steps.py` retourneert altijd een lege lijst (`lambda d: []`). Invullen zodra een formeel JAS-schema voor afleidingsregels beschikbaar is.
- **`httpx.AsyncClient` per aanroep**: `haal_artikel_op` in `api/app/shared/wettenbank.py` maakt elke keer een nieuwe `AsyncClient` aan (nieuwe TCP-verbinding per Wettenbank-call). Maak één lifespan-scoped client via FastAPI `lifespan` — zelfde patroon als bevinding bij PR #15.
- **Human-in-the-loop poll zonder backoff**: `orchestrator.py` pollt elke 2 seconden met een vaste `asyncio.sleep(2)` voor maximaal 24 uur. Bij een toekomstige PostgreSQL-backend overwegen om een LISTEN/NOTIFY-notificatiemechanisme te gebruiken i.p.v. polling, voor lagere DB-load en kortere latentie.

---

## PR #18 — API-tokens (story 018)

- **`ApiTokenAanmakenVerzoek.label` mist Pydantic `max_length`-validator**: het story-schema specificeert max 128 tekens. De store trunceert op 128 (`[:128]`), maar de Pydantic-request-body heeft geen `max_length=128`. Een client die 1000 tekens instuurt krijgt nu een 201 met een stilzwijgend afgeknipte waarde; correctere API-opmaak zou een 422 geven. Functioneel niet-blocking, verfijning voor een volgende ronde (`api/app/features/api_tokens/models.py`).

---

## PR #19 — rapport bekijken (story 013)

- **Story-doc URL drift**: `docs/stories/013-rapport-bekijken.md` vermeldt de teruglink als `/analyse/{id}`, maar de implementatie gebruikt correct `/projecten/{id}`. Story-doc bijwerken zodat de URL klopt.

---

## Frontend — berichten fase 2

- **BFF-rolautorisatie**: `app/api/admin/berichten/` controleert `session.user.rol` niet — momenteel alleen beheerders actief, maar de BFF hoort rolautorisatie te dragen zodra analisten bestaan.
- **E2E-tests voor `/beheer` en `/berichten`**: ontbreken nog (`frontend-bouwen` regel 6). Aanmaken vóór de feature in productie gaat.

---

## Gevonden tijdens story 024 (bwb-import setup)

- **`api/app/shared/crypto.py:29` schendt werkwijze-ADR-0006**: `FERNET_KEY` wordt rechtstreeks uit een env-var gelezen (`os.environ.get("FERNET_KEY", "")`), niet via het `*_FILE`-pad-patroon dat de ADR voorschrijft. `tools/bwb-import`'s nieuwe `Settings` volgt de ADR wél voor `GRAPHDB_PASSWORD`; `crypto.py` retrofitten is een aparte, kleine story.

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

## Gevonden tijdens story 034 (bwb-import circulaires)

- **`tools/bwb-import/CLAUDE.md` is op twee punten stale**: noemt "de nog te bouwen
  GraphDB-writer" (§Architectuurbeslissingen, DI-punt) en "Geen `integration`-marker/echte-
  GraphDB-tests in deze story — komt zodra de GraphDB-writer gebouwd wordt" (§Tests) — beide
  achterhaald sinds story 027 (de GraphDB-writer bestaat, en er is wel degelijk een
  `integration`-marked test tegen de lokale stack). Pre-existing, niet door story 034 veroorzaakt;
  bijwerken bij de eerstvolgende aanraking van dat bestand.
