"""Feedback.

Wat: analisten dienen feedback in over de applicatie; beheerders zien de lijst, verwijderen
items en houden bij tot wanneer ze zelf de pagina hebben gezien.
Waarom: dit is een zelfstandig domein — het bezit zowel de feedback zelf als de per-beheerder
leesbewijzen, en heeft geen andere functie nodig dan dat (werkwijze-ADR-0001, vertical slicing).
Grens: het feedbackdomein levert geen realtime-notificaties (dat is `berichten`); auth-checks
op de router leunen op de gedeelde stand-in (`shared/auth.py`), niet op eigen identiteit.

Tabellen:
  - user_feedback: append-only rij per ingediend item (id, client_id, userid, categorie, tekst, pagina, created).
  - feedback_leesbewijzen: per beheerder tot welk tijdstip de feedbackpagina is gezien.

Beslissingen:
  - ADR-0001 (vertical slicing): eigen tabel `feedback_leesbewijzen` in plaats van kolom op users.
  - ADR-0007 (store-abstractie): router leunt op een Protocol, tests draaien tegen de echte SQL-store.
  - ADR-0011 (schema-eenheid + expliciete mapping): SQLAlchemy Core + Pydantic + `feedback_uit_rij` op één plek.
  - Story 001 §Schemabeslissing: `Literal["verbeteridee",...]` i.p.v. string+regex — genereert een echte enum in OpenAPI.

Interacties:
  - shared/auth.py: `huidige_gebruiker` (indien-ingelogd) en `huidige_beheerder` (rol-check) dependency.
  - shared/tijd.py: `nu()` als vervangbare klok voor `created`/`gezien_tot`.
  - db.py: de `AsyncEngine` wordt via `get_engine()` in de router aan de store gegeven.
"""
