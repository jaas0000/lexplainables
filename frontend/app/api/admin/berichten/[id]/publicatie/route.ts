import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const [gebruikersnaam, { id }, body] = await Promise.all([
    requireSession(),
    params,
    req.text(),
  ]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(`/v1/admin/berichten/${id}/publicatie`, gebruikersnaam, {
    method: "PATCH",
    body,
  });
}
