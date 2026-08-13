# Story 005: Auth — inloggen en uitloggen via Keycloak

**Prioriteit:** high
**Story points:** 5
**Service:** `api`, `frontend`, infrastructuur

## Verhaal

Als beheerder wil ik inloggen met mijn Keycloak-account, zodat alleen geautoriseerde
gebruikers het beheerscherm kunnen gebruiken en de huidige stand-in (beheerder-id vrij
invullen) verdwijnt.

## Aanpak

Keycloak als identity provider (OIDC, Authorization Code + PKCE):

- Keycloak-container in de lokale stack (poort 8080), realm `wetsanalyse` importeerbaar
  via `keycloak/realm-export.json`
- Frontend: `next-auth@5` met Keycloak-provider; `/login` toont een kaart met een
  "Inloggen"-knop die de OIDC-flow start (redirect naar Keycloak); na succesvolle auth
  terug naar `/`
- Backend: verifieer Keycloak-JWT via JWKS-endpoint, lees `preferred_username` +
  `realm_access.roles` uit het token; geen eigen gebruikerstabel nodig
- `shared/auth.py` vervangt de header-stand-ins door JWT-verificatie; routercode
  (`/v1/admin/*`) blijft ongewijzigd behalve de type-aanpassing in `maak_bericht`

Eenvoudige JWT-auth in FastAPI (custom forms, eigen gebruikerstabel) is bewust uitgesteld:
Keycloak beheert gebruikers centraal en kan later uitgebreid worden naar meerdere services
zonder code-aanpassingen in de API's.

## Schemabeslissing

**Geen nieuwe databasetabel** — gebruikersbeheer delegeert volledig aan Keycloak.

**Keycloak-realm (`keycloak/realm-export.json`):**
- Realm: `wetsanalyse`
- Client: `lexplainables` (public client, PKCE verplicht, standard flow)
  - Geldige redirect-URI's: `http://localhost:3001/*`
  - Web origins: `http://localhost:3001`
- Realm-rollen: `beheerder`, `analist`
- Standaard dev-gebruiker: gebruikersnaam `beheerder`, wachtwoord `beheerder123`,
  rol `beheerder` (alleen in de realm-export, niet in de applicatie-DB)

**`GebruikerContext` (intern Pydantic-model, niet als API-respons):**
```python
class GebruikerContext(BaseModel):
    gebruikersnaam: str   # Keycloak preferred_username
    rol: Literal["beheerder", "analist"]
```

**Nieuwe env-vars (API):**

| Var | Voorbeeld | Verplicht |
|---|---|---|
| `KEYCLOAK_URL` | `http://localhost:8080` | ja |
| `KEYCLOAK_REALM` | `wetsanalyse` | ja |

**Nieuwe env-vars (frontend):**

| Var | Voorbeeld | Verplicht |
|---|---|---|
| `NEXTAUTH_URL` | `http://localhost:3001` | ja |
| `NEXTAUTH_SECRET` | (willekeurige string, min 32 chars) | ja |
| `KEYCLOAK_CLIENT_ID` | `lexplainables` | ja |
| `KEYCLOAK_ISSUER` | `http://localhost:8080/realms/wetsanalyse` | ja |

## Acceptatiecriteria

- [ ] Keycloak draait lokaal via docker-compose op poort 8080; realm `wetsanalyse` wordt
      bij het opstarten geïmporteerd uit `keycloak/realm-export.json`.
- [ ] Dev-gebruiker `beheerder` (wachtwoord `beheerder123`, rol `beheerder`) is aanwezig
      na import van de realm-export.
- [ ] De bestaande admin-routes (`/v1/admin/*`) accepteren alleen requests met een geldig
      Keycloak-JWT als `Authorization: Bearer …`-header; een ontbrekend of verlopen token
      geeft `401 Unauthorized`.
- [ ] De `huidige_beheerder`-dependency levert een `GebruikerContext` op met
      `gebruikersnaam` (= Keycloak `preferred_username`) en `rol` (= eerste rol uit
      `realm_access.roles`); de `X-Admin-Id`-header-stand-in is verwijderd.
- [ ] `berichten/router.py` — `maak_bericht` geeft `admin_userid.gebruikersnaam` door aan
      `store.maak()` (was: `admin_userid` direct als `str`); `aangemaakt_door` in de tabel
      bevat de Keycloak-gebruikersnaam.
