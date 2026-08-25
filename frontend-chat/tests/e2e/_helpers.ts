// Gedeelde helper voor e2e-tests — zelfde seed-gebruiker als frontend/tests/e2e/_helpers.ts
// (beide frontends praten met dezelfde `api`-service in dev/CI).

import type { Page } from "@playwright/test";

const SEED_GEBRUIKER = "beheerder";
const SEED_WACHTWOORD = "beheerder123";

export async function login(
  page: Page,
  gebruikersnaam: string = SEED_GEBRUIKER,
  wachtwoord: string = SEED_WACHTWOORD,
) {
  await page.goto("/login");
  await page.getByLabel("Gebruikersnaam").fill(gebruikersnaam);
  await page.getByLabel("Wachtwoord").fill(wachtwoord);
  await page.getByRole("button", { name: "Inloggen" }).click();
  await page.waitForURL("/");
}
