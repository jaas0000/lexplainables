import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Berichten beheren",
  description: "Beheerscherm voor berichten (release notes/aankondigingen)",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="nl">
      <body>{children}</body>
    </html>
  );
}
