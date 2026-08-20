"use client";

import { useState } from "react";
import type { components } from "@/generated/types";

type AnnotatieDocument = components["schemas"]["AnnotatieDocument"];

interface Props {
  onAangemaakt: (doc: AnnotatieDocument) => void;
  onAnnuleren: () => void;
}

export function NieuwDocumentFormulier({ onAangemaakt, onAnnuleren }: Props) {
  const [werkgebied, setWerkgebied] = useState("");
  const [bwbId, setBwbId] = useState("");
  const [artikel, setArtikel] = useState("");
  const [lid, setLid] = useState("");
  const [bezig, setBezig] = useState(false);
  const [fout, setFout] = useState<string | null>(null);

  async function verzend(e: React.FormEvent) {
    e.preventDefault();
    setFout(null);
    setBezig(true);
    try {
      const res = await fetch("/api/annotatie/documenten", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          werkgebied: werkgebied.trim(),
          bwb_id: bwbId.trim(),
          artikel: artikel.trim(),
          lid: lid.trim() || null,
        }),
      });
      if (!res.ok) {
        const data = (await res.json()) as { detail?: string };
        throw new Error(data.detail ?? `${res.status} ${res.statusText}`);
      }
      const doc = (await res.json()) as AnnotatieDocument;
      onAangemaakt(doc);
    } catch (err) {
      setFout(
        err instanceof Error
          ? err.message
          : "Fout bij het aanmaken van het document.",
      );
    } finally {
      setBezig(false);
    }
  }

  return (
    <form onSubmit={(e) => void verzend(e)}>
      {fout && (
        <div
          className="melding melding-fout"
          style={{ marginBottom: "1rem" }}
          role="alert"
        >
          {fout}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <label
          style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}
        >
          <span style={{ fontSize: "0.8125rem", fontWeight: 500 }}>
            Werkgebied <span style={{ color: "rgb(var(--gevaar))" }}>*</span>
          </span>
          <input
            className="field-input"
            type="text"
            required
            placeholder="bijv. Inkomstenbelasting"
            value={werkgebied}
            onChange={(e) => setWerkgebied(e.target.value)}
          />
        </label>

        <label
          style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}
        >
          <span style={{ fontSize: "0.8125rem", fontWeight: 500 }}>
            BWB-id <span style={{ color: "rgb(var(--gevaar))" }}>*</span>
          </span>
          <input
            className="field-input"
            type="text"
            required
            placeholder="bijv. BWBR0011823"
            value={bwbId}
            onChange={(e) => setBwbId(e.target.value)}
          />
        </label>

        <label
          style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}
        >
          <span style={{ fontSize: "0.8125rem", fontWeight: 500 }}>
            Artikel <span style={{ color: "rgb(var(--gevaar))" }}>*</span>
          </span>
          <input
            className="field-input"
            type="text"
            required
            placeholder="bijv. 3.1"
            value={artikel}
            onChange={(e) => setArtikel(e.target.value)}
          />
        </label>

        <label
          style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}
        >
          <span style={{ fontSize: "0.8125rem", fontWeight: 500 }}>
            Lid{" "}
            <span style={{ fontSize: "0.75rem", color: "rgb(var(--muted))" }}>
              (optioneel)
            </span>
          </span>
          <input
            className="field-input"
            type="text"
            placeholder="bijv. 1"
            value={lid}
            onChange={(e) => setLid(e.target.value)}
          />
        </label>

        <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.25rem" }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={
              bezig || !werkgebied.trim() || !bwbId.trim() || !artikel.trim()
            }
          >
            {bezig ? "Aanmaken…" : "Document aanmaken"}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onAnnuleren}
            disabled={bezig}
          >
            Annuleren
          </button>
        </div>
      </div>
    </form>
  );
}
