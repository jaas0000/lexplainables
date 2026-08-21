import { test, expect } from "@playwright/test";
import { login } from "./_helpers";

// End-to-end Auth.js-flow. De unit-laag is elders (Playwright kan geen NextAuth-JWT signeren
// zonder AUTH_SECRET-koppeling), dus deze tests gaan door het login-formulier heen en
// verifiëren dat sessie-cookies gezet worden en beschermde routes daarna bereikbaar zijn.

test.describe("login-flow", () => {
  test("gelukkig pad: inloggen leidt naar home en zet sessie-cookie", async ({
    page,
    context,
  }) => {
    await login(page, context);
    // Landt op / (home) na login.
    await expect(page).toHaveURL(/\/$/);
    // Sessie-cookie is gezet (in dev: authjs.session-token, in prod: __Secure-...).
    const cookies = await context.cookies();
    const sessieCookie = cookies.find(
      (c) =>
        c.name === "authjs.session-token" ||
        c.name.endsWith("authjs.session-token"),
    );
    expect(sessieCookie).toBeDefined();
    expect(sessieCookie?.httpOnly).toBe(true);
  });

  test("foutpad: onjuiste credentials tonen foutmelding, geen sessie", async ({
    page,
    context,
  }) => {
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
    await page.getByLabel("Wachtwoord").fill("fout-wachtwoord");
    await page.getByRole("button", { name: "Inloggen" }).click();
    // Foutmelding verschijnt; we blijven op /login.
    await expect(
      page.getByRole("alert").filter({ hasText: /onjuiste/i }),
    ).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
    // Geen sessie-cookie.
    const cookies = await context.cookies();
    const sessieCookie = cookies.find((c) =>
      c.name.endsWith("authjs.session-token"),
    );
    expect(sessieCookie).toBeUndefined();
  });

  test("beschermde route zonder sessie redirect naar /login", async ({
    page,
  }) => {
    await page.goto("/berichten");
    // Auth.js-middleware (proxy.ts) redirect naar /login met callbackUrl.
    await expect(page).toHaveURL(/\/login/);
  });
});
