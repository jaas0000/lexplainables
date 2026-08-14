"use client";

import { useState } from "react";
import { SectieHeader, LeegePlaceholder } from "@/components/beheer/SectieHeader";

type WetKeuze = { bwb_id: string; naam: string };
type ArtikelKeuze = { artikel: string; pad: string };

const NEP_WETTEN: WetKeuze[] = [
  { bwb_id: "BWBR0011823", naam: "Wet werk en bijstand" },
  { bwb_id: "BWBR0015703", naam: "Wet structuur uitvoeringsorganisatie werk en inkomen" },
  { bwb_id: "BWBR0020183", naam: "Participatiewet" },
];

const NEP_STRUCTUUR: Record<string, ArtikelKeuze[]> = {
  BWBR0011823: [
    { artikel: "1", pad: "Hoofdstuk 1 / Artikel 1" },
    { artikel: "2", pad: "Hoofdstuk 1 / Artikel 2" },
    { artikel: "3", pad: "Hoofdstuk 1 / Artikel 3" },
    { artikel: "11", pad: "Hoofdstuk 2 / Artikel 11" },
    { artikel: "17", pad: "Hoofdstuk 2 / Artikel 17" },
    { artikel: "31", pad: "Hoofdstuk 3 / Artikel 31" },
  ],
  BWBR0015703: [
    { artikel: "1", pad: "Hoofdstuk 1 / Artikel 1" },
    { artikel: "7", pad: "Hoofdstuk 2 / Artikel 7" },
    { artikel: "30", pad: "Hoofdstuk 4 / Artikel 30" },
  ],
  BWBR0020183: [
    { artikel: "1", pad: "Hoofdstuk 1 / Artikel 1" },
    { artikel: "8a", pad: "Hoofdstuk 2 / Artikel 8a" },
    { artikel: "10", pad: "Hoofdstuk 2 / Artikel 10" },
    { artikel: "44", pad: "Hoofdstuk 3 / Artikel 44" },
  ],
};

type Variant = "selector-leeg" | "selector-wet-gekozen" | "selector-artikelen-geselecteerd";

const VARIANTEN: { id: Variant; label: string }[] = [
  { id: "selector-leeg", label: "Selector — leeg" },
  { id: "selector-wet-gekozen", label: "Selector — wet gekozen" },
  { id: "selector-artikelen-geselecteerd", label: "Selector — artikelen geselecteerd" },
];

function WetSelectorDemo({
  initWet,
  initArtikelen,
}: {
  initWet: string;
  initArtikelen: string[];
}) {
  const [gekozenWet, setGekozenWet] = useState(initWet);
  const [gekozenArtikelen, setGekozenArtikelen] = useState<string[]>(initArtikelen);
  const artikelen = gekozenWet ? (NEP_STRUCTUUR[gekozenWet] ?? []) : [];

  function toggleArtikel(artikel: string) {
    setGekozenArtikelen((prev) =>
      prev.includes(artikel) ? prev.filter((a) => a !== artikel) : [...prev, artikel]
    );
  }

  return (
    <div style={{ maxWidth: "36rem" }}>
      <div style={{ marginBottom: "1rem" }}>
        <label
          style={{
            display: "block",
            fontSize: "0.8125rem",
            fontWeight: 600,
            marginBottom: "0.375rem",
          }}
        >
          Wet
        </label>
        <select
          className="field-input"
          value={gekozenWet}
          onChange={(e) => {
            setGekozenWet(e.target.value);
            setGekozenArtikelen([]);
          }}
          style={{ width: "100%" }}
        >
          <option value="">— Kies een wet —</option>
          {NEP_WETTEN.map((w) => (
            <option key={w.bwb_id} value={w.bwb_id}>
              {w.naam}
            </option>
          ))}
        </select>
      </div>

      {gekozenWet && (
        <div>
          <label
            style={{
              display: "block",
              fontSize: "0.8125rem",
              fontWeight: 600,
              marginBottom: "0.375rem",
            }}
          >
            Artikelen
            <span
              style={{ fontWeight: 400, color: "rgb(var(--faint))", marginLeft: "0.375rem" }}
            >
              (één of meer kiezen)
            </span>
          </label>
          {artikelen.length === 0 ? (
            <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))" }}>
              Geen artikelen beschikbaar voor deze wet.
            </p>
          ) : (
            <div
              style={{
                border: "1px solid rgb(var(--line))",
                borderRadius: "6px",
                overflow: "hidden",
              }}
            >
              {artikelen.map((a, i) => (
                <label
                  key={a.artikel}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    padding: "0.5rem 0.75rem",
                    cursor: "pointer",
                    background: gekozenArtikelen.includes(a.artikel)
                      ? "rgb(var(--surface))"
                      : "rgb(var(--paper))",
                    borderTop: i > 0 ? "1px solid rgb(var(--line))" : "none",
                    fontSize: "0.875rem",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={gekozenArtikelen.includes(a.artikel)}
                    onChange={() => toggleArtikel(a.artikel)}
                  />
                  <span style={{ fontWeight: 500, minWidth: "3rem" }}>art. {a.artikel}</span>
                  <span style={{ color: "rgb(var(--muted))", fontSize: "0.8125rem" }}>
                    {a.pad}
                  </span>
                </label>
              ))}
            </div>
          )}

          {gekozenArtikelen.length > 0 && (
            <p
              style={{
                marginTop: "0.5rem",
                fontSize: "0.8125rem",
                color: "rgb(var(--muted))",
              }}
            >
              {gekozenArtikelen.length}{" "}
              {gekozenArtikelen.length === 1 ? "artikel" : "artikelen"} geselecteerd
            </p>
          )}
        </div>
      )}

      {!gekozenWet && (
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))", fontStyle: "italic" }}>
          Kies een wet om de artikelstructuur te tonen.
        </p>
      )}
    </div>
  );
}

function LegeLijst() {
  return <LeegePlaceholder tekst="Geen wetten beschikbaar." />;
}

export default function WetcatalogusMockup() {
  const [variant, setVariant] = useState<Variant>("selector-leeg");

  return (
    <div className="main">
      <div
        style={{
          display: "inline-flex",
          background: "rgb(var(--lint))",
          color: "white",
          borderRadius: "4px",
          padding: "0.2rem 0.625rem",
          fontSize: "0.6875rem",
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: "1.25rem",
        }}
      >
        Mockup — Wetcatalogus (story 010)
      </div>

      <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" }}>
        WetSelector-component
      </h1>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "2rem" }}>
        {VARIANTEN.map((v) => (
          <button
            key={v.id}
            className={variant === v.id ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => setVariant(v.id)}
          >
            {v.label}
          </button>
        ))}
      </div>

      <div
        style={{
          background: "rgb(var(--paper))",
          border: "1px solid rgb(var(--line))",
          borderRadius: "8px",
          padding: "1.5rem",
        }}
      >
        <SectieHeader titel="Bronartikelen kiezen" />

        {variant === "selector-leeg" && <WetSelectorDemo initWet="" initArtikelen={[]} />}
        {variant === "selector-wet-gekozen" && (
          <WetSelectorDemo initWet="BWBR0011823" initArtikelen={[]} />
        )}
        {variant === "selector-artikelen-geselecteerd" && (
          <WetSelectorDemo initWet="BWBR0011823" initArtikelen={["1", "17", "31"]} />
        )}
      </div>
    </div>
  );
}
