import { test, expect } from "@playwright/test";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.

const WET_A = {
  bwb_id: "BWBR0004770",
  naam: "Invorderingswet 1990",
  bijgewerkt_door: "beheerder",
  bijgewerkt: new Date().toISOString(),
};

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

test("wetten-beheer toont de catalogus", async ({ page }) => {
  await page.route("/api/admin/wetten", (route) => {
    if (route.request().method() === "GET") {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([WET_A]),
      });
    } else {
      void route.continue();
    }
  });

  await page.goto("/beheer/wetten");
  await expect(page.getByText("Invorderingswet 1990")).toBeVisible();
});

test("verwijderen tijdens bewerken sluit het bewerkformulier zonder crash (regressietest)", async ({
  page,
}) => {
  await page.route("/api/admin/wetten", (route) => {
    if (route.request().method() === "GET") {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([WET_A]),
      });
    } else {
      void route.continue();
    }
  });

  await page.route(`/api/admin/wetten/${WET_A.bwb_id}`, (route) => {
    if (route.request().method() === "DELETE") {
      void route.fulfill({ status: 204 });
    } else {
      void route.continue();
    }
  });

  page.on("dialog", (dialog) => void dialog.accept());

  await page.goto("/beheer/wetten");
  await expect(page.getByText("Invorderingswet 1990")).toBeVisible();

  // Open het bewerkformulier voor deze wet...
  await page.getByRole("button", { name: "Bewerk" }).click();
  await expect(page.getByRole("button", { name: "Opslaan" })).toBeVisible();

  // ...en verwijder 'm terwijl het formulier nog open staat. Zonder de fix crasht dit:
  // `wetten.find(...)!` levert `undefined` op voor de net-verwijderde rij.
  await page.getByRole("button", { name: "Verwijder" }).click();

  // De rij (en daarmee het bewerkformulier) is weg, geen crash/foutscherm.
  await expect(page.getByText("Invorderingswet 1990")).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Opslaan" })).not.toBeVisible();
});
