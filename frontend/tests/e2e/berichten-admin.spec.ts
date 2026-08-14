import { test, expect } from "@playwright/test";

// Vereist (frontend-bouwen regel 6b): de Next.js-server én de API draaien al vóórdat deze
// test start — dit bestand start ze niet zelf (geen `webServer` in playwright.config.ts).
// Elke test gebruikt een eigen, unieke titel, zodat tests onafhankelijk van elkaar (en van
// eerder achtergebleven testdata) blijven werken.

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

test("beheerder maakt een bericht aan en publiceert het, zonder page-reload", async ({
  page,
}) => {
  const titel = `E2E bericht ${Date.now()}`;

  await page.goto("/");

  await page.getByLabel("Titel").fill(titel);
  await page
    .getByLabel("Inhoud")
    .fill("Inhoud voor de e2e-test van het gelukkige pad.");
  await page.getByRole("button", { name: "Aanmaken" }).click();

  const rij = page.locator("tbody tr", { hasText: titel });
  await expect(rij).toBeVisible();
  await expect(rij).toContainText("concept");

  await rij.getByRole("button", { name: "Publiceren" }).click();
  await expect(rij).toContainText("gepubliceerd");
});

test("verwijderen van een al verwijderd bericht toont een zichtbare foutmelding", async ({
  page,
  context,
}) => {
  const titel = `E2E fout-bericht ${Date.now()}`;

  await page.goto("/");
  await page.getByLabel("Titel").fill(titel);
  await page
    .getByLabel("Inhoud")
    .fill("Wordt via twee tabbladen dubbel verwijderd.");
  await page.getByRole("button", { name: "Aanmaken" }).click();

  const rij = page.locator("tbody tr", { hasText: titel });
  await expect(rij).toBeVisible();

  // Tweede tabblad, zelfde browsercontext — sessiecookie wordt gedeeld.
  const page2 = await context.newPage();
  await page2.goto("/");
  const rij2 = page2.locator("tbody tr", { hasText: titel });
  await expect(rij2).toBeVisible();

  await rij.getByRole("button", { name: "Verwijderen" }).click();
  await expect(rij).toHaveCount(0);

  await rij2.getByRole("button", { name: "Verwijderen" }).click();
  await expect(page2.locator('p[role="alert"]')).toBeVisible();
});
