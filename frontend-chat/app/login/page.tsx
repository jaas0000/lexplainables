import { redirect } from "next/navigation";
import { Suspense } from "react";
import { auth } from "@/auth";
import { AuthFrame } from "@/components/auth/AuthFrame";
import { LoginFormulier } from "@/components/auth/LoginFormulier";

export const metadata = { title: "Inloggen · Lex" };

export default async function LoginPagina() {
  const session = await auth();
  if (session?.user) redirect("/");

  return (
    <AuthFrame
      titel="Inloggen"
      onderschrift="Meld je aan om met Lex te chatten."
    >
      <Suspense>
        <LoginFormulier />
      </Suspense>
    </AuthFrame>
  );
}
