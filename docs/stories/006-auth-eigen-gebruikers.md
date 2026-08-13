# Story 006: Auth — eigen gebruikersbeheer (wetsanalyse-patroon)

**Prioriteit:** high
**Story points:** 5
**Service:** `api`, `frontend`, infrastructuur

## Verhaal

Als beheerder wil ik inloggen met gebruikersnaam en wachtwoord via een formulier in de app
zelf — zonder doorstuur naar Keycloak — zodat de loginervaring overeenkomt met de
wetsanalyse-applicatie en er geen externe identity provider nodig is.

## Aanpak

Story 005 (Keycloak OIDC) wordt vervangen door het wetsanalyse-patroon: een eigen
gebruikerstabel, bcrypt-wachtwoorden, en Auth.js Credentials-provider. De API-routes worden
bereikbaar via een Next.js BFF-laag (server-side, vaste `API_TOKEN`). Keycloak verdwijnt
volledig uit de stack.

- **API:** `gebruikers`-tabel (gebruikersnaam, wachtwoord_hash, rol, actief), `POST /v1/auth/verify`
  achter `API_TOKEN`-gate, `shared/auth.py` → `API_TOKEN` + `X-User-Id`-header
- **Frontend:** Auth.js Credentials-provider roept `/v1/auth/verify` server-side aan; loginpagina
  toont gebruikersnaam/wachtwoord-formulier; Next.js BFF-routes proxyen adminverzoeken naar
  de API met `API_TOKEN` + `X-User-Id` uit de Auth.js-sessie
- **Infrastructuur:** Keycloak-service verwijderd uit `docker-compose.yml` en CI;
  `API_TOKEN` + `AUTH_SECRET` als nieuwe env-vars

## Schemabeslissing

**Nieuwe tabel `gebruikers`:**

| Kolom | Type | Opmerking |
|---|---|---|
| `id` | INTEGER PK | auto-increment |
| `gebruikersnaam` | VARCHAR(64) UNIQUE NOT NULL | lowercase, login-identiteit |
| `wachtwoord_hash` | TEXT NOT NULL | bcrypt-hash, verlaat de API nooit |
| `rol` | VARCHAR(16) NOT NULL DEFAULT 'beheerder' | `beheerder` \| `analist` |
| `actief` | BOOLEAN NOT NULL DEFAULT TRUE | |
| `aangemaakt_op` | TIMESTAMP NOT NULL | |

**`POST /v1/auth/verify` (achter API_TOKEN):**

Request: `{"gebruikersnaam": "...", "wachtwoord": "..."}`
Response: `{"ok": true, "gebruikersnaam": "beheerder", "rol": "beheerder"}`
of `{"ok": false, "gebruikersnaam": "", "rol": ""}` — altijd 200 zodat Auth.js de code
kan lezen zonder exception-afhandeling.

**`shared/auth.py` na migratie:**

`huidige_beheerder` verifieert `Authorization: Bearer <API_TOKEN>` (constant-time vergelijking)
en leest gebruikersnaam uit `X-User-Id`-header. De BFF is verantwoordelijk voor rolautorisatie
(stuurt alleen beheerders naar admin-endpoints).

**Nieuwe env-vars:**

| Var | Waar | Opmerking |
|---|---|---|
| `API_TOKEN` | API + frontend (server) | Machine-token BFF→API |
| `AUTH_SECRET` | Frontend (server) | Auth.js JWT-signing |
| `API_BASE_URL` | Frontend (server) | Interne API-URL voor server-side calls |

Vervallen: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `NEXT_PUBLIC_KEYCLOAK_*`, `KEYCLOAK_CLIENT_ID`.
`NEXT_PUBLIC_API_BASE_URL` blijft voor eventuele publieke routes.

## Acceptatiecriteria

- [ ] Tabel `gebruikers` wordt aangemaakt via Alembic-migratie 0003.
- [ ] `POST /v1/auth/verify` achter `API_TOKEN`-gate: geldig wachtwoord → `{"ok": true, ...}`;
      fout wachtwoord of onbekende gebruiker → `{"ok": false, ..., ""}`.
- [ ] Admin-routes (`/v1/admin/*`) accepteren alleen requests met geldige `API_TOKEN` als
      `Authorization: Bearer` en een `X-User-Id`-header; ontbreekt een van beide → `401`.
- [ ] Login via formulier in de app (gebruikersnaam + wachtwoord); geen redirect naar Keycloak.
- [ ] Na inloggen: Auth.js httpOnly sessiecookie; geen token in `localStorage`.
- [ ] Niet-ingelogde gebruiker naar `/` → redirect naar `/login` (via `proxy.ts` middleware).
- [ ] Ingelogde gebruiker naar `/login` → redirect naar `/`.
- [ ] Navigatieheader toont gebruikersnaam en "Uitloggen"-knop; uitloggen wist sessie en stuurt
      door naar `/login`.
- [ ] Admin-API-calls gaan via Next.js BFF-routes (`/api/admin/berichten/...`); browser stuurt
      nooit rechtstreeks naar de API voor admin-endpoints.
- [ ] Keycloak-service en `keycloak/`-directory zijn verwijderd; geen `KEYCLOAK_*` env-vars meer.
- [ ] Bestaande Playwright-E2E-tests aangepast: `beforeEach` logt in via het loginformulier.
- [ ] CI draait zonder Keycloak-container; dev-gebruiker aangemaakt via seed-script.

## Edge cases

- Fout wachtwoord: 200 `{"ok": false}` (geen 401) zodat Auth.js de fout kan tonen.
- Onbekende gebruiker: dummy bcrypt-vergelijking om timing-oracle te voorkomen.
- Uitgelogde sessie: BFF-routes geven 401 terug, client redirect naar `/login`.
- Gedeactiveerde gebruiker: verificatie faalt (`actief=false` → `ok=false`).

## Auth / rollen

- `POST /v1/auth/verify` — achter `API_TOKEN`, geen `X-User-Id` vereist (is de verify zelf)
- `/v1/admin/*` — achter `API_TOKEN` + `X-User-Id`
- Publieke routes — ongewijzigd

## Gedeelde logica

- `shared/auth.py` — `huidige_beheerder` gebruikt `API_TOKEN` + `X-User-Id` (was: Keycloak JWKS)
- `features/identiteit_toegang/` — nieuwe router + store voor gebruikersbeheer en credential-verificatie