- [ ] JWT-verificatie gebruikt het JWKS-endpoint van Keycloak
      (`{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs`); de publieke
      sleutel wordt gecached en periodiek ververst (niet bij elke request opgehaald).
- [ ] Bij ontbrekend of ongeldig token: `401` met `{"detail": "Niet geautoriseerd."}`.
- [ ] Bij geldig token maar verkeerde rol (geen `beheerder`): `403` met
      `{"detail": "Onvoldoende rechten."}`.
- [ ] **Frontend — `/login`-pagina**:
  - Toont een kaart met de tekst "Inloggen" en een primaire knop "Inloggen".
  - Klikken op de knop start de OIDC Authorization Code + PKCE-flow (redirect naar
    Keycloak-loginpagina).
  - Na succesvolle authenticatie: terug naar `/`.
  - Niet-ingelogde gebruiker die `/` bezoekt, wordt doorgestuurd naar `/login`.
  - Ingelogde gebruiker die `/login` bezoekt, wordt doorgestuurd naar `/`.
- [ ] **Frontend — navigatieheader na inloggen**:
  - Toont de gebruikersnaam (Keycloak `preferred_username`) naast een "Uitloggen"-knop.
  - "Uitloggen" wist de sessie en stuurt door naar `/login`.
- [ ] **Frontend — API-calls**:
  - Alle fetch-calls sturen het Keycloak-access-token als `Authorization: Bearer …` mee.
  - Bij een `401`-respons: sessie wissen en doorsturen naar `/login`.
- [ ] Bestaande Playwright-E2E-tests aangepast: de `beforeEach`-hook logt in via de
      Keycloak-loginpagina (directe POST op het Keycloak-token-endpoint, niet via de UI) met
      `beheerder`/`beheerder123`; het verkregen token wordt als cookie of header
      doorgegeven aan de pagina. Data-isolatie via unieke titels.

## Edge cases

- Verlopen JWT: `401 Unauthorized` met `{"detail": "Token verlopen."}`.
- Misvormde JWT: `401` met `{"detail": "Ongeldig token."}`.
- Token bevat geen rollen (lege `realm_access.roles`): `403` met `{"detail": "Onvoldoende rechten."}`.
- Keycloak niet bereikbaar bij opstarten (JWKS-ophalen mislukt): de API start wel, maar
  elke beveiligde aanroep geeft `503 Service Unavailable` zolang de JWKS-cache leeg is.
- `aangemaakt_door` in de `berichten`-tabel: bestaande rijen met de oude vrije string-waarden
  blijven ongewijzigd (geen datamigrate, alleen schemawijzigingen zijn buiten scope).
- Dubbel inloggen (meerdere tabs): `next-auth` beheert de sessie — beide tabs zijn ingelogd,
  het token van de laatste refresh geldt.

## Auth / rollen

- `POST /v1/auth/...` — niet van toepassing; login loopt via Keycloak.
- `/v1/admin/*` — vereist geldig JWT met `realm_access.roles` containing `beheerder`.
- Publieke routes (`GET /v1/berichten`, feedback-routes) — ongewijzigd (`X-User-Id`-stand-in
  blijft; dat is een latere story).
- `/login` (frontend) — geen auth vereist.

## Gedeelde logica

- `shared/auth.py` — `huidige_beheerder` vervangt header-stand-in door JWKS-verificatie;
  `huidige_gebruiker` (publieke routes) blijft ongewijzigd.
- `features/berichten/router.py` — `maak_bericht` past `admin_userid.gebruikersnaam` toe.
- `keycloak/realm-export.json` — nieuwe directory in de repo-root.
- `docker-compose.yml` (of lokale setup) — Keycloak-service toevoegen.

## Mockup (login-pagina)

```
┌─────────────────────────────────────────────────────┐
│ Wetsanalyse                                         │
└─────────────────────────────────────────────────────┘

                 ┌─────────────────────────┐
                 │                         │
                 │   Inloggen              │
                 │                         │
                 │   [  Inloggen  ]        │
                 │                         │
                 └─────────────────────────┘

          (knop stuurt door naar Keycloak-loginpagina)
```

Na inloggen (navigatieheader):

```
┌─────────────────────────────────────────────────────────────────┐
│ Wetsanalyse  │ Berichten  Analisten  Projecten  Instellingen   │  beheerder  [Uitloggen] │
└─────────────────────────────────────────────────────────────────┘
```
