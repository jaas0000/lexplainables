import type { Metadata } from "next";
import { Fira_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const firaSans = Fira_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Wetsanalyse — beheer",
  description: "Beheerscherm voor wetsanalyse",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="nl" className={firaSans.variable}>
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
            </nav>
          </div>
        </header>
        <main className="main">{children}</main>
      </body>
    </html>
  );
}
