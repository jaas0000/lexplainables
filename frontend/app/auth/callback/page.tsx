"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { handleCallback } from "@/lib/auth";

function CallbackInhoud() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [fout, setFout] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFout("Geen autorisatiecode ontvangen van Keycloak.");
      return;
    }

    handleCallback(code)
      .then(() => {
        router.replace("/");
      })
      .catch((err: unknown) => {
        setFout(
          err instanceof Error
            ? err.message
            : "Onbekende fout bij het inloggen.",
        );
      });
  }, [searchParams, router]);

  if (fout) {
    return (
      <div
        className="card"
        style={{ maxWidth: 400, margin: "auto", textAlign: "center" }}
      >
        <p
          role="alert"
          style={{ color: "rgb(213 43 30)", marginBottom: "1rem" }}
        >
          {fout}
        </p>
        <Link href="/login" className="btn btn-secondary">
          Terug naar inloggen
        </Link>
      </div>
    );
  }

  return (
    <div style={{ textAlign: "center", padding: "2rem" }}>
      <p>Laden…</p>
    </div>
  );
}

export default function CallbackPagina() {
  return (
    <Suspense
      fallback={
        <div style={{ textAlign: "center", padding: "2rem" }}>
          <p>Laden…</p>
        </div>
      }
    >
      <CallbackInhoud />
    </Suspense>
  );
}
