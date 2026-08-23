# Story 042 — Account/Beheer → instellingenvenster-patroon

## Verhaal

Als analist/beheerder wil ik Account en alle Beheer-secties bereiken als tabs van één gedeeld
instellingenvenster (zoals in `wetsanalyse-ai`), zodat ik niet door acht losse volle paginaladingen
hoef te klikken om van "gebruikers" naar "API-tokens" te gaan.

## Aanleiding

Gebruiker koos dit expliciet als eerstvolgende GUI-gelijktrek-stap (na de skeletsidebar-vergelijking
met de referentie-app), boven twee kleinere opties (aandacht-kleurtokens, responsive typografie) —
zie de sessie-context. Dit is nadrukkelijk gedaan vóórdat de graph-qa-orkestrator/werkplek-chat
gebouwd wordt; de bestaande skelet-sidebar (`AppSidebar.tsx`) blijft de klassieke nav-link-vorm.

## Referentie-architectuur (`wetsanalyse-ai/frontend`)

- `lib/instellingen.ts` — tabdefinities (`key`/`pad`/`label`/`admin`) + `tabUitPad`/`padVanTab`/
  `isAdminTab`, bewust géén `"use client"` zodat Server Components 'm mogen importeren.
- `app/instellingen/[[...tab]]/page.tsx` — volle pagina (Server Component): leest `auth()`, gate
  `isAdminTab(actief) && !isBeheerder → redirect("/")`, rendert `InstellingenInhoud`.
- `app/@modal/(.)instellingen/[[...tab]]/page.tsx` — intercepting route: zelfde gate, rendert
  `InstellingenDialog` (de `Dialog`-schil) i.p.v. de volle pagina, als je er **vanuit de app**
  naartoe navigeert. `app/@modal/default.tsx` (return null) is verplicht voor het parallel-route-slot.
  `app/layout.tsx` krijgt een `modal`-parallel-route-prop, gerenderd als sibling van de bestaande
  `AppShell`-boom (`Dialog` is `fixed inset-0`, dus onafhankelijk van waar in de DOM-boom hij zit).
- `components/instellingen/InstellingenInhoud.tsx` — de gedeelde tabinhoud (`Tabs`-component,
  verticale oriëntatie, `lazy` zodat alleen het actieve paneel fetcht); `vervangHistorie`-prop bepaalt
  `router.replace` (dialoog) vs. `router.push` (volle pagina) bij tabwissel.
- `components/instellingen/InstellingenDialog.tsx` — dunne `Dialog`-schil (kop + sluitknop +
  `router.back()`), roept `InstellingenInhoud` aan.
- Oude routes (`app/beheer/page.tsx`, `app/account/page.tsx`) blijven bestaan als kale
  `redirect("/instellingen/...")` — bestaande links/bladwijzers blijven werken, de rolgate zit op
  het doelpad.
- `components/ui/Dialog.tsx` (al aanwezig in lexplainables' tailwind-tokens: `rounded-vorm`,
  `shadow-kaart`, `animate-rise`, `.focus-ring` bestaan al 1:1 — geverifieerd tegen
  `tailwind.config.ts`/`globals.css`) en `components/ui/Tabs.tsx` bestaan in lexplainables **nog
  niet** en moeten geport worden.

## lexplainables-specifieke afwijkingen (bewust, met reden)

1. **`components/ui/Dialog.tsx`: alleen de `center`-variant.** De referentie kent vijf varianten
   (`center`/`compact`/`side`/`kolom`/`drawer`) voor de chat-werkplek die hier nog niet bestaat.
   Zonder tweede consument nu is dat vooruitlopend abstraheren (`feature-bouwen` regel 8) — de
   overige varianten zijn een vervolgpunt zodra de werkplek/chat-shell (graph-qa-orkestrator) een
   paneel/drawer nodig heeft. `AppSidebar`'s bestaande mobiele drawer (ad-hoc `role="dialog"` zonder
   focus-trap — dezelfde bug die de referentie noemt als reden om op één `Dialog`-component te
   consolideren) migreren we **niet** mee in deze story; dat is een apart vervolgpunt, geen
   onderdeel van "Account/Beheer → instellingenvenster".
2. **`components/ui/Tabs.tsx`: alleen verticale oriëntatie**, met `lazy` (panelen fetchen bij mount)
   en badge-support (nodig voor de feedbacktab-teller, zie punt 5). De horizontale variant van de
   referentie (voor een rapport-achtig scherm) heeft hier geen consument.
