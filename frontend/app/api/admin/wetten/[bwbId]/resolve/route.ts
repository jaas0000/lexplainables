import { adminProxy } from "@/lib/api-client";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ bwbId: string }> },
) {
  const { bwbId } = await params;
  return adminProxy(`/v1/admin/wetten/${bwbId}/resolve`, { method: "POST" });
}
