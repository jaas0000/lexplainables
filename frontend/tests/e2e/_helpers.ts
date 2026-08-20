// Gedeelde helpers voor e2e-tests.
//
// Doel: elke test staat op zichzelf — bouwt de state op via directe API-aanroepen,
// niet via UI-flows van andere tests. De helpers gaan langs de BFF-proxy heen en
// praten direct met de FastAPI-service op `API_BASE_URL` (default localhost:8000),
// met het API_TOKEN uit de omgeving (default `local-dev-api-token-lexplainables`).
//
// Werkers=1 in CI (playwright.config.ts) → tests zijn seriëel. State-cleanup is
// nog steeds nodig omdat één falende test residu kan achterlaten dat de volgende
// verstoort.

import type { APIRequestContext, BrowserContext, Page } from "@playwright/test";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
const API_TOKEN = process.env.API_TOKEN ?? "local-dev-api-token-lexplainables";
const SEED_GEBRUIKER = "beheerder";
const SEED_WACHTWOORD = "beheerder123";

function headers(gebruiker: string = SEED_GEBRUIKER): Record<string, string> {
  return {
    Authorization: `Bearer ${API_TOKEN}`,
    "X-User-Id": gebruiker,
    "Content-Type": "application/json",
  };
}

export async function login(
  page: Page,
  context: BrowserContext,
  gebruikersnaam: string = SEED_GEBRUIKER,
  wachtwoord: string = SEED_WACHTWOORD,
) {
  await context.addCookies([
    {
      name: "disclaimer_geaccepteerd",
      value: "1",
      domain: "localhost",
      path: "/",
    },
  ]);
  await page.goto("/login");
  await page.getByLabel("Gebruikersnaam").fill(gebruikersnaam);
  await page.getByLabel("Wachtwoord").fill(wachtwoord);
  await page.getByRole("button", { name: "Inloggen" }).click();
  await page.waitForURL("/");
}

// --- API-helpers ---

export async function apiGet(request: APIRequestContext, pad: string) {
  const res = await request.get(`${API_BASE_URL}${pad}`, {
    headers: headers(),
  });
  if (!res.ok()) {
    throw new Error(`GET ${pad} → ${res.status()} ${await res.text()}`);
  }
  return res.json();
}

export async function apiPost(
  request: APIRequestContext,
  pad: string,
  body: unknown,
) {
  const res = await request.post(`${API_BASE_URL}${pad}`, {
    headers: headers(),
    data: JSON.stringify(body),
  });
  if (!res.ok()) {
    throw new Error(`POST ${pad} → ${res.status()} ${await res.text()}`);
  }
  return res.status() === 204 ? undefined : res.json();
}

export async function apiDelete(request: APIRequestContext, pad: string) {
  const res = await request.delete(`${API_BASE_URL}${pad}`, {
    headers: headers(),
  });
  if (!res.ok() && res.status() !== 404) {
    throw new Error(`DELETE ${pad} → ${res.status()} ${await res.text()}`);
  }
}

export async function apiPatch(
  request: APIRequestContext,
  pad: string,
  body: unknown,
) {
  const res = await request.patch(`${API_BASE_URL}${pad}`, {
    headers: headers(),
    data: JSON.stringify(body),
  });
  if (!res.ok()) {
    throw new Error(`PATCH ${pad} → ${res.status()} ${await res.text()}`);
  }
  return res.json();
}

// --- Cleanup / seed ---

/**
 * Zorgt dat de tabel de seed-beheerder heeft als enige actieve beheerder én verwijdert
 * eventuele achtergebleven test-gebruikers. Roep aan in `beforeEach` van tests die
 * gebruikersbeheer aanraken.
 *
 * Aanname: het seed-wachtwoord ("beheerder123") is correct. Als een eerdere test het
 * wachtwoord van de seed-beheerder heeft veranderd, moet die test dat zelf terugdraaien
 * (zie account.spec.ts). We kunnen het hier niet reddend herstellen zonder database-toegang.
 */
