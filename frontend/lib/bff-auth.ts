import "server-only";
import { auth } from "@/auth";

export async function requireSession(): Promise<string | null> {
  const session = await auth();
  return session?.user?.name ?? null;
}

/** Resultaat van `requireBeheerder()` — onderscheidt bewust twee foutgevallen i.p.v. ze
 *  allebei plat te slaan tot 403: `401` (geen geldige sessie — de client (`beheerFetch`)
 *  reageert hierop met een redirect naar `/login`, o.a. nodig voor de live-rol-check-flow:
 *  een gedeactiveerd account moet nog steeds naar login gestuurd worden) versus `403`
 *  (geldige sessie, maar geen beheerder-rol — geen redirect nodig, gewoon onbevoegd).
 *  Werkwijze-story 038: BFF-rolautorisatie. */
export type BeheerderCheck =
  | { gebruikersnaam: string; fout?: undefined }
  | { gebruikersnaam?: undefined; fout: 401 | 403 };

export async function requireBeheerder(): Promise<BeheerderCheck> {
  const session = await auth();
  if (!session?.user?.name) return { fout: 401 };
  if (session.user.rol !== "beheerder") return { fout: 403 };
  return { gebruikersnaam: session.user.name };
}
