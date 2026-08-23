import { adminProxy } from "@/lib/api-client";

export async function PUT(
  req: Request,
  { params }: { params: Promise<{ naam: string }> },
) {
  const [{ naam }, body] = await Promise.all([params, req.text()]);
  return adminProxy(`/v1/admin/profielen/${naam}`, { method: "PUT", body });
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ naam: string }> },
) {
  const { naam } = await params;
  return adminProxy(`/v1/admin/profielen/${naam}`, { method: "DELETE" });
}
