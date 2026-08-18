/**
 * SSE-proxy: pipe de Server-Sent Events-stroom van de API naar de browser.
 *
 * `apiProxy` is niet geschikt voor streaming (het buffert de volledige body). Hier
 * wordt de upstream-body rechtstreeks als ReadableStream doorgegeven zodat de browser
 * de events in real-time ontvangt.
 */

import "server-only";
import { requireSession } from "@/lib/bff-auth";
import { API_BASE_URL, buildBackendHeaders } from "@/lib/api-client";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const [gebruikersnaam, { id }] = await Promise.all([
    requireSession(),
    params,
  ]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });

  const upstream = await fetch(`${API_BASE_URL}/v1/projecten/${id}/events`, {
    headers: buildBackendHeaders(gebruikersnaam, {
      Accept: "text/event-stream",
    }),
    cache: "no-store",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
