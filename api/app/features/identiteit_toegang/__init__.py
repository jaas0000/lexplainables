"""Identiteit en toegang.

Wat: gebruikersbeheer (aanmaken/bewerken/verwijderen door beheerder), inloggen (verify via bcrypt), eigen profiel bekijken en wachtwoord wijzigen, plus eerste-beheerder-setup als de gebruikers-tabel leeg is.
Waarom: eigen domein voor identiteit — auth-verify, rol-check, wachtwoord-flow horen op één plek en zijn wat andere features via `shared/auth.py` gebruiken; hier zit de bron.
Grens: geen sessie-management (Auth.js in de frontend doet dat); het API-token voor externe integratie hoort bij `api_tokens`, niet hier; 2FA/TOTP staat gepland (story 017) maar zit hier nog niet.

Tabellen:
  - gebruikers: id + gebruikersnaam (uniek) + wachtwoord_hash (bcrypt) + email + rol (beheerder/analist) + actief + aangemaakt_op. SQLModel-gedefinieerd (ORM-tak; niet als SQLAlchemy Core Table zoals de rest).

Beslissingen:
  - ADR-0003 (auth-model): rollen `beheerder` en `analist`; bcrypt voor wachtwoorden; eerste beheerder eenmalig via `/setup` (mag alleen als tabel leeg).
  - Story 006 §API-token: `POST /auth/verify` vereist `Depends(vereist_api_token)` (BFF-only) en levert gebruikersinfo terug voor Auth.js session.
  - Story 014 §Laatste beheerder: laatste actieve beheerder kan niet verwijderd of gedegradeerd — `LaatsteBeheerder`-exception → 409.

Interacties:
  - shared/auth.py: `huidige_gebruiker`, `huidige_beheerder`, `vereist_api_token` bouwen op deze tabel (`vereist_api_token` valt op api_tokens terug voor tokens, gebruikers zijn voor identity).
  - db.py: `AsyncEngine` via `get_engine()`; store-functies zijn losse `async def`s die de engine als argument nemen (i.p.v. Protocol-class).
"""
