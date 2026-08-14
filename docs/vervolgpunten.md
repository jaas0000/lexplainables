# Vervolgpunten

Niet-blocking bevindingen uit code-reviews die een follow-up verdienen.

---

## Werkwijze

- **"Ingelogd blijven"-checkbox functioneel maken**: de checkbox staat visueel op de loginpagina maar doet nog niets. Zodra de sessieduur-logica gebouwd wordt (story nog aan te maken), hier de `remember`-vlag doorgeven aan de Auth.js Credentials-provider (zoals wetsanalyse dat doet met `rememberMe` in de JWT-callback).
- **Mockup-stap in `frontend-bouwen` verbeterd en vastgelegd** ✓: dev-server als canvas, `/mockup/<feature>/`-pad, interactieve nepdata-component, badge, promotie naar definitief pad. Vastgelegd in `werkwijze-v2-multi-service/werkwijze/.claude/skills/frontend-bouwen/SKILL.md` (regels 2-4 + §Mockup-structuur).

---

## PR #5 — auth-eigen-gebruikers (story 006)

- `docs/architectuur/c4-model.md` bijwerken: L1/L2 vermelden Keycloak nog als externe service; L3 toont de oude PKCE-componenten en mist `identiteit_toegang` en de BFF-routes.
- BFF-routes controleren `session.user.rol` niet — momenteel geen `analist`-gebruikers, maar de architectuur (story 006) zegt dat de BFF de rolautorisatie draagt. Toevoegen zodra meerdere rollen in gebruik komen.

---

## PR #3 — huisstijl-frontend (story 004)

- **MEDIUM** — `.melding-fout` bypast het token-systeem: `color: rgb(213 43 30)` in
  `frontend/app/globals.css:234` is hardcoded. Fix: `color: rgb(var(--fout))`.
- **MEDIUM** — Geen `<h1>` op de pagina (opgelost in `app/beheer/page.tsx` en `app/berichten/page.tsx`; nog open voor de mockup-pagina's).
- **LAAG** — `border-color` in de universele `*`-reset (`globals.css:26`) preset de
  randkleur op alle elementen; ongebruikelijk en kan onverwachte randen geven op
  elementen zonder CSS-klasse.

---

## PR #6 — admin-mcp (story 007)

- **Simplify-definitie nalopen**: de `n.v.t.`-uitzondering in `feature-bouwen` regel 9 is bedoeld voor "geen productiecode" (puur docs/CI), niet voor "geen bestaande code". Bij de volgende story die `tools/` raakt, `/simplify` ook op nieuwe TypeScript-productiecode draaien.

---

## Frontend — berichten fase 2

- **BFF-rolautorisatie**: `app/api/admin/berichten/` controleert `session.user.rol` niet — momenteel alleen beheerders actief, maar de BFF hoort rolautorisatie te dragen zodra analisten bestaan.
- **Gebruikers-sectie op `/beheer`**: placeholder; geen API nog. Story aanmaken zodra gebruikersbeheer gebouwd wordt.
- **E2E-tests voor `/beheer` en `/berichten`**: ontbreken nog (`frontend-bouwen` regel 6). Aanmaken vóór de feature in productie gaat.
