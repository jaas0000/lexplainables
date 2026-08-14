import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function GET(req: Request) {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  const { search } = new URL(req.url);
  return apiProxy(`/v1/berichten${search}`, gebruikersnaam);
}
