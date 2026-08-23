"use client";

import Image from "next/image";
import Link from "next/link";
import { useRef, useState } from "react";
import { signOut } from "next-auth/react";
import { BerichtenPopover } from "@/components/berichten/BerichtenPopover";
import { NAV_SECTIES, actieveSectie } from "@/lib/nav-secties";
import { useClickOutside } from "@/lib/useClickOutside";

interface Props {
  pathname: string | null;
  naam: string;
  /** Bepaalt of de "Beheer"-link getoond wordt (werkwijze-story 038: BFF-rolautorisatie). */
  rol: string;
  /** Mobiel: staat de off-canvas drawer open, en hoe sluit hij. */
  drawerOpen?: boolean;
  onDrawerSluit?: () => void;
}

/** De linker-sidebar van de app: bovenin het Belastingdienst-logo, daaronder de navigatie, onderin
 *  het gebruikersblok. Vervangt de oude horizontale logobalk + navigatiebalk (Rijkshuisstijl-
 *  conform via de sidebar-vormtaal, niet het gecentreerde lint).
 *
 *  Nog geen gesprekkenlijst zoals in de bron-app — die hoort bij de analyse-werkplek die pas in
 *  fase 4 gebouwd wordt. Deze skelet-versie draagt alvast de vorm (logo, navigatie, gebruikersblok,
 *  mobiele drawer) zodat fase 4 'm kan vullen in plaats van opnieuw op te zetten.
 */
export function AppSidebar({
  pathname,
  naam,
  rol,
  drawerOpen = false,
  onDrawerSluit,
}: Props) {
  return (
    <>
      <aside className="hidden w-[17rem] shrink-0 border-r border-line bg-surface print:hidden lg:block">
        <SidebarInhoud pathname={pathname} naam={naam} rol={rol} />
      </aside>

      {drawerOpen && onDrawerSluit && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Menu sluiten"
            onClick={onDrawerSluit}
            className="absolute inset-0 bg-ink/30"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Navigatie"
            className="absolute inset-y-0 left-0 flex w-[82%] max-w-xs flex-col bg-surface shadow-xl"
          >
            <SidebarInhoud
              pathname={pathname}
              naam={naam}
              rol={rol}
              onSluit={onDrawerSluit}
            />
          </div>
        </div>
      )}
    </>
  );
}

function SidebarInhoud({
  pathname,
  naam,
  rol,
  onSluit,
}: {
  pathname: string | null;
  naam: string;
  rol: string;
  onSluit?: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const actief = actieveSectie(pathname);

  useClickOutside(menuRef, menuOpen, () => setMenuOpen(false));

  return (
    <div className="flex h-full flex-col">
      <div className="relative flex items-center justify-between px-4 pt-[max(0.75rem,env(safe-area-inset-top))]">
        <Link
          href="/"
          aria-label="Belastingdienst, naar startpagina"
          className="block py-1"
        >
          <Image
            src="/belastingdienst-logo.svg"
            alt="Belastingdienst"
            width={275}
            height={125}
            unoptimized
            priority
            className="block h-auto w-[8.5rem]"
          />
        </Link>
        <div className="flex items-center">
          <BerichtenPopover />
          {onSluit && (
            <button
              type="button"
              onClick={onSluit}
              aria-label="Menu sluiten"
              className="focus-ring rounded-kaart p-2 text-muted transition-colors hover:bg-paper hover:text-ink lg:hidden"
            >
              <svg
                viewBox="0 0 20 20"
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                aria-hidden="true"
              >
                <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
              </svg>
            </button>
          )}
        </div>
      </div>

      <div className="px-3 pb-2 pt-3">
        <Link
          href="/projecten/nieuw"
          onClick={onSluit}
          className="flex min-h-[44px] w-full items-center gap-2 rounded-kaart border border-line bg-paper px-3 py-2.5 text-sm font-medium text-lint shadow-zacht transition-colors hover:bg-white hover:shadow-kaart"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden
          >
            <path d="M12 5v14M5 12h14" />
          </svg>
          Nieuwe analyse
        </Link>
      </div>

      <nav className="flex-1 px-3 pb-2">
        {NAV_SECTIES.filter(
          (s) =>
            s.pad !== "/account" &&
            s.pad !== "/berichten" &&
            s.pad !== "/wetcatalogus" &&
            (s.pad !== "/beheer" || rol === "beheerder"),
        ).map((sectie) => (
          <NavLink
            key={sectie.pad}
            href={sectie.pad}
            actief={actief?.pad === sectie.pad}
            onSluit={onSluit}
          >
            {sectie.titel}
          </NavLink>
        ))}
        <span className="flex min-h-[36px] cursor-not-allowed items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-faint coarse:min-h-[44px]">
          Assistent
        </span>
      </nav>

      <div
        ref={menuRef}
        className="relative border-t border-line px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2"
      >
        {menuOpen && (
          <div className="absolute inset-x-3 bottom-full mb-1 overflow-hidden rounded-kaart border border-line bg-paper shadow-kaart">
            <Link
              href="/account"
              className="block px-3 py-2.5 text-sm text-ink transition-colors hover:bg-surface"
              onClick={() => {
                setMenuOpen(false);
                onSluit?.();
              }}
            >
              Account
            </Link>
            <button
              type="button"
              onClick={() => signOut({ callbackUrl: "/login" })}
              className="block w-full px-3 py-2.5 text-left text-sm text-fout transition-colors hover:bg-fout/10"
            >
              Uitloggen
            </button>
          </div>
        )}
        <button
          type="button"
          onClick={() => setMenuOpen((o) => !o)}
          aria-expanded={menuOpen}
          aria-label="Gebruikersmenu"
          className="flex min-h-[44px] w-full items-center gap-2.5 rounded-kaart px-2 py-2 text-left transition-colors hover:bg-paper"
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-lint text-xs font-semibold text-paper">
            {(naam || "?").slice(0, 2).toUpperCase()}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-ink">
              {naam || "Gebruiker"}
            </span>
          </span>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            className="shrink-0 text-muted"
            aria-hidden
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
      </div>
    </div>
  );
}

function NavLink({
  href,
  actief,
  onSluit,
  children,
}: {
  href: string;
  actief: boolean;
  onSluit?: () => void;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      onClick={onSluit}
      aria-current={actief ? "page" : undefined}
      className={`focus-ring flex min-h-[36px] items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors coarse:min-h-[44px] ${
        actief ? "bg-lint/10 font-medium text-lint" : "text-ink hover:bg-paper"
      }`}
    >
      {children}
    </Link>
  );
}
