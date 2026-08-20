import { test, expect } from "@playwright/test";
import { login } from "./_helpers";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.
//
// De "aanmaken + klaar via SSE"-test mockt de POST /api/projecten en de SSE-events
// via `page.route()`. De echte orkestratie in de FastAPI heeft een draaiende
// Wettenbank-MCP + LLM nodig (zie api/app/shared/wettenbank.py). Die dependencies zijn
// er in de e2e-run niet — dus zonder mocken faalt de analyse altijd met "wettekst niet
// ophaalbaar" en bereikt hij status "klaar" nooit. De mocks houden de UI-flow zuiver:
// formulier invullen, navigatie naar detailpagina, en de SSE→UI-render van status "klaar".

const MOCK_ID = "11111111-1111-4111-8111-111111111111";
const MOCK_DETAIL = {
  id: MOCK_ID,
  naam: "BWBR0011823 art. 9",
  bronnen: [{ bwb_id: "BWBR0011823", artikel: "9", lid: null }],
  status: "klaar",
  bijgewerkt: new Date().toISOString(),
  omschrijving: null,
  analysefocus: null,
  model_profiel: null,
  human_in_the_loop: false,
  begrippenlijst: null,
  huidige_fase: null,
  foutmelding: null,
  rapport: null,
};

test.beforeEach(async ({ page, context }) => {
  await login(page, context);
});

test("gebruiker maakt een analyse aan en ziet de status live bijwerken naar klaar", async ({
  page,
}) => {
  // Mock: aanmaken retourneert onze vaste id; detail-fetch en SSE geven direct "klaar".
  await page.route("**/api/projecten", (route) => {
    if (route.request().method() === "POST") {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: MOCK_ID }),
      });
    } else {
      void route.continue();
    }
  });
  await page.route(`**/api/projecten/${MOCK_ID}`, (route) => {
    if (route.request().method() === "GET") {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_DETAIL),
      });
    } else {
      void route.continue();
    }
  });
  await page.route(`**/api/projecten/${MOCK_ID}/events`, (route) => {
    void route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      headers: { "Cache-Control": "no-cache", Connection: "keep-alive" },
      body: `data: ${JSON.stringify({ status: "klaar", huidige_fase: null, foutmelding: null })}\n\n`,
    });
  });

  await page.goto("/projecten/nieuw");
  await expect(
    page.getByRole("heading", { name: "Nieuwe analyse" }),
  ).toBeVisible();

  await page.getByPlaceholder("BWBR0011823").fill("BWBR0011823");
  // Twee "combobox"-elementen op de pagina (artikel-input met role=combobox én een
  // rapport-<select>) — scope op de placeholder "9" om exact de artikel-input te raken.
  await page.getByPlaceholder("9").fill("9");

  const reviewCheckbox = page.getByLabel("Human-in-the-loop review");
  if (await reviewCheckbox.isChecked()) {
    await reviewCheckbox.uncheck();
  }

  await page.getByRole("button", { name: "Analyse starten" }).click();
  await page.waitForURL(/\/projecten\/[0-9a-f-]{36}/);
  await expect(page.getByRole("heading", { level: 2 })).toBeVisible();
  await expect(page.getByText("Klaar")).toBeVisible({ timeout: 15_000 });
  await expect(
    page.getByText("De analyse is succesvol afgerond."),
  ).toBeVisible();
});

test("gebruiker probeert analyse aan te maken zonder bronartikel en ziet validatiefout", async ({
  page,
}) => {
  await page.goto("/projecten/nieuw");
  await page.getByRole("button", { name: "Analyse starten" }).click();
  await expect(
    page.getByText(
      "Voeg minimaal 1 bronartikel toe (wet-id + artikel verplicht).",
    ),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/projecten\/nieuw/);
});
