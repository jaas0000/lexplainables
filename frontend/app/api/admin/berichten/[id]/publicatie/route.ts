import { adminProxy } from "@/lib/api-client";

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const [{ id }, body] = await Promise.all([params, req.text()]);
  return adminProxy(`/v1/admin/berichten/${id}/publicatie`, {
    method: "PATCH",
    body,
  });
}
