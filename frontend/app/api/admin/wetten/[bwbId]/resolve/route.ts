import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ bwbId: string }> },
) {
  const [gebruikersnaam, { bwbId }] = await Promise.all([
    requireSession(),
    params,
  ]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(`/v1/admin/wetten/${bwbId}/resolve`, gebruikersnaam, {
    method: "POST",
  });
}
