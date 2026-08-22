# Story 022: Annotatie-backend

**Prioriteit:** middel
**Story points:** 4
**Service:** `api/`

## Verhaal

Als ingelogde gebruiker wil ik een wetsartikel als annotatie-document kunnen aanmaken, de door de agent voorgestelde JAS-elementen kunnen beoordelen (goedkeuren, bewerken, afwijzen), en een append-only auditlog kunnen raadplegen, zodat de human-in-the-loop annotatie-werkplek een betrouwbare data-basis heeft.

## Acceptatiecriteria

- [x] Een ingelogde gebruiker kan een annotatie-document aanmaken voor een combinatie van werkgebied, bwb-id, artikel en optioneel lid.
- [x] Een agent (of de engine) kan voorgestelde elementen (JAS-klasse + tekst + toelichting + vindplaats) in bulk plaatsen via een PUT-verzoek; ongeldige klassen en lege tekst worden verworpen.
- [x] Een gebruiker kan per element een beslissing registreren: goedkeuren, bewerken (met verplichte reden en gewijzigde velden), afwijzen (met verplichte reden), of een opmerking plaatsen.
- [x] Elke schrijfactie (document aanmaken, elementen zetten, beslissing) schrijft een regel naar het append-only auditlog.
- [x] De gebruiker kan het volledige auditlog van een document opvragen.
- [x] Een document is client-gescopet: een gebruiker kan alleen zijn eigen documenten inzien en bewerken; een onbekend of andermans document geeft een 404 (niet 403) om het bestaan niet te lekken.
- [x] Een gebruiker kan zijn eigen document verwijderen.
- [x] JAS-klassen worden gevalideerd tegen de centrale lijst van geldige klassen (`shared/validation.py`).

## Schemabeslissing

**Alembic-migratie:** maak tabellen `annotatie_documenten` en `annotatie_audit` aan (migrations/0010_*).

**Tabel `annotatie_documenten`:**

| Kolom | Type | Opmerking |
|---|---|---|
| `slug` | TEXT PK | `uuid.uuid4().hex[:16]` — niet raadbaar |
| `client_id` | TEXT NOT NULL | Gebruikersnaam van de eigenaar |
| `werkgebied` | TEXT NOT NULL | Naam van het werkgebied |
| `bwb_id` | TEXT NOT NULL | BWB-identifier |
| `artikel` | TEXT NOT NULL | |
| `lid` | TEXT NOT NULL DEFAULT '' | Optioneel lid |
| `status` | TEXT NOT NULL DEFAULT 'voorgesteld' | `voorgesteld` \| `gedeeltelijk_gereviewd` \| `klaar` |
| `elementen` | JSON NOT NULL DEFAULT '[]' | Lijst van `AnnotatieElement`-objecten als JSON |
| `aangemaakt` | TIMESTAMP NOT NULL | |
| `bijgewerkt` | TIMESTAMP NOT NULL | |

**Tabel `annotatie_audit`:**

| Kolom | Type | Opmerking |
|---|---|---|
| `id` | BIGINT PK | autoincrement; tijdlijn = `ORDER BY id` |
| `document_slug` | TEXT NOT NULL | |
| `client_id` | TEXT NOT NULL | |
| `actor` | TEXT NOT NULL | Gebruikersnaam of agent-identifier |
| `actie` | TEXT NOT NULL | bijv. `document-aangemaakt`, `elementen-voorgesteld`, `beslissing-approve` |
| `element_id` | TEXT | Nullable; gevuld bij element-beslissingen |
| `detail` | JSON NOT NULL DEFAULT '{}' | Vrij detail-object per actie |
| `tijdstip` | TIMESTAMP NOT NULL | |

**Python-models (`api/app/features/annotatie/models.py`):**

Enums:
- `DocumentStatus` — `voorgesteld`, `gedeeltelijk_gereviewd`, `klaar`
- `Levenscyclus` — `voorgesteld`, `critic_gecheckt`, `human_goedgekeurd`, `bewerkt`, `afgewezen`
- `BeslissingType` — `goedkeuren`, `bewerken`, `afwijzen`, `opmerking`
- `BeoordelingsReden` — `onduidelijk`, `fout_klasse`, `fout_tekst`, `dubbeling`, `overig`
- `Aandacht` — `groen`, `geel`, `rood`

