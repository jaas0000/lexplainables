import { test, expect } from "@playwright/test";
import { login } from "./_helpers";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.
//
// De aanmaken-flow mockt POST /api/projecten en de detail-fetch, zodat de UI-flow zuiver
// getest wordt: formulier invullen → navigatie naar detailpagina → detail toont naam +
// bronnen + link naar werkplek. De echte API kan een werkgebied prima aanmaken (geen
// externe dependency zoals wettenbank-MCP nodig sinds de JAS-pipeline is verwijderd), maar
// dan wordt de aangemaakte rij niet vanzelf schoongemaakt — mocken is dus alsnog cleaner.

const MOCK_ID = "11111111-1111-4111-8111-111111111111";
const MOCK_DETAIL = {
  id: MOCK_ID,
  naam: "BWBR0011823 art. 9",
  bronnen: [{ bwb_id: "BWBR0011823", artikel: "9", lid: null }],
  status: "nieuw",
  bijgewerkt: new Date().toISOString(),
  omschrijving: null,
};

test.beforeEach(async ({ page, context }) => {
  await login(page, context);
});

test("gebruiker maakt een werkgebied aan en komt op de detailpagina", async ({
  page,
}) => {
  await page.route("**/api/projecten", (route) => {
    if (route.request().method() === "POST") {
      void route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ id: MOCK_ID, status: "nieuw" }),
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

  await page.goto("/projecten/nieuw");
  await expect(
    page.getByRole("heading", { name: "Nieuw werkgebied" }),
  ).toBeVisible();

  await page.getByPlaceholder("BWBR0011823").fill("BWBR0011823");
  await page.getByPlaceholder("9").fill("9");

  await page.getByRole("button", { name: "Werkgebied aanmaken" }).click();
  await page.waitForURL(/\/projecten\/[0-9a-f-]{36}/);
  await expect(page.getByRole("heading", { level: 2 })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Naar werkplek →" }),
  ).toBeVisible();
});

test("gebruiker probeert werkgebied aan te maken zonder bronartikel en ziet validatiefout", async ({
  page,
}) => {
  await page.goto("/projecten/nieuw");
  await page.getByRole("button", { name: "Werkgebied aanmaken" }).click();
  await expect(
    page.getByText(
      "Voeg minimaal 1 bronartikel toe (wet-id + artikel verplicht).",
    ),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/projecten\/nieuw/);
});
