import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ slug: string }> };

export async function GET(
  _request: Request,
  { params }: Params,
): Promise<Response> {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam) {
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  }
  const { slug } = await params;
  return apiProxy(
    `/v1/annotatie/documenten/${encodeURIComponent(slug)}`,
    gebruikersnaam,
  );
}
