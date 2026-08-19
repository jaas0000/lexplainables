import { requireSession } from "@/lib/bff-auth";
import { apiProxy } from "@/lib/api-client";

export async function PUT(
  req: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const [gebruikersnaam, { slug }, body] = await Promise.all([
    requireSession(),
    params,
    req.text(),
  ]);
  if (!gebruikersnaam)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(
    `/v1/annotatie/documenten/${slug}/elementen`,
    gebruikersnaam,
    { method: "PUT", body },
  );
}
