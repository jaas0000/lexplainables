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

## Frontend — berichten fase 2

- **BFF-rolautorisatie**: `app/api/admin/berichten/` controleert `session.user.rol` niet — momenteel alleen beheerders actief, maar de BFF hoort rolautorisatie te dragen zodra analisten bestaan.
- **Gebruikers-sectie op `/beheer`**: placeholder; geen API nog. Story aanmaken zodra gebruikersbeheer gebouwd wordt.
- **E2E-tests voor `/beheer` en `/berichten`**: ontbreken nog (`frontend-bouwen` regel 6). Aanmaken vóór de feature in productie gaat.
