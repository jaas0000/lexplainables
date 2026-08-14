"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { components } from "@/generated/types";
import { SectieHeader, LeegePlaceholder } from "@/components/beheer/SectieHeader";
import { CATEGORIE_META, type Categorie } from "@/lib/feedback-types";

type FeedbackRead = components["schemas"]["FeedbackRead"];

async function beheerFetch(pad: string, init: RequestInit = {}) {
  const res = await fetch(pad, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (res.status === 401) { window.location.href = "/login"; throw new Error("Niet geautoriseerd."); }
  if (!res.ok) {
    const detail = await res.json().then((d: { detail?: string }) => d.detail).catch(() => null);
    throw new Error(detail ?? `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined;
  return res.json();
}

function CategorieBadge({ categorie }: { categorie: Categorie }) {
  const { label, kleurVar } = CATEGORIE_META[categorie];
  return (
    <span
      style={{
        fontSize: "0.6875rem",
        fontWeight: 600,
        padding: "0.125rem 0.4rem",
        borderRadius: "3px",
        color: `rgb(var(${kleurVar}))`,
        border: `1px solid rgb(var(${kleurVar}) / 0.4)`,
        background: `rgb(var(${kleurVar}) / 0.08)`,
      }}
    >
      {label}
    </span>
  );
}

export default function FeedbackPagina() {
  const [items, setItems] = useState<FeedbackRead[] | null>(null);
  const [laden, setLaden] = useState(false);
  const [fout, setFout] = useState<string | null>(null);
  const [verwijderFout, setVerwijderFout] = useState<string | null>(null);

  const laadFeedback = useCallback(async () => {
    setLaden(true);
    setFout(null);
    try {
      const data = await beheerFetch("/api/admin/feedback") as { items: FeedbackRead[] };
      setItems(data.items);
    } catch (err) {
      setFout(err instanceof Error ? err.message : "Fout bij het ophalen van feedback.");
    } finally {
      setLaden(false);
    }
  }, []);

  useEffect(() => {
    void laadFeedback();
    beheerFetch("/api/admin/feedback/markeer-gezien", { method: "POST" }).catch(console.error);
  }, [laadFeedback]);

  async function verwijderen(id: number) {
    setVerwijderFout(null);
    try {
      await beheerFetch(`/api/admin/feedback/${id}`, { method: "DELETE" });
      setItems((prev) => prev?.filter((item) => item.id !== id) ?? null);
    } catch (err) {
      const bericht = err instanceof Error ? err.message : "Fout bij verwijderen.";
      setVerwijderFout(bericht);
      if (bericht.includes("404") || bericht.includes("Niet gevonden")) {
        void laadFeedback();
      }
    }
  }

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <Link
          href="/beheer"
          style={{ fontSize: "0.8125rem", color: "rgb(var(--lint))" }}
        >
          ← Terug naar beheer
        </Link>
      </div>

      <SectieHeader
        titel="Gebruikersfeedback"
        aantal={items?.length}
      />

      {fout && (
        <div
          className="melding melding-fout"
          style={{ marginBottom: "1rem" }}
        >
          <p role="alert">{fout}</p>
        </div>
      )}

      {verwijderFout && (
        <div
          style={{
            marginBottom: "1rem",
            padding: "0.625rem 1rem",
            borderRadius: "4px",
            background: "rgb(var(--fout) / 0.08)",
            border: "1px solid rgb(var(--fout) / 0.3)",
            color: "rgb(var(--fout))",
            fontSize: "0.875rem",
          }}
        >
          <p role="alert">{verwijderFout}</p>
        </div>
      )}

      {laden && (
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Laden…</p>
      )}

      {!laden && items !== null && items.length === 0 && (
        <LeegePlaceholder tekst="Nog geen feedback ontvangen." />
      )}

      {!laden && items !== null && items.length > 0 && (
        <div>
          {items.map((item) => {
            const datum = new Date(item.created).toLocaleDateString("nl-NL", {
              day: "numeric",
              month: "long",
              year: "numeric",
            });
            return (
              <div
                key={item.id}
                style={{
                  padding: "1rem 0",
                  borderBottom: "1px solid rgb(var(--line))",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: "1rem",
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.5rem",
                      flexWrap: "wrap",
                      marginBottom: "0.375rem",
                    }}
                  >
                    <CategorieBadge categorie={item.categorie as Categorie} />
                    <span style={{ fontSize: "0.75rem", color: "rgb(var(--faint))" }}>
                      {item.userid}
                      {item.pagina ? ` · ${item.pagina}` : ""}
                      {" · "}
                      {datum}
                    </span>
                  </div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "0.875rem",
                      lineHeight: 1.5,
                      color: "rgb(var(--ink))",
                      overflowWrap: "break-word",
                    }}
                  >
                    {item.tekst}
                  </p>
                </div>
                <button
                  className="btn btn-secondary"
                  style={{
                    fontSize: "0.8125rem",
                    minHeight: "1.875rem",
                    padding: "0.25rem 0.625rem",
                    flexShrink: 0,
                  }}
                  onClick={() => void verwijderen(item.id)}
                >
                  Verwijderen
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
