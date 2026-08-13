"use client";

import Link from "next/link";
import { useSession, signOut } from "next-auth/react";

export function NavigatieHeader() {
  const { data: session } = useSession();

  return (
    <header className="header">
      <div className="header-inner">
        <span className="logo">Wetsanalyse</span>
        <nav className="nav">
          <Link href="/" className="nav-link nav-link--active">
            Berichten
          </Link>
          <button
            className="nav-link nav-link--placeholder"
            disabled
            title="Nog niet beschikbaar"
          >
            Analisten
          </button>
          <button
            className="nav-link nav-link--placeholder"
            disabled
            title="Nog niet beschikbaar"
          >
            Projecten
          </button>
          <button
            className="nav-link nav-link--placeholder"
            disabled
            title="Nog niet beschikbaar"
          >
            Instellingen
          </button>
          {session?.user && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                marginLeft: "1rem",
                borderLeft: "1px solid rgba(255 255 255 / 0.25)",
                paddingLeft: "1rem",
              }}
            >
              <span
                style={{
                  fontSize: "0.875rem",
                  color: "rgb(var(--paper))",
                  opacity: 0.85,
                }}
              >
                {session.user.name}
              </span>
              <button
                className="nav-link"
                onClick={() => signOut({ callbackUrl: "/login" })}
              >
                Uitloggen
              </button>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
