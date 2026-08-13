import { Fira_Sans } from "next/font/google";
import { SessionProvider } from "next-auth/react";
import { auth } from "@/auth";
import { NavigatieHeader } from "@/components/NavigatieHeader";
import "./globals.css";

const firaSans = Fira_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-sans",
});

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const session = await auth();

  return (
    <html lang="nl" className={firaSans.variable}>
      <head>
        <title>Wetsanalyse — beheer</title>
        <meta name="description" content="Beheerscherm voor wetsanalyse" />
      </head>
      <body style={{ fontFamily: "var(--font-sans), system-ui, sans-serif" }}>
        <SessionProvider session={session}>
          <NavigatieHeader />
          <main className="main">{children}</main>
        </SessionProvider>
      </body>
    </html>
  );
}
