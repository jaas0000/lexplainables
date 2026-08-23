import "server-only";
import { requireBeheerder } from "@/lib/bff-auth";

export const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
export const API_TOKEN = process.env.API_TOKEN ?? "";

/** Gedeelde auth-headers voor BFF → API communicatie. */
export function buildBackendHeaders(
  gebruikersnaam: string,
  extra: Record<string, string> = {},
): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${API_TOKEN}`,
    "X-User-Id": gebruikersnaam,
    ...extra,
  };
}

async function proxy(
  pad: string,
  headers: Record<string, string>,
  init: RequestInit,
  forwardHeaders: string[],
): Promise<Response> {
  const upstream = await fetch(`${API_BASE_URL}${pad}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  const body = upstream.status === 204 ? null : await upstream.text();
  const respHeaders: Record<string, string> = {
    "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
  };
  for (const naam of forwardHeaders) {
    const waarde = upstream.headers.get(naam);
    if (waarde) respHeaders[naam] = waarde;
  }
  return new Response(body, { status: upstream.status, headers: respHeaders });
}

export function apiProxy(
  pad: string,
  gebruikersnaam: string,
  init: RequestInit = {},
  /** Extra upstream response-headers om door te sturen naar de client (bijv. Content-Disposition). */
  forwardHeaders: string[] = [],
): Promise<Response> {
  const headers = buildBackendHeaders(
    gebruikersnaam,
    init.headers as Record<string, string>,
  );
  return proxy(pad, headers, init, forwardHeaders);
}

/**
 * Proxy voor `/v1/admin/*`-endpoints (en functioneel-admin routes zoals llm-calls): eist
 * `rol === "beheerder"` vóór het doorproxyen (werkwijze-story 038: BFF-rolautorisatie —
 * vóór deze story controleerde geen enkele admin-route de rol, alleen dat er een sessie was).
 */
export async function adminProxy(
  pad: string,
  init: RequestInit = {},
  forwardHeaders: string[] = [],
): Promise<Response> {
  const check = await requireBeheerder();
  if (check.fout) {
    const detail =
      check.fout === 401 ? "Niet geautoriseerd." : "Onvoldoende rechten.";
    return Response.json({ detail }, { status: check.fout });
  }
  return apiProxy(pad, check.gebruikersnaam, init, forwardHeaders);
}

/**
 * Publieke proxy voor endpoints die geen X-User-Id nodig hebben (bijv. setup-flow).
 * Stuurt alleen het machine-token mee.
 */
export function publiekApiProxy(
  pad: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${API_TOKEN}`,
    ...(init.headers as Record<string, string>),
  };
  return proxy(pad, headers, init, []);
}
