import { adminProxy } from "@/lib/api-client";

export async function PUT(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const [{ id }, body] = await Promise.all([params, req.text()]);
  return adminProxy(`/v1/admin/berichten/${id}`, { method: "PUT", body });
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return adminProxy(`/v1/admin/berichten/${id}`, { method: "DELETE" });
}
