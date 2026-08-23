import type { Metadata, Viewport } from "next";
import { SessionProvider } from "next-auth/react";
import { auth } from "@/auth";
import { AppShell } from "@/components/AppShell";
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
  modal,
}: {
  children: React.ReactNode;
  /** Parallel-route-slot voor `app/@modal/…` — het instellingenvenster als dialoog wanneer je
   *  er vanuit de app naartoe navigeert (werkwijze-story 042). `Dialog` is `fixed inset-0`, dus
   *  onafhankelijk van waar in de boom hij als sibling van `AppShell` staat. */
  modal: React.ReactNode;
}) {
  const session = await auth();

  return (
    <html lang="nl" className={`${sans.variable} ${mono.variable}`}>
      <body className="min-h-screen">
        <SessionProvider session={session}>
          <AppShell>{children}</AppShell>
          {session && modal}
        </SessionProvider>
      </body>
    </html>
  );
}
