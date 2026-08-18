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

test("gebruiker maakt een analyse aan en ziet de status live bijwerken naar klaar", async ({
  page,
}) => {
  // Ga naar het aanmaakformulier.
  await page.goto("/projecten/nieuw");
  await expect(
    page.getByRole("heading", { name: "Nieuwe analyse" }),
  ).toBeVisible();

  // Vul een bronartikel in (BWB-id + artikel).
  await page.getByPlaceholder("BWBR0011823").fill("BWBR0011823");
  await page.getByRole("combobox").fill("9");

  // Schakel human-in-the-loop uit zodat de analyse direct naar "klaar" gaat.
  const reviewCheckbox = page.getByLabel("Human-in-the-loop review");
  if (await reviewCheckbox.isChecked()) {
    await reviewCheckbox.uncheck();
  }

  // Verzend het formulier.
  await page.getByRole("button", { name: "Analyse starten" }).click();

  // De pagina navigeert naar de detail-pagina (URL bevat analyse-id).
  await page.waitForURL(/\/projecten\/[0-9a-f-]{36}/);

  // De naam van de analyse (afgeleid van de bron) is zichtbaar.
  await expect(page.getByRole("heading", { level: 2 })).toBeVisible();

  // Wacht op de "klaar"-status via SSE — de achtergrondtaak duurt ~4 seconden.
  await expect(page.getByText("Klaar")).toBeVisible({ timeout: 15_000 });

  // Succesbericht is zichtbaar zonder page-reload.
  await expect(
    page.getByText("De analyse is succesvol afgerond."),
  ).toBeVisible();
});

test("gebruiker probeert analyse aan te maken zonder bronartikel en ziet validatiefout", async ({
  page,
}) => {
  await page.goto("/projecten/nieuw");

  // Klik direct op verzenden zonder bronnen in te vullen.
  await page.getByRole("button", { name: "Analyse starten" }).click();

  // Validatiefout verschijnt — geen page-redirect.
  await expect(
    page.getByText(
      "Voeg minimaal 1 bronartikel toe (wet-id + artikel verplicht).",
    ),
  ).toBeVisible();

  // URL is ongewijzigd (geen navigatie naar detail-pagina).
  await expect(page).toHaveURL(/\/projecten\/nieuw/);
});
