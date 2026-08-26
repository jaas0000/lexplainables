import { requireSession } from "@/lib/bff-auth";
import { apiProxyDownload } from "@/lib/api-client";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ slug: string }> };

export async function POST(
  request: Request,
  { params }: Params,
): Promise<Response> {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam) {
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  }
  const { slug } = await params;
  const qs = new URL(request.url).search;
  return apiProxyDownload(
    `/v1/annotatie/documenten/${encodeURIComponent(slug)}/export${qs}`,
    gebruikersnaam,
    { method: "POST" },
  );
}
