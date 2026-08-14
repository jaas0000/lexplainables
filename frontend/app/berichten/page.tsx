"use client";

import { useEffect, useState } from "react";
import type { components } from "@/generated/types";
import { TypeBadge } from "@/components/berichten/TypeBadge";
import { TYPE_META, type BerichtType } from "@/lib/bericht-types";

type BerichtRead = components["schemas"]["BerichtRead"];

export default function BerichtenPagina() {
  const [berichten, setBerichten] = useState<BerichtRead[] | null>(null);
  const [laden, setLaden] = useState(true);
  const [fout, setFout] = useState<string | null>(null);

  useEffect(() => {
    async function laad() {
      try {
        const res = await fetch("/api/berichten");
        if (res.status === 401) { window.location.href = "/login"; return; }
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const data = (await res.json()) as { items: BerichtRead[] };
        setBerichten(data.items);
        if (data.items.length > 0) {
          fetch("/api/berichten/lees-alles", { method: "POST" }).catch(() => {});
        }
      } catch (err) {
        setFout(err instanceof Error ? err.message : "Fout bij het ophalen van berichten.");
      } finally {
        setLaden(false);
      }
    }
    void laad();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <h1 style={{ fontSize: "1.375rem" }}>Berichten</h1>

      {fout && (
        <div className="melding melding-fout">
          <p role="alert">{fout}</p>
        </div>
      )}

      {laden && <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Laden…</p>}

      {!laden && berichten?.length === 0 && (
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Geen berichten.</p>
      )}

      {!laden && berichten && berichten.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {berichten.map((b) => {
            const { kleurVar } = TYPE_META[b.type as BerichtType];
            const datum = new Date(b.gepubliceerd_op ?? b.created).toLocaleDateString("nl-NL", {
              day: "numeric", month: "long", year: "numeric",
            });
            return (
              <div key={b.id} className="card" style={{ position: "relative", paddingLeft: "1.75rem", background: b.gelezen ? "rgb(var(--paper))" : "rgb(var(--surface))" }}>
                {!b.gelezen && (
                  <span aria-hidden style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "4px", background: `rgb(var(${kleurVar}))`, borderRadius: "6px 0 0 6px" }} />
                )}
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.5rem" }}>
                  <TypeBadge type={b.type as BerichtType} />
                  {b.versie && <span style={{ fontSize: "0.6875rem", fontFamily: "monospace", padding: "0.125rem 0.4rem", borderRadius: "3px", color: "rgb(var(--faint))", border: "1px solid rgb(var(--line))", background: "rgb(var(--surface))" }}>{b.versie}</span>}
                  <span style={{ fontSize: "0.75rem", color: "rgb(var(--faint))", marginLeft: "auto" }}>{datum}</span>
                </div>
                <p style={{ fontSize: "1rem", fontWeight: 600, color: "rgb(var(--ink))", marginBottom: "0.375rem" }}>{b.titel}</p>
                <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))", lineHeight: 1.6 }}>{b.inhoud}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
