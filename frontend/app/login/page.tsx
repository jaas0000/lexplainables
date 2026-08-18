import { redirect } from "next/navigation";
import { Suspense } from "react";
import { auth } from "@/auth";
import { haalSetupStatus } from "@/lib/setup-status";
import { LoginFormulier } from "@/components/auth/LoginFormulier";

export const metadata = { title: "Inloggen · Wetsanalyse" };

export default async function LoginPagina() {
  const session = await auth();
  if (session?.user) redirect("/");

  // Controleer of setup nog gedaan moet worden — zo ja, stuur door naar /setup.
  // Fail-closed: bij netwerk-fout (null) toon gewoon het login-formulier.
  const needsSetup = await haalSetupStatus();
  if (needsSetup) redirect("/setup");

  return (
    <div style={{ maxWidth: "24rem", margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.875rem", fontWeight: 600, lineHeight: 1.2, marginBottom: "0.25rem" }}>
          Inloggen
        </h1>
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Meld je aan om de wetsanalyses te bekijken en te bewerken.
        </p>
      </div>
      <Suspense>
        <LoginFormulier />
      </Suspense>
    </div>
  );
}
