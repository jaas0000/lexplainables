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

test("llm-calls-pagina laadt en toont het invoerveld", async ({ page }) => {
  await page.goto("/beheer/llm-calls");
  await expect(
    page.getByRole("heading", { name: "LLM-calls log" }),
  ).toBeVisible();
  await expect(page.getByLabel("Analyse-id (UUID)")).toBeVisible();
  await expect(page.getByRole("button", { name: "Toon calls" })).toBeVisible();
});

test("onbekend analyse-id toont lege-lijst-melding", async ({ page }) => {
  await page.goto("/beheer/llm-calls");
  const input = page.getByLabel("Analyse-id (UUID)");
  await input.fill("00000000-0000-0000-0000-000000000000");
  await page.getByRole("button", { name: "Toon calls" }).click();
  await expect(
    page.getByText("Geen LLM-calls gevonden voor dit analyse-id"),
  ).toBeVisible();
});

test("beheer-pagina heeft navigatielink naar llm-calls", async ({ page }) => {
  await page.goto("/beheer");
  const link = page.getByRole("link", { name: /LLM-calls/ });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL("/beheer/llm-calls");
});
