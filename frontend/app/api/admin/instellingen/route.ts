import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function GET() {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy("/v1/admin/instellingen", gebruikersnaam);
}

export async function PUT(req: Request) {
  const [gebruikersnaam, body] = await Promise.all([
    requireSession(),
    req.text(),
  ]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy("/v1/admin/instellingen", gebruikersnaam, {
    method: "PUT",
    body,
  });
}
