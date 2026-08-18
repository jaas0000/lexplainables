# Story 020: Wettenbank-beheer (admin CRUD)

**Prioriteit:** middel
**Story points:** 3
**Service:** `api/` + `frontend/`
**Afhankelijkheid:** story 010 (wetcatalogus leesbaar)

## Verhaal

Als beheerder wil ik wetten aan de catalogus kunnen toevoegen, verwijderen, en de officiële citeertitel automatisch kunnen ophalen, zodat analisten altijd over een actuele en correcte wettenlijst beschikken zonder dat ik handmatig in de code of database hoef te werken.

## Acceptatiecriteria

- [ ] Een beheerder kan een wet toevoegen of bijwerken via een PUT-verzoek (bwb-id + naam).
- [ ] Een beheerder kan een wet verwijderen; de API geeft 404 als het bwb-id onbekend is.
- [ ] Een beheerder kan de officiële citeertitel van een wet ophalen via `/resolve`; de API spreekt de Wettenbank-MCP aan om de naam op te vragen.
- [ ] De wetcatalogus is nu database-backed (SQLAlchemy Core `Table`); de hardgecodeerde store (`HardgecodeerdeWetcatalogusStore`) wordt vervangen.
- [ ] De bestaande analist-endpoints `GET /v1/wetten` en `GET /v1/wetten/{bwb_id}/structuur` (story 010) lezen voortaan uit de database; de structuurdata komt nog steeds uit de Wettenbank-MCP.
- [ ] Migratie: bestaande hardgecodeerde wetten worden via een seed-script of migratie naar de database geschreven.
- [ ] Frontend: `/beheer/wetten/` toont de cataloguslijst met bewerk- en verwijderacties; een formulier maakt nieuwe wetten aan of past bestaande bij.
- [ ] Op `/beheer` staat een navigatieknop "Wetten →" met het aantal wetten als teller.

## Schemabeslissing

**Alembic-migratie:** maak tabel `wet_catalogus` aan (migrations/0008_*).

**Tabel `wet_catalogus`:**

| Kolom | Type | Opmerking |
|---|---|---|
| `bwb_id` | TEXT PK | BWB-identifier, bijv. `BWBR0011823` |
| `naam` | TEXT NOT NULL | Leesbare naam / citeertitel |
| `bijgewerkt_door` | TEXT NOT NULL DEFAULT '' | Gebruikersnaam van de beheerder |
| `bijgewerkt` | TIMESTAMP NOT NULL | |

**Python-models (`api/app/features/wetcatalogus/models.py` uitbreiden):**

- Voeg SQLAlchemy Core `Table`-definitie toe voor `wet_catalogus`.
- `WetCreate` — `bwb_id: str`, `naam: str` (max 256)
- `WetRead` — `bwb_id: str`, `naam: str`, `bijgewerkt_door: str`, `bijgewerkt: str`
- `ResolveResultaat` — `naam: str`
- Bestaande modellen (`WetKeuze`, `ArtikelKeuze`, `WetStructuur`) blijven ongewijzigd.

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/admin/wetten` | GET | Lijst catalogus-items (incl. metadata) | beheerder |
| `/v1/admin/wetten/{bwb_id}` | PUT | Wet toevoegen of bijwerken | beheerder |
| `/v1/admin/wetten/{bwb_id}` | DELETE | Wet verwijderen | beheerder |
| `/v1/admin/wetten/{bwb_id}/resolve` | POST | Citeertitel ophalen via Wettenbank-MCP | beheerder |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/admin/wetten/route.ts` | GET | Lijst |
| `app/api/admin/wetten/[bwbId]/route.ts` | PUT, DELETE | Upsert + verwijderen |
| `app/api/admin/wetten/[bwbId]/resolve/route.ts` | POST | Citeertitel ophalen |

## Edge cases

- Onbekend bwb-id bij DELETE → API 404; frontend toont foutmelding.
- PUT met leeg `naam`-veld → API 422; frontend valideert voor verzenden.
- Resolve-endpoint: Wettenbank-MCP niet bereikbaar → API 502 "Wettenbank tijdelijk niet bereikbaar."; frontend toont foutmelding, laat de naam handmatig invullen.
- Resolve-endpoint: bwb-id onbekend bij de Wettenbank → API 404; frontend toont "Wet niet gevonden in de Wettenbank.".
- Verwijderen van een wet die in gebruik is door een bestaande analyse — de catalogus is een gemak voor de UI-dropdown, niet dwingend; verwijderen is altijd toegestaan.
- Gelijktijdige PUT en DELETE op hetzelfde bwb-id → database handelt dit atomair af; de laatste write wint.

## Auth / rollen

- Admin-endpoints: alleen beheerder (`huidige_beheerder` uit `shared/auth.py`).
- Analist-endpoints (`GET /v1/wetten`, `GET /v1/wetten/{bwb_id}/structuur`) — ongewijzigd; vereisen een ingelogde gebruiker.

## Gedeelde logica

- `huidige_beheerder` uit `shared/auth.py` — bestaat ✓
- Store (`api/app/features/wetcatalogus/store.py`) uitbreiden met:
  - `upsert_wet(bwb_id, naam, bijgewerkt_door)` → `WetRead`
  - `verwijder_wet(bwb_id)` — gooit `WetNietGevonden` als onbekend
  - `lijst_met_metadata()` → `list[WetRead]` (uitbreiding van de bestaande `lijst()`)
- Wettenbank-MCP-client aanroepen voor `resolve`: `wettenbank_structuur(bwb_id)` geeft de structuur terug waaruit de citeertitel (`titel`) kan worden gelezen.
- Seed-script of Alembic-dataregel: kopieer de hardgecodeerde wetten uit `HardgecodeerdeWetcatalogusStore` naar de database bij de eerste migratie.

## Implementatienoot

Routerlogica kopiëren en aanpassen vanuit `wetsanalyse-ai/api/app/routers/admin.py` (§wet-catalogus: `lijst_wetten`, `upsert_wet`, `verwijder_wet`, `resolve_wet_naam`) en `wetsanalyse-ai/api/app/wetten.py`. De Wettenbank-MCP-client is al aanwezig in `tools/wettenbank-mcp/`; de API-laag spreekt hem aan via HTTP (zie het topologie-ADR). Vervang de `HardgecodeerdeWetcatalogusStore` door een `DatabaseWetcatalogusStore` en registreer de nieuwe implementatie als de default dependency.

## UI

- **`/beheer/wetten/`**: tabel met bwb-id, naam, bijgewerkt door, datum; "Bewerk"-actie opent een inline-formulier (naam-veld + "Resolve"-knop naast het veld), "Verwijder"-actie vraagt om bevestiging. Bovenaan een "Wet toevoegen"-formulier (bwb-id + naam).
- **Sectie op `/beheer`**: navigatieknop "Wetten →" met het aantal wetten als badge.
- Mockup-varianten: lege catalogus, lijst met twee wetten (één via resolve gevuld), bewerken in uitklapbaar formulier.

**Gebouwd:** nee
