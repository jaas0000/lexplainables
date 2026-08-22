"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { useSession } from "next-auth/react";
import { AppSidebar } from "@/components/AppSidebar";
import { MobileTopbar } from "@/components/MobileTopbar";
import { actieveSectie } from "@/lib/nav-secties";

/** De app-schil: sidebar (desktop) of hamburger + drawer (mobiel) om het hoofdgebied heen.
 *  Vervangt de oude horizontale logobalk + navigatiebalk + footer.
 *
 *  Zonder sessie (login/setup/disclaimer-gate) geen schil — die schermen dragen hun eigen kader
 *  (`AuthFrame`). `pathname` en `naam` worden hier één keer opgehaald en als prop doorgegeven aan
 *  `AppSidebar`, zodat die niet zijn eigen `usePathname`/`useSession` hoeft te resubscriben. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (!session?.user) return <>{children}</>;

  return (
    <div className="flex min-h-screen min-h-[100dvh]">
      <AppSidebar
        pathname={pathname}
        naam={session.user.name ?? ""}
        drawerOpen={drawerOpen}
        onDrawerSluit={() => setDrawerOpen(false)}
      />
      <div className="flex min-h-screen min-h-[100dvh] flex-1 flex-col">
        <MobileTopbar
          titel={actieveSectie(pathname)?.titel ?? "Wetsanalyse"}
          onOpenSidebar={() => setDrawerOpen(true)}
        />
        <a href="/disclaimer" className="poc-strip print:hidden">
          <span className="poc-strip-inner">
            <span className="poc-strip-vet">
              Testomgeving — proof of concept.
            </span>{" "}
            Analyses kunnen verloren gaan.{" "}
            <span className="poc-strip-link">Lees de voorwaarden</span>
          </span>
        </a>
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
          {children}
        </main>
      </div>
    </div>
  );
}
