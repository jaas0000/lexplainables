"use client";

import React, { useEffect, useState } from "react";
import type { components } from "@/generated/types";
import { SectieHeader } from "@/components/beheer/SectieHeader";
import { beheerFetch } from "@/lib/beheer-fetch";

type AppInstellingen = components["schemas"]["AppInstellingen"];

export default function InstellingenPagina() {
  const [instellingen, setInstellingen] = useState<AppInstellingen | null>(
    null,
  );
  const [laden, setLaden] = useState(true);
  const [bezig, setBezig] = useState(false);
  const [fout, setFout] = useState<string | null>(null);

  useEffect(() => {
    beheerFetch("/api/admin/instellingen")
      .then((data) => setInstellingen(data as AppInstellingen))
      .catch((err) =>
        setFout(
          err instanceof Error ? err.message : "Kon instellingen niet ophalen.",
        ),
      )
      .finally(() => setLaden(false));
  }, []);

  async function wisselCapture() {
    if (!instellingen || bezig) return;
    setBezig(true);
    setFout(null);
    try {
      const bijgewerkt = (await beheerFetch("/api/admin/instellingen", {
        method: "PUT",
        body: JSON.stringify({
          capture_llm_calls: !instellingen.capture_llm_calls,
        }),
      })) as AppInstellingen;
      setInstellingen(bijgewerkt);
    } catch (err) {
      setFout(
        err instanceof Error ? err.message : "Kon instelling niet opslaan.",
      );
    } finally {
      setBezig(false);
    }
  }

  const capture = instellingen?.capture_llm_calls ?? false;

  return (
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
        <p
          style={{
            marginTop: "0.25rem",
            fontSize: "0.875rem",
            color: "rgb(var(--muted))",
          }}
        >
          Runtime-configuratie van de applicatie. Wijzigingen zijn direct actief
          (maximaal 10 seconden cache).
        </p>
      </div>

      {laden && (
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Laden…
        </p>
      )}

      {!laden && (
        <section style={{ marginBottom: "2rem" }}>
          <SectieHeader
            titel="LLM-invoer vastleggen"
            subtitel="prompts + respons, voor analyse"
          />

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
                <p
                  style={{
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    color: "rgb(var(--ink))",
                  }}
                >
                  Vastleggen van LLM-calls
                </p>
                <p
                  style={{
                    marginTop: "0.125rem",
                    fontSize: "0.75rem",
                    color: "rgb(var(--muted))",
                  }}
                >
                  Legt per call de letterlijke system/user-prompt en de ruwe
                  respons vast (incl. auto-correctie en gefaalde calls).
                  Standaard uit; aanzetten kost extra opslag per analyse.
                </p>
              </div>

              {/* Tag + knop rechts */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                }}
              >
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
                  disabled={bezig || instellingen === null}
                  onClick={() => void wisselCapture()}
                  style={{
                    padding: "0.5rem 1rem",
                    borderRadius: "4px",
                    border: "none",
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    fontFamily: "inherit",
                    cursor: bezig ? "default" : "pointer",
                    background: capture
                      ? "rgb(var(--surface))"
                      : "rgb(var(--lint))",
                    color: capture ? "rgb(var(--ink))" : "white",
                    boxShadow: capture
                      ? "inset 0 0 0 1px rgb(var(--line))"
                      : "none",
                    opacity: bezig ? 0.6 : 1,
                  }}
                >
                  {bezig ? "Bezig…" : capture ? "Uitzetten" : "Aanzetten"}
                </button>
              </div>
            </div>

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
                {fout}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
