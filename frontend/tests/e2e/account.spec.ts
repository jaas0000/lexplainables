import { test, expect } from "@playwright/test";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.
// De tests loggen in als "beheerder" (seed-gebruiker) en passen het wachtwoord tijdelijk aan.
// Na elk gelukkig-pad-test wordt het wachtwoord teruggezet zodat volgende runs slagen.

const SEED_WACHTWOORD = "beheerder123";

test.beforeEach(async ({ page, context }) => {
  await context.addCookies([
    {
      name: "disclaimer_geaccepteerd",
      value: "1",
      domain: "localhost",
      path: "/",
    },
  ]);
  await page.goto("/login");
  await page.getByLabel("Gebruikersnaam").fill("beheerder");
  await page.getByLabel("Wachtwoord").fill(SEED_WACHTWOORD);
  await page.getByRole("button", { name: "Inloggen" }).click();
  await page.waitForURL("/");
});

test("gelukkig pad: account-pagina laadt gebruikersnaam en rol", async ({
  page,
}) => {
  await page.goto("/account");

  await expect(page.getByRole("heading", { name: "Account" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Mijn gegevens" }),
  ).toBeVisible();

  // Gebruikersnaam zichtbaar in de gegevens-sectie — expliciet uit de <dd>, niet
  // uit de navigatiebalk waar de naam ook staat (strict-mode-conflict).
  await expect(
    page.locator("dd", { hasText: "beheerder" }).first(),
  ).toBeVisible();
});

test("gelukkig pad: wachtwoord wijzigen en terugzetten", async ({ page }) => {
  const tijdelijkWachtwoord = `tijdelijk-${Date.now()}`;

  await page.goto("/account");
  await expect(
    page.getByRole("heading", { name: "Wachtwoord wijzigen" }),
  ).toBeVisible();

  // Vul het formulier in.
  await page.getByLabel("Huidig wachtwoord").fill(SEED_WACHTWOORD);
  await page
    .getByLabel("Nieuw wachtwoord", { exact: false })
    .first()
    .fill(tijdelijkWachtwoord);
  await page.getByLabel("Bevestig nieuw wachtwoord").fill(tijdelijkWachtwoord);
  await page.getByRole("button", { name: "Wachtwoord opslaan" }).click();

  // Succesbericht verschijnt.
  await expect(page.getByText("Wachtwoord succesvol gewijzigd.")).toBeVisible();

  // Formulier is gereset: huidig-wachtwoord-veld is leeg.
  await expect(page.getByLabel("Huidig wachtwoord")).toHaveValue("");

  // Zet het wachtwoord terug zodat de volgende test-run werkt.
  await page.getByLabel("Huidig wachtwoord").fill(tijdelijkWachtwoord);
  await page
    .getByLabel("Nieuw wachtwoord", { exact: false })
    .first()
    .fill(SEED_WACHTWOORD);
  await page.getByLabel("Bevestig nieuw wachtwoord").fill(SEED_WACHTWOORD);
  await page.getByRole("button", { name: "Wachtwoord opslaan" }).click();
  await expect(page.getByText("Wachtwoord succesvol gewijzigd.")).toBeVisible();
});

test("foutpad: verkeerd huidig wachtwoord toont foutmelding bij het veld", async ({
  page,
}) => {
  await page.goto("/account");

  await page.getByLabel("Huidig wachtwoord").fill("dit-is-verkeerd");
  await page
    .getByLabel("Nieuw wachtwoord", { exact: false })
    .first()
    .fill("nieuwwachtwoord1");
  await page.getByLabel("Bevestig nieuw wachtwoord").fill("nieuwwachtwoord1");
  await page.getByRole("button", { name: "Wachtwoord opslaan" }).click();

  // Foutmelding bij het huidig-wachtwoord-veld. Scoped naar de <p role="alert"> in het
  // formulier — `getByRole("alert")` matcht ook Next.js' `__next-route-announcer__` <div>.
  const foutmelding = page.locator('p[role="alert"]');
  await expect(foutmelding).toBeVisible();
  await expect(foutmelding).toContainText("klopt niet");
});

test("Account-link in de navigatie is zichtbaar en navigeert naar /account", async ({
  page,
}) => {
  await page.goto("/");
  const link = page.getByRole("link", { name: "Account" });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL("/account");
  await expect(page.getByRole("heading", { name: "Account" })).toBeVisible();
});
