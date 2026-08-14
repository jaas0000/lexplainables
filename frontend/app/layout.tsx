import Image from "next/image";
import Link from "next/link";
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

export const metadata = {
  title: "Wetsanalyse | Belastingdienst",
  description: "Beheerscherm voor wetsanalyse",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();

  return (
    <html lang="nl" className={firaSans.variable}>
      <body>
        <SessionProvider session={session}>
          <header>
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
        </SessionProvider>
      </body>
    </html>
  );
}
