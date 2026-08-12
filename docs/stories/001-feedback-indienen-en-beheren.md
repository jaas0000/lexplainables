# Story 001: Feedback indienen en beheren

**Prioriteit:** high
**Story points:** 3
**Service:** `api`

Eerste feature van de referentie-implementatie (`BACKLOG.md` §Referentie-implementatie
`voorbeeld/wetsanalyse/`). Herbouwt het feedback-domein van het bestaande, externe project
(`jaas0000/wetsanalyse-ai`, `api/app/feedback.py` + `api/app/routers/feedback.py` +
`api/app/routers/admin.py` §feedback) volgens deze werkwijze, als bewijs-van-concept — niet
door dat project te kopiëren.

## Verhaal

Als gebruiker wil ik feedback kunnen indienen vanuit de webapp, en als beheerder wil ik
ingezonden feedback kunnen inzien, verwijderen en zien hoeveel er ongelezen is, zodat feedback
niet verloren gaat en de beheerder niet elke keer de hele lijst hoeft te doorlopen.

## Acceptatiecriteria

- [ ] Een gebruiker kan feedback indienen (`categorie`, `tekst`, optioneel `pagina`) en krijgt
      het toegekende id terug.
- [ ] Een beheerder ziet ingezonden feedback terug in de admin-lijst, gepagineerd, nieuwste
      eerst, met het totaal aantal.
- [ ] Een beheerder kan een feedbackitem verwijderen op id.
- [ ] Een beheerder kan het aantal ongelezen feedbackitems opvragen: items ingediend ná het
      laatste moment dat deze beheerder de feedbackpagina heeft gemarkeerd als gezien.
- [ ] Een beheerder kan markeren dat hij de feedback gezien heeft, optioneel met een expliciete
      `tot`-timestamp (voorkomt dat feedback die tussen laden en markeren binnenkomt ten
      onrechte als gezien telt).
- [ ] Vóór de eerste keer markeren telt alle ingezonden feedback als ongelezen.

## Schemabeslissing

Twee entiteiten in `api/app/features/feedback/models.py` (de ene bron, ADR-0011):

- `user_feedback` — ongewijzigd t.o.v. het externe project: `id` (PK, autoincrement),
  `client_id` (str 128), `userid` (str 128), `categorie` (kolom str 32; op het Pydantic-contract
  een `Literal["verbeteridee", "probleemmelding", "compliment", "vraag"]` i.p.v. een losse `str`
  met regex-pattern — een gesloten verzameling hoort als strikter type vastgelegd, zie
  `feature-bouwen` regel 3 "wees scherp op precisie"), `tekst` (text, 1-4000 tekens), `pagina`
  (text, nullable, max 500 tekens), `created` (datetime tz-aware, geïndexeerd). Append-only:
  geen update-operatie, alleen indienen/verwijderen/lijst.
- `feedback_leesbewijzen` — **nieuw**, vervangt de `users.feedback_gezien_op`-kolom van het
  externe project. Velden: `admin_userid` (str 128, primary key), `gezien_tot` (datetime
  tz-aware, verplicht). Eén rij per beheerder die ooit gemarkeerd heeft; geen rij =
  "nog nooit gezien".

  **Waarom een eigen tabel in plaats van een kolom op een users-tabel:** het externe project
  leest/schrijft `users.feedback_gezien_op` vanuit de feedback-servicelaag — een cross-domain-
  lek waarbij het feedback-domein een kolom "leent" van het identiteits-/toegangsdomein (zie
  ook `berichten`/`bericht_leesbewijzen` in datzelfde project, dat dit patroon al wél goed
  doet). Vertical slicing (werkwijze-ADR-0001) vraagt dat elke feature zijn eigen data bezit;
  deze demo bouwt dat vanaf het begin goed i.p.v. het lek over te nemen. Geen generieke
  `LeesbewijsStore`-abstractie: dat zou vooruitlopen op een tweede, nog niet gebouwde
  implementatie (`feature-bouwen` regel 8) — dit domein bevat immers geen tweede feature
  (bv. berichten) om het patroon mee te delen.

## Edge cases

- Verwijderen van een onbekend feedback-id → 404.
- `categorie` buiten de toegestane set, `tekst` leeg of > 4000 tekens, `pagina` > 500 tekens →
  422 (schemavalidatie, geen route-logica).
- Ongelezen-aantal voor een beheerder die nog nooit gemarkeerd heeft → alle feedback telt mee
  (zie Schemabeslissing: geen rij in `feedback_leesbewijzen` = alles ongelezen). Dit wijkt af
  van het externe project, dat in dat geval terugvalt op de registratiedatum van de beheerder
  (`users.created`) — een fallback die vereist dat er een gebruikersregistratie bestaat. Dit
  domein heeft bewust geen eigen gebruikerstabel (auth is hier een vereenvoudigde stand-in,
  zie Auth/rollen), dus "alles telt als ongelezen" is de enige zinnige default.
- `markeer-gezien` met een expliciete `tot` in het verleden (bv. gelijk aan de vorige
  `gezien_tot`) → idempotent, geen fout.

## Auth / rollen

Twee rollen, net als het externe project (werkwijze-ADR-0009: gebruikers- vs. admin-auth zijn
gescheiden mechanismen):

- **Indienen** (`POST /v1/feedback`) — elke ingelogde gebruiker.
- **Admin-lijst, verwijderen, ongelezen-aantal, markeer-gezien** (`/v1/admin/feedback/*`) —
  alleen een beheerder.

Beide zijn hier **sterk vereenvoudigd**: een simpele FastAPI-dependency die de gebruiker/
beheerder simuleert via een header (`X-User-Id` resp. `X-Admin-Id`), geen echte sessie/JWT/
bcrypt. Dit is een bewuste stand-in voor het echte, twee-schema's-auth-systeem (ADR-0009) — het
punt van deze referentie-implementatie is de featurestructuur, niet een volledig auth-domein
namaken (dat is voorzien als latere stap, zie `BACKLOG.md`).

## Gedeelde logica

Geen — dit is de eerste feature van deze service, er is nog niets om naar te verwijzen.

## UI

Geen UI. Deze story demonstreert uitsluitend de `api`-service (werkwijze-ADR-0002); `frontend`/
`frontend-chat` zijn nog niet gebouwd in deze referentie-implementatie.
