import "server-only";

export const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
const API_TOKEN = process.env.API_TOKEN ?? "";

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

export async function apiProxy(
  pad: string,
  gebruikersnaam: string,
  init: RequestInit = {},
  /** Extra upstream response-headers om door te sturen naar de client (bijv. Content-Disposition). */
  forwardHeaders: string[] = [],
): Promise<Response> {
  const upstream = await fetch(`${API_BASE_URL}${pad}`, {
    ...init,
    headers: buildBackendHeaders(
      gebruikersnaam,
      init.headers as Record<string, string>,
    ),
    cache: "no-store",
  });

  const body = upstream.status === 204 ? null : await upstream.text();
  const headers: Record<string, string> = {
    "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
  };
  for (const naam of forwardHeaders) {
    const waarde = upstream.headers.get(naam);
    if (waarde) headers[naam] = waarde;
  }
  return new Response(body, { status: upstream.status, headers });
}

/**
 * Publieke proxy voor endpoints die geen X-User-Id nodig hebben (bijv. setup-flow).
 * Stuurt alleen het machine-token mee.
 */
export async function publiekApiProxy(
  pad: string,
  init: RequestInit = {},
): Promise<Response> {
  const upstream = await fetch(`${API_BASE_URL}${pad}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_TOKEN}`,
      ...(init.headers as Record<string, string>),
    },
    cache: "no-store",
  });

  const body = upstream.status === 204 ? null : await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("Content-Type") ?? "application/json",
    },
  });
}
