import { test, expect, type APIRequestContext } from "@playwright/test";
import { apiPost, login } from "./_helpers";

// Story 038 — BFF-rolautorisatie: een analist-sessie mag geen `/beheer`-pagina's en geen
// `/api/admin/*`-routes bereiken. Bestaande beheerder-e2e-tests (gebruikersbeheer.spec.ts,
// wetten-beheer.spec.ts, ...) blijven de regressie-dekking voor het beheerder-pad.
//
// Elke test maakt zijn eigen analist-account met een unieke naam (zelfde reden als
// gebruikersbeheer.spec.ts: `fullyParallel` draait tests binnen dit bestand mogelijk
// tegelijk, dus een gedeelde gebruikersnaam + `resetGebruikers` in `beforeEach` geeft een
// race waarbij de ene test de sessie van de andere onderuit haalt).

const ANALIST_WACHTWOORD = "analistWachtwoord123";

async function maakAnalist(request: APIRequestContext): Promise<string> {
  const naam = `e2e-analist-038-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  await apiPost(request, "/v1/admin/gebruikers", {
    gebruikersnaam: naam,
    wachtwoord: ANALIST_WACHTWOORD,
    rol: "analist",
  });
  return naam;
}

test("analist ziet geen Beheer-link in de sidebar", async ({
  page,
  context,
  request,
}) => {
  const naam = await maakAnalist(request);
  await login(page, context, naam, ANALIST_WACHTWOORD);
  await expect(page.getByRole("link", { name: "Beheer" })).not.toBeVisible();
});

test("analist die /beheer bezoekt wordt teruggestuurd naar home", async ({
  page,
  context,
  request,
}) => {
  const naam = await maakAnalist(request);
  await login(page, context, naam, ANALIST_WACHTWOORD);
  await page.goto("/beheer");
  await expect(page).toHaveURL("/");
});

test("analist krijgt 403 op een admin-BFF-route", async ({
  page,
  context,
  request,
}) => {
  const naam = await maakAnalist(request);
  await login(page, context, naam, ANALIST_WACHTWOORD);
  const res = await page.request.get("/api/admin/gebruikers");
  expect(res.status()).toBe(403);
});
