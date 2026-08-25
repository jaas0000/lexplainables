import { test, expect } from "@playwright/test";
import { login } from "./_helpers";

// De login-flow gaat door de echte `api` heen (CI zet Postgres + api op, zelfde patroon als
// frontend/tests/e2e/login.spec.ts). De chat-interactie zelf mockt `POST /api/chat` — een echte
// graph-qa + GraphDB + Foundry-keten is in CI niet beschikbaar (geen live-credentials/fixture-
// graaf daar); die kant is handmatig live geverifieerd (zie story 056 §Verificatie) en graph-qa
// se eigen `pytest -m integration`-suite dekt de agent-kant al. Dit spec test frontend-chat's
// eigen code: sessie-gate, streaming-rendering, foutafhandeling.

const MOCK_SSE = [
  { type: "token", content: "Een " },
  { type: "token", content: "testantwoord over de wet." },
  {
    type: "grounding",
    grounded: true,
    niveau: "gegrond",
    cited: 1,
    unsupported: [],
    niet_letterlijk: [],
  },
  { type: "done" },
]
  .map((e) => `data: ${JSON.stringify(e)}\n\n`)
  .join("");

test.describe("chat", () => {
  test("gelukkig pad: inloggen en een gestreamd antwoord van Lex zien verschijnen", async ({
    page,
  }) => {
    await login(page);

    await page.route("**/api/chat", (route) =>
      route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: MOCK_SSE,
      }),
    );

    await page
      .getByPlaceholder("Stel een vraag…")
      .fill("Wat is een belastingschuldige?");
    await page.getByRole("button", { name: "Versturen" }).click();

    await expect(page.getByText("Een testantwoord over de wet.")).toBeVisible();
    await expect(page.getByText("gegrond in de kennisgraaf")).toBeVisible();
  });

  test("foutpad: onjuiste credentials tonen foutmelding, geen sessie", async ({
    page,
    context,
  }) => {
    await page.goto("/login");
    await page.getByLabel("Gebruikersnaam").fill("beheerder");
    await page.getByLabel("Wachtwoord").fill("fout-wachtwoord");
    await page.getByRole("button", { name: "Inloggen" }).click();

    await expect(
      page.getByRole("alert").filter({ hasText: /onjuiste/i }),
    ).toBeVisible();
    await expect(page).toHaveURL(/\/login/);

    const cookies = await context.cookies();
    const sessieCookie = cookies.find((c) =>
      c.name.endsWith("authjs.session-token"),
    );
    expect(sessieCookie).toBeUndefined();
  });
});
