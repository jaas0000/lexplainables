"use client";

import type { components } from "@/generated/types";

type AuditRegel = components["schemas"]["AuditRegel"];

function formatTijdstip(iso: string): string {
  return new Date(iso).toLocaleString("nl-NL", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

interface Props {
  audit: AuditRegel[] | null;
}

export function AuditlogTabblad({ audit }: Props) {
  if (audit === null) {
    return (
      <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
        Laden…
      </p>
    );
  }

  if (audit.length === 0) {
    return (
      <p
        style={{
          fontSize: "0.875rem",
          color: "rgb(var(--faint))",
          fontStyle: "italic",
        }}
      >
        Nog geen acties vastgelegd.
      </p>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
      {audit.map((regel, i) => (
        <div
          key={regel.id}
          style={{
            display: "grid",
            gridTemplateColumns: "9rem 1fr",
            gap: "0.75rem",
            padding: "0.75rem 0",
            borderBottom:
              i < audit.length - 1 ? "1px solid rgb(var(--line))" : "none",
          }}
        >
          {/* Tijdstip */}
          <div
            style={{
              fontSize: "0.8125rem",
              color: "rgb(var(--muted))",
              whiteSpace: "nowrap",
              paddingTop: "0.125rem",
            }}
          >
            {formatTijdstip(regel.tijdstip)}
          </div>

          {/* Actie-inhoud */}
          <div>
            <span
              style={{
                display: "inline-block",
                fontSize: "0.75rem",
                fontWeight: 600,
                fontFamily: "monospace",
                background: "rgb(var(--surface))",
                border: "1px solid rgb(var(--line))",
                borderRadius: "4px",
                padding: "0.1rem 0.375rem",
                marginBottom: "0.25rem",
                color: "rgb(var(--ink))",
              }}
            >
              {regel.actie}
            </span>
            <p
              style={{
                fontSize: "0.8125rem",
                color: "rgb(var(--muted))",
                margin: 0,
              }}
            >
              door <strong style={{ color: "rgb(var(--ink))" }}>{regel.actor}</strong>
              {regel.element_id && (
                <span>
                  {" "}
                  · element{" "}
                  <code
                    style={{
                      fontSize: "0.75rem",
                      color: "rgb(var(--faint))",
                    }}
                  >
                    {regel.element_id}
                  </code>
                </span>
              )}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
