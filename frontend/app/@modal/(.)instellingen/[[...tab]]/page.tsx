import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { InstellingenDialog } from "@/components/instellingen/InstellingenDialog";
import { isAdminTab, tabUitPad } from "@/lib/instellingen";

/** Intercepting route: navigeer je binnen de app naar /instellingen/…, dan vult dit het `@modal`-
 *  slot en verschijnt het venster als dialoog over de huidige pagina. Bij een directe link of een
 *  refresh slaat Next dit over en rendert `app/instellingen/[[...tab]]/page.tsx` als volle pagina
 *  (werkwijze-story 042, poort van `wetsanalyse-ai`). */
export default async function InstellingenModal({
  params,
}: {
  params: Promise<{ tab?: string[] }>;
}) {
  const { tab } = await params;
  const actief = tabUitPad(tab);
  const session = await auth();
  const isBeheerder = session?.user?.rol === "beheerder";

  // Zie de toelichting in app/instellingen/[[...tab]]/page.tsx: geen sessie → /login, wel een
  // sessie maar de verkeerde rol → /.
  if (isAdminTab(actief) && !isBeheerder)
    redirect(session?.user ? "/" : "/login");

  return <InstellingenDialog actief={actief} isBeheerder={isBeheerder} />;
}
