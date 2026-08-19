import { test, expect } from "@playwright/test";

// Vereist: de Next.js-server én de API draaien al vóórdat deze test start.

const DUMMY_DOCUMENT = {
  slug: "test-werkgebied-bwbr0011823-art-3",
  client_id: "beheerder",
  werkgebied: "Testdomein",
  bwb_id: "BWBR0011823",
  artikel: "3",
  lid: "",
  status: "voorgesteld" as const,
  elementen: [],
  aangemaakt: new Date().toISOString(),
  bijgewerkt: new Date().toISOString(),
};

const DUMMY_ELEMENT = {
  id: "el-001",
  klasse: "Norm",
  tekst: "De belastingplichtige betaalt belasting.",
  toelichting: "Kernartikel",
  aandacht: "geel" as const,
  levenscyclus: "voorgesteld" as const,
  beslissingen: [],
  alternatieven: [],
  diff: {},
  herkomst: "",
  lid: "",
  vindplaats: "",
  critic: null,
  span: null,
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

test("werkplek-pagina is bereikbaar via de navigatiebalk", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Werkplek" }).click();
  await page.waitForURL("/werkplek");
  await expect(page.getByRole("heading", { name: "Werkplek" })).toBeVisible();
});

test("lege werkplek toont placeholder-tekst", async ({ page }) => {
  // Mock lege documentenlijst
  await page.route("/api/annotatie/documenten", (route) => {
    if (route.request().method() === "GET") {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    } else {
      void route.continue();
    }
  });

  await page.goto("/werkplek");
  await expect(
    page.getByText("Nog geen annotatie-documenten aangemaakt."),
  ).toBeVisible();
});

test("werkplek toont lijst van documenten", async ({ page }) => {
  await page.route("/api/annotatie/documenten", (route) => {
    if (route.request().method() === "GET") {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([DUMMY_DOCUMENT]),
      });
    } else {
      void route.continue();
    }
  });

  await page.goto("/werkplek");
  await expect(page.getByText("Testdomein")).toBeVisible();
  await expect(page.getByText("BWBR0011823")).toBeVisible();
  await expect(page.getByText("Voorgesteld")).toBeVisible();
});

test("gebruiker kan een nieuw document aanmaken via het formulier", async ({
  page,
}) => {
  let postGeroepen = false;

  await page.route("/api/annotatie/documenten", (route) => {
    if (route.request().method() === "GET") {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    } else if (route.request().method() === "POST") {
      postGeroepen = true;
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(DUMMY_DOCUMENT),
      });
    } else {
      void route.continue();
    }
  });

  await page.goto("/werkplek");

  // Klik op "Nieuw document"
  await page.getByRole("button", { name: "+ Nieuw document" }).click();

  // Vul het formulier in
  await page.getByPlaceholder("bijv. Inkomstenbelasting").fill("Testdomein");
  await page.getByPlaceholder("bijv. BWBR0011823").fill("BWBR0011823");
  await page.getByPlaceholder("bijv. 3.1").fill("3");

  // Submit
  await page.getByRole("button", { name: "Document aanmaken" }).click();

  // Na aanmaken verdwijnt het formulier en verschijnt het document in de lijst
  await expect(page.getByText("Testdomein")).toBeVisible();
  expect(postGeroepen).toBe(true);
});

test("submit-knop is uitgeschakeld als verplichte velden leeg zijn", async ({
  page,
}) => {
  await page.route("/api/annotatie/documenten", (route) => {
    void route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.goto("/werkplek");
  await page.getByRole("button", { name: "+ Nieuw document" }).click();

  // Geen velden ingevuld — knop moet uitgeschakeld zijn
  await expect(
    page.getByRole("button", { name: "Document aanmaken" }),
  ).toBeDisabled();
});

test("documentdetail toont elementen en beslissingsacties", async ({ page }) => {
  const docMetElement = {
    ...DUMMY_DOCUMENT,
    elementen: [DUMMY_ELEMENT],
  };

  await page.route(
    `/api/annotatie/documenten/${DUMMY_DOCUMENT.slug}`,
    (route) => {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(docMetElement),
      });
    },
  );

  await page.goto(`/werkplek/${DUMMY_DOCUMENT.slug}`);

  // Element is zichtbaar
  await expect(page.getByText("De belastingplichtige betaalt belasting.")).toBeVisible();
  await expect(page.getByText("Norm")).toBeVisible();

  // Beslissingsacties zijn zichtbaar
  await expect(page.getByRole("button", { name: "Goedkeuren" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Bewerken" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Afwijzen" })).toBeVisible();
});