3. **Geen `beveiliging`-tab.** De referentie splitst account (wachtwoord) en beveiliging (2FA) in
   twee tabs; lexplainables' huidige `/account`-pagina combineert profiel + wachtwoord + 2FA al in
   één scherm zonder dat dat ooit een probleem was. Splitsen zonder aanleiding is vooruitlopende
   abstractie — één `account`-tab met alle drie de secties (huidige `AccountPagina`-inhoud,
   ongewijzigd) volstaat.
4. **Wél een `berichten`-tab (admin), geen aparte niet-admin `berichten`-tab.** lexplainables'
   `/berichten` (analist-archief) blijft een eigen top-level navigatie-item los van
   account/beheer — dat is niet hetzelfde als de referentie se niet-admin `berichten`-tab, dus die
   laatste komt hier niet terug. Maar het oude `app/beheer/page.tsx`-dashboard bleek bij nader
   onderzoek wél een **inline admin-CRUD voor berichten** te bevatten (aanmaken/bewerken/
   publiceren/verwijderen — zichtbaar in `tests/e2e/berichten-admin.spec.ts`, over het hoofd gezien
   bij de eerste scoping van deze story). Die functionaliteit bestond alleen inline op de
   dashboardpagina zelf (geen aparte `/beheer/berichten`-route) en zou zonder een eigen tab
   verdwijnen zodra het dashboard wordt vervangen — verplaatst naar een negende tab
   `berichten` (`components/beheer/BerichtenBeheerPanel.tsx`), analoog aan de referentie se
   `BerichtenBeheerPanel`.
5. **Extra admin-tab `wetten`** (wetcatalogus-beheer, `/beheer/wetten`) — bestaat niet in de
   referentie (die heeft geen wetcatalogus-feature), maar wél in lexplainables; gewoon meenemen.
6. **Feedback-tab-badge hergebruikt bestaande logica.** De ongelezen-teller-fetch
   (`beheerFetch("/api/admin/feedback/ongelezen-aantal")`) staat al inline in het huidige
   `app/beheer/page.tsx` (regel 66) — dezelfde aanpak, alleen verplaatst naar
   `InstellingenInhoud`, geen nieuwe API-aanroep.

## Tabdefinities (`lib/instellingen.ts`)

| key | pad | label | admin | bron van de inhoud |
|---|---|---|---|---|
| `account` | `account` | Account | nee | huidige `app/account/page.tsx`-body → `components/account/AccountPanel.tsx` |
| `berichten` | `beheer/berichten` | Berichten | ja | inline CRUD uit het oude `app/beheer/page.tsx`-dashboard → `components/beheer/BerichtenBeheerPanel.tsx` |
| `modelprofielen` | `beheer/modelprofielen` | LLM-profielen | ja | `app/beheer/llm-profielen/page.tsx` → `components/beheer/ModelprofielenPanel.tsx` |
| `gebruikers` | `beheer/gebruikers` | Gebruikers | ja | `app/beheer/gebruikers/page.tsx` → `components/beheer/GebruikersPanel.tsx` |
| `wetten` | `beheer/wetten` | Wetcatalogus | ja | `app/beheer/wetten/page.tsx` → `components/beheer/WettenPanel.tsx` |
| `instellingen` | `beheer/instellingen` | Instellingen | ja | `app/beheer/instellingen/page.tsx` → `components/beheer/AppInstellingenPanel.tsx` |
| `llm-calls` | `beheer/llm-calls` | LLM-calls | ja | `app/beheer/llm-calls/page.tsx` → `components/beheer/LlmCallsPanel.tsx` |
| `api-tokens` | `beheer/api-tokens` | API-tokens | ja | `app/beheer/api-tokens/page.tsx` → `components/beheer/ApiTokensPanel.tsx` |
| `feedback` | `beheer/feedback` | Feedback | ja | `app/beheer/feedback/page.tsx` → `components/beheer/FeedbackPanel.tsx` |

`isAdminTab`: alle tabs met `pad` beginnend met `"beheer/"` — één prefix-check, zoals de referentie.

## Acceptatiecriteria

- [x] `/instellingen`, `/instellingen/account`, `/instellingen/beheer/<elk-van-de-8>` laden de
      juiste tab-inhoud (directe link + refresh, geen intercepting route van toepassing).
