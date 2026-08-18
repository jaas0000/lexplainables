# Story 018: API-tokens

**Prioriteit:** laag
**Story points:** 3
**Service:** `api/` + `frontend/`

## Verhaal

Als beheerder wil ik programmatische API-toegangstokens kunnen aanmaken en intrekken, zodat externe tools (zoals de Admin-MCP) veilig toegang krijgen tot de beheer-API zonder dat ik voor elk tool een apart statisch token in de omgeving hoef te zetten.

## Acceptatiecriteria

- [ ] Een beheerder kan een lijst van actieve API-tokens inzien; de lijst toont nooit het volledige token — alleen het prefix (eerste 8 tekens) voor identificatie.
- [ ] Een beheerder kan een nieuw token aanmaken met een optioneel label; het volledige token wordt éénmalig teruggegeven en is daarna niet meer opvraagbaar.
- [ ] Een beheerder kan een token intrekken; het token werkt onmiddellijk niet meer.
- [ ] Tokens zijn hoge-entropie random strings (≥ 32 bytes); de hash (SHA-256) staat in de database, nooit het plaintext-token.
- [ ] De API accepteert naast de statische `API_TOKEN` uit de omgeving ook geldige DB-tokens; de verificatielaag (`shared/auth.py`) controleert beide bronnen.
- [ ] Frontend: `/beheer/api-tokens/` toont de tokenlijst met label, prefix, aanmaakdatum en "Intrekken"-actie; een "Nieuw token aanmaken"-formulier staat bovenaan.
- [ ] Op `/beheer` staat een navigatieknop "API-tokens →" met het aantal actieve tokens als teller.

## Schemabeslissing

**Alembic-migratie:** maak tabel `api_tokens` aan (migrations/0006_*).

**Tabel `api_tokens`:**

| Kolom | Type | Opmerking |
|---|---|---|
| `id` | TEXT PK | `uuid.uuid4().hex` |
| `label` | TEXT NOT NULL DEFAULT '' | Beschrijving voor de beheerder |
| `token_hash` | TEXT NOT NULL | SHA-256 van het plaintext-token |
| `token_prefix` | TEXT NOT NULL | Eerste 8 tekens van het token (identificatie) |
| `scope` | TEXT NOT NULL DEFAULT 'beheerder' | Toekomstig uitbreidingspunt |
| `actief` | BOOLEAN NOT NULL DEFAULT TRUE | |
| `aangemaakt_door` | TEXT NOT NULL DEFAULT '' | Gebruikersnaam van de beheerder |
| `aangemaakt_op` | TIMESTAMP NOT NULL | |
| `laatste_gebruik` | TIMESTAMP | Nullable; bijgewerkt bij elke geverifieerde aanroep |

**Python-models (`api/app/features/api_tokens/models.py`):**

- `ApiToken` — SQLAlchemy Core `Table` + bijbehorende Pydantic-representatie
- `ApiTokenRead` — `id: str`, `label: str`, `token_prefix: str`, `scope: str`, `actief: bool`, `aangemaakt_door: str`, `aangemaakt_op: str`, `laatste_gebruik: str | None`
- `ApiTokenAangemaakt` — extends `ApiTokenRead` + `token: str` (eenmalig)
- `ApiTokenAanmakenVerzoek` — `label: str = ""` (max 128)

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/admin/api-tokens` | GET | Lijst actieve tokens | beheerder |
| `/v1/admin/api-tokens` | POST | Nieuw token aanmaken | beheerder |
| `/v1/admin/api-tokens/{id}` | DELETE | Token intrekken | beheerder |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/admin/api-tokens/route.ts` | GET, POST | Lijst + aanmaken |
| `app/api/admin/api-tokens/[id]/route.ts` | DELETE | Intrekken |

## Edge cases

- Onbekend token-id bij intrekken → API 404; frontend toont foutmelding.
- Intrekken van een al ingetrokken token → idempotent (404, niet 409).
- Aanmaken zonder label → label blijft leeg; token is nog steeds geldig.
- Gelijktijdige aanroep met een net-ingetrokken token → database-hash ontbreekt → API weigert (401); race-window is de DB-read-latency.
- `laatste_gebruik` wordt best-effort bijgewerkt — bij een hoge aanvraagfrequentie mogen updates gebatcht worden.
- Geen tokens aanwezig → lege lijst; de statische `API_TOKEN` uit de omgeving blijft altijd het bootstrap-token.

## Auth / rollen

- Alle drie endpoints: alleen beheerder (`huidige_beheerder` uit `shared/auth.py`).
- Verificatie van inkomende requests via `shared/auth.py`: controleer eerst de statische `API_TOKEN`, dan de DB-tokens (hash-vergelijking via `hmac.compare_digest`). Sla `laatste_gebruik` bij een DB-token-treffer asynchroon bij.
- De beheerder die een token aanmaakt, wordt vastgelegd in `aangemaakt_door`.

## Gedeelde logica

- `huidige_beheerder` uit `shared/auth.py` — uitbreiden met DB-token-verificatielaag.
- `shared/crypto.py` niet nodig: tokens zijn hoge-entropie en worden gehashed (SHA-256), niet Fernet-versleuteld.
- Store (`api/app/features/api_tokens/store.py`):
  - `lijst_tokens()` → `list[ApiTokenRead]`
  - `maak_token(label, aangemaakt_door)` → `(ApiTokenRead, plaintext: str)`
  - `trek_in(token_id)` — markeert `actief = FALSE`
  - `verifieer(plaintext_token)` → `str | None` (token-id als de hash matcht en het token actief is; anders None)
- Tokenformaat: `secrets.token_urlsafe(32)` (43 tekens, URL-veilig).

## Implementatienoot

Tokenlogica kopiëren en aanpassen vanuit `wetsanalyse-ai/api/app/api_tokens.py`. De `shared/auth.py` uitbreiden: voeg na de statische `API_TOKEN`-check een asyncrone lookup toe in de `api_tokens`-tabel. Let op: `vereist_api_token` is momenteel synchroon — maak het asynchroon of voer de DB-check uit in een aparte helper die de FastAPI-dependency aanroept. Zorg dat de feature een eigen Alembic-migratie krijgt (migrations/0006_*).

## UI

- **`/beheer/api-tokens/`**: tabel met kolommen label, prefix, aangemaakt door, datum, laatste gebruik; "Intrekken"-knop per rij. Bovenaan een compact formulier "Label (optioneel)" + knop "Nieuw token aanmaken". Na aanmaken verschijnt het token eenmalig in een modal (zelfde patroon als wachtwoord-reset, story 014).
- **Sectie op `/beheer`**: navigatieknop "API-tokens →" met het aantal actieve tokens als badge.

**Gebouwd:** nee
