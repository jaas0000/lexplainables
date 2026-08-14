import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function GET() {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy("/v1/admin/berichten", gebruikersnaam);
}

export async function POST(req: Request) {
  const [gebruikersnaam, body] = await Promise.all([requireSession(), req.text()]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy("/v1/admin/berichten", gebruikersnaam, { method: "POST", body });
}
