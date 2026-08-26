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

  test("annoteren: doel-gedreven annotatiebeurt collapset tot een openbare artefact-chip", async ({
    page,
  }) => {
    await login(page);

    const MOCK_ANNOTATIE_SSE = [
      { type: "doel", doel: { bwbId: "BWBR0004770", artikel: "1", lid: "" } },
      {
        type: "element",
        klasse: "Rechtssubject",
        tekst: "de belastingplichtige",
      },
      { type: "opgeslagen", slug: "doc-1", aanvaard: 1, verworpen: 0 },
      { type: "done" },
    ]
      .map((e) => `data: ${JSON.stringify(e)}\n\n`)
      .join("");

    await page.route("**/api/chat", (route) =>
      route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: MOCK_ANNOTATIE_SSE,
      }),
    );

    await page.getByRole("button", { name: "Annoteren" }).click();
    await page.getByPlaceholder("BWB-id (bv. BWBR0004770)").fill("BWBR0004770");
    await page.getByPlaceholder("Artikel").fill("1");
    await page.getByPlaceholder("Werkgebied").fill("sociaal");
    await page.getByRole("button", { name: "Start annotatie" }).click();

    // De live elementenlijst collapset zodra `opgeslagen` binnenkomt tot een chip die het
    // artefact-paneel opent (`ArtefactPaneel`, eigen dekking in `annotaties.spec.ts`) — hier
    // alleen toetsen dát de chip verschijnt met de juiste telling, niet de paneel-inhoud zelf.
    await expect(page.getByText(/1 aanvaard, 0 verworpen/)).toBeVisible();
  });

  test("gespreksgeschiedenis: een eerder gesprek verschijnt in de sidebar en is te heropenen", async ({
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

    // Bewust een andere vraagtekst dan de placeholder se eigen voorbeeldzin (die noemt
    // "belastingschuldige" letterlijk, anders matcht `getByText` straks de lege-staat-tekst) én
    // uniek per testrun (een lokale herhaling van deze spec tegen dezelfde, niet-opgeruimde
    // dev-Postgres zou anders een sidebar-knop met exact dezelfde titel van een vorige run
    // treffen — `strict mode violation`, geen echte bug).
    const vraag = `Wat is een aansprakelijkstelling? (${Date.now()})`;
    await page.getByPlaceholder("Stel een vraag…").fill(vraag);
    await page.getByRole("button", { name: "Versturen" }).click();
    await expect(page.getByText("Een testantwoord over de wet.")).toBeVisible();

    // De vraag van de gebruiker persisteert de component zelf en geeft het gesprek meteen een
    // titel op basis van die vraag; het antwoord persisteert normaliter graph-qa ná afloop van
    // de stream (hier gemockt, dus dat deel gebeurt niet — alleen de sidebar-titel is hier het
    // controleerbare bewijs van persistentie).
    const sidebarTitel = page.getByRole("button", { name: vraag });
    await expect(sidebarTitel).toBeVisible();

    const berichtenpaneel = page.getByTestId("berichten");
    await page.getByRole("button", { name: "+ Nieuw gesprek" }).click();
    await expect(berichtenpaneel.getByText(vraag)).not.toBeVisible();

    await sidebarTitel.click();
    await expect(berichtenpaneel.getByText(vraag)).toBeVisible();
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
