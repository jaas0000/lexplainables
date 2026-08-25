# Story 056 — frontend-chat: eerste chat-UI voor Lex

## Verhaal

Als jurist wil ik via een webpagina met Lex kunnen chatten — inloggen, een vraag stellen, en het
gestreamde, gegronde antwoord zien verschijnen — zonder zelf curl of een script te hoeven
gebruiken.

## Aanleiding

Tweede en laatste story van het tweeluik (055 = `api`'s chat-proxy, hier: de eerste service die
'm daadwerkelijk gebruikt). `frontend-chat/` bestond alleen als naam in de architectuurdocumentatie
(C4-model: "nog niet gebouwd"). Dit is **geen refactor-poort** van de wetsanalyse-ai-referentie
(die laat de werkplek rechtstreeks met graph-qa praten, via het runs-model) maar nieuwe
architectuur specifiek voor lexplainables' topologie-keuze: `frontend-chat → api → graph-qa`
(ADR-0001, C4-model, stack-profiel), met de gebruiker bevestigd via `AskUserQuestion`
(route via `api`, en Auth.js nu meebouwen i.p.v. een tijdelijke open versie).

## Schemabeslissing

Geen eigen datamodel/tabel — frontend-chat heeft geen database. De enige "vorm" is de body van
`POST /api/chat` (`{question, conversation_id}`, ongewijzigd doorgezet naar `api`'s chat-proxy)
en de SSE-events die terugkomen (ongewijzigd doorgezet naar de browser).

## Wijzigingen

- Nieuwe service `frontend-chat/` (Next.js 16 / Auth.js v5, poort 3002), minimale kopie van
  `frontend/`'s scaffold (`package.json`, `tsconfig.json`, `eslint.config.mjs`,
  `postcss.config.mjs`, `tailwind.config.ts`, `playwright.config.ts`,
  `scripts/genereer-types.sh`).
- **Auth**: `auth.ts`/`auth.config.ts`/`proxy.ts` — zelfde Credentials-provider tegen
  `POST /v1/auth/verify` als `frontend/`, **zonder TOTP/2FA en zonder de live-rol-herverificatie**
  (geen rollen nodig, geen admin-routes). Login-pagina op `/login`
  (`app/login/page.tsx` + `components/auth/{AuthFrame,LoginFormulier}.tsx`, minimale versie
  zonder logo/volledige huisstijl-parity).
- **Chat-UI** (`app/page.tsx` + `components/ChatVenster.tsx`): berichtenlijst + tekstvak +
  verstuur-knop. `conversation_id` client-side gegenereerd (`crypto.randomUUID()`) en in
  React-state gehouden — geen persistentie, geen gesprekgeschiedenis-sidebar. Parseert de
  SSE-events client-side (`token`/`grounding`/`error`/`done`); toont een gegrond-indicator per
  antwoord.
- **BFF-route** `app/api/chat/route.ts`: leest de sessie (`lib/bff-auth.ts::requireSession`),
  forwardt naar `api`'s nieuwe `/v1/chat` met de gebruikersnaam, en streamt de responsebody
  rechtstreeks door (`lib/api-client.ts::apiProxyStream`, nieuw t.o.v. `frontend/`'s altijd-
  bufferende `apiProxy()` — de eerste streaming-BFF-route in dit project).
- **Styling**: alleen de generieke Rijkshuisstijl-tokens + `.btn`/`.field-input`/`.melding`/
  `.card` uit `frontend/app/globals.css` overgenomen (geen volledige huisstijl-parity, geen
  logo/sidebar/appschil).
- **Playwright E2E** (`tests/e2e/chat.spec.ts`): gelukkig pad (inloggen → vraag stellen → een
  gemockt, gestreamd antwoord verschijnt) + foutpad (verkeerd wachtwoord → foutmelding, geen
  sessie-cookie). De chat-interactie zelf mockt `POST /api/chat` (`page.route`) — zie
  §Afwijkingen.
- **CI**: nieuwe `.github/workflows/frontend-chat-ci.yml` (check-ts-style, check-generated-types,
  build, E2E met Postgres+api+frontend-chat), zelfde vorm als `frontend-ci.yml`.
- **Doc-updates**: `docs/project/architectuur/c4-model.md` (`frontend_chat`-container van "nog
  niet gebouwd" naar gebouwd), `CLAUDE.md`'s Structuur-heading.

## lexplainables-specifieke afwijkingen

1. **Geen TOTP/2FA, geen live-rol-herverificatie.** frontend-chat kent geen rollen (geen
   admin-routes) — een account met 2FA aan krijgt hier een generieke "onjuiste
   gebruikersnaam/wachtwoord" i.p.v. een TOTP-scherm. Latere uitbreiding als daar behoefte aan
   komt.
2. **Geen disclaimer-gate.** Die hoort bij `frontend/`'s specifieke onboarding-stroom, niet bij
   een minimale eerste chat-UI.
3. **Geen gesprekgeschiedenis/persistentie, geen "nieuw gesprek"-knop, geen meerdere
   gelijktijdige gesprekken.** `conversation_id` leeft alleen in React-state van de huidige
   pagina-load. graph-qa's eigen checkpointer (story 050) onthoudt het gesprek server-side zolang
   de graph-qa-agent-instantie leeft, maar frontend-chat toont geen historie ná een herlaad.
4. **Geen `sources`-weergave**, alleen een `grounding.niveau`-indicator (gegrond/onbepaald/
   ongegrond) onder het antwoord — een volledige bronnenlijst-UI is meer dan deze eerste story
   aankan.
5. **Gebruikt `/v1/chat` (aan de verbinding gekoppeld), niet `/v1/runs`.** Het runs-model
   (story 054, met `stop_check`/reconnect-na-reload) is voor deze eerste, simpele chat-pagina
   nog niet nodig — een latere story sluit dat aan zodra "van pagina wisselen mag het antwoord
   niet doden" relevant wordt.
6. **E2E-happy-path mockt `POST /api/chat`** (`page.route`) in plaats van een echte graph-qa-
   aanroep. CI heeft geen GraphDB/Foundry-toegang (zelfde reden als graph-qa's eigen
   `pytest -m integration`-tests standaard geskipt worden in CI) — de echte keten is handmatig
   live geverifieerd (zie §Verificatie) en graph-qa's eigen integratietests dekken de agent-kant
   al. Dit spec test frontend-chat's eigen code (sessie-gate, streaming-rendering,
   foutafhandeling), niet graph-qa's gedrag.
7. **Geen `apiProxy()`-hergebruik uit `frontend/`.** Er is geen gedeelde package tussen de twee
   frontends (ADR-0002/8), en `frontend/`'s `apiProxy()` buffert altijd — een streamende
   `apiProxyStream()` is een nieuwe, kleine, feature-lokale functie in `frontend-chat/lib/
   api-client.ts`, geen kopie-met-aanpassing van de bufferende variant.

## Acceptatiecriteria

- [x] Zonder sessie: `/` redirect naar `/login` (`proxy.ts`).
- [x] Inloggen met geldige credentials → sessie-cookie gezet, landt op `/`.
- [x] Inloggen met onjuiste credentials → foutmelding, blijft op `/login`, geen sessie-cookie.
- [x] Een vraag versturen toont de gebruikersvraag + een streamend Lex-antwoord dat token voor
      token opbouwt, eindigend met een grounding-indicator.
- [x] `npm run build` slaagt zonder type-/lint-fouten.
- [x] Playwright E2E (gelukkig pad + foutpad) slaagt lokaal.
- [x] Live: een echte browsersessie (niet gemockt) — inloggen, een vraag stellen, een gestreamd,
      gegrond antwoord van de daadwerkelijk draaiende graph-qa + GraphDB + Foundry-keten zien
      verschijnen. Screenshot als bewijs (zie §Verificatie) — deze live-check ving een echte,
      zelf gevonden bug (zie hieronder).
- [x] `docs/project/architectuur/c4-model.md` toont `frontend_chat` als gebouwd.

**Eén bug zelf gevonden tijdens live-verificatie, binnen deze PR opgelost.** De gemockte
Playwright-test (`page.route().fulfill()`) leverde de hele SSE-body in één stuk, en verborg
daarmee een echte client-side parseerfout: `sse-starlette` scheidt events met `\r\n\r\n`
(CRLF), niet kaal `\n\n`. `ChatVenster.tsx`'s `verwerkStream` splitste alleen op `\n\n` — tegen
een écht, in kleine brokjes binnenkomende antwoord (bevestigd met `console.log` op elke
`reader.read()`: ~30 reads, elk een paar honderd bytes) bleef de buffer stil groeien zonder
ooit een event te herkennen, geen exception, geen foutmelding — het antwoordveld bleef
oneindig op "…" staan. Root cause gevonden door de rauwe bytes te inspecteren (`curl | xxd`
toonde `0d0a 0d0a`, niet `0a0a`). Gefixt: `\r\n` normaliseren naar `\n` vóór het splitsen op
`\n\n`. Dit is precies de reden dat de live-verificatiestap (niet alleen de gemockte E2E-suite)
verplicht is — een test met een kunstmatig eenmalige respons dekt dit soort chunking-gevoelige
bugs niet af.

## Buiten scope

Zie §Afwijkingen punt 1-5. Daarnaast: `frontend-chat`-specifieke Dockerfile/deploy-config (er is
nog geen deploy-doel voor `graph-qa` zelf, zie story 053's vervolgpunt — dezelfde afhankelijkheid
geldt hier), CORS/rate-limiting-aanpassingen op `api`'s kant (ongewijzigd), meertalige UI,
toegankelijkheidsaudit voorbij de basis-Rijkshuisstijl-tokens.

## Prioriteit / story points

Prioriteit: **high**. Story points: **5** (nieuwe service met Auth.js, een nieuwe
streaming-BFF-route — geen precedent in dit project — een client-side SSE-parser, E2E-tests,
een nieuwe CI-workflow, doc-updates).

## Verificatie

- `npx eslint . && npm run format:check`: schoon.
- `npm run build`: slaagt, geen type-/lint-fouten.
- `npm run genereer-types`: `frontend-chat/generated/types.ts` regenereert zonder diff.
- Playwright E2E (`chat.spec.ts`, gemockt `POST /api/chat`): 2 passed (gelukkig pad + foutpad).
- Live: lokaal draaiende `api` (poort 8098, `GRAPH_QA_URL` naar de echte graph-qa-dev-server op
  8099) + `frontend-chat` (poort 3002) + een echte Playwright-browsersessie (niet gemockt) —
  inloggen, "Wat is een belastingschuldige volgens de Invorderingswet 1990?" stellen, een
  gestreamd, correct antwoord met citaat en vindplaats zien verschijnen (~20s), screenshot
  bewaard. Onderweg de `\r\n\r\n`-SSE-parseerbug zelf gevonden en gefixt (zie
  §Acceptatiecriteria).

## Gebouwd:

Ja (PR #94).
