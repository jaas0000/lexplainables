"use client";

import Link from "next/link";
import { useSession, signOut } from "next-auth/react";

export function NavigatieHeader() {
  const { data: session } = useSession();

  if (!session?.user) return null;

  return (
    <nav className="nav">
      <Link href="/" className="nav-link nav-link--active">
        Berichten
      </Link>
      <button className="nav-link nav-link--placeholder" disabled title="Nog niet beschikbaar">
        Analisten
      </button>
      <button className="nav-link nav-link--placeholder" disabled title="Nog niet beschikbaar">
        Projecten
      </button>
      <button className="nav-link nav-link--placeholder" disabled title="Nog niet beschikbaar">
        Instellingen
      </button>
      <div className="nav-gebruiker">
        <span className="nav-gebruiker-naam">{session.user.name}</span>
        <button className="btn btn-secondary" style={{ fontSize: "0.8rem", minHeight: "1.75rem", padding: "0.25rem 0.625rem" }} onClick={() => signOut({ callbackUrl: "/login" })}>
          Uitloggen
        </button>
      </div>
    </nav>
  );
}
