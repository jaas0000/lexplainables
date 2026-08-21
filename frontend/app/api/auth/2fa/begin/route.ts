import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function POST() {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy("/v1/auth/2fa/begin", gebruikersnaam, { method: "POST" });
}
