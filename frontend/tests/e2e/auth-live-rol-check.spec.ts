import { test, expect } from "@playwright/test";
import { Client } from "pg";
import { login } from "./_helpers";

// Fase 2b.3 — Auth.js live-rol-check.
//
// De JWT-callback in `auth.ts` roept periodiek `GET /v1/auth/me` aan (elke
// SESSION_CHECK_TTL_MS ms) en zet de sessie op `null` bij een 401 (account
// gedeactiveerd). CI zet `SESSION_CHECK_TTL_MS=100` zodat we niet 5 minuten
// hoeven te wachten in een test.

async function zetActief(actief: boolean): Promise<void> {
  const url =
    process.env.DATABASE_URL_SYNC ?? "postgresql://lex:lex@localhost:5432/lex";
  const client = new Client({ connectionString: url });
  await client.connect();
  try {
    await client.query(
      "UPDATE gebruikers SET actief = $1 WHERE gebruikersnaam = 'beheerder'",
      [actief],
    );
  } finally {
    await client.end();
  }
}

test.describe("Auth.js live-rol-check", () => {
  test.afterEach(async () => {
    // Herstel — anders zit de seed-beheerder gedeactiveerd voor vervolgtests.
    await zetActief(true);
  });

  test("gedeactiveerde beheerder wordt na TTL uitgelogd", async ({
    page,
    context,
  }) => {
    // In CI staat SESSION_CHECK_TTL_MS op 100ms; anders slaan we deze test over
    // omdat 5 min wachten geen realistische test-vensters oplevert.
    const ttl = Number(process.env.SESSION_CHECK_TTL_MS ?? "");
    test.skip(
      !Number.isFinite(ttl) || ttl > 5000,
      "SESSION_CHECK_TTL_MS ontbreekt of is te lang voor een e2e-test",
    );
    test.setTimeout(30_000);

    // Log in met de nog-actieve seed-beheerder.
    await login(page, context);
    await expect(page).toHaveURL("/");

    // Deactiveer het account terwijl de sessie loopt — zolang de TTL nog geldig
    // is, blijft de user gewoon werken.
    await zetActief(false);

    // Wacht tot de TTL verlopen is — de volgende navigation moet de JWT-callback
    // triggeren, die dan `GET /v1/auth/me` doet en een 401 krijgt → sessie null.
    await page.waitForTimeout(ttl + 200);

    // Beschermde route → redirect naar /login.
    await page.goto("/beheer");
    await expect(page).toHaveURL(/\/login/);
  });
});
