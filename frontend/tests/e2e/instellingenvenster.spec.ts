import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { apiPost, login } from "./_helpers";

// Werkwijze-story 042 — Account/Beheer → instellingenvenster-patroon. Dekt wat de bestaande
// per-paneel-e2e's (gebruikersbeheer.spec.ts, llm-profielen.spec.ts, ...) niet raken: de
// dialoog-versus-volle-pagina-tweedeling zelf, tabwissel-historiegedrag en de rol-gate op het
// nieuwe pad.
//
// Story 043 verplaatste "Beheer" van een losse navlink naar het uitklapmenu (net als de
// referentie-app) — de sidebar-klik-tests openen dat menu daarom eerst.

async function maakAnalist(request: APIRequestContext): Promise<string> {
  const naam = `e2e-analist-042-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  await apiPost(request, "/v1/admin/gebruikers", {
    gebruikersnaam: naam,
    wachtwoord: "analistWachtwoord123",
    rol: "analist",
  });
  return naam;
}

async function klikBeheerInMenu(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Gebruikersmenu" }).click();
  await page.getByRole("link", { name: "Beheer" }).click();
}

test("sidebar-klik op Beheer opent het instellingenvenster als dialoog", async ({
  page,
  context,
}) => {
  await login(page, context);
  await klikBeheerInMenu(page);

  const dialoog = page.getByRole("dialog", { name: "Instellingen" });
  await expect(dialoog).toBeVisible();
  // De URL is meegewisseld, maar we zijn niet van pagina gewisseld (geen volle-paginaload) —
  // de vorige pagina blijft achter de backdrop staan.
  await expect(page).toHaveURL("/instellingen/beheer/modelprofielen");
});

test("tabwissel in de dialoog toont het juiste paneel en gebruikt replace (geen extra history-entry)", async ({
  page,
  context,
}) => {
  await login(page, context);
  await klikBeheerInMenu(page);
  await expect(
    page.getByRole("dialog", { name: "Instellingen" }),
  ).toBeVisible();

  await page.getByRole("tab", { name: "Gebruikers" }).click();
  await expect(page).toHaveURL("/instellingen/beheer/gebruikers");
  await expect(
    page.getByRole("tab", { name: "Gebruikers", selected: true }),
  ).toBeVisible();

  // Terug in de historie sluit de dialoog in één stap i.p.v. terug te lopen naar de vorige tab —
  // dat is precies waarom de tabwissel `replace` gebruikt en geen `push`.
  await page.goBack();
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("Escape sluit de dialoog", async ({ page, context }) => {
  await login(page, context);
  await klikBeheerInMenu(page);
  await expect(
    page.getByRole("dialog", { name: "Instellingen" }),
  ).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("directe link naar een instellingen-tab laadt de volle pagina, geen dialoog", async ({
  page,
  context,
}) => {
  await login(page, context);
  await page.goto("/instellingen/beheer/gebruikers");

  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByRole("link", { name: "Terug" })).toBeVisible();
  await expect(
    page.getByRole("tab", { name: "Gebruikers", selected: true }),
  ).toBeVisible();
});

test("analist die direct een beheer-tab bezoekt wordt teruggestuurd naar home", async ({
  page,
  context,
  request,
}) => {
  const naam = await maakAnalist(request);
  await login(page, context, naam, "analistWachtwoord123");
  await page.goto("/instellingen/beheer/gebruikers");
  await expect(page).toHaveURL("/");
});
