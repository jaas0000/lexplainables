"use client";

import { useState } from "react";
import Link from "next/link";

export function WaarschuwingIcoon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      style={{
        width: "1.75rem",
        height: "1.75rem",
        flexShrink: 0,
        marginTop: "0.125rem",
        color: "rgb(var(--waarschuwing))",
      }}
    >
      <path
        d="M12 3.2 22.2 20.4H1.8Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinejoin="round"
      />
      <path
        d="M12 9.2v4.4"
        stroke="rgb(var(--ink))"
        strokeWidth="2.2"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="12" cy="17" r="1.3" fill="rgb(var(--ink))" />
    </svg>
  );
}

export function MeldingWaarschuwing({
  titel,
  children,
}: {
  titel: string;
  children: React.ReactNode;
}) {
  return (
    <div className="melding melding-waarschuwing">
      <WaarschuwingIcoon />
      <div style={{ minWidth: 0, flex: 1 }}>
        <p style={{ fontWeight: 600, marginBottom: "0.25rem" }}>{titel}</p>
        <p style={{ fontSize: "0.875rem", marginTop: "0.25rem" }}>{children}</p>
      </div>
    </div>
  );
}

export function DisclaimerClient({
  alGeaccepteerd,
  callbackUrl,
}: {
  alGeaccepteerd: boolean;
  callbackUrl: string;
}) {
  const [bezig, setBezig] = useState(false);
  const [fout, setFout] = useState<string | null>(null);

  async function handleAccepteer() {
    setBezig(true);
    setFout(null);
    try {
      const res = await fetch("/api/disclaimer/accepteer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ callbackUrl }),
      });
      if (res.ok) {
        const data = (await res.json()) as { ok: boolean; redirect: string };
        window.location.href = data.redirect;
        return;
      }
    } catch {
      // val door naar de foutmelding hieronder
    }
    setFout("Er ging iets mis. Probeer het opnieuw.");
    setBezig(false);
  }

  return (
    <div style={{ maxWidth: "42rem", margin: "0 auto" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1
          style={{
            fontSize: "1.75rem",
            fontWeight: 600,
            marginBottom: "0.25rem",
          }}
        >
          Voordat je begint
        </h1>
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Lees dit even door. Het gaat over wat deze omgeving wel en niet is, en
          wat dat betekent voor het werk dat je hier doet.
        </p>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <MeldingWaarschuwing titel="Testomgeving, geen productie">
          Deze omgeving is een <strong>proof of concept</strong>. Er wordt
          actief aan ontwikkeld; beschikbaarheid en stabiliteit zijn niet
          gegarandeerd.
        </MeldingWaarschuwing>

        <MeldingWaarschuwing titel="Geen garantie op behoud van analyses">
          Analyses kunnen{" "}
          <strong>
            zonder waarschuwing vooraf verwijderd worden of verloren gaan
          </strong>
          . Bewaar een lokale kopie van elk rapport dat je wilt behouden.
        </MeldingWaarschuwing>

        <MeldingWaarschuwing titel="Geen garantie op een eindproduct">
          Wat je hier ziet is een tussenstand. De uiteindelijke toepassing kan
          er <strong>heel anders uitzien</strong> — of er komt nooit een
          eindproduct.
        </MeldingWaarschuwing>
      </div>

      {fout && (
        <p
          className="melding melding-fout"
          role="alert"
          style={{ marginBottom: "1rem" }}
        >
          {fout}
        </p>
      )}

      {alGeaccepteerd ? (
        <Link href="/" className="btn btn-secondary">
          Terug naar de startpagina
        </Link>
      ) : (
        <button
          className="btn btn-primary"
          onClick={handleAccepteer}
          disabled={bezig}
        >
          {bezig ? "Bezig…" : "Begrepen — doorgaan"}
        </button>
      )}
    </div>
  );
}
