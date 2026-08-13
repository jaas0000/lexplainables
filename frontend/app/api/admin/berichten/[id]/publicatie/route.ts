import { auth } from "@/auth";
import { apiProxy } from "@/lib/proxy";

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const [session, { id }, body] = await Promise.all([
    auth(),
    params,
    req.text(),
  ]);
  if (!session?.user?.name)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(`/v1/admin/berichten/${id}/publicatie`, session.user.name, {
    method: "PATCH",
    body,
  });
}
