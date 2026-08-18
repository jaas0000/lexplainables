# Changelog

## Niet uitgebracht

- Beheerders kunnen nu via het beheerscherm gebruikersaccounts aanmaken, rollen en actief-status wijzigen, wachtwoorden resetten (tijdelijk wachtwoord eenmalig zichtbaar) en accounts verwijderen; de laatste actieve beheerder kan niet worden gedeactiveerd of verwijderd. (PR #14)
- Gebruikers kunnen hun accountgegevens bekijken en hun wachtwoord wijzigen via de Account-pagina. (PR #12)
- Analisten kunnen nu een analyse starten door bronartikelen te selecteren, een doel en context op te geven, en vervolgens de voortgang live te volgen. De analyselijst toont alle eigen analyses met status en zoek-/filteropties. (PR #11)
- Analisten kunnen nu een wet kiezen en de bijbehorende artikelen selecteren via het nieuwe Wetcatalogus-scherm dat de structuur van drie wetten toont. (PR #9)
- Beheerders kunnen nu LLM-profielen (provider, model, API-sleutel) aanmaken, bewerken, als standaard instellen en verwijderen via het beheerscherm. API-sleutels worden versleuteld opgeslagen. (PR #10)
- Ingelogde gebruikers kunnen feedback indienen via een zwevende knop rechtsonder op elk scherm. Beheerders zien het ongelezen-aantal op het beheerscherm en kunnen feedback bekijken en verwijderen via een nieuwe feedbackpagina. (PR #8)
- Elke ingelogde gebruiker ziet bovenaan het scherm een gele balk die aangeeft dat het om een testomgeving gaat, en moet eenmalig bevestigen dat ze dat begrijpen voordat ze verder kunnen. (PR #7)
- Beheerders kunnen nu via Claude Code rechtstreeks vanuit de terminal berichten aanmaken en publiceren, zonder de browser te hoeven openen. (PR #6)
- Inloggen gaat nu via een gebruikersnaam/wachtwoord-formulier in de app zelf — zonder doorstuur naar een externe loginpagina. (PR #5)
- Beheerders kunnen nu inloggen via Keycloak; de tijdelijke beheerder-id header is vervangen door echte authenticatie met een Keycloak-account. (PR #4)
- Beheerders kunnen via een webscherm berichten aanmaken, bewerken, publiceren/depubliceren en verwijderen; analisten zien gepubliceerde berichten via het bel-icoon in de navigatie, in de huisstijl van de wetsanalyse-applicatie. (PR #2, #3)
- Beheerders kunnen berichten (release notes/aankondigingen) aanmaken, bewerken, publiceren en verwijderen via de API; analisten kunnen gepubliceerde berichten lezen met een gelezen/ongelezen-status. (PR #1)
