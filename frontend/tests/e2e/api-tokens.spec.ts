import { test, expect } from "@playwright/test";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.

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
  await page.getByLabel("Wachtwoord").fill("beheerder123");
  await page.getByRole("button", { name: "Inloggen" }).click();
  await page.waitForURL("/");
});

test("api-tokens-pagina laadt met heading en aanmaakformulier", async ({
  page,
}) => {
  await page.goto("/beheer/api-tokens");
  await expect(page.getByRole("heading", { name: "API-tokens" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Nieuw token aanmaken" }),
  ).toBeVisible();
});

test("nieuw token aanmaken toont eenmalige token-modal", async ({ page }) => {
  await page.goto("/beheer/api-tokens");
  await page.getByLabel("Label").fill("e2e-test");
  await page.getByRole("button", { name: "Nieuw token aanmaken" }).click();

  // Modal moet verschijnen met het eenmalige token.
  await expect(
    page.getByRole("dialog", { name: "Nieuw API-token" }),
  ).toBeVisible();
  await expect(
    page.getByText("Sla dit token op — het is maar één keer zichtbaar"),
  ).toBeVisible();

  // Modal sluiten.
  await page
    .getByRole("button", { name: "Ik heb het token opgeslagen" })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();

  // Nieuw token staat in de lijst.
  await expect(page.getByText("e2e-test")).toBeVisible();
});

test("token intrekken verwijdert het uit de lijst", async ({ page }) => {
  await page.goto("/beheer/api-tokens");

  // Maak een token aan om in te trekken.
  await page.getByLabel("Label").fill("e2e-intrek");
  await page.getByRole("button", { name: "Nieuw token aanmaken" }).click();
  await page
    .getByRole("button", { name: "Ik heb het token opgeslagen" })
    .click();

  // Intrekken.
  const rij = page.getByRole("row").filter({ hasText: "e2e-intrek" });
  await rij.getByRole("button", { name: "Intrekken" }).click();

  // Token verdwenen uit de lijst.
  await expect(page.getByText("e2e-intrek")).not.toBeVisible();
});

test("beheer-pagina heeft navigatielink naar api-tokens", async ({ page }) => {
  await page.goto("/beheer");
  const link = page.getByRole("link", { name: /API-tokens/ });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL("/beheer/api-tokens");
});
