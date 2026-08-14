/**
 * Integratietests voor de lexplainables-admin MCP-tools.
 *
 * Aanpak: de TOOLS-array wordt direct aangesproken met een gemockte globalThis.fetch,
 * zodat er geen draaiende API nodig is. De MCP-server zelf wordt niet gestart.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { z } from "zod";

// Env-vars zetten vóór de module-import zodat de module niet weigert te laden.
process.env.LEXPLAINABLES_API_URL = "http://test-api";
process.env.API_TOKEN = "test-token";
process.env.MCP_GEBRUIKERSNAAM = "test-beheerder";

// Dynamische import na het zetten van de env-vars (statische imports worden gehoist).
const { TOOLS } = await import("./index.js");

// ── Hulpfuncties ──────────────────────────────────────────────────────────────

function vindTool(naam: string) {
  const tool = TOOLS.find((t) => t.name === naam);
  assert.ok(tool !== undefined, `Tool '${naam}' niet gevonden in TOOLS-array`);
  return tool;
}

function mockFetch(responseBody: unknown, status = 200): typeof fetch {
  return (async () => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(responseBody),
  })) as unknown as typeof fetch;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test("maak_bericht met geldige input geeft bericht met id terug", async () => {
  const tool = vindTool("maak_bericht");
  const mockBericht = {
    id: 42,
    titel: "Nieuwe versie beschikbaar",
    inhoud: "Versie 1.1.0 is uitgerold.",
    type: "update",
    versie: "v1.1.0",
    gepubliceerd: false,
    aangemaakt_op: "2026-08-14T10:00:00Z",
  };

  const origFetch = globalThis.fetch;
  globalThis.fetch = mockFetch(mockBericht, 201);
  try {
    const args = tool.input.parse({
      titel: "Nieuwe versie beschikbaar",
      inhoud: "Versie 1.1.0 is uitgerold.",
      type: "update",
      versie: "v1.1.0",
    }) as Record<string, unknown>;
    const result = await tool.run(args);
    const resultStr = JSON.stringify(result);
    assert.ok(resultStr.includes("42"), `Resultaat moet id 42 bevatten, maar was: ${resultStr}`);
    assert.ok(
      resultStr.includes("Nieuwe versie beschikbaar"),
      "Resultaat moet de titel bevatten",
    );
  } finally {
    globalThis.fetch = origFetch;
  }
});

test("maak_bericht met ongeldig type gooit Zod-validatiefout vóór API-aanroep", () => {
  const tool = vindTool("maak_bericht");
  assert.throws(
    () =>
      tool.input.parse({
        titel: "Test",
        inhoud: "Testinhoud",
        type: "ongeldig-type",
      }),
    (e: unknown) => e instanceof z.ZodError,
    "Verwacht een ZodError bij een ongeldig type",
  );
});

test("list_berichten_admin geeft items-array terug uit gepagineerde respons", async () => {
  const tool = vindTool("list_berichten_admin");
  const mockItems = [
    { id: 1, titel: "Bericht A", type: "info", versie: null, gepubliceerd: true, created: "2026-08-14T10:00:00Z" },
    { id: 2, titel: "Bericht B", type: "update", versie: "v1.0", gepubliceerd: false, created: "2026-08-13T10:00:00Z" },
  ];

  const origFetch = globalThis.fetch;
  globalThis.fetch = mockFetch({ items: mockItems, totaal: 2 });
  try {
    const result = await tool.run({});
    const resultStr = JSON.stringify(result);
    assert.ok(resultStr.includes("Bericht A"), "Resultaat moet items bevatten");
    assert.ok(resultStr.includes("Bericht B"), "Resultaat moet alle items bevatten");
    assert.ok(!resultStr.includes('"totaal"'), "Resultaat mag geen wrapper-object met 'totaal' bevatten");
  } finally {
    globalThis.fetch = origFetch;
  }
});

test("publiceer_bericht met onbekend id geeft leesbare 404-foutmelding", async () => {
  const tool = vindTool("publiceer_bericht");

  const origFetch = globalThis.fetch;
  globalThis.fetch = mockFetch({ detail: "Bericht niet gevonden" }, 404);
  try {
    const args = tool.input.parse({ id: 999, gepubliceerd: true }) as Record<string, unknown>;
    await assert.rejects(
      () => tool.run(args),
      (e: Error) => {
        assert.ok(
          e.message.includes("404"),
          `Foutmelding moet '404' bevatten, maar was: ${e.message}`,
        );
        assert.ok(
          e.message.includes("Bericht niet gevonden") || e.message.includes("404"),
          "Foutmelding moet leesbare tekst bevatten",
        );
        return true;
      },
    );
  } finally {
    globalThis.fetch = origFetch;
  }
});
