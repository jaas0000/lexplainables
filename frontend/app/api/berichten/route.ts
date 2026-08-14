import { auth } from "@/auth";
import { apiProxy } from "@/lib/proxy";

export async function GET(req: Request) {
  const session = await auth();
  if (!session?.user?.name)
    return Response.json({ detail: "Niet geautoriseerd." }, { status: 401 });
  const { search } = new URL(req.url);
  return apiProxy(`/v1/berichten${search}`, session.user.name);
}
