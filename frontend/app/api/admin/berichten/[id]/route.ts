import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function PUT(
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
  return apiProxy(`/v1/admin/berichten/${id}`, gebruikersnaam, {
    method: "PUT",
    body,
  });
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const [gebruikersnaam, { id }] = await Promise.all([
    requireSession(),
    params,
  ]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(`/v1/admin/berichten/${id}`, gebruikersnaam, {
    method: "DELETE",
  });
}
