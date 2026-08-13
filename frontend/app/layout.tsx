"use client";

import { useEffect, useState } from "react";
import { Fira_Sans } from "next/font/google";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getToken, getGebruikersnaam, clearAuth } from "@/lib/auth";
import "./globals.css";

const firaSans = Fira_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-sans",
});

const AUTH_VRIJE_ROUTES = ["/login", "/auth/callback"];

export default function RootLayout({ children }: LayoutProps<"/">) {
  const router = useRouter();
  const pathname = usePathname();
  const [isIngelogd, setIsIngelogd] = useState(false);
  const [gebruikersnaam, setGebruikersnaam] = useState<string | null>(null);

  useEffect(() => {
    const huidigToken = getToken();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsIngelogd(!!huidigToken);
    setGebruikersnaam(getGebruikersnaam());

    if (!huidigToken && !AUTH_VRIJE_ROUTES.includes(pathname ?? "")) {
      router.replace("/login");
    }
  }, [pathname, router]);

  function uitloggen() {
    clearAuth();
    router.push("/login");
  }

  return (
    <html lang="nl" className={firaSans.variable}>
      <head>
        <title>Wetsanalyse — beheer</title>
        <meta name="description" content="Beheerscherm voor wetsanalyse" />
      </head>
      <body style={{ fontFamily: "var(--font-sans), system-ui, sans-serif" }}>
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
              {isIngelogd && (
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
                    {gebruikersnaam}
                  </span>
                  <button className="nav-link" onClick={uitloggen}>
                    Uitloggen
                  </button>
                </div>
              )}
            </nav>
          </div>
        </header>
        <main className="main">{children}</main>
      </body>
    </html>
  );
}
