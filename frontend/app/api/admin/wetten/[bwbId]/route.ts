import { adminProxy } from "@/lib/api-client";

export async function PUT(
  req: Request,
  { params }: { params: Promise<{ bwbId: string }> },
) {
  const [{ bwbId }, body] = await Promise.all([params, req.text()]);
  return adminProxy(`/v1/admin/wetten/${bwbId}`, { method: "PUT", body });
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ bwbId: string }> },
) {
  const { bwbId } = await params;
  return adminProxy(`/v1/admin/wetten/${bwbId}`, { method: "DELETE" });
}
