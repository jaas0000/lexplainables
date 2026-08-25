import "server-only";
import { auth } from "@/auth";

export async function requireSession(): Promise<string | null> {
  const session = await auth();
  return session?.user?.name ?? null;
}