- [x] Een analist (niet-beheerder) die `/instellingen/beheer/<willekeurig>` direct bezoekt wordt
      server-side naar `/` geredirect (zelfde check als de referentie:
      `isAdminTab(actief) && !isBeheerder`).
- [x] Navigeren **vanuit de sidebar** (Beheer-link, of Account via het gebruikersmenu) naar
      `/instellingen/...` opent het venster als gecentreerde dialoog over de huidige pagina
      (intercepting route), met sluiten via kruisje/Escape/achtergrondklik → `router.back()`.
- [x] Een directe link of paginarefresh op `/instellingen/...` toont dezelfde inhoud als **volle
      pagina** (geen dialoog) — Next se intercepting-route-gedrag, niet iets om zelf te bouwen.
- [x] Tabwissel binnen de dialoog gebruikt `router.replace` (geen nieuwe history-entry per tab, dus
      Escape/terug sluit de dialoog i.p.v. door tabs terug te lopen); op de volle pagina
      `router.push`.
- [x] `/beheer`, `/beheer/<elk-van-de-7 bestaande subroutes>` en `/account` blijven werken als kale
      server-side redirect naar het bijbehorende `/instellingen/...`-pad (bestaande bladwijzers/
      links breken niet). De negende tab (`berichten`) had nooit een eigen route (zat inline op het
      oude dashboard), dus daar is geen aparte redirect-stub voor nodig.
- [x] `auth.config.ts`'s rol-gate verschuift van `pathname.startsWith("/beheer")` naar
      `pathname.startsWith("/instellingen/beheer")` — de oude `/beheer/*`-routes zijn nu voor elke
      ingelogde gebruiker bereikbaar (ze redirecten meteen door; de gate zit op het doelpad, zoals
      de referentie).
- [x] Een analist die de **oude** route `/beheer/<sub>` bezoekt doorloopt de volledige keten
      correct: server-side redirect naar `/instellingen/beheer/<tab>`, gevolgd door de rol-gate op
      dát pad → eindigt op `/`. Geen tussentijdse flits van beheerinhoud.
- [x] `AppSidebar`: de "Beheer"-navlink en de "Account"-link in het gebruikersmenu wijzen direct naar
      `/instellingen/beheer/modelprofielen` resp. `/instellingen/account` (geen onnodige bounce via
      de oude route). `lib/nav-secties.ts`'s `NAV_SECTIES` krijgt bijgewerkte `pad`s met de oude
      paden als `aliassen` (voor `actieveSectie()`/mobiele topbar-titel bij oude bladwijzers).
  - [x] Elke bestaande beheer-/account-pagina se functionaliteit (alle CRUD, alle formulieren, alle
      foutafhandeling) blijft **exact** werken na de verplaatsing naar een panel-component — dit is
      een structurele verplaatsing, geen herschrijving. Bestaande E2E-tests die deze pagina's raken
      moeten slagen tegen de nieuwe paden (zie volgend punt).
- [x] Playwright-E2E (`frontend/tests/e2e/`) die de instellingenvenster-navigatie dekt: sidebar-klik
      opent de dialoog, tabwissel toont het juiste paneel, Escape sluit, directe link laadt de volle
      pagina, niet-beheerder krijgt de redirect. Bestaande E2E's die naar `/beheer/...`/`/account`
      linken worden bijgewerkt naar de nieuwe paden (of blijven staan als regressietest van de
      redirect-stubs — kies per test wat hij eigenlijk toetst).

### Tijdens de bouw gevonden en gefixt

- **Ontbrekende negende tab.** De eerste scoping (§lexplainables-specifieke afwijkingen, punt 4
  hierboven zoals oorspronkelijk geschreven) miste dat het oude `app/beheer/page.tsx`-dashboard
  een écht werkende, inline berichten-CRUD droeg (`tests/e2e/berichten-admin.spec.ts`). Zonder
  ingrijpen zou die functionaliteit stilzwijgend verdwijnen zodra het dashboard vervangen wordt.
  Gevonden door de volledige oude 832-regelige `app/beheer/page.tsx` terug te lezen (`git show
  HEAD:frontend/app/beheer/page.tsx`) ná het draaien van de volledige e2e-suite tegen de nieuwe
  routes — gefixt met een negende tab (`berichten`, zie de tabel hierboven).
