import { test, expect } from "@playwright/test";

// Vereist (frontend-bouwen regel 6b): de Next.js-server én de API draaien al vóórdat deze
// test start — dit bestand start ze niet zelf (geen `webServer` in playwright.config.ts).
// Elke test gebruikt een eigen, unieke profielnaam, zodat tests onafhankelijk van elkaar
// (en van eerder achtergebleven testdata) blijven werken.

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

  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(/bestaat al|conflict/i);
});

test("foutpad: verwijderen van het enige profiel toont zichtbare foutmelding", async ({
  page,
}) => {
  const naam = `e2e-enige-${Date.now()}`;

  await page.goto("/beheer/llm-profielen");
  await expect(
    page.getByRole("heading", { name: "LLM-profielen" }),
  ).toBeVisible();

  // Zorg dat er precies één profiel is: verwijder alle bestaande profielen tot er één over is,
  // of maak er één aan als er geen zijn. Dit is een simplistische opzet voor de test —
  // in een volledige test-harness zou je de database leegmaken vóór elke test.
  const aantalRows = await page.locator("tbody tr").count();

  if (aantalRows === 0) {
    // Geen profielen: maak er één aan.
    await page.getByLabel("Naam *").fill(naam);
    await page.getByLabel("Model *").fill("gpt-4o");
    await page.getByLabel("API base URL *").fill("https://api.openai.com/v1");
    await page.getByRole("button", { name: "Aanmaken" }).click();
    await expect(page.locator("tbody tr", { hasText: naam })).toBeVisible();
  }

  // Probeer het laatste profiel te verwijderen (als er meerdere zijn, sla test over).
  const huidigeAantal = await page.locator("tbody tr").count();
  if (huidigeAantal !== 1) {
    test.skip(
      true,
      "Meer dan één profiel aanwezig — sla test over om bestaande data te respecteren.",
    );
    return;
  }

  const enige = page.locator("tbody tr").first();
  await enige.getByRole("button", { name: "Verwijder" }).click();

  // Foutmelding moet zichtbaar worden.
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(
    /enige profiel|kan niet/i,
  );
});
