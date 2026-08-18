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

## Frontend — berichten fase 2

- **BFF-rolautorisatie**: `app/api/admin/berichten/` controleert `session.user.rol` niet — momenteel alleen beheerders actief, maar de BFF hoort rolautorisatie te dragen zodra analisten bestaan.
- **Gebruikers-sectie op `/beheer`**: placeholder; geen API nog. Story aanmaken zodra gebruikersbeheer gebouwd wordt.
- **E2E-tests voor `/beheer` en `/berichten`**: ontbreken nog (`frontend-bouwen` regel 6). Aanmaken vóór de feature in productie gaat.
