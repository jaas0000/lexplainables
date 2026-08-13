import { redirect } from "next/navigation";
import { Suspense } from "react";
import { auth } from "@/auth";
import { LoginFormulier } from "@/components/auth/LoginFormulier";

export const metadata = { title: "Inloggen · Wetsanalyse" };

export default async function LoginPagina() {
  const session = await auth();
  if (session?.user) redirect("/");

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
      }}
    >
      <div
        className="card"
        style={{ maxWidth: 320, width: "100%", margin: "auto" }}
      >
        <h2 style={{ marginBottom: "1.25rem", textAlign: "center" }}>
          Inloggen
        </h2>
        <Suspense>
          <LoginFormulier />
        </Suspense>
      </div>
    </div>
  );
}
