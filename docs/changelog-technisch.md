# Technische changelog

- Eerste frontend: berichten-admin-scherm (PR #2): Eerste frontend-service (`frontend/`) — Next.js admin-scherm voor berichtenbeheer, contractgeneratie API→TypeScript via `openapi-typescript`, CORS-middleware op de API, Playwright E2E-test (gelukkig pad + foutpad), eigen `frontend-ci.yml`, C4-architectuurdocumentatie.
- Huisstijl-frontend (PR #3): Wetsanalyse-kleurtokens als CSS-variabelen in `globals.css`, Fira Sans via `next/font/google`, navigatieheader in `layout.tsx`, en herstructurering van `page.tsx` naar CSS-klassen (`btn`, `field-input`, `tabel`, `badge`, `melding`); E2E-selectorfix `p[role="alert"]` in commit `9c45f09`.
