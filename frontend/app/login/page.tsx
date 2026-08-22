import { redirect } from "next/navigation";
import { Suspense } from "react";
import { auth } from "@/auth";
import { haalSetupStatus } from "@/lib/setup-status";
import { AuthFrame } from "@/components/auth/AuthFrame";
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
    <AuthFrame
      titel="Inloggen"
      onderschrift="Meld je aan om de wetsanalyses te bekijken en te bewerken."
    >
      <Suspense>
        <LoginFormulier />
      </Suspense>
    </AuthFrame>
  );
}
