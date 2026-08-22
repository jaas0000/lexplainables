# Story 011: LLM-profielen (admin)

**Prioriteit:** hoog
**Story points:** 4
**Service:** `api/` + `frontend/`

## Verhaal

Als beheerder wil ik LLM-profielen kunnen aanmaken, bewerken en verwijderen, en één profiel als standaard kunnen instellen, zodat analyses automatisch het juiste LLM-model gebruiken zonder dat de analist dit hoeft te kiezen.

## Acceptatiecriteria

- [x] Een beheerder kan een lijst van alle LLM-profielen inzien.
- [x] Een beheerder kan een nieuw profiel aanmaken (naam, provider, model, api_base, api_versie, temperatuur, api_sleutel, is_standaard).
- [x] Een beheerder kan een bestaand profiel bewerken (alle velden behalve naam; naam is de stabiele identifier).
- [x] Een beheerder kan een profiel verwijderen, mits het niet het enige profiel is.
- [x] De API-sleutel wordt Fernet-versleuteld opgeslagen; bij opvragen staat `sleutel_ingesteld: bool` in de response — de plaintext-sleutel verlaat de API nooit.
- [x] Er is altijd maximaal één standaard-profiel: bij het instellen van een nieuw standaard wordt het vorige automatisch omgezet naar niet-standaard.
- [x] Bij het aanmaken van een analyse (story 012) wordt het standaard-profiel automatisch gebruikt.
- [x] Frontend: op `/beheer` staat een sectie "LLM-profielen" met een navigatieknop naar `/beheer/llm-profielen`.
- [x] `/beheer/llm-profielen` toont de profielenlijst met aanmaken-formulier en bewerk/verwijder-actie per profiel.

## Schemabeslissing

**Python-models (`api/app/features/llm_profielen/models.py`):**

- `LlmProfielCreate` — `naam: str`, `provider: str`, `model: str`, `api_base: str`, `api_versie: str | None = None`, `temperatuur: float = 0.0`, `api_sleutel: str | None = None`, `is_standaard: bool = False`
- `LlmProfielUpdate` — `provider: str`, `model: str`, `api_base: str`, `api_versie: str | None`, `temperatuur: float`, `api_sleutel: str | None`, `is_standaard: bool`
- `LlmProfielRead` — `naam: str`, `provider: str`, `model: str`, `api_base: str`, `api_versie: str | None`, `temperatuur: float`, `sleutel_ingesteld: bool`, `is_standaard: bool`, `updated: str`

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/admin/profielen` | GET | Lijst alle profielen | beheerder |
| `/v1/admin/profielen` | POST | Nieuw profiel aanmaken | beheerder |
| `/v1/admin/profielen/{naam}` | PUT | Profiel bijwerken | beheerder |
| `/v1/admin/profielen/{naam}` | DELETE | Profiel verwijderen | beheerder |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/admin/profielen/route.ts` | GET, POST | Lijst + aanmaken |
| `app/api/admin/profielen/[naam]/route.ts` | PUT, DELETE | Bijwerken + verwijderen |

## Edge cases

- Verwijderen van het enige profiel → API 409; frontend toont foutmelding.
- Naam-conflict bij aanmaken → API 409; frontend toont foutmelding.
- `api_sleutel` leeg bij update → sleutel ongewijzigd laten (niet overschrijven met null).
- Geen standaard-profiel aanwezig → analyse-aanmaken (story 012) geeft 422 met duidelijk bericht.
- Verwijderen van het standaard-profiel → API staat dit toe mits er nog minstens één ander profiel is; geen automatische herbenoeming.

## Auth / rollen

- Alle endpoints: alleen beheerder (rolcheck server-side via `shared/auth.py`).
- BFF controleert alleen sessie-aanwezigheid via `requireSession()`.

## Gedeelde logica

- `requireSession()` + `apiProxy()` — bestaan ✓
- `SectieHeader` + `LeegePlaceholder` — bestaan ✓
- `beheerFetch` + `BeheerFetchFout` uit `lib/beheer-fetch.ts` — bestaat ✓
- Fernet-encryptie kopiëren vanuit `wetsanalyse-ai/api/app/secrets_crypto.py`.
- Profiellogica kopiëren en aanpassen vanuit `wetsanalyse-ai/api/app/llm_profile.py` → herindelen als `api/app/features/llm_profielen/models.py` + `store.py` + `router.py`.

## UI

- **`/beheer/llm-profielen`**: tabel met naam/provider/model/standaard per profiel, aanmaken-formulier onderaan (of collapse-knop), bewerk- en verwijder-actie per rij.
- **Sectie op `/beheer`**: navigatieknop "Beheer LLM-profielen →" met het aantal profielen als teller.
- Mockup-varianten: lege lijst (geen profielen), lijst met twee profielen (waarvan één standaard), bewerk-formulier ingevuld.

**Gebouwd:** ja (PR #10)
