import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

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
  const body = await request.text();
  return apiProxy(
    `/v1/annotatie/documenten/${encodeURIComponent(slug)}/status`,
    gebruikersnaam,
    {
      method: "POST",
      body,
    },
  );
}
