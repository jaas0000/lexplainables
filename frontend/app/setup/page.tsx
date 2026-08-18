import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { haalSetupStatus } from "@/lib/setup-status";
import SetupFormulier from "./SetupFormulier";

export const metadata = { title: "Initiële beheerder aanmaken · Wetsanalyse" };

export default async function SetupPagina() {
  // Een ingelogde gebruiker hoeft de setup niet te doen.
  const session = await auth();
  if (session?.user) redirect("/");

  // Controleer of setup al gedaan is; zo ja, redirect naar login.
  // Fail-open: als de API niet bereikbaar is, toon het formulier
  // (de backend weigert setup toch al als ingericht: 409).
  const needsSetup = (await haalSetupStatus()) ?? true;
  if (!needsSetup) redirect("/login");

  return (
    <div style={{ maxWidth: "24rem", margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1
          style={{
            fontSize: "1.875rem",
            fontWeight: 600,
            lineHeight: 1.2,
            marginBottom: "0.25rem",
          }}
        >
          Eerste beheerder aanmaken
        </h1>
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Er bestaat nog geen account. Maak hier eenmalig de eerste beheerder
          aan; daarna voeg je verdere gebruikers toe via het beheerscherm.
        </p>
      </div>
      <SetupFormulier />
    </div>
  );
}
