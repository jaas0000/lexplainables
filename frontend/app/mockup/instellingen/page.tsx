"use client";

import React, { useState } from "react";
import { SectieHeader } from "@/components/beheer/SectieHeader";

type Variant = "uit" | "aan" | "bezig-aanzetten" | "bezig-uitzetten" | "fout";

const VARIANTEN: { waarde: Variant; label: string }[] = [
  { waarde: "uit", label: "Uit (standaard)" },
  { waarde: "aan", label: "Aan" },
  { waarde: "bezig-aanzetten", label: "Bezig — aanzetten" },
  { waarde: "bezig-uitzetten", label: "Bezig — uitzetten" },
  { waarde: "fout", label: "Foutmelding" },
];

export default function InstellingenMockup() {
  const [variant, setVariant] = useState<Variant>("uit");

  const capture = variant === "aan" || variant === "bezig-uitzetten";
  const bezig = variant === "bezig-aanzetten" || variant === "bezig-uitzetten";
  const fout = variant === "fout";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Variant-schakelaar (mockup-navigatie, niet in de echte pagina) */}
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          flexWrap: "wrap",
          alignItems: "center",
          padding: "0.75rem 1rem",
          background: "rgb(var(--waarschuwing) / 0.08)",
          borderRadius: "6px",
          border: "1px solid rgb(var(--waarschuwing) / 0.3)",
          fontSize: "0.8rem",
        }}
      >
        <span style={{ color: "rgb(var(--waarschuwing))", fontWeight: 500, fontSize: "0.75rem" }}>
          mockup — nepdata
        </span>
        <span style={{ color: "rgb(var(--faint))", marginLeft: "0.5rem" }}>Variant:</span>
        {VARIANTEN.map((v) => (
          <button
            key={v.waarde}
            type="button"
            onClick={() => setVariant(v.waarde)}
            style={{
              padding: "0.25rem 0.625rem",
              borderRadius: "4px",
              border: "1px solid",
              fontSize: "0.8rem",
              cursor: "pointer",
              fontFamily: "inherit",
              background: variant === v.waarde ? "rgb(var(--lint))" : "rgb(var(--paper))",
              color: variant === v.waarde ? "rgb(var(--paper))" : "rgb(var(--muted))",
              borderColor: variant === v.waarde ? "rgb(var(--lint))" : "rgb(var(--line))",
            }}
          >
            {v.label}
          </button>
        ))}
      </div>

      {/* Paginakop — zelfde als wetsanalyse-ai beheer-pagina (grote blauwe h1, max-w gecentreerd) */}
      <div style={{ maxWidth: "56rem", margin: "0 auto", width: "100%" }}>
        <div style={{ marginBottom: "1.5rem" }}>
          <h1
            style={{
              fontSize: "1.875rem",
              fontWeight: 600,
              color: "rgb(var(--lint))",
            }}
          >
            Instellingen
          </h1>
          <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
            Runtime-configuratie van de applicatie. Wijzigingen zijn direct actief (maximaal 10 seconden cache).
          </p>
        </div>

        {/* Sectie LLM-invoer vastleggen */}
        <section style={{ marginBottom: "2rem" }}>
          <SectieHeader
            titel="LLM-invoer vastleggen"
            subtitel="prompts + respons, voor analyse"
          />

          {/* Kaart — zelfde als wetsanalyse-ai LlmCapturePanel */}
          <div
            style={{
              marginBottom: "1rem",
              padding: "1rem",
              background: "rgb(var(--surface))",
              border: "1px solid rgb(var(--line))",
              borderRadius: "6px",
            }}
          >
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: "0.75rem",
              }}
            >
              {/* Tekst links */}
              <div style={{ flex: 1, minWidth: "16rem" }}>
                <p style={{ fontSize: "0.875rem", fontWeight: 500, color: "rgb(var(--ink))" }}>
                  Vastleggen van LLM-calls
                </p>
                <p style={{ marginTop: "0.125rem", fontSize: "0.75rem", color: "rgb(var(--muted))" }}>
                  Legt per call de letterlijke system/user-prompt en de ruwe respons vast (incl.
                  auto-correctie en gefaalde calls). Standaard uit; aanzetten kost extra opslag per analyse.
                </p>
              </div>

              {/* Tag + knop rechts */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <span
                  style={{
                    fontSize: "0.75rem",
                    padding: "0.125rem 0.5rem",
                    borderRadius: "9999px",
                    background: capture
                      ? "rgb(var(--succes) / 0.1)"
                      : "rgb(var(--faint) / 0.15)",
                    color: capture ? "rgb(var(--succes))" : "rgb(var(--muted))",
                    border: `1px solid ${capture ? "rgb(var(--succes) / 0.3)" : "rgb(var(--line))"}`,
                    fontWeight: 500,
                  }}
                >
                  {capture ? "aan" : "uit"}
                </span>
                <button
                  type="button"
                  disabled={bezig}
                  style={{
                    padding: "0.5rem 1rem",
                    borderRadius: "4px",
                    border: "none",
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    fontFamily: "inherit",
                    cursor: bezig ? "default" : "pointer",
                    background: capture ? "rgb(var(--surface))" : "rgb(var(--lint))",
                    color: capture ? "rgb(var(--ink))" : "white",
                    boxShadow: capture ? "inset 0 0 0 1px rgb(var(--line))" : "none",
                    opacity: bezig ? 0.6 : 1,
                  }}
                >
                  {bezig ? "Bezig…" : capture ? "Uitzetten" : "Aanzetten"}
                </button>
              </div>
            </div>

            {/* Foutmelding */}
            {fout && (
              <div
                role="alert"
                style={{
                  marginTop: "0.75rem",
                  padding: "0.5rem 0.875rem",
                  borderRadius: "4px",
                  background: "rgb(var(--fout) / 0.08)",
                  border: "1px solid rgb(var(--fout) / 0.3)",
                  color: "rgb(var(--fout))",
                  fontSize: "0.8125rem",
                }}
              >
                Kon instelling niet opslaan. Probeer opnieuw.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
