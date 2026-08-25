import { requireSession } from "@/lib/bff-auth";
import { apiProxyStream } from "@/lib/api-client";

// SSE-stream — nooit cachen/statisch optimaliseren.
export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<Response> {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam) {
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  }

  const body = await request.text();
  return apiProxyStream("/v1/chat", gebruikersnaam, {
    method: "POST",
    body,
  });
}
