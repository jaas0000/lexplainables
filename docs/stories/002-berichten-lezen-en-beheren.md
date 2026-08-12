# Story 002: Berichten lezen en beheren

**Prioriteit:** high
**Story points:** 3
**Service:** `api`

Tweede feature van de referentie-implementatie. Herbouwt het berichtendomein (release notes /
aankondigingen) van het bestaande, externe project (`jaas0000/wetsanalyse-ai`,
`api/app/berichten.py` + `api/app/routers/berichten.py` + `api/app/routers/admin.py`
§berichtensysteem) volgens deze werkwijze, als tweede bewijs-van-concept — niet door dat
project te kopiëren.

## Verhaal

Als beheerder wil ik berichten kunnen schrijven, bewerken en publiceren, en als analist wil ik
gepubliceerde berichten kunnen lezen met een gelezen/ongelezen-status, zodat aankondigingen
(nieuwe functies, gedragswijzigingen) analisten bereiken zonder dat ze elke keer de hele lijst
hoeven na te lopen.

## Acceptatiecriteria

- [ ] Een beheerder kan een bericht aanmaken (`titel`, `inhoud`, `type`, optioneel `versie`) —
      het komt altijd als concept (`gepubliceerd=False`) binnen, nooit direct live.
- [ ] Een beheerder kan een bestaand bericht bewerken (titel/inhoud/type/versie); leesbewijzen
      van analisten blijven daarbij intact.
- [ ] Een beheerder kan een bericht publiceren en depubliceren; publiceren zet
      `gepubliceerd_op`, depubliceren wist het weer.
- [ ] Een beheerder ziet alle berichten (ook concepten) in een gepagineerde admin-lijst, met
      het totaal aantal.
- [ ] Een beheerder kan een bericht verwijderen op id; de leesbewijzen van dat bericht
      verdwijnen in dezelfde transactie (cascade).
- [ ] Een analist ziet alleen gepubliceerde berichten, gepagineerd, met een `gelezen`-vlag per
      item en een `ongelezen`-filter.
- [ ] Een analist kan het aantal ongelezen gepubliceerde berichten opvragen.
- [ ] Een analist kan in één keer alle zichtbare gepubliceerde berichten als gelezen markeren
      (`lees-alles`); dit is idempotent — twee keer aanroepen geeft geen fout.

## Schemabeslissing

Twee entiteiten in `api/app/features/berichten/models.py` (de ene bron, ADR-0011):

- `berichten` — ongewijzigd t.o.v. het externe project: `id` (PK, autoincrement), `titel`
  (text), `inhoud` (text), `type` (kolom `String(16)`; op het Pydantic-contract een
  `Literal["info", "update", "waarschuwing", "kritiek"]` i.p.v. een losse `str` met
  regex-pattern — zelfde precisie-eis als bij feedback, `feature-bouwen` regel 3), `versie`
  (`String(32)`, nullable), `gepubliceerd` (bool), `gepubliceerd_op` (datetime tz-aware,
  nullable — alleen gezet bij publiceren), `aangemaakt_door` (`String(128)`), `created`,
  `updated`. Index op `(gepubliceerd, created)`.
- `bericht_leesbewijzen` — `bericht_id` + `userid` + `gelezen_op`, samengestelde primary key op
  `(bericht_id, userid)`. **Dit is al een eigen jointabel binnen het berichten-domein** — geen
  cross-domain-lek zoals feedback dat had (die leende een kolom van een users-tabel, zie
  [`001-feedback-indienen-en-beheren.md`](001-feedback-indienen-en-beheren.md)
  §Schemabeslissing). Niets architecturaals te repareren op dit punt, alleen netjes overnemen.

**Bewuste vereenvoudiging — geen registratiemoment-filter.** Het externe project verbergt voor
een analist berichten van vóór zijn eigen accountregistratie (`_zichtbaar_vanaf(bericht) >=
users.created`), zodat een nieuwe collega geen ongelezen-badge krijgt van historische
berichten. Die check hangt af van `users.created` — een tabel/feature die in dit project nog
niet bestaat (net als bij feedback is auth hier een vereenvoudigde stand-in, zie Auth/rollen).
Deze implementatie laat het weg: elke gebruiker ziet alle gepubliceerde berichten, zonder filter
op registratiemoment. Zodra een echte `identiteit`/`auth`-feature met een `users`-tabel bestaat,
kan die filter alsnog toegevoegd worden — dat is nu geen aanname om vooruitlopend te forceren.

