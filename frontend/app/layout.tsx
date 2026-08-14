import Image from "next/image";
import Link from "next/link";
import { Fira_Sans } from "next/font/google";
import type { Metadata } from "next";
import { SessionProvider } from "next-auth/react";
import { auth } from "@/auth";
import { NavigatieHeader } from "@/components/NavigatieHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { FeedbackKnop } from "@/components/feedback/FeedbackKnop";
import "./globals.css";

const firaSans = Fira_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Wetsanalyse | Belastingdienst",
  description: "Beheerscherm voor wetsanalyse",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon-16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-48.png", sizes: "48x48", type: "image/png" },
      { url: "/favicon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();

  return (
    <html lang="nl" className={firaSans.variable}>
      <body>
        <SessionProvider session={session}>
          <header>
            {/* PoC-strip: alleen zichtbaar na inloggen, scrollt mee met de pagina */}
            {session && (
              <a
                href="/disclaimer"
                className="poc-strip"
              >
                <span className="poc-strip-inner">
                  <span className="poc-strip-vet">Testomgeving — proof of concept.</span>{" "}
                  Analyses kunnen verloren gaan.{" "}
                  <span className="poc-strip-link">Lees de voorwaarden</span>
                </span>
              </a>
            )}
            {/* Logobalk — wit, logo gecentreerd (Rijkshuisstijl) */}
            <div className="logobalk">
              <div className="logobalk-inner">
                <Link href="/" aria-label="Belastingdienst, naar startpagina" className="logobalk-link">
                  <Image
                    src="/belastingdienst-logo.svg"
                    alt="Belastingdienst"
                    width={275}
                    height={125}
                    priority
                    unoptimized
                    className="logobalk-logo"
                  />
                </Link>
              </div>
            </div>
            {/* Navigatiebalk — wit, applicatienaam + nav */}
            <div className="navbalk">
              <div className="navbalk-inner">
                <Link href="/" className="navbalk-titel">
                  Wetsanalyse
                </Link>
                <NavigatieHeader />
              </div>
            </div>
          </header>
          <main className="main">{children}</main>
          {session && <FeedbackKnop />}
          <SiteFooter />
        </SessionProvider>
      </body>
    </html>
  );
}
