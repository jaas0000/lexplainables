# Vervolgpunten

Niet-blocking bevindingen uit code-reviews die een follow-up verdienen.

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

## PR #9 — wetcatalogus (story 010)

- **C4-model bijwerken**: `docs/architectuur/c4-model.md` is niet bijgewerkt voor de nieuwe wetcatalogus-feature. Toe te voegen: L3 Component `api` — wetcatalogus (`features/wetcatalogus/`); L3 Component `frontend` — wetcatalogus-pagina (`app/wetcatalogus/`), `WetSelector` (`components/WetSelector.tsx`) en BFF-routes (`app/api/wetten/`); L2 Container — beschrijving van `api` bijwerken (wetcatalogus staat er nog als "nog niet gebouwd").

---

## PR #10 — llm-profielen (story 011)

- **C4-model bijwerken**: `docs/architectuur/c4-model.md` is niet bijgewerkt voor de nieuwe llm_profielen-feature. Toe te voegen: L3 Component `api` — `llm_profielen` (`features/llm_profielen/`), `shared/crypto` (`shared/crypto.py`); L3 Component `frontend` — `LlmProfielenPagina` (`app/beheer/llm-profielen/page.tsx`) en BFF-routes (`app/api/admin/profielen/`). Ook de api- en frontend-beschrijving in L2 Container bijwerken.
- **Story 011 "Gebouwd: nee"**: `docs/stories/011-llm-profielen.md` heeft onderaan nog `**Gebouwd:** nee` staan. Bijwerken naar `ja` bij de eerste volgende commit op die story.

---

## PR #11 — analyse aanmaken & volgen (story 012)

- **C4-model bijwerken**: `docs/architectuur/c4-model.md` is niet bijgewerkt voor de nieuwe `projecten`-feature. Toe te voegen: L3 Component `api` — `projecten` (`features/projecten/`); L3 Component `frontend` — analyselijst/detail/nieuw (`app/projecten/`), BFF-routes (`app/api/projecten/`), `StatusPill`/`VerwijderKnop` (`components/projecten/`). Ook de api- en frontend-beschrijving in L2 Container bijwerken.
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
- **MEDIUM** — TOCTOU race in upsert: SELECT + INSERT/UPDATE is niet atomair op PostgreSQL; twee gelijktijdige PUT-requests op hetzelfde nieuwe `bwb_id` kunnen beiden de INSERT uitvoeren → onafgevangen IntegrityError. Fix: `insert(...).on_conflict_do_update(index_elements=["bwb_id"])` (`api/app/features/wetcatalogus/store.py:83-104`).
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
- **LAAG** — `frontend/app/beheer/instellingen/page.tsx`: 197 regels inline styles voor één kaart — kaart-layout en status-badge herhalen patronen die extraction verdienen (zie `SectieHeader` als precedent).
- **LAAG** — `api/app/features/runtime_config/store.py` + `api/app/features/berichten/store.py`: dialect-check `conn.engine.url.get_backend_name()` staat nu in twee stores; extraheer naar `api/app/shared/db.py` als `dialect_insert_fn(engine)`.

---

## PR #17 — analyse-engine (story 024)

- **Act3b schema-validatie is een no-op**: `schema_check_act3b` in `api/app/engine/steps.py` retourneert altijd een lege lijst (`lambda d: []`). Invullen zodra een formeel JAS-schema voor afleidingsregels beschikbaar is.
- **`httpx.AsyncClient` per aanroep**: `haal_artikel_op` in `api/app/shared/wettenbank.py` maakt elke keer een nieuwe `AsyncClient` aan (nieuwe TCP-verbinding per Wettenbank-call). Maak één lifespan-scoped client via FastAPI `lifespan` — zelfde patroon als bevinding bij PR #15.
- **C4-model bijwerken**: `docs/architectuur/c4-model.md` is niet bijgewerkt voor de nieuwe modules `api/app/engine/` (orchestrator, steps, prompts, retry), `api/app/shared/llm/` (LiteLLMClient), `api/app/shared/wettenbank.py`, `api/app/shared/validation.py`, en de nieuwe endpoints `/akkoord`+`/afwijzen`. Bijwerken in een volgende architectuurslag.
- **Human-in-the-loop poll zonder backoff**: `orchestrator.py` pollt elke 2 seconden met een vaste `asyncio.sleep(2)` voor maximaal 24 uur. Bij een toekomstige PostgreSQL-backend overwegen om een LISTEN/NOTIFY-notificatiemechanisme te gebruiken i.p.v. polling, voor lagere DB-load en kortere latentie.

---

## Frontend — berichten fase 2

- **BFF-rolautorisatie**: `app/api/admin/berichten/` controleert `session.user.rol` niet — momenteel alleen beheerders actief, maar de BFF hoort rolautorisatie te dragen zodra analisten bestaan.
- **E2E-tests voor `/beheer` en `/berichten`**: ontbreken nog (`frontend-bouwen` regel 6). Aanmaken vóór de feature in productie gaat.
