# Story 014: Gebruikersbeheer uitbreiden

**Prioriteit:** middel
**Story points:** 2
**Service:** `api/` + `frontend/`
**Afhankelijkheid:** story 006 (aanmaken + lijst bestaand)

## Verhaal

Als beheerder wil ik een bestaand account kunnen bewerken (rol en actief-status), een wachtwoord kunnen resetten, en een account kunnen verwijderen, zodat ik de toegang actueel kan houden zonder handmatig in de database te hoeven werken.

## Acceptatiecriteria

- [ ] Een beheerder kan de rol (`beheerder` | `analist`) en de actief-status van een bestaand account wijzigen via een PATCH-verzoek.
- [ ] Een beheerder kan een tijdelijk wachtwoord genereren voor een account; dit wachtwoord wordt éénmalig teruggegeven en is daarna niet meer opvraagbaar.
- [ ] Een beheerder kan een account verwijderen.
- [ ] De laatste actieve beheerder mag niet worden gedeactiveerd of verwijderd — de API weigert dit met een 409.
- [ ] Frontend: de gebruikerslijst op `/beheer` toont per rij een "Bewerk"-actie (inline rol/actief-formulier), een "Reset wachtwoord"-knop, en een "Verwijder"-knop.
- [ ] Na een geslaagde wachtwoord-reset toont de frontend het tijdelijke wachtwoord eenmalig in een modal — de gebruiker wordt gevraagd het te noteren.
- [ ] Bij verwijderen vraagt de frontend om bevestiging ("Weet je zeker dat je ... wilt verwijderen?").

## Schemabeslissing

**Python-models (`api/app/features/identiteit_toegang/models.py` uitbreiden):**

- `GebruikerPatch` — `rol: str | None = None`, `actief: bool | None = None`
- `TijdelijkWachtwoord` — `gebruikersnaam: str`, `tijdelijk_wachtwoord: str`

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/admin/gebruikers/{gebruikersnaam}` | PATCH | Rol en/of actief wijzigen | beheerder |
| `/v1/admin/gebruikers/{gebruikersnaam}/reset-wachtwoord` | POST | Tijdelijk wachtwoord genereren | beheerder |
| `/v1/admin/gebruikers/{gebruikersnaam}` | DELETE | Account verwijderen | beheerder |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/admin/gebruikers/[gebruikersnaam]/route.ts` | PATCH, DELETE | Bewerken + verwijderen |
| `app/api/admin/gebruikers/[gebruikersnaam]/reset-wachtwoord/route.ts` | POST | Wachtwoord resetten |

## Edge cases

- Onbekend account bij PATCH/DELETE/reset → API 404; frontend toont foutmelding.
- Laatste actieve beheerder deactiveren of verwijderen → API 409; frontend toont "Kan de laatste actieve beheerder niet verwijderen."
- Ongeldige rol-waarde bij PATCH → API 422; frontend valideert voor verzenden al met een select-element.
- Gelijktijdige verwijder-acties (race) → degene die als tweede arriveert krijgt 404; frontend herlaadt de lijst.
- Tijdelijk wachtwoord gesloten zonder te noteren → alleen een nieuwe reset-actie helpt; de API biedt geen herstel.

## Auth / rollen

- Alle drie endpoints: alleen beheerder (`huidige_beheerder` uit `shared/auth.py`).
- Een beheerder kan ook zijn eigen account deactiveren (wat leidt tot het 409-conflict als hij de laatste actieve beheerder is).

## Gedeelde logica

- `huidige_beheerder` uit `shared/auth.py` — bestaat ✓
- `requireSession()` + `apiProxy()` uit de BFF-lib — bestaan ✓
- `beheerFetch` + `BeheerFetchFout` — bestaan ✓
- Store-functie `wijzig_gebruiker(gebruikersnaam, *, rol, actief)` toevoegen aan `identiteit_toegang/store.py`.
- Store-functie `verwijder_gebruiker(gebruikersnaam)` toevoegen.
- Store-functie `reset_wachtwoord(gebruikersnaam)` toevoegen — genereert een veilig willekeurig wachtwoord (`secrets.token_urlsafe(12)`), slaat de bcrypt-hash op, en geeft de plaintext terug.
- Invariant "laatste actieve beheerder" afdwingen in `store.py` vóór de mutatie (één atomaire check + schrijf om TOCTOU te voorkomen).

## Implementatienoot

De routerlogica kopiëren en aanpassen vanuit `wetsanalyse-ai/api/app/routers/admin.py` (§gebruikersbeheer, functies `wijzig_user`, `verwijder_user`, `reset_user_wachtwoord`). De identiteit van de ingelogde beheerder (voor de invariant-check: "is dit de laatste actieve beheerder?") is beschikbaar via de `X-User-Id`-header. Controleer of de `identiteit_toegang` al op SQLAlchemy Core + Pydantic staat (werkwijze-ADR-0011); migreer indien nodig.

## UI

- **Gebruikersrij op `/beheer`**: per rij knoppengroep "Bewerk / Reset / Verwijder". Bewerken opent een inline-formulier (rol-dropdown + actief-checkbox) of een modal — kies de compactste optie.
- **Reset-modal**: toont het tijdelijke wachtwoord met een "Kopieer"-knop en de melding "Dit wachtwoord wordt niet meer getoond."
- **Verwijder-dialoog**: eenvoudige bevestigingsdialoog, geen vrij tekstveld.

**Gebouwd:** ja (PR #..., feature/story-014-impl)
