import { test, expect } from "@playwright/test";
import { login, resetFeedback } from "./_helpers";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.
// Elke test ruimt eerst alle feedbackitems op via de admin-API, zodat er geen residu
// uit vorige tests achterblijft (de foutpad-test scoped op unieke tekst).

test.beforeEach(async ({ page, context, request }) => {
  await resetFeedback(request);
  await login(page, context);
});

test("gebruiker opent feedbackformulier, vult tekst in en ziet succesbericht", async ({
  page,
}) => {
  await page.goto("/");

  // "Feedback geven" zit sinds story 043 in het uitklapmenu (net als de referentie-app), niet meer
  // als losse zwevende knop.
  await page.getByRole("button", { name: "Gebruikersmenu" }).click();
  const knop = page.getByRole("button", { name: "Feedback geven" });
  await expect(knop).toBeVisible();

  // Venster opent na klikken.
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
  // Zorg dat er precies één feedbackitem is met unieke tekst — dan kunnen we het item
  // scopen op tekst (i.p.v. op `.first()`, dat door residu of parallelle items faalt).
  const tekst = `E2E dubbel-verwijder ${Date.now()}`;

  await page.goto("/");
  await page.getByRole("button", { name: "Gebruikersmenu" }).click();
  await page.getByRole("button", { name: "Feedback geven" }).click();
  await page.getByLabel("Uw opmerking").fill(tekst);
  await page.getByRole("button", { name: "Verzenden" }).click();
  await expect(page.getByText("Bedankt voor uw feedback!")).toBeVisible();

  // Ga naar de feedbackpagina en scope op de container met de unieke tekst.
  await page.goto("/beheer/feedback");
  const item = page
    .locator("div", { hasText: tekst })
    .filter({ has: page.getByRole("button", { name: "Verwijderen" }) })
    .first();
  const verwijderKnop = item.getByRole("button", { name: "Verwijderen" });
  await expect(verwijderKnop).toBeVisible();

  // Tweede tabblad, zelfde sessie — verwijdert hetzelfde item.
  const page2 = await context.newPage();
  await page2.goto("/beheer/feedback");
  const item2 = page2
    .locator("div", { hasText: tekst })
    .filter({ has: page2.getByRole("button", { name: "Verwijderen" }) })
    .first();
  const verwijderKnop2 = item2.getByRole("button", { name: "Verwijderen" });
  await expect(verwijderKnop2).toBeVisible();

  // Eerste tab verwijdert.
  await verwijderKnop.click();
  await expect(item).toHaveCount(0);

  // Tweede tab probeert hetzelfde item te verwijderen → foutmelding.
  await verwijderKnop2.click();
  await expect(page2.locator('p[role="alert"]')).toBeVisible();
});
