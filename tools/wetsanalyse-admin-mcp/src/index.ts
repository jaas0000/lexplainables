#!/usr/bin/env node
/**
 * Lexplainables Admin MCP-server (stdio).
 *
 * Ontsluit de admin-API van lexplainables (/v1/admin/berichten*) als agent-tools, zodat
 * een MCP-client (Claude Code) berichten kan aanmaken, bijwerken en publiceren.
 *
 * Config via env (nooit in de repo):
 *   LEXPLAINABLES_API_URL   — basis-URL van de API, bv. http://localhost:8000
 *   API_TOKEN               — machine-token; stuurt als Authorization: Bearer <token>
 *   MCP_GEBRUIKERSNAAM      — beheerder-gebruikersnaam; stuurt als X-User-Id: <naam>
 *
 * Fail-closed: zonder alle drie env-vars weigert de server te starten. Logs (JSON) gaan
 * naar stderr; het token wordt nooit gelogd. stdout is exclusief voor het MCP-protocol.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { fileURLToPath } from "node:url";
import { z } from "zod";

// ── Config ────────────────────────────────────────────────────────────────────

const API_URL = (process.env.LEXPLAINABLES_API_URL ?? "").replace(/\/+$/, "");
const API_TOKEN = (process.env.API_TOKEN ?? "").trim();
const MCP_GEBRUIKERSNAAM = (process.env.MCP_GEBRUIKERSNAAM ?? "").trim();

// ── Logging (JSON naar stderr; nooit tokens) ───────────────────────────────────

function log(
  niveau: "info" | "warn" | "error",
  bericht: string,
  velden: Record<string, unknown> = {},
): void {
  process.stderr.write(
    JSON.stringify({ ts: new Date().toISOString(), niveau, bericht, ...velden }) + "\n",
  );
}

// ── API-client ──────────────────────────────────────────────────────────────

export async function apiFetch(
  method: string,
  path: string,
  body?: unknown,
): Promise<unknown> {
  const url = `${API_URL}${path}`;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${API_TOKEN}`,
    "X-User-Id": MCP_GEBRUIKERSNAAM,
  };
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new Error(`API niet bereikbaar (${method} ${path}): ${(e as Error).message}`);
  }

  const tekst = await res.text();
  let data: unknown = tekst;
  try {
    data = tekst ? JSON.parse(tekst) : null;
  } catch {
    /* geen JSON — laat de ruwe tekst staan */
  }

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? (data as { detail: unknown }).detail
        : tekst;
    throw new Error(`API ${res.status} op ${method} ${path}: ${String(detail).slice(0, 300)}`);
  }
  return data;
}

// ── Tool-definities (declaratief) ──────────────────────────────────────────────

interface ToolDef {
  name: string;
  description: string;
  input: z.ZodType;
  run: (a: Record<string, unknown>) => Promise<unknown>;
}

const BERICHT_TYPE = z.enum(["info", "update", "waarschuwing", "kritiek"]);

export const TOOLS: ToolDef[] = [
  {
    name: "list_berichten_admin",
    description:
      "Lijst alle berichten (ook concepten). Geeft id, titel, type, versie, " +
      "gepubliceerd-status en aanmaakdatum. Handig om bestaande id's op te zoeken.",
    input: z.object({}),
    run: async () => {
      const resp = (await apiFetch("GET", "/v1/admin/berichten")) as { items: unknown };
      return resp.items;
    },
  },
  {
    name: "maak_bericht",
    description:
      "Maak een nieuw concept-bericht aan. Type is 'info', 'update', 'waarschuwing' of 'kritiek'. " +
      "Versie is optioneel (bv. 'v1.0.0'). Geeft het aangemaakte bericht (inclusief id) terug.",
    input: z.object({
      titel: z.string(),
      inhoud: z.string(),
      type: BERICHT_TYPE,
      versie: z.string().optional(),
    }),
    run: ({ titel, inhoud, type, versie }) =>
      apiFetch("POST", "/v1/admin/berichten", {
        titel,
        inhoud,
        type,
        versie: versie ?? null,
      }),
  },
  {
    name: "update_bericht",
    description:
      "Overschrijf alle velden van een bestaand bericht (ook als het al gepubliceerd is). " +
      "Roep eerst list_berichten_admin aan om de huidige waarden te zien. " +
      "Geeft het bijgewerkte bericht terug.",
    input: z.object({
      id: z.number(),
      titel: z.string(),
      inhoud: z.string(),
      type: BERICHT_TYPE,
      versie: z.string().optional(),
    }),
    run: ({ id, ...body }) =>
      apiFetch("PUT", `/v1/admin/berichten/${id as number}`, body),
  },
  {
    name: "publiceer_bericht",
    description:
      "Publiceer (gepubliceerd=true) of depubliceer (gepubliceerd=false) een bericht op id. " +
      "Geeft de bijgewerkte status terug.",
    input: z.object({
      id: z.number(),
      gepubliceerd: z.boolean(),
    }),
    run: ({ id, gepubliceerd }) =>
      apiFetch("PATCH", `/v1/admin/berichten/${id as number}/publicatie`, {
        gepubliceerd,
      }),
  },
];

// ── Server ────────────────────────────────────────────────────────────────────

// Statische MCP-tool-lijst: één keer opgebouwd bij module-init, hergebruikt op elke ListTools.
const TOOL_LIST = TOOLS.map((t) => {
  const { $schema: _drop, ...inputSchema } = z.toJSONSchema(t.input, { io: "input" }) as {
    $schema?: unknown;
    [k: string]: unknown;
  };
  return { name: t.name, description: t.description, inputSchema };
});

async function main(): Promise<void> {
  if (!API_URL || !API_TOKEN || !MCP_GEBRUIKERSNAAM) {
    log(
      "error",
      "Weigering te starten: zet LEXPLAINABLES_API_URL, API_TOKEN en MCP_GEBRUIKERSNAAM.",
    );
    process.exit(1);
  }

  const server = new Server(
    { name: "lexplainables-admin", version: "0.1.0" },
    { capabilities: { tools: {} } },
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOL_LIST }));

  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const def = TOOLS.find((t) => t.name === req.params.name);
    if (!def) throw new Error(`Onbekende tool: ${req.params.name}`);
    const args = def.input.parse(req.params.arguments ?? {}) as Record<string, unknown>;
    try {
      const resultaat = await def.run(args);
      log("info", "tool ok", { tool: def.name });
      return { content: [{ type: "text", text: JSON.stringify(resultaat, null, 2) }] };
    } catch (e) {
      log("warn", "tool fout", { tool: def.name, fout: (e as Error).message });
      return {
        content: [{ type: "text", text: `Fout: ${(e as Error).message}` }],
        isError: true,
      };
    }
  });

  await server.connect(new StdioServerTransport());
  log("info", "lexplainables-admin MCP gestart (stdio)", {
    api_url: API_URL,
    tools: TOOLS.length,
  });
}

// Alleen starten als direct uitgevoerd (niet geïmporteerd voor tests)
const __filename = fileURLToPath(import.meta.url);
if (__filename === process.argv[1]) {
  main().catch((e) => {
    log("error", "fatale startfout", { fout: (e as Error).message });
    process.exit(1);
  });
}
