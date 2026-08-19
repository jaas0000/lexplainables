"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { BerichtenPopover } from "@/components/berichten/BerichtenPopover";

export function NavigatieHeader() {
  const { data: session } = useSession();
  const pathname = usePathname();

  if (!session?.user) return null;

  const isBeheer =
    pathname.startsWith("/beheer") || pathname.startsWith("/mockup/beheer");
  const isAccount = pathname.startsWith("/account");
  const isWerkplek = pathname.startsWith("/werkplek");

  return (
    <nav className="nav">
      <button
        className="nav-link nav-link--placeholder"
        disabled
        title="Nog niet beschikbaar"
      >
        Projecten
      </button>
      <Link
        href="/werkplek"
        className={`nav-link${isWerkplek ? " nav-link--active" : ""}`}
      >
        Werkplek
      </Link>
      <button
        className="nav-link nav-link--placeholder"
        disabled
        title="Nog niet beschikbaar"
      >
        Assistent
      </button>
      <Link
        href="/account"
        className={`nav-link${isAccount ? " nav-link--active" : ""}`}
      >
        Account
      </Link>
      <Link
        href="/beheer"
        className={`nav-link${isBeheer ? " nav-link--active" : ""}`}
      >
        Beheer
      </Link>

      <button
        className="btn btn-primary"
        disabled
        title="Nog niet beschikbaar"
        style={{ marginLeft: "0.25rem", opacity: 0.45, cursor: "not-allowed" }}
      >
        Nieuwe analyse
      </button>

      <BerichtenPopover />

      <div className="nav-gebruiker">
        <span className="nav-gebruiker-naam">{session.user.name}</span>
        <button
          className="btn btn-secondary"
          style={{
            fontSize: "0.8rem",
            minHeight: "1.75rem",
            padding: "0.25rem 0.625rem",
          }}
          onClick={() => signOut({ callbackUrl: "/login" })}
        >
          Uitloggen
        </button>
      </div>
    </nav>
  );
}
