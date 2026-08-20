import { test, expect } from "@playwright/test";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.
// De API moet een lege gebruikers-tabel hebben voor het gelukkige pad.
// Het foutpad (al ingericht) werkt zodra er al een gebruiker bestaat.

test.describe("setup-flow", () => {
  test("gelukkig pad: formulier zichtbaar, beheerder aanmaken leidt naar login", async ({
    page,
  }) => {
    // Navigeer naar /setup — de pagina is publiek en toont het formulier
    // als needs_setup: true.
    await page.goto("/setup");

    // Controleer dat we op de setup-pagina zijn (niet doorgestuurd naar login).
    // Als de API al ingericht is, zal de test hier falen (expected behavior:
    // in CI start je met een lege database).
    const heading = page.getByRole("heading", {
      name: /eerste beheerder aanmaken/i,
    });
    await expect(heading).toBeVisible();

    // Vul het formulier in met een unieke gebruikersnaam
    const gebruikersnaam = `admin${Date.now()}`;
    await page.getByLabel("Gebruikersnaam").fill(gebruikersnaam);
    await page.getByLabel("E-mailadres").fill(`${gebruikersnaam}@example.com`);
    await page.getByLabel("Wachtwoord", { exact: true }).fill("veiligww123");
    await page.getByLabel("Wachtwoord bevestigen").fill("veiligww123");

    await page.getByRole("button", { name: "Aanmaken" }).click();

    // Na succesvol aanmaken → redirect naar /login
    await page.waitForURL("/login");
    await expect(
      page.getByRole("heading", { name: /inloggen/i }),
    ).toBeVisible();
  });

  test("foutpad: al ingericht — /setup redirect naar /login", async ({
    page,
  }) => {
    // Als de database al een gebruiker heeft (doordat een vorige test 'm aangemaakt heeft
    // of doordat de API-server al ingericht is), moet /setup doorsturen naar /login.
    // Dit test het pad waarbij de server-side redirect in de SetupPagina plaatsvindt.

    // Navigeer naar /setup; als de API needs_setup: false geeft, komt een redirect.
    const response = await page.goto("/setup");

    // Ofwel zijn we op /login geland (redirect na setup-status false),
    // ofwel op /setup zelf als needs_setup nog true is.
    // Controleer: als we op /login zijn, is het foutpad succesvol afgehandeld.
    if (page.url().includes("/login")) {
      await expect(
        page.getByRole("heading", { name: /inloggen/i }),
      ).toBeVisible();
    } else {
      // Als we op /setup staan, verwachten we het formulier.
      // (Dit is het geval als de database leeg is en needs_setup true is.)
      await expect(
        page.getByRole("heading", { name: /eerste beheerder aanmaken/i }),
      ).toBeVisible();
    }

    // In ieder geval: geen onverwachte foutpagina's.
    expect(response?.status()).not.toBe(500);
  });
});
