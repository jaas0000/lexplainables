# Changelog

## Niet uitgebracht

- Beheerders kunnen nu de vastgelegde LLM-aanroepen per analyse bekijken: gebruikte prompts, modelnaam en token-verbruik per aanroep. (PR #20)
- Beheerders kunnen nu programmatische API-tokens aanmaken en intrekken via `/beheer/api-tokens`. Tokens worden als SHA-256-hash opgeslagen; het volledige token is alleen bij aanmaken eenmalig zichtbaar. (PR #18)
- Analisten kunnen na een afgeronde analyse het rapport bekijken: bronnen, begrippen en afleidingsregels worden overzichtelijk weergegeven en het rapport is te downloaden als Markdown-bestand. (PR #19)
- Analyses voeren nu echte juridische analyse uit via een taalmodel — het systeem haalt de wettekst op, genereert JAS-markeringen per bron (activiteit 2) en begrippen + afleidingsregels (activiteit 3), en slaat het rapport op. Human-in-the-loop: na activiteit 2 wacht de analyse op akkoord van de analist voordat activiteit 3 start. (PR #17)
- Beheerders kunnen via het beheerscherm de instelling "LLM-calls vastleggen" aan- en uitzetten; wijzigingen zijn binnen 10 seconden actief. (PR #16)
- Beheerders kunnen nu via het beheerscherm gebruikersaccounts aanmaken, rollen en actief-status wijzigen, wachtwoorden resetten (tijdelijk wachtwoord eenmalig zichtbaar) en accounts verwijderen; de laatste actieve beheerder kan niet worden gedeactiveerd of verwijderd. (PR #14)
- Beheerders kunnen nu via het Beheer-scherm wetten toevoegen, hernoemen en verwijderen, waarbij de citeertitel automatisch opgehaald kan worden via de Wettenbank. (PR #15)
- Bij een lege database kunnen beheerders nu via de `/setup`-pagina eenmalig een eerste beheerdersaccount aanmaken. Na de eerste aanmelding is de setup-pagina niet meer beschikbaar. (PR #13)
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
