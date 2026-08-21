# ADR-0004: Auth.js in de frontend voor sessies, custom store aan de api-kant

**Status:** geaccepteerd
**Datum:** 2026-08-21

## Context

Lexplainables heeft nu een eigen, minimale auth-flow: een POST-endpoint `/api/auth/verify` in
de api, een custom cookie in de frontend, geen sessie-invalidatie, geen CSRF-bescherming, geen
provider-integratie. Werkbaar voor een demo, ongeschikt voor productie.

Wetsanalyse-ai gebruikt **Auth.js (voorheen NextAuth) in de frontend** als sessie-manager: de
frontend regelt login, sessie-cookies, CSRF en `middleware.ts`-guards. De api blijft daarbij de
identiteitsbron — een `POST /v1/auth/verify` levert userid + rol na correcte credentials, en
`GET /v1/auth/me` bevestigt de sessie. Auth.js praat server-side met de api en injecteert het
API-token; het API-token komt nooit in de browser.

Alternatieven:
- **Blijven bij custom cookie-flow** — te weinig CSRF/session-invalidatie voor productie.
- **Keycloak** (oorspronkelijke gedachte in ADR-0002) — is uit wetsanalyse-ai verwijderd omdat
  de operationele last (aparte service, aparte upgrade-cyclus, eigen DB) niet opweegt tegen wat
  we ermee doen (userid + rol; geen SSO-integratie met externe systemen op korte termijn).
- **Volledig custom sessies aan api-kant** — dan bouw je Auth.js opnieuw, slechter.

## Beslissing

**Auth.js in de frontend voor sessie-management + guards + CSRF; api blijft identiteitsbron.**

Concreet:
- Frontend gebruikt Auth.js (Credentials-provider) met sessie in JWT-cookie.
- `middleware.ts` beschermt alle `/app/*`-routes behalve `/login`, `/setup`.
- API blijft: `POST /v1/auth/verify` voor login, `GET /v1/auth/me` voor sessie-verificatie,
  eigen store voor gebruikers (`features/identiteit_toegang`).
- Server-side BFF-routes injecteren het API-token; browser krijgt het nooit.
- Rol-check in de api via een gedeelde dependency (`shared/auth.py`), zoals nu.

## Consequenties

- **Bewust geaccepteerd:** Auth.js is een dependency met eigen upgrade-track en breaking
  changes (bijv. NextAuth v4 → Auth.js v5 herstructurering). We aanvaarden die last omdat een
  eigen sessie-implementatie meer werk en meer risico geeft.
- **BFF-scheiding hard**: `frontend/lib/config.ts` (token uit env, cached) en `frontend/auth.ts`
  zijn server-only; nooit importeren vanuit Client Components. Dit is de harde regel uit
  wetsanalyse-ai's `frontend/CLAUDE.md` — die nemen we mee.
- **ADR-0002 (Keycloak) is vervangen** — zie de update daar.
- **2FA (story 017)** past hierin: Auth.js callback verifieert de TOTP-stap via de api voordat
  hij een sessie aanmaakt.
- **Sessie-storage:** JWT-cookies, geen server-side sessie-tabel (geen extra tabel in de api,
  geen redis). Wetsanalyse-ai draait het zo en dat werkt.
