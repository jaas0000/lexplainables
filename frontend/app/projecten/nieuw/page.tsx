"use client";

import { useEffect, useId, useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "@/generated/types";

type AnalyseAanmaken = components["schemas"]["AnalyseAanmaken"];
type BronKeuze = components["schemas"]["BronKeuze"];
type LlmProfielRead = components["schemas"]["LlmProfielRead"];

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

export default function NieuweAnalysePagina() {
  const router = useRouter();

  const [profielen, setProfielen] = useState<LlmProfielRead[] | null>(null);
  const [profielenFout, setProfielenFout] = useState(false);

  const [bronnen, setBronnen] = useState<BronKeuze[]>([
    { bwb_id: "", artikel: "", lid: null },
  ]);
  const [naam, setNaam] = useState("");
  const [omschrijving, setOmschrijving] = useState("");
  const [analysefocus, setAnalysefocus] = useState("");
  const [begrippenTekst, setBegrippenTekst] = useState("");
  const [profiel, setProfiel] = useState("");
  const [review, setReview] = useState(true);
  const [geprobeerd, setGeprobeerd] = useState(false);
  const [verzendenFout, setVerzendenFout] = useState<string | null>(null);
  const [bezig, setBezig] = useState(false);

  useEffect(() => {
    async function laadProfielen() {
      try {
        const res = await fetch("/api/admin/profielen");
        if (res.ok) {
          const lijst = (await res.json()) as LlmProfielRead[];
          setProfielen(lijst);
          const standaard = lijst.find((p) => p.is_standaard) ?? lijst[0];
          if (standaard) setProfiel(standaard.naam);
        } else {
          setProfielenFout(true);
          setProfielen([]);
        }
      } catch {
        setProfielenFout(true);
        setProfielen([]);
      }
    }
    void laadProfielen();
  }, []);

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
      analysefocus: analysefocus.trim() || null,
      begrippenlijst: null,
      model_profiel: profiel || null,
      human_in_the_loop: review,
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

  const begrippenRegels = begrippenTekst
    .trim()
    .split("\n")
    .filter(Boolean).length;

  return (
    <div style={{ maxWidth: "40rem" }}>
      <button
        className="btn btn-secondary"
        style={{ fontSize: "0.8125rem", marginBottom: "1rem" }}
        onClick={() => router.push("/projecten")}
      >
        ← Terug naar analyses
      </button>

      <h2
        style={{
          fontSize: "1.5rem",
          fontWeight: 700,
          color: "rgb(var(--lint))",
          marginBottom: "0.25rem",
        }}
      >
        Nieuwe analyse
      </h2>
      <p
        style={{
          fontSize: "0.875rem",
          color: "rgb(var(--muted))",
          marginBottom: "1.5rem",
        }}
      >
        De orchestrator haalt de wettekst op via de wettenbank en doorloopt
        activiteit 2 en 3. Met review aan pauzeert hij na elke activiteit voor
        jouw akkoord.
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
          {/* Bronnen */}
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

          {/* Model-profiel */}
          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
              }}
            >
              <label className="field-label">Model-profiel</label>
              <span style={{ fontSize: "0.75rem", color: "rgb(var(--link))" }}>
                beheer via /beheer
              </span>
            </div>
            {profielen === null ? (
              <p style={{ fontSize: "0.8125rem", color: "rgb(var(--muted))" }}>
                Laden…
              </p>
            ) : profielenFout || profielen.length === 0 ? (
              <input
                className="field-input"
                type="text"
                placeholder="Model-profiel naam"
                value={profiel}
                onChange={(e) => setProfiel(e.target.value)}
              />
            ) : (
              <select
                className="field-input"
                value={profiel}
                onChange={(e) => setProfiel(e.target.value)}
              >
                {profielen.map((p) => (
                  <option key={p.naam} value={p.naam}>
                    {p.naam}
                    {p.is_standaard ? " (standaard)" : ""}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Naam werkgebied */}
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

          {/* Omschrijving */}
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
              placeholder="Achtergrond bij deze analyse…"
              value={omschrijving}
              onChange={(e) => setOmschrijving(e.target.value)}
              style={{ resize: "vertical", fontFamily: "inherit" }}
            />
          </div>

          {/* Analysefocus */}
          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
              }}
            >
              <label className="field-label">Hoofdvraag / analysefocus</label>
              <span style={{ fontSize: "0.75rem", color: "rgb(var(--muted))" }}>
                optioneel
              </span>
            </div>
            <textarea
              className="field-input"
              rows={2}
              placeholder="Waar moet de analyse antwoord op geven?"
              value={analysefocus}
              onChange={(e) => setAnalysefocus(e.target.value)}
              style={{ resize: "vertical", fontFamily: "inherit" }}
            />
          </div>

          {/* Begrippenlijst (inklapbaar) */}
          <details
            style={{
              border: "1px solid rgb(var(--line))",
              borderRadius: "6px",
              padding: "0.875rem",
              background: "rgb(var(--surface))",
            }}
          >
            <summary
              style={{
                cursor: "pointer",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "rgb(var(--ink))",
              }}
            >
              Bestaande begrippenlijst{" "}
              <span style={{ fontWeight: 400, color: "rgb(var(--muted))" }}>
                (optioneel)
              </span>
              {begrippenRegels > 0 && (
                <span
                  style={{
                    marginLeft: "0.5rem",
                    fontFamily: "monospace",
                    fontSize: "0.75rem",
                    color: "rgb(var(--faint))",
                  }}
                >
                  {begrippenRegels} regel{begrippenRegels === 1 ? "" : "s"}{" "}
                  ingevoerd
                </span>
              )}
            </summary>
            <div
              style={{
                marginTop: "0.75rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
              }}
            >
              <p style={{ fontSize: "0.8125rem", color: "rgb(var(--muted))" }}>
                Plak of upload een bestaande begrippenlijst (JSON, CSV of één
                begrip per regel).
              </p>
              <textarea
                className="field-input"
                rows={4}
                placeholder={
                  "belastingplichtige; degene die aangifte moet doen\nbijdrage-inkomen"
                }
                value={begrippenTekst}
                onChange={(e) => setBegrippenTekst(e.target.value)}
                style={{
                  resize: "vertical",
                  fontFamily: "monospace",
                  fontSize: "0.8125rem",
                }}
              />
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.8125rem",
                    color: "rgb(var(--muted))",
                    marginBottom: "0.25rem",
                  }}
                >
                  Of upload een bestand (.csv, .json, .txt):
                </label>
                <input
                  type="file"
                  accept=".csv,.json,.txt"
                  style={{ fontSize: "0.8125rem", color: "rgb(var(--ink))" }}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    const reader = new FileReader();
                    reader.onload = () =>
                      setBegrippenTekst(String(reader.result ?? ""));
                    reader.readAsText(f);
                  }}
                />
              </div>
            </div>
          </details>

          {/* Human-in-the-loop */}
          <label
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "0.75rem",
              padding: "0.875rem",
              border: "1px solid rgb(var(--line))",
              borderRadius: "6px",
              cursor: "pointer",
              background: "rgb(var(--surface))",
            }}
          >
            <input
              type="checkbox"
              checked={review}
              onChange={(e) => setReview(e.target.checked)}
              style={{ marginTop: "0.125rem", width: "1rem", height: "1rem" }}
            />
            <span>
              <span
                style={{
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  color: "rgb(var(--ink))",
                  display: "block",
                }}
              >
                Human-in-the-loop review
              </span>
              <span
                style={{
                  fontSize: "0.8125rem",
                  color: "rgb(var(--muted))",
                  display: "block",
                  marginTop: "0.125rem",
                }}
              >
                Pauzeer na activiteit 2 en 3 voor jouw beoordeling. Uit =
                volautomatisch tot het rapport.
              </span>
            </span>
          </label>

          {/* Actieknoppen */}
          <div
            style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}
          >
            <button
              className="btn btn-primary"
              type="submit"
              style={{ fontWeight: 600 }}
              disabled={bezig}
            >
              {bezig ? "Bezig…" : "Analyse starten"}
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
