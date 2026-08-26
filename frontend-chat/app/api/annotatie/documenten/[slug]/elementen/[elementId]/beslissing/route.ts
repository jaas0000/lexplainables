import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ slug: string; elementId: string }> };

export async function POST(
  request: Request,
  { params }: Params,
): Promise<Response> {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam) {
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  }
  const { slug, elementId } = await params;
  const body = await request.text();
  return apiProxy(
    `/v1/annotatie/documenten/${encodeURIComponent(slug)}/elementen/${encodeURIComponent(elementId)}/beslissing`,
    gebruikersnaam,
    { method: "POST", body },
  );
}
