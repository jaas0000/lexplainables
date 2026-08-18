import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function PUT(
  req: Request,
  { params }: { params: Promise<{ naam: string }> },
) {
  const [gebruikersnaam, { naam }, body] = await Promise.all([
    requireSession(),
    params,
    req.text(),
  ]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(`/v1/admin/profielen/${naam}`, gebruikersnaam, {
    method: "PUT",
    body,
  });
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ naam: string }> },
) {
  const [gebruikersnaam, { naam }] = await Promise.all([
    requireSession(),
    params,
  ]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(`/v1/admin/profielen/${naam}`, gebruikersnaam, {
    method: "DELETE",
  });
}
