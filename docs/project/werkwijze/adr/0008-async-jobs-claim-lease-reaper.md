# ADR-0008: Async jobs — claim/lease/reaper/reconcile-bij-herstart

**Status:** geaccepteerd
**Datum:** 2026-08-12

## Context

Een achtergrondtaak die door meerdere workers/instanties tegelijk opgepakt kan worden, heeft een
mechanisme nodig om te voorkomen dat twee workers dezelfde taak dubbel uitvoeren, én om een
taak die halverwege crasht (worker valt weg zonder de taak af te melden) alsnog opnieuw op te
laten pakken.

## Beslissing

Een achtergrondtaak doorloopt altijd dezelfde levenscyclus:

- **Claim** — een worker markeert een taak atomisch als "in behandeling door mij", met een
  expliciete lease-vervaltijd. De claim is een atomische schrijfoperatie met een
  voorwaardecheck op de huidige state (CAS): slaagt de schrijfoperatie niet, dan heeft een
  andere worker de taak eerder opgepakt of klopt de state niet. De claim schrijft ook
  een `owner`-veld (worker-identiteit) en een `lease_until`-tijdstip.
- **Lease verlengen** — zolang de worker actief met de taak bezig is, verlengt hij de lease
  periodiek. De verlenging is owner-fenced: alleen de worker die de taak claimde mag verlengen
  (`WHERE owner = <eigen-id>`). Geen match betekent dat de worker zijn lease kwijt is — het
  signaal aan de worker om te stoppen.
- **Reaper** — een apart, periodiek proces dat drie patronen afhandelt:
  1. **Verlopen lease** — taken in een actieve state met `lease_until` in het verleden worden
     teruggezet naar een fout-state. De claim hiervoor gebruikt dezelfde CAS-schrijfoperatie
     als een gewone claim, maar met een extra voorwaarde dat de lease ook daadwerkelijk verlopen
     is (`lease_until < now`).
  2. **Verweesde queued-taken** — taken die al een tijd in de wachtrij staan zonder dat ze ooit
     geclaimed zijn (geen `owner`, aanmaaktijdstip ouder dan een drempelwaarde). Dit vangt het
     geval op waarbij een worker crasht tussen het aanmaken en het claimen van een taak.
  3. **Lease-loze actieve taken (migratievangnet)** — actieve taken zonder `lease_until`-veld
     (kunnen ontstaan na een schema-migratie of bij een eerste uitrol): zet `lease_until` op
     `now - 1s` zodat patroon 1 ze alsnog oppikt.
- **Reconcile bij herstart** — bij het opstarten van een worker/service controleert het proces
  expliciet op taken die vóór een crash "in behandeling" stonden bij diezelfde worker, niet
  alleen passief op de reaper wachten.

### Schrijven naar een taak (owner-fencing)

Elke schrijfoperatie op een taak die geen claim of lease-verlenging is (inhoudelijke
voortgang, resultaat opslaan) is eveneens owner-fenced: de schrijfoperatie slaagt alleen als
`owner` nog steeds overeenkomt met de eigen worker-identiteit. Hiermee wordt voorkomen dat een
stale snapshot van een vorige worker (die de lease kwijtraakte) de toestand van de nieuwe
eigenaar overschrijft. `owner` en `lease_until` worden nooit via een gewone save-operatie
geschreven — uitsluitend via claim en lease-verlenging.

### Voortgangsrapportage (observerend, buiten de state-CAS)

Fijnmazige voortgangstikken — welke substap loopt, hoe ver een lange stap gevorderd is —
worden in een apart veld bijgehouden dat géén onderdeel is van de state-machine. Schrijven
naar dit veld raakt `updated` niet en verstoort de state-CAS niet. Clients kunnen dit veld
pollen voor live voortgang zonder dat de worker extra claims of state-transities hoeft te doen.

### Configureerbare knoppen

- **Lease-duur** — kies ruim langer dan de langste realistische staptijd (LLM-calls,
  externe API's). De worker verlengt actief; de lease-duur is de vangnet-grens, niet de
  verwachte doorlooptijd.
- **Reaper-interval** — hoe vaak het reaper-proces draait. Waarde 0 zet de reaper uit
  (handig in testomgevingen met één worker).

## Consequenties

- Een gecrashte worker verliest nooit stilzwijgend een taak — de lease-vervaltijd is de harde
  bovengrens op hoe lang een taak "vast" kan blijven staan.
- Verweesde taken (aangemaakt maar nooit geclaimed) worden ook door de reaper opgeruimd, niet
  alleen taken met een verlopen lease.
- Stale schrijfoperaties van een vorige worker overschrijven de nieuwe eigenaar nooit dankzij
  owner-fencing.
- Meerdere workers kunnen veilig parallel dezelfde wachtrij leeglezen zonder dubbel werk.
- Nadeel, bewust geaccepteerd: meer bewegende delen dan een simpele "pak de eerste onbehandelde
  rij"-aanpak — een reaper-proces en een expliciet lease-veld zijn alleen de moeite waard zodra
  er daadwerkelijk meerdere workers of langlopende taken zijn.
