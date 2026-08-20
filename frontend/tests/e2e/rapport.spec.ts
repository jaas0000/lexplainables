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

test("rapport-pagina toont melding als analyse nog niet klaar is (409)", async ({
  page,
}) => {
  // Maak een nieuwe analyse aan (status wordt 'wachtrij').
  await page.goto("/projecten/nieuw");
  await page.getByPlaceholder("BWBR0011823").fill("BWBR0011823");
  // Twee "combobox"-elementen op de pagina (artikel-input met role=combobox én een
  // rapport-<select>) — scope op de placeholder "9" om exact de artikel-input te raken.
  await page.getByPlaceholder("9").fill("9");
  await page.getByRole("button", { name: "Analyse starten" }).click();
  await page.waitForURL(/\/projecten\/[0-9a-f-]{36}/);

  // Direct naar de rapport-pagina navigeren (analyse is nog niet 'klaar').
  const analyseUrl = page.url();
  const analyseId = analyseUrl.split("/projecten/")[1];
  await page.goto(`/projecten/${analyseId}/rapport`);

  // Rapport is nog niet beschikbaar → melding zichtbaar. Filter op tekst omdat Next's
  // eigen `__next-route-announcer__` ook `role="alert"` heeft (strict-mode-conflict).
  await expect(
    page.getByRole("alert").filter({ hasText: "Rapport nog niet beschikbaar" }),
  ).toBeVisible();

  // Teruglink naar de analyse-detailpagina aanwezig.
  await expect(
    page.getByRole("link", { name: /Terug naar analyse/ }),
  ).toBeVisible();
});

test("rapport-pagina navigeert terug naar projecten-lijst bij onbekend analyse-id (404)", async ({
  page,
}) => {
  await page.goto("/projecten/00000000-0000-0000-0000-000000000000/rapport");

  // Frontend navigeert door naar /projecten bij een 404.
  await page.waitForURL(/\/projecten$/);
  await expect(page).toHaveURL(/\/projecten$/);
});
