"use client";

import { useId, useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "@/generated/types";

type AnalyseAanmaken = components["schemas"]["AnalyseAanmaken"];
type BronKeuze = components["schemas"]["BronKeuze"];

// ─── Artikel-combobox ─────────────────────────────────────────────────────────

function ArtikelCombobox({
  suggesties,
  value,
  onChange,
}: {
  suggesties: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  const listboxId = useId();
  const [open, setOpen] = useState(false);
  const opties = suggesties.filter((a) =>
    value === "" ? true : a.toLowerCase().startsWith(value.toLowerCase()),
  );

  return (
    <div style={{ position: "relative" }}>
      <input
        className="field-input"
        style={{ width: "6rem" }}
        type="text"
        placeholder="9"
        value={value}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-autocomplete="list"
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && opties.length > 0 && (
        <ul
          id={listboxId}
          role="listbox"
          style={{
            position: "absolute",
            zIndex: 20,
            top: "100%",
            left: 0,
            background: "rgb(var(--paper))",
            border: "1px solid rgb(var(--line))",
            borderRadius: "4px",
            padding: "0.25rem 0",
            listStyle: "none",
            margin: "2px 0 0 0",
            maxHeight: "11rem",
            overflowY: "auto",
            minWidth: "8rem",
            boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
          }}
        >
          {opties.map((a) => (
            <li
              key={a}
              role="option"
              aria-selected={value === a}
              style={{
                padding: "0.375rem 0.75rem",
                fontSize: "0.875rem",
                cursor: "pointer",
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(a);
                setOpen(false);
              }}
            >
              Art. {a}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Bron-rij ─────────────────────────────────────────────────────────────────

function BronRij({
  bron,
  artikelSuggesties,
  onUpdate,
  onVerwijder,
  verwijderDisabled,
}: {
  bron: BronKeuze;
  artikelSuggesties: string[];
  onUpdate: (patch: Partial<BronKeuze>) => void;
  onVerwijder: () => void;
  verwijderDisabled: boolean;
}) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr auto auto auto",
        gap: "0.75rem",
        alignItems: "end",
        padding: "0.875rem",
        border: "1px solid rgb(var(--line))",
        borderRadius: "6px",
        background: "rgb(var(--paper))",
      }}
    >
      <div>
        <label className="field-label">Wet (BWB-id)</label>
        <input
          className="field-input"
          type="text"
          placeholder="BWBR0011823"
          value={bron.bwb_id}
          onChange={(e) =>
            onUpdate({ bwb_id: e.target.value, artikel: "", lid: null })
          }
          autoComplete="off"
        />
      </div>
      <div>
        <label className="field-label">
          Artikel{" "}
          <span style={{ color: "rgb(var(--fout))", fontWeight: 700 }}>*</span>
        </label>
        <ArtikelCombobox
          suggesties={artikelSuggesties}
          value={bron.artikel}
          onChange={(a) => onUpdate({ artikel: a, lid: null })}
        />
      </div>
      <div>
        <label className="field-label" style={{ color: "rgb(var(--muted))" }}>
          Lid
        </label>
        <input
          className="field-input"
          style={{ width: "5rem" }}
          type="text"
          placeholder="1"
          value={bron.lid ?? ""}
          onChange={(e) => onUpdate({ lid: e.target.value || null })}
          autoComplete="off"
        />
      </div>
      <div>
        <label className="field-label" style={{ visibility: "hidden" }}>
          _
        </label>
        <button
          className="btn btn-secondary"
          style={{ fontSize: "1.125rem", padding: "0.35rem 0.75rem" }}
          type="button"
          onClick={onVerwijder}
          disabled={verwijderDisabled}
          aria-label="Bron verwijderen"
        >
          ×
        </button>
      </div>
    </div>
  );
}

// ─── Hoofd-component ──────────────────────────────────────────────────────────

export default function NieuwWerkgebiedPagina() {
  const router = useRouter();

  const [bronnen, setBronnen] = useState<BronKeuze[]>([
    { bwb_id: "", artikel: "", lid: null },
  ]);
  const [naam, setNaam] = useState("");
  const [omschrijving, setOmschrijving] = useState("");
  const [geprobeerd, setGeprobeerd] = useState(false);
  const [verzendenFout, setVerzendenFout] = useState<string | null>(null);
  const [bezig, setBezig] = useState(false);

  const heeftGeldigeBron = bronnen.some(
    (b) => b.bwb_id.trim().length > 0 && b.artikel.trim().length > 0,
  );

  function updateBron(i: number, patch: Partial<BronKeuze>) {
    setBronnen((bs) => bs.map((b, j) => (j === i ? { ...b, ...patch } : b)));
  }
  function voegBronToe() {
    setBronnen((bs) => [...bs, { bwb_id: "", artikel: "", lid: null }]);
  }
  function verwijderBron(i: number) {
    setBronnen((bs) => (bs.length > 1 ? bs.filter((_, j) => j !== i) : bs));
  }

  async function handleVerzenden(e: React.FormEvent) {
    e.preventDefault();
    setGeprobeerd(true);
    if (!heeftGeldigeBron) return;

    setBezig(true);
    setVerzendenFout(null);

    const geldige = bronnen.filter((b) => b.bwb_id.trim() && b.artikel.trim());
    const body: AnalyseAanmaken = {
      naam: naam.trim() || null,
      bronnen: geldige,
      omschrijving: omschrijving.trim() || null,
    };

    try {
      const res = await fetch("/api/projecten", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.status === 401) {
        router.push("/login");
        return;
      }
      if (!res.ok) {
        const data = (await res.json()) as { detail?: string };
        setVerzendenFout(data.detail ?? `Fout ${res.status}`);
        return;
      }
      const result = (await res.json()) as { id: string };
      router.push(`/projecten/${result.id}`);
    } catch (err) {
      setVerzendenFout(err instanceof Error ? err.message : "Netwerkfout.");
    } finally {
      setBezig(false);
    }
  }

  return (
    <div style={{ maxWidth: "40rem" }}>
      <button
        className="btn btn-secondary"
        style={{ fontSize: "0.8125rem", marginBottom: "1rem" }}
        onClick={() => router.push("/projecten")}
      >
        ← Terug naar werkgebieden
      </button>

      <h2
        style={{
          fontSize: "1.5rem",
          fontWeight: 700,
          color: "rgb(var(--lint))",
          marginBottom: "0.25rem",
        }}
      >
        Nieuw werkgebied
      </h2>
      <p
        style={{
          fontSize: "0.875rem",
          color: "rgb(var(--muted))",
          marginBottom: "1.5rem",
        }}
      >
        Kies één of meer bronartikelen. Na aanmaken opent de werkplek voor
        annotatie.
      </p>

      {verzendenFout && (
        <div className="melding melding-fout" style={{ marginBottom: "1rem" }}>
          <p role="alert">{verzendenFout}</p>
        </div>
      )}

      <div className="card">
        <form
          onSubmit={handleVerzenden}
          style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}
        >
          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: "0.625rem",
              }}
            >
              <span className="field-label" style={{ marginBottom: 0 }}>
                Bronnen in het werkgebied
              </span>
              <span style={{ fontSize: "0.75rem", color: "rgb(var(--muted))" }}>
                {bronnen.length} bron{bronnen.length === 1 ? "" : "nen"}
              </span>
            </div>
            {geprobeerd && !heeftGeldigeBron && (
              <p
                style={{
                  fontSize: "0.75rem",
                  color: "rgb(var(--fout))",
                  marginBottom: "0.5rem",
                }}
              >
                Voeg minimaal 1 bronartikel toe (wet-id + artikel verplicht).
              </p>
            )}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.625rem",
              }}
            >
              {bronnen.map((b, i) => (
                <BronRij
                  key={i}
                  bron={b}
                  artikelSuggesties={[]}
                  onUpdate={(patch) => updateBron(i, patch)}
                  onVerwijder={() => verwijderBron(i)}
                  verwijderDisabled={bronnen.length === 1}
                />
              ))}
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ marginTop: "0.625rem", fontSize: "0.8125rem" }}
              onClick={voegBronToe}
            >
              + Bron toevoegen
            </button>
          </div>

          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
              }}
            >
              <label className="field-label">Naam werkgebied</label>
              <span style={{ fontSize: "0.75rem", color: "rgb(var(--muted))" }}>
                optioneel — anders afgeleid
              </span>
            </div>
            <input
              className="field-input"
              type="text"
              placeholder="Inkomensafhankelijke bijdrage Zvw"
              value={naam}
              onChange={(e) => setNaam(e.target.value)}
              autoComplete="off"
            />
          </div>

          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
              }}
            >
              <label className="field-label">Omschrijving / context</label>
              <span style={{ fontSize: "0.75rem", color: "rgb(var(--muted))" }}>
                optioneel
              </span>
            </div>
            <textarea
              className="field-input"
              rows={2}
              placeholder="Achtergrond bij dit werkgebied…"
              value={omschrijving}
              onChange={(e) => setOmschrijving(e.target.value)}
              style={{ resize: "vertical", fontFamily: "inherit" }}
            />
          </div>

          <div
            style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}
          >
            <button
              className="btn btn-primary"
              type="submit"
              style={{ fontWeight: 600 }}
              disabled={bezig}
            >
              {bezig ? "Bezig…" : "Werkgebied aanmaken"}
            </button>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={() => router.push("/projecten")}
            >
              Annuleer
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
