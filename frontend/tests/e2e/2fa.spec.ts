import { test, expect } from "@playwright/test";
import { authenticator } from "otplib";
import { login } from "./_helpers";
import { Client } from "pg";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";
const API_TOKEN = process.env.API_TOKEN ?? "local-dev-api-token-lexplainables";

async function schakel2FAUit(): Promise<void> {
  // Best-effort cleanup: als de test halverwege faalt, zit de seed-beheerder nog met 2FA
  // aan en kunnen vervolgtests niet inloggen. Directe DB-wipe is de betrouwbare route
  // (het API-uitschakel-pad vereist een geldige TOTP-code, die we niet altijd hebben).
  const url =
    process.env.DATABASE_URL_SYNC ?? "postgresql://lex:lex@localhost:5432/lex";
  const client = new Client({ connectionString: url });
  await client.connect();
  try {
    await client.query(
      "UPDATE gebruikers SET totp_secret_enc = NULL, totp_ingeschakeld = false " +
        "WHERE gebruikersnaam = 'beheerder'",
    );
  } finally {
    await client.end();
  }
}

test.describe("2FA-activering", () => {
  test.afterEach(async () => {
    // Altijd terugzetten — ook als de test tussendoor faalt — zodat de seed-beheerder
    // beschikbaar blijft voor vervolgtests.
    await schakel2FAUit();
  });

  test("gebruiker koppelt en logt in met code", async ({
    page,
    context,
    request,
  }) => {
    test.setTimeout(60_000);

    // Log in als seed-beheerder (nog geen 2FA aan).
    await login(page, context);
    await page.goto("/account");

    // Klik "Activeer 2FA"; wacht op de QR-code.
    await page.getByRole("button", { name: "Activeer 2FA" }).click();
    await expect(page.getByAltText("QR-code voor 2FA-koppeling")).toBeVisible({
      timeout: 10_000,
    });

    // Haal het secret op via de begin-endpoint direct — de UI toont dezelfde URI. We roepen
    // 'm nogmaals aan (het genereert een nieuw secret, maar dat is prima want we activeren
    // vervolgens met dat nieuwe secret).
    const beginRes = await request.post(`${API_BASE}/v1/auth/2fa/begin`, {
      headers: {
        Authorization: `Bearer ${API_TOKEN}`,
        "X-User-Id": "beheerder",
      },
    });
    expect(beginRes.ok()).toBeTruthy();
    const { otpauth_uri } = (await beginRes.json()) as { otpauth_uri: string };
    const secret = new URL(otpauth_uri).searchParams.get("secret")!;
    expect(secret).toBeTruthy();

    const code = authenticator.generate(secret);

    // Voer de code in het formulier in en klik Bevestig.
    await page.getByLabel("TOTP-code").fill(code);
    await page.getByRole("button", { name: "Bevestig" }).click();

    // Badge wijzigt naar "Actief".
    await expect(page.getByText(/^Actief$/)).toBeVisible({ timeout: 5_000 });

    // Log uit door de cookies te wissen en opnieuw naar /login te gaan.
    await context.clearCookies();
    await context.addCookies([
      {
        name: "disclaimer_geaccepteerd",
        value: "1",
        domain: "localhost",
        path: "/",
      },
    ]);
    await page.goto("/login");

    // Log opnieuw in — nu vereist de flow een TOTP-code.
    await page.getByLabel("Gebruikersnaam").fill("beheerder");
    await page.getByLabel("Wachtwoord").fill("beheerder123");
    await page.getByRole("button", { name: "Inloggen" }).click();

    // Tweede scherm — voer een geldige code in.
    await expect(page.getByLabel("Tweestapsverificatiecode")).toBeVisible({
      timeout: 10_000,
    });
    const nieuwe_code = authenticator.generate(secret);
    await page.getByLabel("Tweestapsverificatiecode").fill(nieuwe_code);
    await page.getByRole("button", { name: "Code bevestigen" }).click();
    await page.waitForURL("/");
  });
});
