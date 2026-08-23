# Story 043 — sidebar-uitklapmenu-parity met wetsanalyse-ai

## Verhaal

Als gebruiker wil ik dat het uitklapmenu onderin de sidebar dezelfde opties toont als in
`wetsanalyse-ai`, zodat de twee apps zich hetzelfde gedragen op de plek waar ik account, beheer,
feedback en uitloggen verwacht.

## Aanleiding

Vervolg op story 042 ("kan je eerst de gui gelijktrekken met de wetsanalyse-ai app"). Gebruiker
vroeg nu expliciet om de sidebar en het uitklapmenu "precies hetzelfde". Via `AskUserQuestion` zijn
twee scopebeslissingen genomen:
1. Het bovenste deel van de sidebar (navigatie) kan niet inhoudelijk identiek worden — de
   referentie is opgebouwd rond een chatgeschiedenis-lijst die hier nog niet bestaat (geen
   chat-backend/graph-qa-orkestrator). Gekozen: waar mogelijk wél de **vormgeving** gelijktrekken
   (bv. de "Nieuwe analyse"-knop krijgt dezelfde focus-stijl als "Nieuw gesprek"), inhoud blijft
   projecten/werkplek-navigatie.
2. Het uitklapmenu (onderin) wordt **exact** zoals de referentie: "Feedback geven" wordt een
   menu-item (de bestaande zwevende knop rechtsonder vervalt), en "Beheer" verhuist van de
   hoofdnavigatie naar het menu.

## Referentie (`wetsanalyse-ai/frontend/components/werkplek/GesprekSidebar.tsx`)

Uitklapmenu-inhoud (in volgorde): "Account & instellingen" → `/instellingen/account`,
"Beheer" (alleen beheerder) → `/instellingen/beheer/modelprofielen`, "Feedback geven" (opent
`FeedbackDialoog`), "Uitloggen". De trigger-knop toont avatar-initialen + naam + een tweede regel
`"{Beheerder|Analist} · instellingen"`.

`FeedbackDialoog` (`components/FeedbackDialoog.tsx`) is een `Dialog`-venster met `variant="compact"`
(content-hoogte i.p.v. de vaste 42rem van het instellingenvenster — anders staat er een halve
pagina wit onder de verzendknop van een driveldsformulier), geopend vanuit het uitklapmenu, geen
eigen zwevende knop ("de app-shell heeft geen plek voor een zwevende knop — die zou over de
chat-invoer van de werkplek vallen", zie de reference-`CLAUDE.md`; lexplainables heeft dat probleem
nu niet, maar de menu-plek is toch consistenter met de rest van het uitklapmenu).

## lexplainables-specifieke afwijkingen (bewust, met reden)

1. **Geen `Button`/`Field`/`ButtonRow`/`Melding`-componentprimitives geport.** De referentie se
   `FeedbackDialoog` gebruikt die; lexplainables heeft dat hele primitives-systeem niet en gebruikt
   overal `className="btn ..."`/`field-input` + inline styles (zie elk beheer-panel uit story 042).
   Een volledige migratie naar componentprimitives is een aparte, veel grotere refactor die niemand
   heeft gevraagd — de bestaande, werkende formulierlogica uit `FeedbackKnop.tsx` verhuist
   ongewijzigd naar de nieuwe `FeedbackDialoog.tsx`, alleen de schil (zwevende `div` → gedeelde
   `Dialog`) en de trigger (zwevende knop → menu-item) veranderen.
2. **`components/ui/Dialog.tsx` krijgt de `compact`-variant.** Story 042 liet expres alleen
   `center` bouwen ("geen tweede consument nu") — deze story is die tweede consument. Poort van de
   referentie se `compact`-`PANEEL_CLASS` (content-hoogte met een plafond, i.p.v. de vaste
   42rem-hoogte van `center`).
3. **"Annotaties"-navlink niet meegenomen.** De referentie toont die boven de gesprekkenlijst;
   lexplainables heeft geen losstaande `/annotaties`-pagina (annoteren gebeurt binnen `/werkplek`).
   Er is niets om naar te verwijzen — geen nep-link toevoegen.