- **Geknipte kop-teksten braken bestaande e2e-assertions.** Bij het verplaatsen van elke pagina
  naar een panel-component zijn losse `<h1>`-koppen aanvankelijk weggelaten (de tab-label leek de
  kop al te dekken) — dat brak `getByRole("heading", {name: "Gebruikersbeheer"/"Account"/
  "LLM-calls log"/"API-tokens"})` in bestaande specs. Teruggezet in exact die vier panelen waar een
  test er daadwerkelijk op steunt (`AccountPanel`, `GebruikersPanel`, `LlmCallsPanel`,
  `ApiTokensPanel`); niet teruggezet waar `SectieHeader`'s eigen `<h2>` of de venster-chrome al een
  passende heading levert (`ModelprofielenPanel`, `WettenPanel`, `AppInstellingenPanel`,
  `FeedbackPanel`) — dat had een dubbele "Instellingen"-kop opgeleverd.
- **Sessie-invalidatie-regressie in de nieuwe rol-gate.** `auth-live-rol-check.spec.ts` (gedeactiveerd
  account moet naar `/login`) faalde: de nieuwe SSR-gate in beide instellingenroutes deed
  `isAdminTab(actief) && !isBeheerder → redirect("/")` zonder onderscheid tussen "geen sessie meer"
  (een net-live-herverifieerd gedeactiveerd account) en "wel een sessie, verkeerde rol" (een
  analist) — exact dezelfde valkuil die `requireBeheerder()`'s 401/403-splitsing in story 038 al
  een keer oploste, nu op de pagina-laag herhaald. Root-oorzaak gevonden door de e2e-suite eerst
  tegen `master` te draaien (via `git stash`) om te bevestigen dat de test daar wél slaagt, dus de
  regressie exclusief aan deze story lag. Gefixt: `redirect(session?.user ? "/" : "/login")` in
  beide routes.
- **Verouderde "klik een kaart op het beheer-dashboard"-e2e's.** Het oude 832-regelige
  `app/beheer/page.tsx`-dashboard had losse navigatiekaarten per sectie; drie e2e-tests
  (`llm-calls.spec.ts`, `api-tokens.spec.ts`, `instellingen.spec.ts`) klikten zo'n kaart aan om de
  betreffende subpagina te bereiken. Die kaarten bestaan niet meer (de tabs-UI is de nieuwe directe
  ingang, gedekt door het nieuwe `instellingenvenster.spec.ts`) — de drie tests zijn verwijderd
  i.p.v. omgebouwd, om duplicatie met die nieuwe dekking te voorkomen.

## Buiten scope

- Overige `Dialog`-varianten (`side`/`kolom`/`drawer`/`compact`) en het migreren van `AppSidebar`'s
  mobiele drawer naar `Dialog` — vervolgpunt, wacht op een echte tweede consument (werkplek-chat).
  Zie `docs/project/vervolgpunten.md` na deze story.
- `aandacht-kleurtokens` (`ElementenKolom.tsx` hardcoded hex → design tokens) en de
  responsive-typografiestrategie — expliciet niet gekozen door de gebruiker deze ronde.
- Geen wijziging aan de daadwerkelijke CRUD-logica/velden binnen elk paneel — puur een
  structuurverplaatsing (pagina → panel-component + tab).

## Prioriteit / story points

Prioriteit: **medium** (gekozen door de gebruiker als volgende stap, maar geen productie-bug).
Story points: **5** — meerdere entiteiten (9 tabs, 2 nieuwe gedeelde UI-componenten, routing-infra
met een parallel-route-slot), auth-gate-verschuiving, en raakt de bestaande rol-gate uit story 038.

## Implementatieplan

