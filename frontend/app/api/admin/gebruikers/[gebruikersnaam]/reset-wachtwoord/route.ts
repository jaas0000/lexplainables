import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ gebruikersnaam: string }> },
) {
  const [sessieGebruikersnaam, { gebruikersnaam }] = await Promise.all([
    requireSession(),
    params,
  ]);
  if (!sessieGebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(
    `/v1/admin/gebruikers/${gebruikersnaam}/reset-wachtwoord`,
    sessieGebruikersnaam,
    { method: "POST" },
  );
}
