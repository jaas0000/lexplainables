import { test, expect } from "@playwright/test";

// Vereist: de Next.js-server én de API draaien vóórdat deze test start.
// Elke test gebruikt unieke gebruikersnamen zodat tests onafhankelijk blijven.

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

test("gelukkig pad: gebruiker aanmaken, rol wijzigen en wachtwoord resetten", async ({
  page,
}) => {
  const naam = `e2e-gebruiker-${Date.now()}`;

  await page.goto("/beheer/gebruikers");
  await expect(
    page.getByRole("heading", { name: "Gebruikersbeheer" }),
  ).toBeVisible();

  // Gebruiker aanmaken.
  await page.getByLabel("Gebruikersnaam").fill(naam);
  await page.getByLabel("Wachtwoord").fill("testWachtwoord123");
  // Rol staat standaard op 'analist' — laat staan.
  await page.getByRole("button", { name: "Gebruiker toevoegen" }).click();

  // Nieuwe gebruiker verschijnt in de lijst.
  const rij = page.locator(".card", { hasText: naam });
  await expect(rij).toBeVisible();
  await expect(rij.locator("text=analist")).toBeVisible();

  // Rol wijzigen naar beheerder.
  await rij.getByRole("button", { name: "Maak beheerder" }).click();
  await expect(rij.locator("text=beheerder")).toBeVisible();

  // Wachtwoord resetten.
  await rij.getByRole("button", { name: "Wachtwoord resetten" }).click();

  // Tijdelijk wachtwoord melding verschijnt.
  await expect(
    page.getByText("Tijdelijk wachtwoord — noteer dit nu"),
  ).toBeVisible();
  await expect(page.getByText(naam)).toBeVisible();

  // Sluiten.
  await page.getByRole("button", { name: "Sluiten" }).click();
  await expect(
    page.getByText("Tijdelijk wachtwoord — noteer dit nu"),
  ).not.toBeVisible();

  // Opruimen: gebruiker verwijderen.
  page.on("dialog", (dialog) => dialog.accept());
  await rij.getByRole("button", { name: "Verwijderen" }).click();
  await expect(rij).not.toBeVisible();
});

test("foutpad: laatste beheerder verwijderen geeft 409-melding", async ({
  page,
}) => {
  await page.goto("/beheer/gebruikers");
  await expect(
    page.getByRole("heading", { name: "Gebruikersbeheer" }),
  ).toBeVisible();

  // Probeer de 'beheerder'-gebruiker te verwijderen (is de enige beheerder in een verse testomgeving).
  page.on("dialog", (dialog) => dialog.accept());
  const rij = page.locator(".card", { hasText: "beheerder" }).first();
  await rij.getByRole("button", { name: "Verwijderen" }).click();

  // Foutmelding verschijnt.
  await expect(
    page.getByText("Kan de laatste actieve beheerder niet verwijderen."),
  ).toBeVisible();
});
