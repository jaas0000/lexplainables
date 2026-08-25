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
 * Streaming BFF-proxy: geeft de upstream-responsebody rechtstreeks door (geen buffering) —
 * nodig voor SSE-endpoints zoals `/v1/chat`. Losse variant naast een toekomstige bufferende
 * `apiProxy()` (die dit project nog niet heeft — frontend-chat heeft tot nu toe alleen deze
 * ene, streamende route nodig, zie story 056 §Wijzigingen).
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
