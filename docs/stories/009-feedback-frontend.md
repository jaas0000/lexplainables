# Story 009: Feedback frontend

**Prioriteit:** medium
**Story points:** 3
**Service:** `frontend/`

## Verhaal

Als ingelogde gebruiker wil ik feedback kunnen indienen via een zwevende knop rechtsonder in de UI zonder de pagina te verlaten, zodat ik snel een opmerking of probleem kan doorgeven.

Als beheerder wil ik ingezonden feedback kunnen inzien en verwijderen via het beheerscherm, met een zichtbare teller voor ongelezen items, zodat ik weet wat er speelt en de lijst actueel blijft.

## Acceptatiecriteria

- [ ] Elke ingelogde gebruiker ziet rechtsonder een zwevende knop waarmee een feedbackformulier geopend kan worden.
- [ ] Het formulier bevat: categorie (verbeteridee / probleemmelding / compliment / vraag), vrije tekst (verplicht, max 4000 tekens), en een verzendknop. De huidige `pagina` wordt automatisch meegestuurd via `window.location.pathname`.
- [ ] Lege tekst of categorie buiten de toegestane set blokkeert verzenden (client-side validatie).
- [ ] Na succesvol verzenden sluit het formulier en ziet de gebruiker een korte bevestiging.
- [ ] Bij een netwerk- of serverfout blijft het formulier open met een foutmelding.
- [ ] Een beheerder ziet op `/beheer` in de sectie "Gebruikersfeedback" een knop "Bekijk feedback →" met het ongelezen-aantal als badge. De knop navigeert naar `/beheer/feedback`.
- [ ] `/beheer/feedback` toont alle ingezonden feedbackitems (nieuwste eerst, gepagineerd met max 50 items).
- [ ] Een beheerder kan een feedbackitem verwijderen op `/beheer/feedback`.
- [ ] Als de feedbacksectie geladen wordt, roept de frontend automatisch `POST /api/admin/feedback/markeer-gezien` aan (vergelijkbaar met hoe berichten werken in de popover).
- [ ] Het ongelezen-aantal verschijnt als badge of teller zichtbaar voor de beheerder in de `/beheer` sectie-header.
- [ ] Bij een lege feedbacklijst staat "Nog geen feedback ontvangen."

## Schemabeslissing

Geen nieuwe datamodellen — de API-types worden via de bestaande contractgeneratie (`openapi-typescript`) gebruikt:

- `components["schemas"]["FeedbackCreate"]` — voor het indieningsformulier (`categorie`, `tekst`, `pagina`)
- `components["schemas"]["FeedbackRead"]` — voor de adminlijst
- `operations["lijst_feedback_v1_admin_feedback_get"]["responses"]["200"]["content"]["application/json"]` — paginacontainer met `items` + `totaal`

**BFF-routes** (volgen het berichten-patroon: `requireSession()` + `apiProxy()`):

| Route | Methode | Doel |
|---|---|---|
| `app/api/feedback/route.ts` | POST | Indienen (elke ingelogde gebruiker) |
| `app/api/admin/feedback/route.ts` | GET | Admin-lijst (beheerder) |
| `app/api/admin/feedback/[id]/route.ts` | DELETE | Verwijderen (beheerder) |
| `app/api/admin/feedback/markeer-gezien/route.ts` | POST | Markeer gezien (beheerder) |
| `app/api/admin/feedback/ongelezen-aantal/route.ts` | GET | Ongelezen-teller (beheerder) |

## Edge cases

- Lege tekst of ongeldige categorie → client-side foutmelding, formulier verzenden geblokkeerd.
- Netwerk- of serverfout bij indienen → foutmelding in het formulier, formulier blijft open.
- Admin verwijdert een al verwijderd item (race condition) → API geeft 404 → toon foutmelding, herlaad de lijst.
- Admin-lijst is leeg → toon "Nog geen feedback ontvangen."
- Dubbel indienen (snel tweemaal klikken) → verzendknop disabled na eerste klik.

## Auth / rollen

- Indienen (`POST /api/feedback`): elke ingelogde gebruiker — `requireSession()` geeft gebruikersnaam terug, doorgegeven als `X-User-Id` header via `apiProxy()`.
- Admin-lijst, verwijderen, markeer-gezien, ongelezen-aantal: alleen beheerder — rolcheck gebeurt server-side in de API; de BFF controleert alleen of er een sessie is.

## Gedeelde logica

- `requireSession()` uit `lib/bff-auth.ts` — bestaat ✓
- `apiProxy()` uit `lib/api-client.ts` — bestaat ✓
- `SectieHeader` + `LeegePlaceholder` uit `components/beheer/SectieHeader.tsx` — bestaat ✓

## UI

- **Zwevende knop**: rechtsonder, vaste positie op het scherm, zichtbaar op alle pagina's na inloggen. Stijl: `btn btn-primary` met een feedbackicoon.
- **Formulier**: opent als overlay/panel boven de knop (niet een modal die de hele pagina blokkeert). Sluit bij Escape en bij klikken buiten het paneel.
- **Admin-knop op `/beheer`**: in de sectie "Gebruikersfeedback", één regel met het ongelezen-aantal als rode badge en een "Bekijk feedback →"-knop die linkt naar `/beheer/feedback`.
- **Feedbackpagina `/beheer/feedback`**: toont de volledige lijst met `SectieHeader`, `CategorieBadge` per item, userid/pagina/datum, en een verwijderknop per item.

**Gebouwd:** ja (PR #8)
