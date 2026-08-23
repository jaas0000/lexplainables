import { test, expect } from "@playwright/test";
import { login, resetBerichten } from "./_helpers";

// Vereist (frontend-bouwen regel 6b): de Next.js-server én de API draaien al vóórdat deze
// test start — dit bestand start ze niet zelf (geen `webServer` in playwright.config.ts).
// Elke test ruimt eerst alle berichten op via de admin-API, zodat de UI in een bekende
// beginstaat begint (geen residu van vorige runs of tests).
//
// UI-topologie: berichten-beheer zit op de "Berichten"-tab van het instellingenvenster
// (/instellingen/beheer/berichten, werkwijze-story 042 — voorheen inline op /beheer). De
// interactie is: klik "Nieuw bericht" → vul formulier (Titel, Inhoud) → "Opslaan" → open
// de lijst via "Toon berichten". Berichten renderen als expandable cards (geen tabelrijen);
// per bericht is er een toggle-knop bovenaan die de acties (Bewerken, Publiceren, Verwijderen)
// ontvouwt.

test.beforeEach(async ({ page, context, request }) => {
  await resetBerichten(request);
  await login(page, context);
});

test("beheerder maakt een bericht aan en publiceert het, zonder page-reload", async ({
  page,
}) => {
  const titel = `E2E bericht ${Date.now()}`;

  await page.goto("/instellingen/beheer/berichten");

  await page.getByRole("button", { name: "Nieuw bericht" }).click();
  await page.getByLabel("Titel").fill(titel);
  await page
    .getByLabel("Inhoud")
    .fill("Inhoud voor de e2e-test van het gelukkige pad.");
  await page.getByRole("button", { name: "Opslaan" }).click();

  // Na opslaan wordt de lijst automatisch getoond; het bericht verschijnt als card.
  const card = page.locator(".card", { hasText: titel });
  await expect(card).toBeVisible();
  await expect(card).toContainText("Concept");

  // Klap de card open zodat de acties zichtbaar worden.
  await card.getByRole("button", { name: new RegExp(titel, "i") }).click();
  await card.getByRole("button", { name: "Publiceren" }).click();
  await expect(card).toContainText("Gepubliceerd");
});

test("verwijderen van een al verwijderd bericht toont een zichtbare foutmelding", async ({
  page,
  context,
}) => {
  const titel = `E2E fout-bericht ${Date.now()}`;

  await page.goto("/instellingen/beheer/berichten");
  await page.getByRole("button", { name: "Nieuw bericht" }).click();
  await page.getByLabel("Titel").fill(titel);
  await page
    .getByLabel("Inhoud")
    .fill("Wordt via twee tabbladen dubbel verwijderd.");
  await page.getByRole("button", { name: "Opslaan" }).click();

  const card = page.locator(".card", { hasText: titel });
  await expect(card).toBeVisible();

  // Tweede tabblad, zelfde browsercontext — sessiecookie wordt gedeeld.
  const page2 = await context.newPage();
  await page2.goto("/instellingen/beheer/berichten");
  await page2.getByRole("button", { name: "Toon berichten" }).click();
  const card2 = page2.locator(".card", { hasText: titel });
  await expect(card2).toBeVisible();

  // Klap beide cards uit om de Verwijderen-knop te ontsluiten.
  await card.getByRole("button", { name: new RegExp(titel, "i") }).click();
  await card2.getByRole("button", { name: new RegExp(titel, "i") }).click();

  await card.getByRole("button", { name: "Verwijderen" }).click();
  await expect(card).toHaveCount(0);

  await card2.getByRole("button", { name: "Verwijderen" }).click();
  // Foutmelding — scoped naar de <p role="alert"> in de fout-melding-doos (Next's
  // eigen `__next-route-announcer__` heeft ook `role="alert"`).
  await expect(page2.locator('p[role="alert"]')).toBeVisible();
});
