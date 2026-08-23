"""Identiteit en toegang.

Wat: gebruikersbeheer (aanmaken/bewerken/verwijderen door beheerder), inloggen (verify via
bcrypt), eigen profiel bekijken (incl. `actief`-vlag voor de Auth.js live-rol-check) en
wachtwoord wijzigen, plus TOTP-2FA (story 017) en eerste-beheerder-setup als de
gebruikers-tabel leeg is.
Waarom: eigen domein voor identiteit — auth-verify, rol-check, wachtwoord-flow, 2FA horen op
één plek en zijn wat andere features via `shared/auth.py` gebruiken; hier zit de bron.
Grens: sessie-cookies zelf leven in Auth.js (frontend); die roept `GET /v1/auth/me` periodiek
aan (fase 2b.3 live-rol-check) voor rol-updates en deactivering. Het API-token voor externe
integratie hoort bij `api_tokens`, niet hier.

Tabellen:
  - gebruikers: id + gebruikersnaam (uniek) + wachtwoord_hash (bcrypt) + email + rol
    (beheerder/analist) + actief + aangemaakt_op + totp_secret_enc + totp_ingeschakeld.
    SQLAlchemy Core Table + Pydantic-contracten, zelfde patroon als de rest (werkwijze-ADR-0011).

Beslissingen:
  - ADR-0003 (auth-model): rollen `beheerder` en `analist`; bcrypt voor wachtwoorden; eerste
    beheerder eenmalig via `/setup` (mag alleen als tabel leeg).
  - Story 006 §API-token: `POST /auth/verify` vereist `Depends(vereist_api_token)` (BFF-only)
    en levert gebruikersinfo terug voor Auth.js session.
  - Story 014 §Laatste beheerder: laatste actieve beheerder kan niet verwijderd of
    gedegradeerd — `LaatsteBeheerder`-exception → 409.
  - Fase 2b.3 §Live-rol-check: `MijnProfiel` bevat `actief` — Auth.js JWT ververst z'n
    rol/actief-cache periodiek via `GET /v1/auth/me`; 401 op deze route betekent voor de
    frontend "sessie ongeldig, uitloggen".

Interacties:
  - shared/auth.py: `huidige_gebruiker`, `huidige_beheerder`, `vereist_api_token` bouwen op
    deze tabel (`vereist_api_token` valt op api_tokens terug voor tokens, gebruikers zijn
    voor identity).
  - db.py: `AsyncEngine` via `get_engine()`; store-functies zijn losse `async def`s die de
    engine als argument nemen (i.p.v. Protocol-class).
"""
