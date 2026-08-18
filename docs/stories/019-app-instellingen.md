# Story 019: App-instellingen (runtime-config)

**Prioriteit:** hoog
**Story points:** 2
**Service:** `api/` + `frontend/`

## Verhaal

Als beheerder wil ik runtime-configuratie van de applicatie kunnen lezen en wijzigen via de beheerinterface, zonder de applicatie opnieuw te hoeven starten, zodat ik gedragsopties (zoals het vastleggen van LLM-calls) snel aan of uit kan zetten.

## Acceptatiecriteria

- [ ] `GET /v1/admin/instellingen` geeft de huidige waarde van alle runtime-instellingen terug als een getypt object.
- [ ] `PUT /v1/admin/instellingen` past één of meer instellingen aan; weggelaten velden blijven ongewijzigd.
- [ ] De instelling `capture_llm_calls` (bool) bepaalt of de LLM-calls per analyse worden opgeslagen (story 021); de waarde is na een herstart persistent (opgeslagen in de database).
- [ ] Waarden worden gecachet met een korte TTL (≤ 10 seconden) om de database niet bij elke LLM-call te bevragen.
- [ ] Frontend: op `/beheer` staat een sectie "Instellingen" met een schakelaar voor `capture_llm_calls` en een opslaan-knop; of een aparte pagina `/beheer/instellingen/`.

## Schemabeslissing

**Alembic-migratie:** maak tabel `app_instellingen` aan (migrations/0007_*).

**Tabel `app_instellingen`:**

| Kolom | Type | Opmerking |
|---|---|---|
| `sleutel` | TEXT PK | Configuratiesleutel, bijv. `capture_llm_calls` |
| `waarde` | TEXT NOT NULL | JSON-geëncodeerde waarde (`"true"`, `"false"`, `"42"`) |
| `bijgewerkt` | TIMESTAMP NOT NULL | |

**Python-models (`api/app/features/runtime_config/models.py`):**

- `AppInstellingen` — `capture_llm_calls: bool = False`
- `AppInstellingenPatch` — `capture_llm_calls: bool | None = None`

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/admin/instellingen` | GET | Lees alle instellingen | beheerder |
| `/v1/admin/instellingen` | PUT | Pas (deel van) instellingen aan | beheerder |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/admin/instellingen/route.ts` | GET, PUT | Lezen + bijwerken |

## Edge cases

- Ontbrekende rij in de database → gebruik standaardwaarde (`capture_llm_calls = false`); schrijf de rij pas bij de eerste PUT.
- Ongeldige JSON in de `waarde`-kolom → vang op bij lezen, gebruik standaardwaarde, log een waarschuwing.
- Gelijktijdige PUT-requests (race) → de laatste schrijfactie wint; instellingen zijn niet transactioneel-kritisch.
- `PUT` met alleen `null`-velden → geen schrijfactie; retourneer de huidige waarden.
- TTL-cache maakt een net-gewijzigde instelling kort onzichtbaar — dit is acceptabel voor niet-kritische config.

## Auth / rollen

- Beide endpoints: alleen beheerder (`huidige_beheerder` uit `shared/auth.py`).
- Leesrechten voor de engine (story 021): de engine-laag leest de instelling intern via de store, niet via het admin-endpoint.

## Gedeelde logica

- `huidige_beheerder` uit `shared/auth.py` — bestaat ✓
- Store (`api/app/features/runtime_config/store.py`):
  - `lees_instelling(sleutel, standaard)` — met TTL-cache (in-process dict met timestamp).
  - `schrijf_instelling(sleutel, waarde)` — upsert + wis cache-entry.
  - `lees_alle()` → `AppInstellingen` — samengesteld uit losse sleutels.
- `capture_llm_calls`-check beschikbaar als `runtime_config.capture_ingeschakeld()` voor gebruik in story 021.

## Implementatienoot

Logica kopiëren en aanpassen vanuit `wetsanalyse-ai/api/app/app_settings.py` en de bijbehorende routes in `wetsanalyse-ai/api/app/routers/admin.py` (`haal_settings`, `zet_settings`). De sleutel-waarde-tabel is uitbreidbaar: nieuwe instellingen zijn een nieuw veld op `AppInstellingen` en een nieuw `sleutel`-record in de database — geen migratie nodig voor elke nieuwe instelling.

## UI

- **Sectie "Instellingen" op `/beheer`** (of aparte `/beheer/instellingen/`-pagina): schakelaar "LLM-calls vastleggen" met beschrijving "Sla alle LLM-aanroepen (prompt + respons) op in de database voor later inzage. Schakel alleen in als dat nodig is — de opgeslagen inhoud kan gevoelige tekst bevatten." Plus een "Opslaan"-knop.
- Mockup-varianten: instelling uit (grijs), instelling aan (actief), na opslaan (succesmelding).

**Gebouwd:** nee
