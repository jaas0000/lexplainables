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

test("instellingen-pagina laadt en toont de LLM-capture schakelaar", async ({
  page,
}) => {
  await page.goto("/beheer/instellingen");
  await expect(
    page.getByRole("heading", { name: "Instellingen" }),
  ).toBeVisible();
  await expect(page.getByText("Vastleggen van LLM-calls")).toBeVisible();
  // De knop "Aanzetten" of "Uitzetten" is zichtbaar.
  const knop = page.getByRole("button", { name: /Aanzetten|Uitzetten/ });
  await expect(knop).toBeVisible();
});

test("beheerder kan capture aanzetten en daarna uitzetten", async ({
  page,
}) => {
  await page.goto("/beheer/instellingen");

  // Zorg dat de status "uit" is — druk eventueel op Uitzetten eerst.
  const uitzetten = page.getByRole("button", { name: "Uitzetten" });
  if (await uitzetten.isVisible()) {
    await uitzetten.click();
    await expect(page.getByRole("button", { name: "Aanzetten" })).toBeVisible();
  }

  // Zet aan.
  await page.getByRole("button", { name: "Aanzetten" }).click();
  await expect(page.getByRole("button", { name: "Uitzetten" })).toBeVisible();
  await expect(page.getByText("aan")).toBeVisible();

  // Zet uit.
  await page.getByRole("button", { name: "Uitzetten" }).click();
  await expect(page.getByRole("button", { name: "Aanzetten" })).toBeVisible();
  await expect(page.getByText("uit")).toBeVisible();
});

test("beheer-pagina heeft navigatieknop naar instellingen", async ({
  page,
}) => {
  await page.goto("/beheer");
  const link = page.getByRole("link", { name: /Instellingen/ });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL("/beheer/instellingen");
});
