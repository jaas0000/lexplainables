import { test, expect } from "@playwright/test";
import { API_BASE_URL, API_TOKEN, login } from "./_helpers";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.
// De toggle-test forceert capture=false via de admin-API vóór de UI-interactie, zodat
// de startstaat deterministisch is (i.p.v. afhankelijk van residu van eerdere runs).

test.beforeEach(async ({ page, context, request }) => {
  await request.put(`${API_BASE_URL}/v1/admin/instellingen`, {
    headers: {
      Authorization: `Bearer ${API_TOKEN}`,
      "X-User-Id": "beheerder",
      "Content-Type": "application/json",
    },
    data: JSON.stringify({ capture_llm_calls: false }),
  });
  await login(page, context);
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

  // De aan/uit-tag zit direct naast de aan/uit-knop — scope via de knop's voorafgaande
  // sibling om conflicten met andere "aan"/"uit"-teksten op de pagina te vermijden.
  const knop = page.getByRole("button", { name: /Aanzetten|Uitzetten/ });
  const tag = knop.locator("xpath=preceding-sibling::span");

  // Wacht tot de initiële status geladen is (knop wordt enabled na fetch).
  await expect(knop).toBeEnabled();
  // beforeEach zette capture=false → startstaat is "Aanzetten"/"uit".
  await expect(page.getByRole("button", { name: "Aanzetten" })).toBeVisible();

  // Zet aan.
  await page.getByRole("button", { name: "Aanzetten" }).click();
  await expect(page.getByRole("button", { name: "Uitzetten" })).toBeVisible();
  await expect(tag).toHaveText("aan");

  // Zet uit.
  await page.getByRole("button", { name: "Uitzetten" }).click();
  await expect(page.getByRole("button", { name: "Aanzetten" })).toBeVisible();
  await expect(tag).toHaveText("uit");
});

test("beheer-pagina heeft navigatieknop naar instellingen", async ({
  page,
}) => {
  await page.goto("/beheer");
  // Case-insensitive: de link heet "Beheer instellingen →" (kleine letter i).
  const link = page.getByRole("link", { name: /instellingen/i });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL("/beheer/instellingen");
});
