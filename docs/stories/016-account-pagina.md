# Story 016: Account-pagina (eigen profiel)

**Prioriteit:** laag
**Story points:** 2
**Service:** `api/` + `frontend/`
**Afhankelijkheid:** story 015 (e-mailveld aanwezig in gebruikerstabel)

## Verhaal

Als ingelogde gebruiker wil ik mijn eigen accountgegevens kunnen inzien en mijn wachtwoord kunnen wijzigen, zodat ik mijn account zelfstandig kan beheren zonder een beheerder te hoeven inschakelen.

## Acceptatiecriteria

- [ ] `GET /v1/auth/me` geeft de eigen accountgegevens terug: gebruikersnaam, e-mail, rol en of 2FA aanstaat.
- [ ] `POST /v1/auth/wijzig-wachtwoord` accepteert het huidige en het nieuwe wachtwoord; bij een verkeerd huidig wachtwoord geeft de API een 400 terug.
- [ ] Het nieuwe wachtwoord moet minimaal 8 tekens zijn; de API valideert dit en de frontend valideert voor verzenden.
- [ ] De frontend-route `/account` toont gebruikersnaam, e-mail en rol als alleen-lezen, met daaronder een sectie "Wachtwoord wijzigen".
- [ ] Na een geslaagde wachtwoord-wijziging toont de frontend een succesmelding; het formulier wordt gereset.
- [ ] Een niet-ingelogde gebruiker die `/account` bezoekt, wordt omgeleid naar `/login`.
- [ ] De navigatiebalk heeft een link naar `/account` (of een accountmenu achter de gebruikersnaam).

## Schemabeslissing

**Python-models (`api/app/features/identiteit_toegang/models.py` uitbreiden):**

- `EigenAccountInfo` — `gebruikersnaam: str`, `email: str`, `rol: str`, `totp_ingeschakeld: bool`
- `WachtwoordWijzigenVerzoek` — `huidig: str` (max 512), `nieuw: str` (min 8, max 512)

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/auth/me` | GET | Eigen accountgegevens | `vereist_api_token` + `X-User-Id` |
| `/v1/auth/wijzig-wachtwoord` | POST | Eigen wachtwoord wijzigen | `vereist_api_token` + `X-User-Id` |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/auth/me/route.ts` | GET | Proxy → `/v1/auth/me` |
| `app/api/auth/wijzig-wachtwoord/route.ts` | POST | Proxy → `/v1/auth/wijzig-wachtwoord` |

## Edge cases

- Account niet meer actief of verwijderd terwijl sessie nog geldig is → API 401; frontend redirect naar `/login`.
- Huidig wachtwoord onjuist → API 400 met "Huidig wachtwoord klopt niet."; frontend toont foutmelding bij het veld.
- Nieuw wachtwoord gelijk aan het huidige → de API staat dit toe (geen beleidsverplichting om te variëren).
- Sessie verlopen tussen laden en verzenden → BFF geeft 401 terug; frontend redirect naar `/login`.
- `totp_ingeschakeld` is `false` als 2FA nog niet gebouwd is (story 017 vult dit in); het veld is al aanwezig in het model.

## Auth / rollen

- `GET /v1/auth/me` en `POST /v1/auth/wijzig-wachtwoord` — achter `vereist_api_token` (BFF-machine-token) + `X-User-Id`-header (identiteit uit de Auth.js-sessie).
- Geen rolbeperking — elke ingelogde gebruiker (beheerder én analist) mag zijn eigen account beheren.

## Gedeelde logica

- `vereist_api_token` + `huidige_gebruiker` uit `shared/auth.py` — bestaan ✓
- Store-functie `haal_gebruiker(gebruikersnaam)` uitbreiden of hergebruiken.
- Store-functie `wijzig_eigen_wachtwoord(gebruikersnaam, huidig, nieuw)` toevoegen — vergelijkt het huidige wachtwoord via bcrypt, hasht het nieuwe en slaat op.
- `requireSession()` + `apiProxy()` uit de BFF-lib — bestaan ✓

## Implementatienoot

Routerlogica kopiëren en aanpassen vanuit `wetsanalyse-ai/api/app/routers/auth.py` (functies `me` en `change_password`). De `X-User-Id`-header identificeert de gebruiker; de BFF leest dit uit de Auth.js-sessie. Het veld `totp_ingeschakeld` is initieel altijd `false`; story 017 maakt het functioneel.

## UI

- **`/account`**: twee secties — "Mijn gegevens" (gebruikersnaam, e-mail, rol als leesbare tekst) en "Wachtwoord wijzigen" (formulier met drie velden: huidig, nieuw, bevestiging). Optioneel in de toekomst: 2FA-sectie (story 017).
- **Navigatiebalk**: gebruikersnaam als klikbare link naar `/account`, of als label in een dropdown naast de "Uitloggen"-knop.
- Mockup-varianten: accountpagina (leeg), na succesvolle wachtwoord-wijziging (succesmelding), na verkeerd wachtwoord (foutmelding bij veld).

**Gebouwd:** ja (PR #12)
