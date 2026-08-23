import { adminProxy } from "@/lib/api-client";

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return adminProxy(`/v1/admin/feedback/${id}`, { method: "DELETE" });
}
