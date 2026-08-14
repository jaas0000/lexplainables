import { cookies } from "next/headers";

export async function POST(req: Request) {
  const body = (await req.json()) as { callbackUrl?: unknown };

  let callbackUrl = "/";
  if (typeof body.callbackUrl === "string" && body.callbackUrl) {
    try {
      const base = new URL(req.url);
      const parsed = new URL(body.callbackUrl, base);
      if (parsed.origin === base.origin) {
        callbackUrl = parsed.pathname + parsed.search + parsed.hash;
      }
    } catch {
      // ongeldige URL — val terug op /
    }
  }

  const cookieStore = await cookies();
  cookieStore.set("disclaimer_geaccepteerd", "1", {
    httpOnly: true,
    path: "/",
    sameSite: "lax",
    maxAge: 365 * 24 * 3600,
  });

  return Response.json({ ok: true, redirect: callbackUrl });
}
