"use client";

import { useState } from "react";
import Link from "next/link";
import {
  WaarschuwingIcoon,
  MeldingWaarschuwing,
} from "@/components/disclaimer/DisclaimerClient";

// Mockup — nepdata | twee varianten: vóór en ná acceptatie
// De PoC-strip staat in layout.tsx (boven het Belastingdienst-logo) — die zie je al hierboven.

export default function DisclaimerMockup() {
  const [geaccepteerd, setGeaccepteerd] = useState(false);

  return (
    <div>
      {/* Mockup-badge */}
      <div
        style={{
          position: "fixed",
          top: "0.75rem",
          right: "0.75rem",
          background: "rgb(var(--waarschuwing))",
          color: "#fff",
          fontSize: "0.7rem",
          fontWeight: 700,
          padding: "0.25rem 0.625rem",
          borderRadius: "999px",
          zIndex: 9999,
          letterSpacing: "0.03em",
        }}
      >
        mockup — nepdata
      </div>

      {/* Schakelaar voor de twee varianten */}
      <div
        style={{
          background: "rgb(var(--surface))",
          border: "1px solid rgb(var(--line))",
          borderRadius: 6,
          padding: "0.75rem 1rem",
          marginBottom: "2.5rem",
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          fontSize: "0.875rem",
        }}
      >
        <span style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>Variant:</span>
        <button
          className={`btn ${!geaccepteerd ? "btn-primary" : "btn-secondary"}`}
          onClick={() => setGeaccepteerd(false)}
        >
          Niet geaccepteerd
        </button>
        <button
          className={`btn ${geaccepteerd ? "btn-primary" : "btn-secondary"}`}
          onClick={() => setGeaccepteerd(true)}
        >
          Al geaccepteerd
        </button>
      </div>

      {/* /voorwaarden pagina-inhoud — gecentreerd (max-w-2xl mx-auto) */}
      <div style={{ maxWidth: "42rem", margin: "0 auto" }}>
        <div style={{ marginBottom: "1.5rem" }}>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 600, marginBottom: "0.25rem" }}>
            Voordat je begint
          </h1>
          <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
            Lees dit even door. Het gaat over wat deze omgeving wel en niet is, en wat dat
            betekent voor het werk dat je hier doet.
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginBottom: "1.5rem" }}>
          <MeldingWaarschuwing titel="Testomgeving, geen productie">
            Deze omgeving is een <strong>proof of concept</strong>. Er wordt actief aan
            ontwikkeld; beschikbaarheid en stabiliteit zijn niet gegarandeerd.
          </MeldingWaarschuwing>

          <MeldingWaarschuwing titel="Geen garantie op behoud van analyses">
            Analyses kunnen{" "}
            <strong>zonder waarschuwing vooraf verwijderd worden of verloren gaan</strong>.
            Bewaar een lokale kopie van elk rapport dat je wilt behouden.
          </MeldingWaarschuwing>

          <MeldingWaarschuwing titel="Geen garantie op een eindproduct">
            Wat je hier ziet is een tussenstand. De uiteindelijke toepassing kan er{" "}
            <strong>heel anders uitzien</strong> — of er komt nooit een eindproduct.
          </MeldingWaarschuwing>
        </div>

        {geaccepteerd ? (
          <Link href="/" className="btn btn-secondary">
            Terug naar de startpagina
          </Link>
        ) : (
          <button className="btn btn-primary" onClick={() => setGeaccepteerd(true)}>
            Begrepen — doorgaan
          </button>
        )}
      </div>
    </div>
  );
}
