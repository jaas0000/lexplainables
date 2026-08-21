# Identiteit en toegang

gebruikersbeheer (aanmaken/bewerken/verwijderen door beheerder), inloggen (verify via bcrypt), eigen profiel bekijken (incl. `actief`-vlag voor de Auth.js live-rol-check) en wachtwoord wijzigen, plus TOTP-2FA (story 017) en eerste-beheerder-setup als de gebruikers-tabel leeg is.

**Waarom apart:** eigen domein voor identiteit — auth-verify, rol-check, wachtwoord-flow, 2FA horen op één plek en zijn wat andere features via `shared/auth.py` gebruiken; hier zit de bron.

**Grens:** sessie-cookies zelf leven in Auth.js (frontend); die roept `GET /v1/auth/me` periodiek aan (fase 2b.3 live-rol-check) voor rol-updates en deactivering. Het API-token voor externe integratie hoort bij `api_tokens`, niet hier.

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `GET` | `/auth/setup-status` | — | `SetupStatus` |
| `POST` | `/auth/setup` | — | `GebruikerInfo` |
| `POST` | `/auth/verify` | — | `VerifyResult` |
| `POST` | `/auth/2fa/begin` | beheerder | `TotpBeginResultaat` |
| `POST` | `/auth/2fa/activeer` | beheerder | — |
| `POST` | `/auth/2fa/uitschakel` | beheerder | — |
| `GET` | `/auth/me` | beheerder | `MijnProfiel` |
| `POST` | `/auth/wijzig-wachtwoord` | beheerder | — |
| `GET` | `/admin/gebruikers` | beheerder | `list[GebruikerRead]` |
| `POST` | `/admin/gebruikers` | beheerder | `GebruikerRead` |
| `PATCH` | `/admin/gebruikers/{gebruikersnaam}` | beheerder | `GebruikerRead` |
| `POST` | `/admin/gebruikers/{gebruikersnaam}/reset-wachtwoord` | beheerder | `TijdelijkWachtwoord` |
| `DELETE` | `/admin/gebruikers/{gebruikersnaam}` | beheerder | — |

## Interacties

- shared/auth.py: `huidige_gebruiker`, `huidige_beheerder`, `vereist_api_token` bouwen op deze tabel (`vereist_api_token` valt op api_tokens terug voor tokens, gebruikers zijn voor identity).
- db.py: `AsyncEngine` via `get_engine()`; store-functies zijn losse `async def`s die de engine als argument nemen (i.p.v. Protocol-class).

## Getest gedrag

- Begin totp koppeling maakt secret en uri.
- Begin zonder fernet key gooit cryptofout.
- Activeer totp met goede code zet vlag.
- Activeer totp met foute code raist.
- Activeer zonder pending setup raist.
- Uitschakel totp wist secret en vlag.
- Uitschakel totp met foute code raist.
- Verifieer credentials totp required zonder totp.
- Verifieer credentials met correcte totp slaagt.
- Verifieer credentials met verkeerde totp geeft invalid.
- Begin via http zonder sessie geeft 401.
- Begin zonder fernet key geeft 400.
- Admin gebruikers zonder token geeft 401.
- Admin gebruikers met fout token geeft 401.
- Admin gebruikers zonder user id geeft 401.
- Admin gebruikers met geldig token en user id geeft 200.
- Verify zonder api token geeft 401.
- Verify goede credentials.
- Verify fout wachtwoord.
- Verify onbekende gebruiker.
- Verify te veel pogingen geeft 429.
- Verify inactieve gebruiker.
- Maak gebruiker indien ontbreekt is idempotent.
- Me zonder token geeft 401.
- Me met geldig token geeft profiel.
- Haal gebruiker profiel.
- Mijnprofiel bevat actief veld voor live rol check.
- Haal gebruiker onbekend geeft domein fout.
- Wijzig wachtwoord zonder token geeft 401.
- Wijzig wachtwoord succes.
- Wijzig wachtwoord fout huidig geeft domein fout.
- Wijzig wachtwoord te kort geeft 422.
- Lijst gebruikers leeg.
- Lijst gebruikers na aanmaken.
- Maak gebruiker admin duplicaat.
- Wijzig rol.
- Wijzig actief.
- Wijzig onbekende gebruiker geeft exception.
- Wijzig laatste beheerder deactiveren geeft exception.
- Wijzig laatste beheerder degraderen geeft exception.
- Wijzig beheerder met meerdere beheerders.
- Reset wachtwoord.
- Reset onbekende gebruiker.
- Verwijder gebruiker.
- Verwijder onbekende gebruiker.
- Verwijder laatste beheerder gooit exception.
- Get gebruikers geeft lege lijst.
- Get gebruikers zonder auth geeft 401.
- Post gebruiker maakt aan.
- Post gebruiker duplicaat geeft 409.
- Post gebruiker ongeldige rol geeft 422.
- Patch wijzigt rol.
- Patch onbekende gebruiker geeft 404.
- Patch laatste beheerder deactiveren geeft 409.
- Patch ongeldige rol geeft 422.
- Reset wachtwoord endpoint.
- Reset onbekende gebruiker geeft 404.
- Delete verwijdert gebruiker.
- Delete onbekende gebruiker geeft 404.
- Delete laatste beheerder geeft 409.
- Delete zonder auth geeft 401.
- Tabel leeg bij lege db.
- Tabel leeg na gebruiker.
- Setup status zonder token geeft 401.
- Setup status leeg geeft needs setup true.
- Setup maakt eerste beheerder.
- Setup daarna needs setup false.
- Setup twee keer geeft 409.
- Setup wachtwoord te kort geeft 422.
- Setup ongeldige gebruikersnaam geeft 422.
- Setup zonder token geeft 401.

## Beslissingen

- ADR-0003 (auth-model): rollen `beheerder` en `analist`; bcrypt voor wachtwoorden; eerste beheerder eenmalig via `/setup` (mag alleen als tabel leeg).
- Story 006 §API-token: `POST /auth/verify` vereist `Depends(vereist_api_token)` (BFF-only) en levert gebruikersinfo terug voor Auth.js session.
- Story 014 §Laatste beheerder: laatste actieve beheerder kan niet verwijderd of gedegradeerd — `LaatsteBeheerder`-exception → 409.
- Fase 2b.3 §Live-rol-check: `MijnProfiel` bevat `actief` — Auth.js JWT ververst z'n rol/actief-cache periodiek via `GET /v1/auth/me`; 401 op deze route betekent voor de frontend "sessie ongeldig, uitloggen".
