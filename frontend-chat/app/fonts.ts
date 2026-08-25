import { Fira_Sans } from "next/font/google";

// Rijkshuisstijl-typografie, zelfde keuze als frontend/app/fonts.ts (Fira Sans benadert
// Rijksoverheid Sans).
export const sans = Fira_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});
