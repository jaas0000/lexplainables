# Story 015: Setup-flow (initiële beheerder)

**Prioriteit:** middel
**Story points:** 2
**Service:** `api/` + `frontend/`

## Verhaal

Als eerste gebruiker van een verse installatie wil ik direct in de app een beheerdersaccount kunnen aanmaken, zonder eerst handmatig een seed-commando te draaien, zodat de applicatie meteen bruikbaar is na deployment.

## Acceptatiecriteria

- [ ] `GET /v1/auth/setup-status` geeft `{"needs_setup": true}` terug zolang de `gebruikers`-tabel leeg is, en `{"needs_setup": false}` zodra er minstens één gebruiker bestaat.
- [ ] `POST /v1/auth/setup` maakt de eerste beheerder aan en geeft het account terug; als er al gebruikers zijn, geeft de API 409 terug.
- [ ] De frontend controleert bij het laden van `/login` of setup nodig is en redirect naar `/setup` als dat zo is.
- [ ] De setuproute `/setup` toont een formulier met gebruikersnaam, e-mailadres en wachtwoord (bevestiging); na een geslaagde setup redirect de pagina naar `/login`.
- [ ] Een ingelogde gebruiker die `/setup` bezoekt, wordt omgeleid naar `/` (setup is al gedaan).
- [ ] Na de setup is de seed-procedure (`maak_gebruiker_indien_ontbreekt`) niet meer nodig voor verse installaties; het seed-script blijft beschikbaar voor CI/dev-omgevingen.
- [ ] Alembic-migratie voegt het kolom `email` (TEXT NOT NULL DEFAULT '') toe aan de `gebruikers`-tabel; bestaande rijen krijgen een lege e-mail.

## Schemabeslissing

**Alembic-migratie:** voeg `email TEXT NOT NULL DEFAULT ''` en `bijgewerkt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP` toe aan `gebruikers` (migrations/0004_*).

**Python-models (`api/app/features/identiteit_toegang/models.py` uitbreiden):**

- `SetupStatus` — `needs_setup: bool`
- `SetupVerzoek` — `gebruikersnaam: str` (max 64, `[a-z0-9._-]{3,64}`), `email: str` (max 320), `wachtwoord: str` (min 8, max 512)
- `GebruikerInfo` — `gebruikersnaam: str`, `email: str`, `rol: str`

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/auth/setup-status` | GET | Is er nog geen account? | `vereist_api_token` |
| `/v1/auth/setup` | POST | Maak de eerste beheerder aan | `vereist_api_token` |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/auth/setup-status/route.ts` | GET | Proxy → `/v1/auth/setup-status` |
| `app/api/auth/setup/route.ts` | POST | Proxy → `/v1/auth/setup` |

## Edge cases

- Setup aanroepen terwijl er al gebruikers zijn → API 409 met "Setup al voltooid."; de frontend toont een foutmelding en een link naar `/login`.
- Ongeldige gebruikersnaam (te kort, verboden tekens) → API 422; frontend toont foutmelding per veld.
- Wachtwoord te kort (<8 tekens) → API 422; frontend valideert voor verzenden.
- E-mailadres al in gebruik (toekomst, momenteel enige gebruiker) → API 409.
- Netwerk-fout bij setup → foutmelding; formulier blijft invulbaar.
- Setup-status endpoint is openbaar (alleen API_TOKEN, geen X-User-Id) zodat de middleware de check kan doen vóór login.

## Auth / rollen

- `GET /v1/auth/setup-status` — achter `vereist_api_token` (BFF-machine-token); geen `X-User-Id` nodig.
- `POST /v1/auth/setup` — achter `vereist_api_token`; geen `X-User-Id` nodig (er is immers nog geen ingelogde gebruiker).
- De frontend-middleware (`middleware.ts`) controleert setup-status vóór de sessiecheck: needs_setup → `/setup`, anders normale sessiestroom.

## Gedeelde logica

- `vereist_api_token` uit `shared/auth.py` — bestaat ✓
- Store-functie `tabel_leeg() -> bool` toevoegen aan `identiteit_toegang/store.py`.
- Store-functie `maak_eerste_beheerder(gebruikersnaam, email, wachtwoord)` toevoegen — gooit `GebruikerFout` als de tabel al niet leeg is.
- `requireSession()` uit de BFF-lib — bestaat ✓; setup-routes zijn exempt van sessiecheck.

## Implementatienoot

Routerlogica kopiëren en aanpassen vanuit `wetsanalyse-ai/api/app/routers/auth.py` (functies `setup_status` en `setup`). De setup-route is slechts een thin wrapper: de invariant "tabel leeg" zit in `store.py`. De `email`-migratie maakt het veld nullable of voorziet een lege default om te voorkomen dat de migratie faalt op bestaande rijen; de login-flow gebruikt `email` niet als identiteit.

## UI

- **`/setup`** (Server Component met client-formulier): bevat een formulier met drie velden (gebruikersnaam, e-mail, wachtwoord + bevestiging), een submit-knop "Aanmaken" en de melding "Stel de eerste beheerder in — dit formulier is na de eerste aanmelding niet meer beschikbaar."
- **Redirect-logica** in `middleware.ts`: controleer setup-status bij elke request; redirect naar `/setup` als `needs_setup: true`; redirect van `/setup` naar `/` als de gebruiker al ingelogd is.
- Huisstijl: zelfde opmaak als het login-formulier (story 005).

**Gebouwd:** nee
