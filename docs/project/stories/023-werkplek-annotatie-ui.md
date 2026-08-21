# Story 023: Werkplek (annotatie-UI)

**Prioriteit:** middel
**Story points:** 5
**Service:** `frontend/`
**Afhankelijkheid:** story 022 (annotatie-backend)

## Verhaal

Als analist wil ik een wetsartikel kunnen selecteren, de door de agent voorgestelde JAS-elementen kunnen zien, en per element een beslissing kunnen nemen (goedkeuren, bewerken, afwijzen), zodat ik de annotatie efficiënt kan uitvoeren en altijd weet wat de status van elk element is.

## Acceptatiecriteria

- [ ] De werkplek (`/werkplek/`) toont een lijst van eigen annotatie-documenten met bwb-id, artikel, werkgebied, status en datum.
- [ ] Een analist kan een nieuw annotatie-document aanmaken via een formulier (werkgebied-naam, bwb-id, artikel, optioneel lid).
- [ ] Het documentdetailscherm (`/werkplek/{slug}`) toont de volledige wetsartikeltekst (opgehaald via de Wettenbank-MCP of de API) en de voorgestelde elementen.
- [ ] Per element is de klasse, tekst, toelichting en aandachtsniveau (`groen`/`geel`/`rood`) zichtbaar; de levenscyclus-status (voorgesteld, goedgekeurd, bewerkt, afgewezen) is als badge zichtbaar.
- [ ] Een analist kan per element op "Goedkeuren", "Bewerken" of "Afwijzen" klikken; bij bewerken en afwijzen is een verplichte reden selecteerbaar.
- [ ] Na een beslissing wordt het element direct bijgewerkt in de UI (optimistisch of na een API-antwoord).
- [ ] De analist kan het auditlog van een document opvragen (tijdlijn van alle acties).
- [ ] Een analist kan een document verwijderen; er wordt om bevestiging gevraagd.
- [ ] De UI is toegankelijk voor analisten én beheerders (geen rolbeperking); elk ziet alleen zijn eigen documenten.

## Schemabeslissing

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/annotatie/documenten/route.ts` | GET, POST | Lijst + aanmaken |
| `app/api/annotatie/documenten/[slug]/route.ts` | GET, DELETE | Document ophalen + verwijderen |
| `app/api/annotatie/documenten/[slug]/elementen/route.ts` | PUT | Elementen zetten |
| `app/api/annotatie/documenten/[slug]/elementen/[id]/beslissing/route.ts` | POST | Beslissing registreren |
| `app/api/annotatie/documenten/[slug]/audit/route.ts` | GET | Auditlog |

Geen nieuwe API-endpoints — alles proxyt naar de endpoints van story 022.

## Edge cases

- Document niet gevonden of toegang geweigerd (404 van de API) → redirect naar `/werkplek/` met foutmelding.
- Beslissing mislukt (netwerk-fout) → foutmelding bij het element; beslissing wordt niet optimistisch bevestigd.
- Lege elementenlijst → toon "Geen elementen voorgesteld door de agent." met een optionele "Elementen inladen"-knop (voor toekomstig gebruik door de agent).
- `bewerken` zonder reden of wijzigingen → submit-knop blijft uitgeschakeld (client-side validatie).
- Auditlog leeg (net aangemaakt document) → toon "Nog geen acties vastgelegd."
- Lange wetsartikeltekst → scrollbare leesruimte naast de elementenkolom; geen afkap.
- Sessie verlopen tijdens annotatie → bij de eerste mislukte BFF-aanroep redirect naar `/login`.

## Auth / rollen

- Alle werkplek-routes vereisen een ingelogde gebruiker (`requireSession()` in de BFF).
- De API (story 022) dwingt client-scoping af; de frontend hoeft de filtering niet zelf te doen.
- De BFF stuurt de `X-User-Id`-header mee bij elke API-aanroep (al ingebouwd via `apiProxy()`).

## Gedeelde logica

- `requireSession()` + `apiProxy()` uit `lib/bff-auth.ts` en `lib/api-client.ts` — bestaan ✓
- TypeScript-types worden gegenereerd vanuit de OpenAPI-schema van de API (via `scripts/genereer-types.sh`); gebruik de gegenereerde `AnnotatieDocument`-, `BeslissingInvoer`- en aanverwante types.
- `WetSelector`-component (story 010) hergebruiken voor de bwb-id/artikel-invoer bij het aanmaken.
- Huisstijl-componenten (`SectieHeader`, `LeegePlaceholder`, `Badge` o.i.d.) hergebruiken.

## Implementatienoot

De werkplek kopiëren en aanpassen vanuit `wetsanalyse-ai/frontend/app/workbench/`. De UI bestaat uit twee kolommen: links de wetsartikeltekst (opgehaald via `GET /v1/wetten/{bwb_id}/structuur` + de volledige artikeltekst), rechts de elementenlijst met beslissingsacties. De wetsartikeltekst op volledig artikel-niveau — met alle leden — is beschikbaar via de Wettenbank-MCP; in de BFF-laag kan dit worden opgehaald via `GET /api/wetten/{bwbId}/structuur` of een apart tekst-endpoint indien beschikbaar. De annotatie-beslissings-UI is een Server Component (lijst/document) met Client Component voor de interactieve beslissingen per element.

## UI

- **`/werkplek/`** (Server Component): kaartoverzicht of tabel van eigen documenten (bwb-id, artikel, werkgebied, status-badge, datum). Knop "Nieuw document" opent een aanmaakformulier (of navigeert naar `/werkplek/nieuw/`).
- **`/werkplek/{slug}`** (combinatie Server + Client Components):
  - Linkerkolom: wetsartikeltekst met wetsidentificatie en lidaanduiding.
  - Rechterkolom: elementenlijst, gesorteerd op aandachtsniveau (rood → geel → groen → geen). Per element: klasse-badge, tekst, toelichting, aandacht-indicator, levenscyclus-badge, drie knoppen (Goedkeuren / Bewerken / Afwijzen).
  - "Bewerken"-formulier: inline-formulier met klasse-dropdown, tekst-textarea, toelichting-textarea, reden-select (verplicht).
  - "Afwijzen"-formulier: reden-select (verplicht), optioneel opmerkingsveld.
  - "Auditlog"-tabblad: tijdlijn van acties (actie, actor, element, tijdstip).
- Mockup-varianten: lege documentenlijst, document met mix van besliste en onbesliste elementen, bewerken-formulier open, auditlog-tabblad.

**Gebouwd:** nee