Het `coalesce(gepubliceerd_op, created)`-gedrag ("zichtbaar vanaf") blijft wél staan, los van de
weggelaten registratiefilter: een concept is nog niet zichtbaar (het valt terug op `created`,
maar `gepubliceerd=False` sluit het al uit van elke analist-query), en een gepubliceerd bericht
sorteert op zijn publicatiemoment, niet op wanneer het als concept is aangemaakt. Dit is een
onafhankelijke, bewust behouden eigenschap.

**Geen gedeelde `LeesbewijsStore`-abstractie tussen `feedback` en `berichten`.** Beide domeinen
hebben een "wie-heeft-dit-gezien"-patroon, maar structureel verschillend: feedback gebruikt een
cursor-per-beheerder (`gezien_tot`, één rij per beheerder, "alles vóór dit moment is gezien"),
berichten gebruikt een fijnmazige jointabel per (bericht, gebruiker) — geen echte duplicatie,
dus geen abstractie (`feature-bouwen` regel 8: alleen delen bij eenzelfde patroon, niet
vooruitlopend forceren). `berichten` krijgt een eigen `store.py`.

**Wel gedeeld: de auth-stand-in.** `huidige_gebruiker`/`huidige_beheerder` (header-gebaseerde
simulatie van ingelogde gebruiker/beheerder) zijn hetzelfde generieke patroon dat feedback al
had — geen natuurlijke eigenaar-feature (het hoort niet bij `Feedback` of bij `Bericht` als
entiteit). Dit is de tweede, onafhankelijke keer dat dit patroon nodig is, dus verplaatst naar
`api/app/shared/auth.py` (`feature-bouwen` regel 8, "geen natuurlijke eigenaar" → `shared/`).
`feedback/router.py` is aangepast om dezelfde module te gebruiken, in plaats van zijn eigen
kopie te behouden.

## Concurrency-detail — `lees-alles`

`markeer_alles_gelezen` gebruikt een dialect-aware upsert (`INSERT … ON CONFLICT DO NOTHING` op
de samengestelde primary key `(bericht_id, userid)`) in plaats van een check-then-insert: twee
gelijktijdige aanroepen (bijvoorbeeld twee open tabbladen) kunnen anders een duplicate-key-fout
geven, omdat check-then-insert niet atomair is. Overgenomen zoals het externe project het doet.

## Edge cases

- Bewerken/publiceren/depubliceren/verwijderen van een onbekend bericht-id → 404.
- `type` buiten de toegestane set, `titel`/`inhoud` leeg of te lang → 422 (schemavalidatie,
  geen route-logica).
- `lees-alles` twee keer achter elkaar aanroepen → geen fout, tweede aanroep is een no-op
  (idempotent via `ON CONFLICT DO NOTHING`).
- Een analist zonder ooit gemarkeerd te hebben ziet alle gepubliceerde berichten als ongelezen
  (geen rij in `bericht_leesbewijzen` = ongelezen, net als bij feedback).
- Een bericht verwijderen nadat analisten het al gelezen hebben → de bijbehorende
  leesbewijzen verdwijnen mee (cascade in dezelfde transactie), geen wees-rijen.

## Auth / rollen

Twee rollen, zelfde vereenvoudigde stand-in als feedback (zie
[`001-feedback-indienen-en-beheren.md`](001-feedback-indienen-en-beheren.md) §Auth/rollen),
hergebruikt via `api/app/shared/auth.py`:

- **Lezen, ongelezen-aantal, lees-alles** (`/v1/berichten/*`) — elke ingelogde gebruiker
  (analist).
- **Admin-lijst, aanmaken, bewerken, publicatie zetten, verwijderen** (`/v1/admin/berichten/*`)
  — alleen een beheerder.

## Gedeelde logica

Gebruikt `shared/auth.py` (`huidige_gebruiker`/`huidige_beheerder`), zie
§Schemabeslissing hierboven voor de afweging.

## UI

Geen UI. Deze story demonstreert uitsluitend de `api`-service (werkwijze-ADR-0002).