**Nieuwe bestanden:**
- `components/ui/Dialog.tsx` — poort van `wetsanalyse-ai`, alleen `center`-variant + focus-trap + Escape.
- `components/ui/Tabs.tsx` — poort, alleen verticale oriëntatie, `lazy` + badge-support.
- `lib/instellingen.ts` — `INSTELLINGEN_TABS` (9 tabs), `tabUitPad`/`padVanTab`/`isAdminTab`.
- `components/account/AccountPanel.tsx` — verplaatste body van `app/account/page.tsx`.
- `components/beheer/{ModelprofielenPanel,GebruikersPanel,WettenPanel,AppInstellingenPanel,LlmCallsPanel,ApiTokensPanel,FeedbackPanel}.tsx` — verplaatste bodies van de 7 `app/beheer/*/page.tsx`.
- `components/beheer/BerichtenBeheerPanel.tsx` — verplaatste inline berichten-CRUD uit het oude `app/beheer/page.tsx`-dashboard (geen eigen route om te vervangen).
- `components/instellingen/InstellingenInhoud.tsx` — tabs-shell, `PANEEL`-lookup, feedback-teller, `replace`/`push`-keuze.
- `components/instellingen/InstellingenDialog.tsx` — `Dialog`-schil om `InstellingenInhoud`.
- `app/instellingen/[[...tab]]/page.tsx` — volle pagina, rol-gate.
- `app/@modal/(.)instellingen/[[...tab]]/page.tsx` — intercepting route, zelfde gate.
- `app/@modal/default.tsx` — leeg slot.
- `tests/e2e/instellingenvenster.spec.ts` — dialoog/tabwissel/Escape/directe-link/rol-gate-dekking.

**Aangepaste bestanden:**
- `app/layout.tsx` — `modal`-parallel-route-prop toevoegen, als sibling van `AppShell` renderen.
- `app/account/page.tsx`, `app/beheer/page.tsx`, `app/beheer/*/page.tsx` (7x) — vervangen door kale `redirect("/instellingen/...")`.
- `auth.config.ts` — rol-gate `/beheer` → `/instellingen/beheer`.
- `lib/nav-secties.ts` — `NAV_SECTIES`-pads naar `/instellingen/beheer` en `/instellingen/account`, oude paden als `aliassen`.
- `components/AppSidebar.tsx` — gebruikersmenu-link naar `/instellingen/account`.
- `tests/e2e/account.spec.ts` — URL-assertie naar `/instellingen/account`.

**Routing:** geen migratie, geen nieuwe endpoints — zuiver frontend-routing/structuur.

**Testcases:** zie story §Acceptatiecriteria — elke tab direct + via dialoog, tabwissel-historiegedrag, alle oude routes redirecten, niet-beheerder-gate op het doelpad, bestaande CRUD-E2E's blijven groen tegen de verplaatste panelen.

**Aandachtspunten:**
- lexplainables' sessieveld heet `rol`, niet `role` (referentie) — in beide nieuwe route-bestanden gebruiken.
- `Dialog`/`Tabs` beperkt tot wat nu nodig is (`center`/verticaal) — overige varianten zijn vervolgpunt, geen vooruitlopende abstractie.
- `app/beheer/page.tsx`'s 832-regel dashboard-inhoud (nav-kaarten, tellers) vervalt; de tabs-UI is de nieuwe directe ingang.

## Verificatie

- `cd frontend && npx tsc --noEmit && npm run lint && npm run format:check` — schoon.
- `npm run build` — succesvol, routing-tabel bevestigt `/instellingen/[[...tab]]` +
  `/(.)instellingen/[[...tab]]` + alle redirect-stubs.
- `CI=1 SESSION_CHECK_TTL_MS=100 npx playwright test` — volledige e2e-suite (57 tests) tegen de
  draaiende lokale API + frontend-dev-server: **55 geslaagd**, 2 pre-existing faalt in
  `wetcatalogus.spec.ts` (bevestigd via `git stash` dat die ook op `master` falen, dus
  ongerelateerd aan deze story). Alle 8 nieuw geraakte/toegevoegde specs (`account`,
  `gebruikersbeheer`, `wetten-beheer`, `rolautorisatie`, `llm-calls`, `api-tokens`, `instellingen`,
  `llm-profielen`, `feedback`, `berichten-admin`, `auth-live-rol-check`, `2fa`,
  `instellingenvenster`) slagen.

## Gebouwd:

Ja (PR #79). Volledige verplaatsing van Account + 8 beheer-secties (incl. de bij het bouwen
ontdekte negende, `berichten`) naar een gedeeld instellingenvenster met dialoog- en
volle-pagina-vorm, zoals in `wetsanalyse-ai`. Twee reële regressies onderweg gevonden en gefixt
(zie "Tijdens de bouw gevonden en gefixt" hierboven) — geen van beide zichtbaar zonder de volledige
e2e-suite te draaien, wat precies is waarom dat verplicht is vóór deze PR.
