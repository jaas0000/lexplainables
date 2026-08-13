import "server-only";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
const API_TOKEN = process.env.API_TOKEN ?? "";

export async function apiProxy(
  pad: string,
  gebruikersnaam: string,
  init: RequestInit = {},
): Promise<Response> {
  const upstream = await fetch(`${API_BASE_URL}${pad}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_TOKEN}`,
      "X-User-Id": gebruikersnaam,
      ...init.headers,
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
