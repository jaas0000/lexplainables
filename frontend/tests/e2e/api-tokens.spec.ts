import { test, expect } from "@playwright/test";
import { login, resetApiTokens } from "./_helpers";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.
// `resetApiTokens` in beforeEach verwijdert alle bestaande tokens, en elke test gebruikt
// een uniek label — anders zou `getByText(label)` op strict-mode-conflict lopen door residu.

test.beforeEach(async ({ page, context, request }) => {
  await resetApiTokens(request);
  await login(page, context);
});

test("api-tokens-pagina laadt met heading en aanmaakformulier", async ({
  page,
}) => {
  await page.goto("/beheer/api-tokens");
  await expect(page.getByRole("heading", { name: "API-tokens" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Nieuw token aanmaken" }),
  ).toBeVisible();
});

test("nieuw token aanmaken toont eenmalige token-modal", async ({ page }) => {
  const label = `e2e-test-${Date.now()}`;
  await page.goto("/beheer/api-tokens");
  await page.getByLabel("Label").fill(label);
  await page.getByRole("button", { name: "Nieuw token aanmaken" }).click();

  // Modal moet verschijnen met het eenmalige token.
  await expect(
    page.getByRole("dialog", { name: "Nieuw API-token" }),
  ).toBeVisible();
  await expect(
    page.getByText("Sla dit token op — het is maar één keer zichtbaar"),
  ).toBeVisible();

  // Modal sluiten.
  await page
    .getByRole("button", { name: "Ik heb het token opgeslagen" })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();

  // Nieuw token staat in de lijst — scoped op de unieke label.
  await expect(page.getByText(label)).toBeVisible();
});

test("token intrekken verwijdert het uit de lijst", async ({ page }) => {
  const label = `e2e-intrek-${Date.now()}`;
  await page.goto("/beheer/api-tokens");

  // Maak een token aan om in te trekken.
  await page.getByLabel("Label").fill(label);
  await page.getByRole("button", { name: "Nieuw token aanmaken" }).click();
  await page
    .getByRole("button", { name: "Ik heb het token opgeslagen" })
    .click();

  // Intrekken.
  const rij = page.getByRole("row").filter({ hasText: label });
  await rij.getByRole("button", { name: "Intrekken" }).click();

  // Token verdwenen uit de lijst.
  await expect(page.getByText(label)).not.toBeVisible();
});
