# Story 008: Disclaimer en PoC-strip

**Prioriteit:** medium
**Story points:** 3
**Service:** `frontend/`

Nieuwe gebruikers moeten begrijpen dat deze omgeving een proof of concept is voordat ze ermee
werken. Wetsanalyse heeft dit al (disclaimer-pagina + PoC-strip in de header). Lexplainables
krijgt hetzelfde patroon, aangepast aan zijn eigen codebase.

## Verhaal

Als ingelogde gebruiker wil ik duidelijk zien dat ik in een testomgeving werk — via een
zichtbare strip bovenaan elk scherm en een bevestiging bij de eerste keer inloggen — zodat er
geen misverstanden ontstaan over stabiliteit, databehoud en de eindigheid van het product.

## Acceptatiecriteria

- [ ] Na elke succesvolle login wordt de gebruiker doorgestuurd naar `/disclaimer` als hij de
      disclaimer nog niet heeft geaccepteerd; na acceptatie gaat hij door naar de oorspronkelijke
      bestemming.
- [ ] `/disclaimer` toont de drie waarschuwingsblokken met de volgende koppen en bodytekst:
      1. "Testomgeving, geen productie" — "Deze omgeving is een proof of concept. Er wordt actief
         aan ontwikkeld; beschikbaarheid en stabiliteit zijn niet gegarandeerd."
      2. "Geen garantie op behoud van analyses" — "Analyses kunnen zonder waarschuwing vooraf
         verwijderd worden of verloren gaan. Bewaar een lokale kopie van elk rapport dat je wilt
         behouden."
      3. "Geen garantie op een eindproduct" — "Wat je hier ziet is een tussenstand. De
         uiteindelijke toepassing kan er heel anders uitzien — of er komt nooit een eindproduct."
- [ ] Op `/disclaimer` staat een "Begrepen — doorgaan"-knop die de disclaimer accepteert en de
      gebruiker doorstuurt. Heeft de gebruiker al eerder geaccepteerd, dan staat er een
      "Terug"-link in plaats van de knop.
- [ ] De acceptatie wordt bijgehouden via een httpOnly-cookie (`disclaimer_geaccepteerd=1`), zodat
      de check server-side kan plaatsvinden zonder een API-aanroep.
- [ ] Elke pagina toont wanneer de gebruiker ingelogd is een horizontale strip bovenaan de header
      met de tekst "Testomgeving — proof of concept. Analyses kunnen verloren gaan. Lees de
      voorwaarden", waarbij "Lees de voorwaarden" een klikbare link is naar `/disclaimer`.
- [ ] De strip gebruikt de bestaande CSS-variabele `--waarschuwing` voor de achtergrondkleur (geen
      losse hex).
- [ ] `/disclaimer` is ook bereikbaar als leespagina nadat de disclaimer al geaccepteerd is (de
      strip linkt er altijd naar).

## Schemabeslissing

Geen database- of API-wijziging. De enige state is een cookie in de browser:

- Cookie `disclaimer_geaccepteerd`, waarde `1`, `httpOnly`, `Path=/`, `SameSite=Lax`.
- Gezet via een Next.js Route Handler (`POST /api/disclaimer/accepteer`) die de cookie plaatst en
  een redirect uitvoert.
- Uitgelezen server-side via `cookies()` uit `next/headers` in de Server Component van
  `/disclaimer` en in de `authorized`-callback of middleware (`proxy.ts`) voor de redirect-gate.

## Redirect-gate

De `authorized`-callback in `auth.config.ts` (de logica die via `proxy.ts` als Next.js-middleware
draait) controleert de cookie bij elk inkomend verzoek van een ingelogde gebruiker. Ontbreekt
hij, dan stuurt de callback de gebruiker door naar `/disclaimer?callbackUrl=<bestemming>`. Paden die uitgesloten zijn van de gate:
`/disclaimer`, `/login`, `/api/**`.

## UI

Twee componenten:

- **PoC-strip** — in `frontend/app/layout.tsx`, zichtbaar wanneer `session !== null`. Eén
  horizontale balk boven de logobalk, achtergrond `rgb(var(--waarschuwing) / 0.1)`.
- **DisclaimerPagina** — `frontend/app/disclaimer/page.tsx` (Server Component) + optioneel een
  Client Component voor de acceptatieknop als die een fetch nodig heeft.

## Edge cases

- Directe navigatie naar `/disclaimer` zonder disclaimer-cookie → pagina toont de knop.
- Directe navigatie naar `/disclaimer` mét disclaimer-cookie → pagina toont de "Terug"-link.
- `callbackUrl` ontbreekt of wijst buiten de eigen origin → val terug op `/`.
- Niet-ingelogde gebruiker → `proxy.ts` stuurt al naar `/login` vóór de disclaimer-check; de gate
  hoeft alleen ingelogde gebruikers te behandelen.

## Auth / rollen

Geen rol-onderscheid. Zowel beheerders als analisten zien de strip en moeten de disclaimer
eenmalig accepteren.

## Gedeelde logica

Geen nieuwe gedeelde modules. De strip komt in `layout.tsx`; de redirect-gate in
`auth.config.ts` (`authorized`-callback) of `proxy.ts`.

