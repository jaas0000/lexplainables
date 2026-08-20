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

test("gebruiker opent feedbackformulier, vult tekst in en ziet succesbericht", async ({
  page,
}) => {
  await page.goto("/");

  // Feedbackknop moet zichtbaar zijn rechtsonder.
  const knop = page.getByRole("button", { name: "Feedback geven" });
  await expect(knop).toBeVisible();

  // Paneel opent na klikken.
  await knop.click();
  await expect(page.getByText("Geef feedback")).toBeVisible();

  // Vul tekst in en verzend.
  await page
    .getByLabel("Uw opmerking")
    .fill("E2E-test feedback via Playwright");
  await page.getByRole("button", { name: "Verzenden" }).click();

  // Succesbericht verschijnt zonder page-reload.
  await expect(page.getByText("Bedankt voor uw feedback!")).toBeVisible();
});

test("beheerder verwijdert al verwijderd feedbackitem en ziet zichtbare foutmelding", async ({
  page,
  context,
}) => {
  // Zorg dat er een feedbackitem bestaat om te verwijderen.
  // Maak het aan via de feedbackknop op de hoofdpagina.
  await page.goto("/");
  const knop = page.getByRole("button", { name: "Feedback geven" });
  await knop.click();
  await page.getByLabel("Uw opmerking").fill("E2E dubbel-verwijder test item");
  await page.getByRole("button", { name: "Verzenden" }).click();
  await expect(page.getByText("Bedankt voor uw feedback!")).toBeVisible();

  // Ga naar de feedbackpagina.
  await page.goto("/beheer/feedback");
  const eersteVerwijderKnop = page
    .getByRole("button", { name: "Verwijderen" })
    .first();
  await expect(eersteVerwijderKnop).toBeVisible();

  // Tweede tabblad, zelfde sessie — verwijdert hetzelfde item.
  const page2 = await context.newPage();
  await page2.goto("/beheer/feedback");
  const eersteVerwijderKnop2 = page2
    .getByRole("button", { name: "Verwijderen" })
    .first();
  await expect(eersteVerwijderKnop2).toBeVisible();

  // Eerste tab verwijdert.
  await eersteVerwijderKnop.click();
  await expect(eersteVerwijderKnop).toHaveCount(0);

  // Tweede tab probeert hetzelfde item te verwijderen → foutmelding.
  await eersteVerwijderKnop2.click();
  await expect(page2.locator('p[role="alert"]')).toBeVisible();
});
