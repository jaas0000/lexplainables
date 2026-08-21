# Story 003: Berichten-admin-scherm (eerste frontend)

**Prioriteit:** medium
**Story points:** 3
**Service:** `frontend`

Eerste scherm van de `frontend`-service. Geeft beheerders een webinterface voor het berichtenbeheer dat story 002 als API heeft opgeleverd. Tegelijk het opzetmoment van de `frontend`-service zelf: contractgeneratie (API→TypeScript), CI, E2E-testinfrastructuur.

## Verhaal

Als beheerder wil ik via een webscherm berichten kunnen aanmaken, bewerken, publiceren en verwijderen, zodat ik geen HTTP-client hoef te gebruiken voor dagelijks berichtenbeheer.

## Acceptatiecriteria

- [x] De beheerder vult een beheerder-id in (auth-stand-in, opgeslagen in localStorage, meegestuurd als `X-Admin-Id`-header); zonder id worden geen berichten geladen.
- [x] Een overzichtstabel toont alle berichten (ook concepten) met titel, type, status en aangemaakt-door.
- [x] Een beheerder kan een nieuw bericht aanmaken via een formulier (titel, inhoud, type, versie); het bericht verschijnt direct in de tabel zonder page-reload.
- [x] Een beheerder kan een bestaand bericht bewerken; de tabel toont de bijgewerkte waarden direct na opslaan.
- [x] Een beheerder kan een bericht publiceren of depubliceren; de statuskolom in de tabel past zich direct aan.
- [x] Een beheerder kan een bericht verwijderen; de rij verdwijnt direct uit de tabel.
- [x] Bij een foutrespons van de API (bv. 404 bij verwijderen van een al verwijderd bericht) toont de pagina een zichtbare foutmelding (`role="alert"`), zonder stil te falen.

## Schemabeslissing

Geen nieuwe tabellen — de `frontend` heeft geen eigen database. Types komen uit `frontend/generated/types.ts`, gegenereerd via `frontend/scripts/genereer-types.sh` uit `api/generated/openapi.json` (contractgeneratie, stack-profiel.md §Contractgeneratie). Nooit met de hand bewerken.

Gebruikte types: `BerichtAdminRead`, `BerichtCreate` (uit het door story 002 gedefinieerde schema).

## Auth / rollen

Auth-stand-in (geen echt inlogscherm): beheerder-id als tekstveld, meegestuurd als `X-Admin-Id`-header — zelfde mechanisme als de API-stand-in in `api/app/shared/auth.py`. Een echt inlogscherm is toekomstwerk.

## Edge cases

- Beheerder-id leeg → geen API-aanroepen, promptmelding om id in te vullen.
- Verwijderen van een al verwijderd bericht (concurrente tabbladen) → zichtbare foutmelding, geen silent fail.
- Mutaties (aanmaken/bewerken/publicatie/verwijderen) updaten de lokale lijststatus optimistisch via de mutatierespons van de API, zonder volledige herlaad.

## Gedeelde logica

Geen `shared/`-modules voor de frontend (eerste scherm — niets te delen nog).

## Bijhouden

Update deze story als de auth-stand-in vervangen wordt door een echte sessie/loginflow, of als het scherm uitgebreid wordt met analist-functionaliteit (gelezen/ongelezen).

**Gebouwd:** ja (gemerged)
