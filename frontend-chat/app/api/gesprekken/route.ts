import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam) {
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  }
  const qs = new URL(request.url).search;
  return apiProxy(`/v1/gesprekken${qs}`, gebruikersnaam);
}

export async function POST(request: Request): Promise<Response> {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam) {
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  }
  const body = await request.text();
  return apiProxy("/v1/gesprekken", gebruikersnaam, { method: "POST", body });
}
