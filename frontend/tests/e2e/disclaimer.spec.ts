import { test, expect } from "@playwright/test";

// Vereist (frontend-bouwen regel 6b): de Next.js-server én de API draaien al vóórdat deze
// test start — dit bestand start ze niet zelf (geen `webServer` in playwright.config.ts).

test("gelukkig pad: inloggen zonder disclaimer-cookie leidt naar /disclaimer, daarna door naar /", async ({
  page,
  context,
}) => {
  // Zorg dat er géén disclaimer-cookie is
  await context.clearCookies();

  await page.goto("/login");
  await page.getByLabel("Gebruikersnaam").fill("beheerder");
  await page.getByLabel("Wachtwoord").fill("beheerder123");
  await page.getByRole("button", { name: "Inloggen" }).click();

  // Na inloggen: verwacht redirect naar /disclaimer
  await page.waitForURL(/\/disclaimer/);
  await expect(page).toHaveURL(/\/disclaimer/);

  // Klik "Begrepen — doorgaan"
  await page.getByRole("button", { name: "Begrepen — doorgaan" }).click();

  // Verwacht redirect naar startpagina
  await page.waitForURL("/");
  await expect(page).toHaveURL("/");
});

test("foutpad: /disclaimer met cookie toont terug-link, geen accepteerknop", async ({
  page,
  context,
}) => {
  // Disclaimer al geaccepteerd
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

  // Navigeer direct naar /disclaimer
  await page.goto("/disclaimer");

  // "Terug naar de startpagina"-link zichtbaar, geen accepteerknop
  await expect(
    page.getByRole("link", { name: "Terug naar de startpagina" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Begrepen — doorgaan" }),
  ).not.toBeVisible();
});
