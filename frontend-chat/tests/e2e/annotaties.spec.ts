import { test, expect } from "@playwright/test";
import { login } from "./_helpers";

// Een echte graph-qa+GraphDB-keten (die annotatiedocumenten normaliter aanmaakt) is in CI niet
// beschikbaar — zelfde reden als chat.spec.ts. Deze spec mockt `api`'s annotatie-endpoints via
// `page.route()` en test frontend-chat's eigen code: het overzicht, het artefact-paneel, en de
// review-acties. Live tegen de echte stack geverifieerd bij het bouwen (screenshot van een
// werkende review-flow, inclusief tekstselectie → eigen markering, afronden/heropenen-slot, en
// een PDF-export-download).

const SLUG = "doc-1";

const SAMENVATTING = {
  slug: SLUG,
  bwb_id: "BWBR0004770",
  artikel: "1",
  lid: "",
  werkgebied: "sociaal",
  status: "voorgesteld",
  aantal_elementen: 1,
  bijgewerkt: "2026-08-26T10:00:00+00:00",
};

function maakDocument(status = "voorgesteld") {
  return {
    slug: SLUG,
    client_id: "beheerder",
    werkgebied: "sociaal",
    bwb_id: "BWBR0004770",
    artikel: "1",
    lid: "",
    status,
    elementen: [
      {
        id: "el-1",
        klasse: "Rechtssubject",
        tekst: "de belastingplichtige",
        lid: "1",
        toelichting: "Subject dat de plicht draagt.",
        vindplaats: "art. 1 lid 1",
        span: null,
        herkomst: "agent",
        levenscyclus: "voorgesteld",
        alternatieven: [],
        aandacht: "groen",
        critic: null,
        critic_rondes: [],
        beslissingen: [],
        diff: {},
      },
    ],
    laatste_run: null,
    aangemaakt: "2026-08-26T09:00:00+00:00",
    bijgewerkt: "2026-08-26T10:00:00+00:00",
  };
}

const WETSARTIKEL = {
  bwb_id: "BWBR0004770",
  artikel: "1",
  opschrift: null,
  tekst: "Iedere ingezetene is verplicht aangifte te doen.",
  onderdelen: [],
  leden: [
    {
      nummer: "1",
      tekst: "Iedere ingezetene is verplicht aangifte te doen.",
      onderdelen: [],
    },
  ],
};

test.describe("annotaties", () => {
  test("overzicht toont documenten en opent het artefact-paneel", async ({
    page,
  }) => {
    await login(page);

    await page.route("**/api/annotatie/documenten", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [SAMENVATTING] }),
      }),
    );
    await page.route(`**/api/annotatie/documenten/${SLUG}`, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(maakDocument()),
      }),
    );
    await page.route(
      `**/api/annotatie/documenten/${SLUG}/wetsartikel`,
      (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(WETSARTIKEL),
        }),
    );

    await page.getByRole("link", { name: "Annotaties" }).click();
    await expect(page).toHaveURL(/\/annotaties/);
    await expect(page.getByText("BWBR0004770 — art. 1")).toBeVisible();

    await page
      .locator("button.card")
      .filter({ hasText: "BWBR0004770" })
      .click();
    await expect(page.getByText("de belastingplichtige")).toBeVisible();
    await expect(page.getByText("Rechtssubject")).toBeVisible();
    await expect(page.getByText("Status: voorgesteld")).toBeVisible();
  });

  test("akkoord op een element en afronden vergrendelt het document", async ({
    page,
  }) => {
    await login(page);

    let huidigStatus = "voorgesteld";
    await page.route("**/api/annotatie/documenten", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [SAMENVATTING] }),
      }),
    );
    await page.route(`**/api/annotatie/documenten/${SLUG}`, (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(maakDocument(huidigStatus)),
      });
    });
    await page.route(
      `**/api/annotatie/documenten/${SLUG}/wetsartikel`,
      (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(WETSARTIKEL),
        }),
    );
    await page.route(
      `**/api/annotatie/documenten/${SLUG}/elementen/el-1/beslissing`,
      (route) => {
        const doc = maakDocument(huidigStatus);
        doc.elementen[0].levenscyclus = "human_goedgekeurd";
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(doc),
        });
      },
    );
    await page.route(`**/api/annotatie/documenten/${SLUG}/status`, (route) => {
      huidigStatus = "geaccordeerd";
      const doc = maakDocument(huidigStatus);
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(doc),
      });
    });

    await page.getByRole("link", { name: "Annotaties" }).click();
    await page
      .locator("button.card")
      .filter({ hasText: "BWBR0004770" })
      .click();
    await expect(page.getByText("de belastingplichtige")).toBeVisible();

    await page.getByRole("button", { name: "Akkoord" }).click();
    await expect(page.getByText("goedgekeurd")).toBeVisible();

    await page.getByRole("button", { name: "Afronden" }).click();
    await expect(page.getByText("Status: geaccordeerd")).toBeVisible();
    await expect(
      page.getByText(
        "Deze annotatie is afgerond. Heropen hem om markeringen te wijzigen.",
      ),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Heropenen" })).toBeVisible();
  });
});
