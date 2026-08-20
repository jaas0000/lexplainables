import { test, expect } from "@playwright/test";
import { SEED_GEBRUIKER, login, resetGebruikers } from "./_helpers";

// Vereist: de Next.js-server én de API draaien vóórdat deze test start.
// Elke test gebruikt unieke gebruikersnamen zodat tests onafhankelijk blijven, en
// `resetGebruikers` verwijdert alle niet-seed gebruikers vooraf (om residu van eerder
// gefaalde tests op te ruimen — anders faalt de "laatste beheerder"-invariant-check).

test.beforeEach(async ({ page, context, request }) => {
  await resetGebruikers(request);
  await login(page, context);
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
  // De naam verschijnt zowel in de modal-paragraaf ("Voor <naam>") als in de card in de
  // achtergrond — `.first()` prikt op de modal-instantie zonder strict-mode-conflict.
  await expect(page.getByText(naam).first()).toBeVisible();

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

  // Na `resetGebruikers` is er nog maar één beheerder: de seed. Scope de card exact op
  // de seed-naam (i.p.v. substring "beheerder", dat óók een rol-tag matcht).
  page.on("dialog", (dialog) => dialog.accept());
  const rij = page
    .locator(".card")
    .filter({ has: page.getByText(SEED_GEBRUIKER, { exact: true }) })
    .first();
  await rij.getByRole("button", { name: "Verwijderen" }).click();

  // Foutmelding verschijnt.
  await expect(
    page.getByText("Kan de laatste actieve beheerder niet verwijderen."),
  ).toBeVisible();
});
