import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const [gebruikersnaam, { slug }] = await Promise.all([
    requireSession(),
    params,
  ]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(`/v1/annotatie/documenten/${slug}`, gebruikersnaam);
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const [gebruikersnaam, { slug }] = await Promise.all([
    requireSession(),
    params,
  ]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(`/v1/annotatie/documenten/${slug}`, gebruikersnaam, {
    method: "DELETE",
  });
}