Pydantic-modellen:
- `Alternatief` — `klasse: str`, `tekst: str`, `toelichting: str`
- `Beslissing` — `type: BeslissingType`, `actor: str`, `tijd: str`, `reden: BeoordelingsReden | None`, `opmerking: str | None`, `wijziging: dict`
- `AnnotatieElement` — `id: str`, `klasse: str`, `tekst: str`, `lid: str`, `toelichting: str`, `vindplaats: str`, `span: dict | None`, `herkomst: str`, `levenscyclus: Levenscyclus`, `alternatieven: list[Alternatief]`, `aandacht: Aandacht | None`, `critic: str | None`, `beslissingen: list[Beslissing]`, `diff: dict`
- `AnnotatieDocument` — `slug: str`, `client_id: str`, `werkgebied: str`, `bwb_id: str`, `artikel: str`, `lid: str`, `status: DocumentStatus`, `elementen: list[AnnotatieElement]`, `aangemaakt: str`, `bijgewerkt: str`
- `AuditRegel` — `id: int`, `document_slug: str`, `client_id: str`, `actor: str`, `actie: str`, `element_id: str | None`, `detail: dict`, `tijdstip: str`
- `DocumentAanmaken` — `werkgebied: str`, `bwb_id: str`, `artikel: str`, `lid: str | None = None`
- `ElementInvoer` — `klasse: str`, `tekst: str`, `lid: str = ""`, `toelichting: str = ""`, `vindplaats: str = ""`, `span: dict | None = None`, `alternatieven: list[Alternatief] = []`, `aandacht: Aandacht | None = None`, `critic: str | None = None`
- `ElementenInvoer` — `elementen: list[ElementInvoer]`
- `WijzigingInvoer` — `klasse: str | None`, `tekst: str | None`, `toelichting: str | None`, `lid: str | None`
- `BeslissingInvoer` — `type: BeslissingType`, `reden: BeoordelingsReden | None = None`, `opmerking: str | None = None`, `wijziging: WijzigingInvoer | None = None`
- `DocumentSamenvatting` — `slug: str`, `bwb_id: str`, `artikel: str`, `lid: str`, `werkgebied: str`, `status: DocumentStatus`, `aantal_elementen: int`, `bijgewerkt: str`

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/annotatie/documenten` | POST | Document aanmaken | ingelogd |
| `/v1/annotatie/documenten` | GET | Eigen documenten (samenvatting) | ingelogd |
| `/v1/annotatie/documenten/{slug}` | GET | Volledig document | ingelogd (eigenaar) |
| `/v1/annotatie/documenten/{slug}` | DELETE | Eigen document verwijderen | ingelogd (eigenaar) |
| `/v1/annotatie/documenten/{slug}/elementen` | PUT | Voorgestelde elementen zetten | ingelogd (eigenaar) |
| `/v1/annotatie/documenten/{slug}/elementen/{id}/beslissing` | POST | Human-decision registreren | ingelogd (eigenaar) |
| `/v1/annotatie/documenten/{slug}/audit` | GET | Auditlog opvragen | ingelogd (eigenaar) |

Geen BFF-routes in deze story — de frontend (story 023) voegt die toe.

## Edge cases

- Onbekend of andermans document → 404 (niet 403) bij alle `/{slug}`-routes.
- Ongeldige JAS-klasse bij `PUT elementen` → element overgeslagen (niet de hele batch afgewezen); de response bevat het aantal verworpen elementen.
- Lege tekst bij element → overgeslagen.
- `bewerken`-beslissing zonder `reden` of `wijziging` → API 422.
- `afwijzen`-beslissing zonder `reden` → API 422.
- `goedkeuren` of `opmerking` zonder `reden` → reden wordt genegeerd.
- Element niet gevonden bij beslissing → API 404.
- Dubbele slug (astronomisch onwaarschijnlijk bij 16-hex-tekens) → INSERT faalt met UNIQUE-conflict → API 500 (acceptabel; geen retry-logica nodig).
- Document met lege elementenlijst → geldig; verwijderen is altijd toegestaan.

## Auth / rollen

- Alle endpoints: ingelogde gebruiker (`huidige_gebruiker` uit `shared/auth.py`).
- Client-scoping via `client_id`: de gebruikersnaam uit de `X-User-Id`-header. Andere documenten zijn niet zichtbaar (404).
- Geen admin-endpoints in deze story; een beheerder ziet ook alleen zijn eigen documenten.

## Gedeelde logica

- `huidige_gebruiker` uit `shared/auth.py` — bestaat ✓
- `shared/validation.py` — voeg `GELDIGE_JAS_KLASSEN: frozenset[str]` toe als gedeelde constante.
- Store (`api/app/features/annotatie/store.py`):
  - `maak_document(doc: AnnotatieDocument)` — INSERT
  - `laad_document(slug)` → `AnnotatieDocument | None`
  - `lijst_documenten(client_id, limit, offset)` → `list[AnnotatieDocument]`
  - `verwijder_document(slug)` — DELETE + bijbehorende audit-regels
  - `vervang_elementen(slug, elementen)` — UPDATE (volledige JSON-kolom)
  - `schrijf_audit(slug, client_id, actor, actie, *, element_id=None, detail={})`
  - `lees_audit(slug)` → `list[AuditRegel]`
- `utcnow()` uit `shared/db.py` of als hulpfunctie in de store.

## Implementatienoot

Contracten kopiëren en aanpassen vanuit `wetsanalyse-ai/api/app/annotatie_contracts.py`; routerlogica vanuit `wetsanalyse-ai/api/app/routers/annotatie.py`; storelogica vanuit `wetsanalyse-ai/api/app/annotatie_store.py`. Hernoem waar nodig naar Nederlandse termen (zie de modellen hierboven). De `elementen`-kolom slaat Pydantic-objecten op als JSON; de store serialiseert en deserialiseert via `model_dump()` / `model_validate()`. Zorg dat de annotatie-store een aparte `AnnotatieStore`-klasse is (niet gedeeld met de projecten-store) zodat de domein-grenzen helder blijven.

**Gebouwd:** ja (PR #21)
