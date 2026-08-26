import "server-only";

export const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
export const API_TOKEN = process.env.API_TOKEN ?? "";

function buildBackendHeaders(gebruikersnaam: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${API_TOKEN}`,
    "X-User-Id": gebruikersnaam,
  };
}

/**
 * Bufferende BFF-proxy voor niet-streamende `api`-routes (`/v1/gesprekken/*`) — tweede
 * verbruiker naast `apiProxyStream`, vandaar nu een losse, gedeelde helper (feature-bouwen
 * regel 8).
 */
export async function apiProxy(
  pad: string,
  gebruikersnaam: string,
  init: RequestInit = {},
): Promise<Response> {
  const upstream = await fetch(`${API_BASE_URL}${pad}`, {
    ...init,
    headers: buildBackendHeaders(gebruikersnaam),
    cache: "no-store",
  });
  const tekst = await upstream.text();
  return new Response(tekst, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * Downloadende BFF-proxy: geeft de upstream-responsebody + Content-Type/-Disposition
 * ongewijzigd door — nodig voor binaire bestanden (`.../export`), waar `apiProxy` se
 * hardgecodeerde `application/json` en `.text()`-buffering een PDF zou corrumperen.
 */
export async function apiProxyDownload(
  pad: string,
  gebruikersnaam: string,
  init: RequestInit = {},
): Promise<Response> {
  const upstream = await fetch(`${API_BASE_URL}${pad}`, {
    ...init,
    headers: buildBackendHeaders(gebruikersnaam),
    cache: "no-store",
  });
  const headers: Record<string, string> = {
    "Content-Type":
      upstream.headers.get("Content-Type") ?? "application/octet-stream",
  };
  const disposition = upstream.headers.get("Content-Disposition");
  if (disposition) headers["Content-Disposition"] = disposition;
  return new Response(upstream.body, { status: upstream.status, headers });
}

/**
 * Streaming BFF-proxy: geeft de upstream-responsebody rechtstreeks door (geen buffering) —
 * nodig voor SSE-endpoints zoals `/v1/chat`.
 */
export async function apiProxyStream(
  pad: string,
  gebruikersnaam: string,
  init: RequestInit = {},
): Promise<Response> {
  const upstream = await fetch(`${API_BASE_URL}${pad}`, {
    ...init,
    headers: buildBackendHeaders(gebruikersnaam),
    cache: "no-store",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("Content-Type") ?? "text/event-stream",
    },
  });
}
