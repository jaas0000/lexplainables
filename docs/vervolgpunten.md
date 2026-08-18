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
- **Pre-existing CI failure**: `test_admin_bericht_met_geldig_token_en_user_id_geeft_200` in `api/app/features/identiteit_toegang/tests/test_auth.py` faalt op `no such table: berichten` — los van deze PR, maar blokkeert CI.

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

## Frontend — berichten fase 2

- **BFF-rolautorisatie**: `app/api/admin/berichten/` controleert `session.user.rol` niet — momenteel alleen beheerders actief, maar de BFF hoort rolautorisatie te dragen zodra analisten bestaan.
- **Gebruikers-sectie op `/beheer`**: placeholder; geen API nog. Story aanmaken zodra gebruikersbeheer gebouwd wordt.
- **E2E-tests voor `/beheer` en `/berichten`**: ontbreken nog (`frontend-bouwen` regel 6). Aanmaken vóór de feature in productie gaat.
