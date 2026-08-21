# ADR-0002: Keycloak als identity provider voor auth

**Status:** vervangen door ADR-0004
**Datum:** 2026-08-13
**Vervangen:** 2026-08-21

> **Herroepen.** Bij het overzetten van wetsanalyse-ai is Keycloak volledig weggehaald: de
> operationele last (aparte service, upgrade-cyclus, eigen DB) woog niet op tegen wat we ermee
> deden (userid + rol). Vervangen door **Auth.js in de frontend** met de api als
> identiteitsbron — zie [ADR-0004](0004-authjs-frontend-sessies.md). De rest van dit document
> blijft staan voor historische context, maar de beslissing is niet meer van kracht.

## Context

De applicatie heeft auth nodig. Er zijn twee realistische opties:

1. **Eenvoudige JWT in FastAPI** — eigen `gebruikers`-tabel, bcrypt-hashing, token-signing
   met een server-side secret. Volledig in eigen beheer, geen externe afhankelijkheid.
2. **Keycloak (OIDC, Authorization Code + PKCE)** — externe identity provider, geen eigen
   gebruikerstabel, login via Keycloak-UI, token-verificatie via JWKS.

De architectuur (ADR-0001) plant zes services. SSO wordt waardevol zodra er meerdere services
zijn die dezelfde gebruiker herkennen: een gebruiker die inlogt op de frontend hoeft dan niet
opnieuw in te loggen op een andere service.

## Beslissing

**Keycloak als identity provider.**

De applicatie beheert zelf geen wachtwoorden of gebruikersrecords. Login loopt via de
standaard OIDC Authorization Code + PKCE-flow. De API verifieert het Keycloak-JWT via het
JWKS-endpoint; de frontend gebruikt `next-auth@5` met de Keycloak-provider.

Lokale ontwikkeling gebruikt een Keycloak-container (poort 8080) met een realm-export
(`keycloak/realm-export.json`) die reproduceerbaar het realm, de client, de rollen en een
standaard dev-gebruiker configureert.

## Consequenties

**Voordelen:**
- Geen eigen wachtwoord-hashing, geen eigen gebruikersbeheer — minder code, minder
  beveiligingsrisico's.
- SSO werkt later gratis voor alle services die dezelfde Keycloak-realm gebruiken.
- Keycloak biedt MFA, social login, wachtwoord-policy en audit-logs out-of-the-box.
- De API-grens is schoon: `shared/auth.py` is het enige raakvlak; vervanging (bv. Azure AD)
  vereist uitsluitend aanpassingen in dat bestand.

**Nadelen / risico's:**
- Keycloak is zware infrastructuur voor een vroeg-stadium project.
- Lokale dev vereist een draaiende Keycloak-container; `docker-compose up` wordt een vereiste.
- E2E-tests hebben een speciale aanpak nodig (direct token ophalen via Keycloak-endpoint).
- De login-pagina in de applicatie is een doorstuurpagina naar Keycloak, niet een eigen
  formulier — visuele controle over de login-UI is beperkt zonder Keycloak-theming.

**Buiten scope (expliciet uitgesteld):**
- Keycloak-theming (login-pagina in wetsanalyse-huisstijl).
- Wachtwoord-reset-flow via de applicatie.
- Admin-UI voor gebruikersbeheer in Keycloak (gebruik de Keycloak-beheersconsole).
- Service-to-service auth (nog geen tweede service).
