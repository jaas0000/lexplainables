import { test, expect } from "@playwright/test";

// Vereist (frontend-bouwen regel 6b): de Next.js-dev-server én de API draaien al vóórdat deze
// test start — dit bestand start ze niet zelf (geen `webServer` in playwright.config.ts).
// Elke test gebruikt een eigen, unieke beheerder-id en titel, zodat tests onafhankelijk van
// elkaar (en van eerder achtergebleven testdata) blijven werken.

test("beheerder maakt een bericht aan en publiceert het, zonder page-reload", async ({
  page,
}) => {
  const adminId = `e2e-${Date.now()}`;
  const titel = `E2E bericht ${Date.now()}`;

  await page.goto("/");
  await page.getByLabel("Beheerder-id").fill(adminId);

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
  const adminId = `e2e-fout-${Date.now()}`;
  const titel = `E2E fout-bericht ${Date.now()}`;

  await page.goto("/");
  await page.getByLabel("Beheerder-id").fill(adminId);
  await page.getByLabel("Titel").fill(titel);
  await page
    .getByLabel("Inhoud")
    .fill("Wordt via twee tabbladen dubbel verwijderd.");
  await page.getByRole("button", { name: "Aanmaken" }).click();

  const rij = page.locator("tbody tr", { hasText: titel });
  await expect(rij).toBeVisible();

  // Tweede tabblad, zelfde browsercontext (localStorage — dus de beheerder-id — wordt gedeeld):
  // toont dezelfde, nog niet ververste lijst met hetzelfde bericht.
  const page2 = await context.newPage();
  await page2.goto("/");
  const rij2 = page2.locator("tbody tr", { hasText: titel });
  await expect(rij2).toBeVisible();

  // Verwijder het bericht op het eerste tabblad — dat lukt.
  await rij.getByRole("button", { name: "Verwijderen" }).click();
  await expect(rij).toHaveCount(0);

  // Het tweede tabblad heeft de rij nog staan (geen refetch getriggerd); een verwijdering
  // daarvandaan botst op een 404 van de server. Die fout moet zichtbaar zijn, niet stil falen.
  // `p[role="alert"]` i.p.v. de generieke rol: Next.js zet zelf ook een (lege)
  // route-announcer met role="alert" in de DOM.
  await rij2.getByRole("button", { name: "Verwijderen" }).click();
  await expect(page2.locator('p[role="alert"]')).toBeVisible();
});
