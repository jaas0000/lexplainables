"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { startLogin, getToken } from "@/lib/auth";

export default function LoginPagina() {
  const router = useRouter();

  useEffect(() => {
    if (getToken()) {
      router.replace("/");
    }
  }, [router]);

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
        <button
          className="btn btn-primary"
          onClick={() => {
            startLogin().catch(console.error);
          }}
          style={{ width: "100%" }}
        >
          Inloggen
        </button>
      </div>
    </div>
  );
}
