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

Nieuwe helper naast het bestaande `requireSession()` in `lib/bff-auth.ts` — onderscheidt
bewust "geen sessie" (401) van "sessie zonder beheerder-rol" (403), zie Edge cases hieronder
voor waarom dat onderscheid nodig bleek:

```ts
export type BeheerderCheck =
  | { gebruikersnaam: string; fout?: undefined }
  | { gebruikersnaam?: undefined; fout: 401 | 403 };

export async function requireBeheerder(): Promise<BeheerderCheck> {
  const session = await auth();
  if (!session?.user?.name) return { fout: 401 };
  if (session.user.rol !== "beheerder") return { fout: 403 };
  return { gebruikersnaam: session.user.name };
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
- **Gevonden tijdens verificatie (regressie, gefixt):** `requireBeheerder()` sloeg aanvankelijk
  "geen geldige sessie" en "wel een sessie, geen beheerder-rol" allebei plat tot 403. Dat brak
  `auth-live-rol-check.spec.ts`: bij een gedeactiveerd account wordt de sessie server-side
  (node, live-check) ongeldig, maar de *edge*-middleware (`proxy.ts`, licht `authConfig` zonder
  live-check) blijft de oude, nog-geldig-ogende cookie zien en laat `/beheer` gewoon door. Vóór
  deze story kreeg de client dan 401 van `requireSession()`, en `beheerFetch` redirect
  specifiek op 401 naar `/login` — met een blanket 403 verdween die redirect. Fix:
  `requireBeheerder()` retourneert nu `{fout: 401}` (geen sessie) vs. `{fout: 403}` (sessie,
  verkeerde rol) i.p.v. één plat `string | null`.

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
succeedt.

CI ving een echte regressie op `auth-live-rol-check.spec.ts` die lokaal aanvankelijk niet als
zodanig herkend werd: `SESSION_CHECK_TTL_MS` stond lokaal niet standaard op de CI-waarde (100ms),
waardoor de test lokaal ook al zonder mijn wijzigingen faalde (verkeerd toegeschreven aan
pre-existing gedrag) — pas met `SESSION_CHECK_TTL_MS=100` lokaal ingesteld bleek het een echte
regressie: de blanket-403 in `requireBeheerder()` at de 401-gedreven login-redirect van
`beheerFetch` op (zie Edge cases). Gefixt door 401 en 403 te onderscheiden. Na de fix: volledige
lokale e2e-suite met `SESSION_CHECK_TTL_MS=100 --workers=1` (55 tests) — 53 groen, 2
`wetcatalogus.spec.ts`-tests falen ook op ongewijzigde `master` (bevestigd door te stashen en
dezelfde tests te herdraaien) én slagen wél in CI — lokale-fixture-staat, geen regressie van
deze story. Nieuwe `tests/e2e/rolautorisatie.spec.ts` (3 tests: sidebar verbergt Beheer-link,
`/beheer`-redirect, 403 op een admin-BFF-route bij een geldige analist-sessie) groen; de
401-tak wordt gedekt door het herstelde `auth-live-rol-check.spec.ts`.
