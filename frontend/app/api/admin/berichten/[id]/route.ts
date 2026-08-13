import { auth } from "@/auth";
import { apiProxy } from "@/lib/proxy";

export async function PUT(
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
  return apiProxy(`/v1/admin/berichten/${id}`, session.user.name, {
    method: "PUT",
    body,
  });
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const [session, { id }] = await Promise.all([auth(), params]);
  if (!session?.user?.name)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy(`/v1/admin/berichten/${id}`, session.user.name, {
    method: "DELETE",
  });
}
