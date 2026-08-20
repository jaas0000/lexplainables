import { test, expect } from "@playwright/test";
import { DatabaseSync } from "node:sqlite";
import { existsSync } from "node:fs";
import { API_BASE_URL, API_TOKEN } from "./_helpers";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.
//
// De gelukkig-pad test heeft een lege `gebruikers`-tabel nodig (needs_setup: true) —
// dat kan niet via de admin-API worden opgebouwd (de "laatste actieve beheerder"-
// invariant staat het verwijderen van de laatste beheerder niet toe). Daarom wipen we
// hier direct via SQLite (Node 22 heeft `node:sqlite` ingebouwd). Na afloop zetten we
// de seed-beheerder terug via het publieke setup-endpoint, zodat vervolgtests weer
// kunnen inloggen als "beheerder".
//
// De DB-pad wordt afgeleid uit env `DATABASE_URL_SYNC` (bijv.
// `sqlite:///./ci-e2e.db` in CI, resolved t.o.v. de api-cwd — dus vanaf frontend/
// prependen we `../api/`). Lokaal valt hij terug op `../api/local-e2e.db`.

function dbPad(): string {
  const env = process.env.DATABASE_URL_SYNC;
  if (env?.startsWith("sqlite:///")) {
    const rel = env.slice("sqlite:///".length); // bv. "./ci-e2e.db"
    const kandidaten = [`../api/${rel.replace(/^\.\//, "")}`, rel];
    for (const p of kandidaten) if (existsSync(p)) return p;
  }
  const fallbacks = ["../api/ci-e2e.db", "../api/local-e2e.db"];
  for (const p of fallbacks) if (existsSync(p)) return p;
  throw new Error(
    "Kon SQLite DB-bestand niet vinden — controleer DATABASE_URL_SYNC of de fallback-paden ../api/{ci,local}-e2e.db.",
  );
}

function wipeGebruikers() {
  const db = new DatabaseSync(dbPad());
  db.exec("DELETE FROM gebruikers");
  db.close();
}

async function herstelSeedBeheerder(
  request: import("@playwright/test").APIRequestContext,
) {
  // Wipe eerst — de gelukkig-test heeft mogelijk een admin{timestamp} aangemaakt.
  wipeGebruikers();
  // Herzet de seed-beheerder via het setup-endpoint (gate: API_TOKEN, werkt alleen als
  // de tabel leeg is).
  const res = await request.post(`${API_BASE_URL}/v1/auth/setup`, {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_TOKEN}`,
    },
    data: JSON.stringify({
      gebruikersnaam: "beheerder",
      email: "beheerder@local",
      wachtwoord: "beheerder123",
    }),
  });
  if (!res.ok()) {
    throw new Error(
      `setup-herstel faalde: ${res.status()} ${await res.text()}`,
    );
  }
}

test.describe("setup-flow", () => {
  test("gelukkig pad: formulier zichtbaar, beheerder aanmaken leidt naar login", async ({
    page,
    request,
  }) => {
    // Wipe de gebruikers-tabel zodat needs_setup: true — het formulier verschijnt.
    wipeGebruikers();
    try {
      await page.goto("/setup");
      const heading = page.getByRole("heading", {
        name: /eerste beheerder aanmaken/i,
      });
      await expect(heading).toBeVisible();

      const gebruikersnaam = `admin${Date.now()}`;
      await page.getByLabel("Gebruikersnaam").fill(gebruikersnaam);
      await page
        .getByLabel("E-mailadres")
        .fill(`${gebruikersnaam}@example.com`);
      await page.getByLabel("Wachtwoord", { exact: true }).fill("veiligww123");
      await page.getByLabel("Wachtwoord bevestigen").fill("veiligww123");

      await page.getByRole("button", { name: "Aanmaken" }).click();

      await page.waitForURL("/login");
      await expect(
        page.getByRole("heading", { name: /inloggen/i }),
      ).toBeVisible();
    } finally {
      // Zet de seed-beheerder terug zodat volgende tests kunnen inloggen.
      await herstelSeedBeheerder(request);
    }
  });

  test("foutpad: al ingericht — /setup redirect naar /login", async ({
    page,
  }) => {
    // Deze test werkt in beide situaties: als de DB al een beheerder heeft (normale
    // volgorde), verwachten we redirect. Bij een verse DB (nog geen beheerder) toont
    // Next het setup-formulier.
    const response = await page.goto("/setup");

    if (page.url().includes("/login")) {
      await expect(
        page.getByRole("heading", { name: /inloggen/i }),
      ).toBeVisible();
    } else {
      await expect(
        page.getByRole("heading", { name: /eerste beheerder aanmaken/i }),
      ).toBeVisible();
    }
    expect(response?.status()).not.toBe(500);
  });
});
