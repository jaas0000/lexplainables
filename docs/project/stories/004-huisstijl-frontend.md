# Story 004: Wetsanalyse-huisstijl toepassen op de frontend

**Prioriteit:** medium
**Story points:** 2
**Service:** `frontend`

## Verhaal

Als beheerder wil ik dat het berichtenscherm er net zo uitziet als de wetsanalyse-applicatie, zodat de UI herkenbaar aanvoelt bij gebruik naast de bestaande tools.

## Acceptatiecriteria

- [x] De pagina gebruikt de wetsanalyse-kleurenpalet (lint/paper/surface/ink/line/accent en statusvarianten) via CSS-variabelen in `globals.css`.
- [x] Het Fira Sans-lettertype is geladen en toegepast op de body.
- [x] De header toont het project-logo/naam in de lintblauwe balk met navigatieruimte voor toekomstige secties.
- [x] Het formulier en de tabel gebruiken de wetsanalyse-veldstijl (`rounded-field`, `border-line`, focus-ring in lintblauw) en knoppen met de juiste varianten (`primary`, `secondary`, `danger`).
- [x] Knoppen die nog geen geïmplementeerde bestemming hebben (navigatielinks naar niet-bestaande secties) zijn zichtbaar disabled of gemarkeerd als placeholder — ze leiden nergens naartoe en dat is duidelijk.
- [x] De bestaande Playwright-E2E-test (`berichten-admin.spec.ts`) blijft slagen — gedrag verandert niet.

## Schemabeslissing

Geen databasewijzigingen. Uitsluitend `frontend/app/globals.css`, `frontend/app/layout.tsx` en `frontend/app/page.tsx`.

## Edge cases

- Dark mode: de huisstijl gebruikt geen dark mode; de `prefers-color-scheme: dark` override in de huidige globals.css wordt verwijderd.

## Auth / rollen

Ongewijzigd — auth-stand-in via beheerder-id tekstinvoer blijft hetzelfde.

## Gedeelde logica

Geen shared modules — alle styling staat inline of in globals.css (eerste scherm, niets te abstraheren).

**Gebouwd:** ja (gemerged)
