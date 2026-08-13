import { auth } from "@/auth";
import { apiProxy } from "@/lib/proxy";

export async function GET() {
  const session = await auth();
  if (!session?.user?.name)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy("/v1/admin/berichten", session.user.name);
}

export async function POST(req: Request) {
  const [session, body] = await Promise.all([auth(), req.text()]);
  if (!session?.user?.name)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy("/v1/admin/berichten", session.user.name, {
    method: "POST",
    body,
  });
}
