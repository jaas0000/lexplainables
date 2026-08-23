import { adminProxy } from "@/lib/api-client";

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ gebruikersnaam: string }> },
) {
  const [{ gebruikersnaam }, body] = await Promise.all([params, req.text()]);
  return adminProxy(`/v1/admin/gebruikers/${gebruikersnaam}`, {
    method: "PATCH",
    body,
  });
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ gebruikersnaam: string }> },
) {
  const { gebruikersnaam } = await params;
  return adminProxy(`/v1/admin/gebruikers/${gebruikersnaam}`, {
    method: "DELETE",
  });
}
