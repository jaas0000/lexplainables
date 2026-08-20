import { test, expect } from "@playwright/test";
import { apiGet, apiPost, login, resetProfielen } from "./_helpers";

// Vereist (frontend-bouwen regel 6b): de Next.js-server én de API draaien al vóórdat deze
// test start — dit bestand start ze niet zelf (geen `webServer` in playwright.config.ts).
// Elke test ruimt eerst alle profielen op via de admin-API en gebruikt daarna unieke
// profielnamen, zodat de foutpad-tests (enige profiel, naam-conflict) deterministisch zijn.
// De API weigert het laatste profiel te verwijderen (EnigeProfielFout), dus na
// `resetProfielen` blijven er 0 of 1 profielen over — de "enige profiel"-test vult naar 1
// aan wanneer nodig.

test.beforeEach(async ({ page, context, request }) => {
  await resetProfielen(request);
  await login(page, context);
});

test("gelukkig pad: profiel aanmaken, standaard instellen en verwijderen", async ({
  page,
}) => {
  const naam = `e2e-profiel-${Date.now()}`;
  const naam2 = `e2e-profiel-b-${Date.now()}`;

  await page.goto("/beheer/llm-profielen");

  // Wacht tot de pagina geladen is (geen laad-indicator meer).
  await expect(
    page.getByRole("heading", { name: "LLM-profielen" }),
  ).toBeVisible();

  // Maak eerste profiel aan.
  await page.getByLabel("Naam *").fill(naam);
  await page.getByLabel("Model *").fill("gpt-4o");
  await page.getByLabel("API base URL *").fill("https://api.openai.com/v1");
  await page.getByRole("button", { name: "Aanmaken" }).click();

  // Profiel verschijnt in de tabel.
  const rij = page.locator("tbody tr", { hasText: naam });
  await expect(rij).toBeVisible();

  // Maak tweede profiel aan zodat we het eerste kunnen verwijderen.
  await page.getByLabel("Naam *").fill(naam2);
  await page.getByLabel("Model *").fill("gpt-4o-mini");
  await page.getByLabel("API base URL *").fill("https://api.openai.com/v1");
  await page.getByRole("button", { name: "Aanmaken" }).click();

  const rij2 = page.locator("tbody tr", { hasText: naam2 });
  await expect(rij2).toBeVisible();

  // Eerste profiel als standaard instellen via bewerk-formulier.
  await rij.getByRole("button", { name: "Bewerk" }).click();
  await page.getByLabel("Instellen als standaard-profiel").first().check();
  await page.getByRole("button", { name: "Opslaan" }).click();

  // Standaard-badge verschijnt in de tabel.
  await expect(rij.getByText("standaard")).toBeVisible();

  // Verwijder tweede profiel (er zijn nu 2, dus dit is toegestaan).
  await rij2.getByRole("button", { name: "Verwijder" }).click();

  // Tweede profiel verdwijnt zonder page-reload.
  await expect(rij2).not.toBeVisible();
  await expect(rij).toBeVisible();
});

test("foutpad: naam-conflict bij aanmaken toont zichtbare foutmelding", async ({
  page,
}) => {
  const naam = `e2e-conflict-${Date.now()}`;

  await page.goto("/beheer/llm-profielen");
  await expect(
    page.getByRole("heading", { name: "LLM-profielen" }),
  ).toBeVisible();

  // Maak het profiel de eerste keer aan.
  await page.getByLabel("Naam *").fill(naam);
  await page.getByLabel("Model *").fill("gpt-4o");
  await page.getByLabel("API base URL *").fill("https://api.openai.com/v1");
  await page.getByRole("button", { name: "Aanmaken" }).click();

  const rij = page.locator("tbody tr", { hasText: naam });
  await expect(rij).toBeVisible();

  // Tweede aanmaakpoging met dezelfde naam → 409 → foutmelding.
  await page.getByLabel("Naam *").fill(naam);
  await page.getByLabel("Model *").fill("gpt-4o");
  await page.getByLabel("API base URL *").fill("https://api.openai.com/v1");
  await page.getByRole("button", { name: "Aanmaken" }).click();

  const alert = page.locator('p[role="alert"]');
  await expect(alert).toBeVisible();
  await expect(alert).toContainText(/bestaat al|conflict/i);
});

test("foutpad: verwijderen van het enige profiel toont zichtbare foutmelding", async ({
  page,
  request,
}) => {
  // Zorg dat er precies één profiel is. `resetProfielen` verwijdert alles op één na
  // (of laat de tabel leeg bij een verse DB); vul aan tot exact 1 waar nodig.
  const bestaand = (await apiGet(request, "/v1/admin/profielen")) as unknown[];
  if (bestaand.length === 0) {
    await apiPost(request, "/v1/admin/profielen", {
      naam: `e2e-enige-${Date.now()}`,
      provider: "openai",
      model: "gpt-4o",
      api_base: "https://api.openai.com/v1",
      is_standaard: false,
    });
  }

  await page.goto("/beheer/llm-profielen");
  await expect(
    page.getByRole("heading", { name: "LLM-profielen" }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(1);

  await page
    .locator("tbody tr")
    .first()
    .getByRole("button", { name: "Verwijder" })
    .click();

  // Foutmelding moet zichtbaar worden.
  const alert = page.locator('p[role="alert"]');
  await expect(alert).toBeVisible();
  await expect(alert).toContainText(/enige profiel|kan niet/i);
});
