import Image from "next/image";
import Link from "next/link";
import type { Metadata, Viewport } from "next";
import { SessionProvider } from "next-auth/react";
import { auth } from "@/auth";
import { NavigatieHeader } from "@/components/NavigatieHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { FeedbackKnop } from "@/components/feedback/FeedbackKnop";
import { sans, mono } from "./fonts";
import "./globals.css";

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
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
};

export const viewport: Viewport = {
  themeColor: "#154273",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();

  return (
    <html lang="nl" className={`${sans.variable} ${mono.variable}`}>
      <body className="min-h-screen">
        <SessionProvider session={session}>
          <header className="relative z-30">
            {/* PoC-strip: alleen zichtbaar na inloggen, scrollt mee met de pagina */}
            {session && (
              <a href="/disclaimer" className="poc-strip">
                <span className="poc-strip-inner">
                  <span className="poc-strip-vet">
                    Testomgeving — proof of concept.
                  </span>{" "}
                  Analyses kunnen verloren gaan.{" "}
                  <span className="poc-strip-link">Lees de voorwaarden</span>
                </span>
              </a>
            )}
            {/* Logobalk (Rijkshuisstijl): het LINT staat altijd op de horizontale middenas,
                bovenaan op een witte achtergrond, met het woordmerk rechts ernaast; géén andere
                elementen in de balk. Lintbreedte 50px desktop, schaalt naar 45/40px (tablet/mobiel)
                via de root-font-size (100/90/80). Het lint zit op 25/275 van de logobreedte, dus
                we verschuiven het logo links 1,5625rem (= halve lintbreedte) ná left-1/2, zodat het
                lintmidden samenvalt met het balkmidden. De max-breedte voorkomt overflow op smalle
                schermen. Verticale marge = 0,5 lintbreedte (1,5625rem). */}
            <div className="border-b border-line bg-paper">
              <div className="mx-auto max-w-6xl px-6">
                <Link
                  href="/"
                  aria-label="Belastingdienst, naar startpagina"
                  className="relative left-1/2 block w-fit max-w-[calc(50%+1.5625rem)] -translate-x-[1.5625rem] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-lint"
                >
                  <Image
                    src="/belastingdienst-logo.svg"
                    alt="Belastingdienst"
                    width={275}
                    height={125}
                    priority
                    unoptimized
                    className="block h-auto w-[17.1875rem] max-w-full"
                  />
                </Link>
              </div>
            </div>
            {/* Navigatiebalk — onder de logobalk (Rijkshuisstijl: geen navigatie in/boven het lint).
                De applicatienaam "Wetsanalyse" hoort hier, niet in de logobalk. */}
            <div className="relative border-b border-line bg-paper">
              <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6">
                <Link
                  href="/"
                  className="shrink-0 py-3 text-sm font-semibold text-lint focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lint"
                >
                  Wetsanalyse
                </Link>
                <NavigatieHeader />
              </div>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
          {session && <FeedbackKnop />}
          <SiteFooter />
        </SessionProvider>
      </body>
    </html>
  );
}