## Wijzigingen

**`components/AppSidebar.tsx`:**
- "Nieuwe analyse"-knop krijgt de ontbrekende `focus-visible:outline …`-klassen (de referentie se
  "Nieuw gesprek"-knop heeft ze, lexplainables se knop niet).
- Hoofdnavigatie sluit `/instellingen/beheer` altijd uit (niet meer conditioneel op rol) — die
  optie verhuist naar het uitklapmenu.
- Trigger-knop van het uitklapmenu krijgt een tweede regel: `"{Beheerder|Analist} · instellingen"`.
- Uitklapmenu-inhoud wordt: "Account & instellingen" (hernoemd, zelfde link), "Beheer"
  (nieuw, alleen `rol === "beheerder"`), "Feedback geven" (nieuw, opent `FeedbackDialoog`),
  "Uitloggen" (ongewijzigd).

**`components/feedback/FeedbackDialoog.tsx`** (nieuw): de bestaande formulierlogica uit
`FeedbackKnop.tsx` (categorie/tekst-state, submit-handler, succesmelding) in de gedeelde `Dialog`
(`variant="compact"`), met dezelfde kop-vorm als `InstellingenDialog` (titel + kruisje).
`components/feedback/FeedbackKnop.tsx` vervalt; `app/layout.tsx` verliest de globale
`{session && <FeedbackKnop />}`.

**`components/ui/Dialog.tsx`:** `variant?: "center" | "compact"`-prop, default `"center"` (bestaande
aanroepen — `InstellingenDialog` — blijven ongewijzigd werken).

## Acceptatiecriteria

- [x] Uitklapmenu toont in volgorde: Account & instellingen, Beheer (alleen beheerder), Feedback
      geven, Uitloggen.
- [x] "Beheer" staat niet meer als losse link in de hoofdnavigatie (voor geen enkele rol).
- [x] "Feedback geven" opent een gecentreerd `compact`-dialoogvenster (geen zwevende knop meer
      rechtsonder), met dezelfde formulierlogica (categorie, tekst, verzenden, succesmelding) als
      voorheen.
- [x] De trigger-knop van het gebruikersmenu toont naam + rol-onderschrift.
- [x] Bestaande E2E's die de oude interactie-volgorde aannemen zijn bijgewerkt: `instellingenvenster.
      spec.ts` (Beheer-link zit nu in het menu), `account.spec.ts` (menu-itemtekst hernoemd,
      substring-match op "Account" blijft geldig), `feedback.spec.ts` (feedbackformulier opent nu
      via het menu, niet via een directe knop op `/`), `rolautorisatie.spec.ts` (blijft kloppen:
      geen Beheer-link zichtbaar voor een analist, nu ook niet in het gesloten menu — geen
      wijziging nodig).

## Verificatie

- `npx tsc --noEmit`, `npm run lint`, `npm run format:check` — schoon.
- `npm run build` — succesvol.
- `CI=1 SESSION_CHECK_TTL_MS=100 npx playwright test` — volledige suite: 55 geslaagd, dezelfde 2
  pre-existing `wetcatalogus.spec.ts`-faalgevallen als in story 042 (bevestigd ongerelateerd).

## Buiten scope

- Vollediger vormgelijktrekken van de hoofdnavigatie (chatgeschiedenis, "Annotaties"-link) — wacht
  op de chat-backend (graph-qa-orkestrator), zoals al vastgelegd in `vervolgpunten.md` (Fase 3).
- Migratie naar de referentie se `Button`/`Field`/`ButtonRow`/`Melding`-componentprimitives.

## Prioriteit / story points

Prioriteit: **medium** (expliciet gevraagd door de gebruiker). Story points: **3** — meerdere
bestanden, één nieuwe gedeelde UI-variant, geen nieuwe entiteiten/schema.

## Gebouwd:

Ja (PR #80). Uitklapmenu 1:1 met `wetsanalyse-ai`; hoofdnavigatie-stijl van de "nieuw"-knop
gelijkgetrokken waar mogelijk zonder de ontbrekende chatgeschiedenis na te bouwen.