export async function resetGebruikers(request: APIRequestContext) {
  const setupStatusRes = await request.get(
    `${API_BASE_URL}/v1/auth/setup-status`,
    { headers: headers() },
  );
  const setupStatus = (await setupStatusRes.json()) as { needs_setup: boolean };

  if (setupStatus.needs_setup) {
    // Volledig lege tabel — maak seed via het publieke setup-endpoint.
    const res = await request.post(`${API_BASE_URL}/v1/auth/setup`, {
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify({
        gebruikersnaam: SEED_GEBRUIKER,
        email: `${SEED_GEBRUIKER}@local`,
        wachtwoord: SEED_WACHTWOORD,
      }),
    });
    if (!res.ok()) {
      throw new Error(`setup faalde: ${res.status()} ${await res.text()}`);
    }
  }

  // Zorg dat de seed weer beheerder én actief is (mocht een test dat gewijzigd hebben).
  try {
    await request.patch(
      `${API_BASE_URL}/v1/admin/gebruikers/${SEED_GEBRUIKER}`,
      {
        headers: headers(),
        data: JSON.stringify({ actief: true, rol: "beheerder" }),
      },
    );
  } catch {
    /* niet-kritiek — kan mislukken als de patch een no-op zou zijn (409 last-active is niet
       hier van toepassing want we activeren i.p.v. deactiveren). */
  }

  // Verwijder alle andere gebruikers.
  const alleRes = await request.get(`${API_BASE_URL}/v1/admin/gebruikers`, {
    headers: headers(),
  });
  const alle = (await alleRes.json()) as { gebruikersnaam: string }[];
  for (const g of alle) {
    if (g.gebruikersnaam !== SEED_GEBRUIKER) {
      await request.delete(
        `${API_BASE_URL}/v1/admin/gebruikers/${g.gebruikersnaam}`,
        { headers: headers() },
      );
    }
  }
}

/** Verwijdert alle admin-berichten. */
export async function resetBerichten(request: APIRequestContext) {
  const res = (await apiGet(request, "/v1/admin/berichten")) as {
    items: { id: number }[];
  };
  for (const b of res.items) {
    await apiDelete(request, `/v1/admin/berichten/${b.id}`);
  }
}

/** Verwijdert alle feedbackitems. */
export async function resetFeedback(request: APIRequestContext) {
  const res = (await apiGet(request, "/v1/admin/feedback")) as {
    items: { id: number }[];
  };
  for (const f of res.items) {
    await apiDelete(request, `/v1/admin/feedback/${f.id}`);
  }
}

/**
 * Verwijdert zoveel mogelijk LLM-profielen. De API weigert het laatste profiel te
 * verwijderen (409 EnigeProfielFout) — in dat geval blijft er precies één profiel over.
 * De tests die exact 0 of exact 1 profiel verwachten, gaan hier expliciet mee om.
 */
export async function resetProfielen(request: APIRequestContext) {
  const res = (await apiGet(request, "/v1/admin/profielen")) as {
    naam: string;
  }[];
  for (const p of res) {
    const url = `${API_BASE_URL}/v1/admin/profielen/${encodeURIComponent(p.naam)}`;
    const delRes = await request.delete(url, { headers: headers() });
    // 404 = al weg (race), 409 = het is het enige profiel — accepteer beide.
    if (!delRes.ok() && delRes.status() !== 404 && delRes.status() !== 409) {
      throw new Error(
        `DELETE ${url} → ${delRes.status()} ${await delRes.text()}`,
      );
    }
  }
}

/** Verwijdert alle API-tokens. */
export async function resetApiTokens(request: APIRequestContext) {
  const res = (await apiGet(request, "/v1/admin/api-tokens")) as {
    id: string;
  }[];
  for (const t of res) {
    await apiDelete(request, `/v1/admin/api-tokens/${t.id}`);
  }
}

export { SEED_GEBRUIKER, SEED_WACHTWOORD, API_BASE_URL, API_TOKEN };
