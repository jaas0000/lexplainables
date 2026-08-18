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

test("gelukkig pad: wetten laden, wet kiezen, artikelen zien, artikel selecteren", async ({
  page,
}) => {
  await page.goto("/wetcatalogus");

  // Wettenlijst is geladen: de dropdown bevat keuzes.
  const wetDropdown = page.getByRole("combobox");
  await expect(wetDropdown).toBeVisible();

  // Kies "Wet werk en bijstand".
  await wetDropdown.selectOption({ label: "Wet werk en bijstand" });

  // Artikelen van die wet worden getoond.
  await expect(page.getByText("art. 1")).toBeVisible();
  await expect(page.getByText("art. 31")).toBeVisible();

  // Selecteer het eerste artikel via de checkbox.
  await page.getByRole("checkbox").first().check();

  // Teller toont "1 artikel geselecteerd".
  await expect(page.getByText("1 artikel geselecteerd")).toBeVisible();
});

test("foutpad: onbereikbare structuur-route geeft foutmelding in de UI", async ({
  page,
}) => {
  // Intercept de structuurroute voor een bekende wet zodat die 404 teruggeeft.
  await page.route("/api/wetten/BWBR0011823/structuur", (route) =>
    route.fulfill({
      status: 404,
      body: JSON.stringify({ detail: "Wet niet gevonden." }),
    }),
  );

  await page.goto("/wetcatalogus");

  // Kies "Wet werk en bijstand" — de intercepted route geeft nu 404.
  const wetDropdown = page.getByRole("combobox");
  await expect(wetDropdown).toBeVisible();
  await wetDropdown.selectOption({ label: "Wet werk en bijstand" });

  // WetSelector toont een foutmelding via role="alert".
  await expect(page.locator('[role="alert"]')).toBeVisible();
});