test("lege elementen toont placeholder-tekst", async ({ page }) => {
  await page.route(
    `/api/annotatie/documenten/${DUMMY_DOCUMENT.slug}`,
    (route) => {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(DUMMY_DOCUMENT),
      });
    },
  );

  await page.goto(`/werkplek/${DUMMY_DOCUMENT.slug}`);
  await expect(
    page.getByText("Geen elementen voorgesteld door de agent."),
  ).toBeVisible();
});

test("goedkeuren-beslissing verstuurt POST naar de BFF", async ({ page }) => {
  const docMetElement = {
    ...DUMMY_DOCUMENT,
    elementen: [DUMMY_ELEMENT],
  };

  let beslissingBody: unknown = null;
  const goedgekeurdDoc = {
    ...docMetElement,
    elementen: [
      {
        ...DUMMY_ELEMENT,
        levenscyclus: "human_goedgekeurd",
        beslissingen: [
          { type: "goedkeuren", actor: "beheerder", tijd: new Date().toISOString() },
        ],
      },
    ],
  };

  await page.route(
    `/api/annotatie/documenten/${DUMMY_DOCUMENT.slug}`,
    (route) => {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(docMetElement),
      });
    },
  );

  await page.route(
    `/api/annotatie/documenten/${DUMMY_DOCUMENT.slug}/elementen/${DUMMY_ELEMENT.id}/beslissing`,
    async (route) => {
      beslissingBody = JSON.parse(route.request().postData() ?? "{}");
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(goedgekeurdDoc),
      });
    },
  );

  await page.goto(`/werkplek/${DUMMY_DOCUMENT.slug}`);
  await page.getByRole("button", { name: "Goedkeuren" }).click();

  // Na beslissing is de knop weg en is de badge bijgewerkt
  await expect(page.getByText("Goedgekeurd")).toBeVisible();
  expect((beslissingBody as { type?: string })?.type).toBe("goedkeuren");
});

test("afwijzen-formulier vereist een reden", async ({ page }) => {
  const docMetElement = {
    ...DUMMY_DOCUMENT,
    elementen: [DUMMY_ELEMENT],
  };

  await page.route(
    `/api/annotatie/documenten/${DUMMY_DOCUMENT.slug}`,
    (route) => {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(docMetElement),
      });
    },
  );

  await page.goto(`/werkplek/${DUMMY_DOCUMENT.slug}`);
  await page.getByRole("button", { name: "Afwijzen" }).click();

  // Bevestigknop is uitgeschakeld zonder reden
  await expect(
    page.getByRole("button", { name: "Afwijzen bevestigen" }),
  ).toBeDisabled();

  // Kies een reden — knop wordt enabled
  await page.getByRole("combobox").last().selectOption("onduidelijk");
  await expect(
    page.getByRole("button", { name: "Afwijzen bevestigen" }),
  ).toBeEnabled();
});

test("auditlog-tabblad toont tijdlijn of lege placeholder", async ({ page }) => {
  await page.route(
    `/api/annotatie/documenten/${DUMMY_DOCUMENT.slug}`,
    (route) => {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(DUMMY_DOCUMENT),
      });
    },
  );

  await page.route(
    `/api/annotatie/documenten/${DUMMY_DOCUMENT.slug}/audit`,
    (route) => {
      void route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );

  await page.goto(`/werkplek/${DUMMY_DOCUMENT.slug}`);

  // Klik op Auditlog-tabblad
  await page.getByRole("button", { name: "Auditlog" }).click();

  await expect(page.getByText("Nog geen acties vastgelegd.")).toBeVisible();
});

test("document verwijderen navigeert terug naar werkplek", async ({ page }) => {
  await page.route(
    `/api/annotatie/documenten/${DUMMY_DOCUMENT.slug}`,
    (route) => {
      if (route.request().method() === "GET") {
        void route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(DUMMY_DOCUMENT),
        });
      } else if (route.request().method() === "DELETE") {
        void route.fulfill({ status: 204 });
      } else {
        void route.continue();
      }
    },
  );

  // Sluit de confirm-dialog automatisch met OK
  page.on("dialog", (dialog) => void dialog.accept());

  await page.goto(`/werkplek/${DUMMY_DOCUMENT.slug}`);
  await page.getByRole("button", { name: "Verwijder document" }).click();

  await page.waitForURL("/werkplek");
});
