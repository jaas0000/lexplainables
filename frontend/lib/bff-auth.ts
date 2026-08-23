import "server-only";
import { auth } from "@/auth";

export async function requireSession(): Promise<string | null> {
  const session = await auth();
  return session?.user?.name ?? null;
}

/** Zelfde als `requireSession()`, maar eist bovendien `rol === "beheerder"` — voor
 *  `/api/admin/*`-routes (werkwijze-story 038: BFF-rolautorisatie). */
export async function requireBeheerder(): Promise<string | null> {
  const session = await auth();
  if (session?.user?.rol !== "beheerder") return null;
  return session.user.name ?? null;
}
