import type { Metadata, Viewport } from "next";
import { SessionProvider } from "next-auth/react";
import { auth } from "@/auth";
import { AppShell } from "@/components/AppShell";
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
          <AppShell>{children}</AppShell>
          {session && <FeedbackKnop />}
        </SessionProvider>
      </body>
    </html>
  );
}
