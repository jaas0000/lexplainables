import { auth } from "@/auth";
import { apiProxy } from "@/lib/proxy";

export async function POST() {
  const session = await auth();
  if (!session?.user?.name)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  return apiProxy("/v1/berichten/lees-alles", session.user.name, { method: "POST" });
}
