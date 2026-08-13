import { test, expect } from "@playwright/test";

// Vereist (frontend-bouwen regel 6b): de Next.js-dev-server én de API draaien al vóórdat deze
// test start — dit bestand start ze niet zelf (geen `webServer` in playwright.config.ts).
// Elke test gebruikt een eigen, unieke titel, zodat tests onafhankelijk van elkaar (en van
// eerder achtergebleven testdata) blijven werken.

const KEYCLOAK_URL = process.env.KEYCLOAK_URL ?? "http://localhost:8080";
const KEYCLOAK_REALM = "wetsanalyse";
const KEYCLOAK_CLIENT_ID = "lexplainables";

async function getKeycloakToken(): Promise<string> {
  const response = await fetch(
    `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "password",
        client_id: KEYCLOAK_CLIENT_ID,
        username: "beheerder",
        password: "beheerder123",
      }).toString(),
    },
  );
  const data = (await response.json()) as { access_token: string };
  return data.access_token;
}

test.beforeEach(async ({ page }) => {
  const token = await getKeycloakToken();
  const gebruikersnaam =
    (
      JSON.parse(Buffer.from(token.split(".")[1], "base64").toString()) as {
        preferred_username?: string;
      }
    ).preferred_username ?? "beheerder";
  await page.addInitScript(
    ({ t, u }: { t: string; u: string }) => {
      localStorage.setItem("access_token", t);
      localStorage.setItem("gebruikersnaam", u);
    },
    { t: token, u: gebruikersnaam },
  );
});

test("beheerder maakt een bericht aan en publiceert het, zonder page-reload", async ({
  page,
}) => {
  const titel = `E2E bericht ${Date.now()}`;

  await page.goto("/");

  await page.getByLabel("Titel").fill(titel);
  await page
    .getByLabel("Inhoud")
    .fill("Inhoud voor de e2e-test van het gelukkige pad.");
  await page.getByRole("button", { name: "Aanmaken" }).click();

  const rij = page.locator("tbody tr", { hasText: titel });
  await expect(rij).toBeVisible();
  await expect(rij).toContainText("concept");

  await rij.getByRole("button", { name: "Publiceren" }).click();
  await expect(rij).toContainText("gepubliceerd");
});

test("verwijderen van een al verwijderd bericht toont een zichtbare foutmelding", async ({
  page,
  context,
}) => {
  const titel = `E2E fout-bericht ${Date.now()}`;

  await page.goto("/");
  await page.getByLabel("Titel").fill(titel);
  await page
    .getByLabel("Inhoud")
    .fill("Wordt via twee tabbladen dubbel verwijderd.");
  await page.getByRole("button", { name: "Aanmaken" }).click();

  const rij = page.locator("tbody tr", { hasText: titel });
  await expect(rij).toBeVisible();

  // Tweede tabblad, zelfde browsercontext (localStorage — dus het token — wordt gedeeld):
  // toont dezelfde, nog niet ververste lijst met hetzelfde bericht.
  const page2 = await context.newPage();
  await page2.goto("/");
  const rij2 = page2.locator("tbody tr", { hasText: titel });
  await expect(rij2).toBeVisible();

  // Verwijder het bericht op het eerste tabblad — dat lukt.
  await rij.getByRole("button", { name: "Verwijderen" }).click();
  await expect(rij).toHaveCount(0);

  // Het tweede tabblad heeft de rij nog staan (geen refetch getriggerd); een verwijdering
  // daarvandaan botst op een 404 van de server. Die fout moet zichtbaar zijn, niet stil falen.
  // `p[role="alert"]` i.p.v. de generieke rol: Next.js zet zelf ook een (lege)
  // route-announcer met role="alert" in de DOM.
  await rij2.getByRole("button", { name: "Verwijderen" }).click();
  await expect(page2.locator('p[role="alert"]')).toBeVisible();
});
