import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ id: string }> };

export async function POST(
  request: Request,
  { params }: Params,
): Promise<Response> {
  const gebruikersnaam = await requireSession();
  if (!gebruikersnaam) {
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  }
  const { id } = await params;
  const body = await request.text();
  return apiProxy(
    `/v1/gesprekken/${encodeURIComponent(id)}/berichten`,
    gebruikersnaam,
    {
      method: "POST",
      body,
    },
  );
}
