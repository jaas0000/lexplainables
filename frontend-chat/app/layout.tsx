import type { Metadata } from "next";
import { SessionProvider } from "next-auth/react";
import { auth } from "@/auth";
import { sans } from "./fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lex | Belastingdienst",
  description: "Chat met Lex over wet- en regelgeving",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();

  return (
    <html lang="nl" className={sans.variable}>
      <body className="min-h-screen">
        <SessionProvider session={session}>{children}</SessionProvider>
      </body>
    </html>
  );
}
