# Story 038: BFF-rolautorisatie voor admin-routes

**Prioriteit:** hoog
**Story points:** 5
**Service:** `frontend/` (geen backend-wijziging — story 006 legt rolautorisatie bewust bij de
BFF, niet bij de API)
**Afhankelijkheid:** geen

## Verhaal

Als beheerder wil ik dat een analist-account nooit bij `/beheer` of een van de
`/api/admin/*`-routes kan, zodat een geldige maar lager-geprivilegieerde sessie geen
beheerhandelingen kan uitvoeren — ook niet door de URL rechtstreeks te bezoeken.

## Aanleiding

Vervolgpunt "BFF-rolautorisatie ontbreekt project-breed" (drie eerdere, losse vermeldingen
samengevoegd — PR #5 story 006, Frontend-berichten-fase-2, Fase-3-sidebar), zie
`docs/project/vervolgpunten.md`. `huidige_beheerder` in `api/app/shared/auth.py` verifieert
alleen het machine-`API_TOKEN` + een `X-User-Id`-header en retourneert altijd `rol="beheerder"`
— de architectuur (story 006) legt de echte rolcontrole bewust bij de BFF. Maar geen enkele
`app/api/admin/*`-route (berichten, gebruikers, wetten, instellingen, api-tokens, profielen) en
ook `app/api/projecten/[id]/llm-calls` (functioneel een admin-only log, path niet onder
`/admin/`) controleert `session.user.rol` vóór het doorproxyen. `AppSidebar.tsx` toont de
"Beheer"-link bovendien aan elke ingelogde gebruiker, ongeacht rol.

Praktisch risico was tot nu toe nihil (er bestonden nog geen `analist`-gebruikers), maar sinds
`GebruikerCreate.rol`/`GebruikerPatch.rol` (PR #73) daadwerkelijk `analist`-accounts toestaat is
dit een echt gat: een analist met een geldige sessie kan via de BFF elk admin-endpoint bereiken.

## Acceptatiecriteria

- [x] Een ingelogde `analist`-sessie krijgt **403** op elke `/api/admin/*`-route en op
      `/api/projecten/[id]/llm-calls`, vóór er iets naar de backend geproxyd wordt.
- [x] Een ingelogde `beheerder`-sessie blijft ongewijzigd werken op al die routes (regressietest
      — geen enkele bestaande admin-flow breekt).
- [x] Een sessie zonder `rol`-claim (zou niet moeten voorkomen, maar fail-closed) krijgt ook 403,
      niet stilzwijgend 200.
- [x] Navigeert een `analist` rechtstreeks naar `/beheer/*` (adresbalk, niet via een link), dan
      redirect de edge-`authorized`-callback naar `/` — geen 403-pagina, geen flits van
      beheerinhoud vóór de redirect.
- [x] `AppSidebar.tsx` toont de "Beheer"-link alleen aan een `beheerder`-sessie.
- [x] Bestaande e2e-tests die als `beheerder` inloggen blijven slagen zonder aanpassing van hun
      verwachte gedrag (alleen eventueel een nieuwe test voor het analist-pad erbij).

## Schemabeslissing

Geen nieuw datamodel — dit is autorisatielogica, geen nieuwe entiteit. `session.user.rol` bestaat
al (`auth.config.ts`'s `session`-callback zet 'm al vanuit het JWT).

## Aanpak

Nieuwe helper naast het bestaande `requireSession()` in `lib/bff-auth.ts`:

```ts
export async function requireBeheerder(): Promise<string | null> {
  const session = await auth();
  if (session?.user?.rol !== "beheerder") return null;
  return session.user.name ?? null;
}
```

Gecombineerd met de al genoteerde DRY-vervolgpunt (`lib/bff-auth.ts`/`api-client.ts`: de
`requireSession()` + `apiProxy()`-boilerplate is al gedupliceerd over de admin-routes) in één
nieuwe `adminProxy(pad, init?)`-helper in `lib/api-client.ts` die `requireBeheerder()` +
`apiProxy()` combineert — elke admin-route wordt daarmee een oneliner in plaats van het huidige
4-regelige `requireSession` + 401-check + `apiProxy`-patroon. Twee vervolgpunten die om dezelfde
reden op dezelfde plek samenkomen (zie vervolgpunten.md regel 233), dus in één story oppakken in
plaats van twee losse wijzigingen aan dezelfde bestanden.

Edge-gate: `auth.config.ts`'s `authorized`-callback krijgt een check die `/beheer`-paden alleen
doorlaat bij `auth.user?.rol === "beheerder"`, anders `Response.redirect(new URL("/", ...))` —
zelfde patroon als de bestaande disclaimer-/setup-redirects in diezelfde callback.

## Edge cases

- Analist bezoekt `/beheer` via de adresbalk → edge-redirect naar `/`, nooit een gerenderde
  beheerpagina (ook niet kort).
- Analist roept een admin-BFF-route rechtstreeks aan (bv. via curl/devtools, niet via de UI) →
  403 met een duidelijke `detail`, consistent met de bestaande 401-vorm
  (`{"detail": "Niet geautoriseerd."}` → hier `{"detail": "Onvoldoende rechten."}`).
- Sessie verloopt/rol wijzigt tussen het laden van de sidebar en een click (bestaande live-rol-
  check ververst dit periodiek, zie `auth.ts`'s `jwt`-callback) — buiten scope van deze story:
  de route-level 403 vangt dit sowieso af bij de eerstvolgende server-aanroep.

## Auth / rollen

Dit ís de story — geen aparte sectie nodig buiten het bovenstaande.

## Gedeelde logica

- `requireBeheerder()` naast bestaand `requireSession()` in `lib/bff-auth.ts`.
- `adminProxy()` naast bestaand `apiProxy()`/`publiekApiProxy()` in `lib/api-client.ts`.
- Alle 18 route-bestanden onder `app/api/admin/**` + `app/api/projecten/[id]/llm-calls/route.ts`
  migreren naar `adminProxy()`.

## UI

- `AppSidebar.tsx`: `NAV_SECTIES`-filter krijgt een voorwaarde die `/beheer` alleen toont bij
  `naam`/sessie-rol `"beheerder"` — component krijgt de rol als nieuwe prop (server component die
  de sidebar plaatst geeft 'm door, zelfde patroon als `naam` nu al binnenkomt).

**Gebouwd:** ja (PR #75). Geverifieerd: `tsc --noEmit`/`eslint`/`prettier` schoon, `npm run build`
succeedt. Volledige lokale e2e-regressie gedraaid (55 tests, `--workers=1`) — 52 groen, 3
faalden ook op ongewijzigde `master` (bevestigd door de wijzigingen te stashen en dezelfde tests
te herdraaien: `auth-live-rol-check.spec.ts`'s TTL-test en twee `wetcatalogus.spec.ts`-tests,
beide pre-existing/lokale-omgeving-gebonden, geen regressie van deze story). Nieuwe
`tests/e2e/rolautorisatie.spec.ts` (3 tests: sidebar verbergt Beheer-link, `/beheer`-redirect,
403 op een admin-BFF-route) groen.
