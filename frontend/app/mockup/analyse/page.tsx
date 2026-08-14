"use client";

import { useState } from "react";
import { LeegePlaceholder } from "@/components/beheer/SectieHeader";

type AnalyseStatus = "wachtrij" | "actief" | "review" | "klaar" | "fout";

type AnalyseOverzicht = {
  id: string;
  naam: string;
  status: AnalyseStatus;
  bijgewerkt: string;
};

const NEP_ANALYSES: AnalyseOverzicht[] = [
  { id: "a1b2c3", naam: "Wwb participatieplicht 2026", status: "klaar", bijgewerkt: "2026-08-14T11:30:00Z" },
  { id: "d4e5f6", naam: "SUWI uitwisseling persoonsgegevens", status: "actief", bijgewerkt: "2026-08-14T10:15:00Z" },
  { id: "g7h8i9", naam: "Participatiewet art. 8a–10", status: "wachtrij", bijgewerkt: "2026-08-14T09:00:00Z" },
  { id: "j0k1l2", naam: "Test met verkeerde API-sleutel", status: "fout", bijgewerkt: "2026-08-13T16:45:00Z" },
];

const NEP_WETTEN = [
  { bwb_id: "BWBR0011823", naam: "Wet werk en bijstand" },
  { bwb_id: "BWBR0015703", naam: "Wet structuur uitvoeringsorganisatie werk en inkomen" },
  { bwb_id: "BWBR0020183", naam: "Participatiewet" },
];

const NEP_STRUCTUUR: Record<string, { artikel: string; pad: string }[]> = {
  BWBR0011823: [
    { artikel: "1", pad: "Hoofdstuk 1 / Artikel 1" },
    { artikel: "2", pad: "Hoofdstuk 1 / Artikel 2" },
    { artikel: "17", pad: "Hoofdstuk 2 / Artikel 17" },
    { artikel: "31", pad: "Hoofdstuk 3 / Artikel 31" },
  ],
  BWBR0015703: [
    { artikel: "1", pad: "Hoofdstuk 1 / Artikel 1" },
    { artikel: "7", pad: "Hoofdstuk 2 / Artikel 7" },
  ],
  BWBR0020183: [
    { artikel: "8a", pad: "Hoofdstuk 2 / Artikel 8a" },
    { artikel: "10", pad: "Hoofdstuk 2 / Artikel 10" },
    { artikel: "44", pad: "Hoofdstuk 3 / Artikel 44" },
  ],
};

const STATUS_META: Record<AnalyseStatus, { label: string; kleur: string }> = {
  wachtrij: { label: "Wachtrij", kleur: "rgb(var(--waarschuwing))" },
  actief:   { label: "Actief",   kleur: "rgb(var(--info))" },
  review:   { label: "Review",   kleur: "rgb(var(--info))" },
  klaar:    { label: "Klaar",    kleur: "rgb(var(--succes))" },
  fout:     { label: "Fout",     kleur: "rgb(var(--fout))" },
};

type Variant =
  | "formulier"
  | "lijst"
  | "status-lopend"
  | "status-klaar"
  | "status-fout";

const VARIANTEN: { id: Variant; label: string }[] = [
  { id: "formulier",     label: "Aanmaken-formulier" },
  { id: "lijst",         label: "Analyselijst" },
  { id: "status-lopend", label: "Status — lopend" },
  { id: "status-klaar",  label: "Status — klaar" },
  { id: "status-fout",   label: "Status — fout" },
];

function StatusBadge({ status }: { status: AnalyseStatus }) {
  const { label, kleur } = STATUS_META[status];
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.125rem 0.5rem",
        borderRadius: "99px",
        fontSize: "0.75rem",
        fontWeight: 600,
        background: kleur,
        color: "white",
      }}
    >
      {label}
    </span>
  );
}

function WetSelectorInForm() {
  const [gekozenWet, setGekozenWet] = useState("");
  const [gekozenArtikelen, setGekozenArtikelen] = useState<string[]>([]);
  const artikelen = gekozenWet ? (NEP_STRUCTUUR[gekozenWet] ?? []) : [];

  function toggleArtikel(artikel: string) {
    setGekozenArtikelen((prev) =>
      prev.includes(artikel) ? prev.filter((a) => a !== artikel) : [...prev, artikel]
    );
  }

  return (
    <div>
      <div style={{ marginBottom: "0.75rem" }}>
        <label
          style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.25rem" }}
        >
          Wet
        </label>
        <select
          className="field-input"
          value={gekozenWet}
          onChange={(e) => { setGekozenWet(e.target.value); setGekozenArtikelen([]); }}
          style={{ width: "100%" }}
        >
          <option value="">— Kies een wet —</option>
          {NEP_WETTEN.map((w) => (
            <option key={w.bwb_id} value={w.bwb_id}>{w.naam}</option>
          ))}
        </select>
      </div>

      {gekozenWet && (
        <div>
          <label
            style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.25rem" }}
          >
            Artikelen
          </label>
          <div style={{ border: "1px solid rgb(var(--line))", borderRadius: "6px", overflow: "hidden" }}>
            {artikelen.map((a, i) => (
              <label
                key={a.artikel}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.4rem 0.75rem",
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
                <span style={{ color: "rgb(var(--muted))", fontSize: "0.8125rem" }}>{a.pad}</span>
              </label>
            ))}
          </div>
          {gekozenArtikelen.length > 0 && (
            <p style={{ marginTop: "0.375rem", fontSize: "0.75rem", color: "rgb(var(--muted))" }}>
              {gekozenArtikelen.length} {gekozenArtikelen.length === 1 ? "artikel" : "artikelen"} geselecteerd
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function AanmakenFormulier() {
  return (
    <div style={{ maxWidth: "40rem" }}>
      <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1.5rem" }}>
        Nieuwe analyse
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <div>
          <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.25rem" }}>
            Naam werkgebied
          </label>
          <input
            className="field-input"
            type="text"
            placeholder="bv. Participatieplicht 2026"
            style={{ width: "100%" }}
          />
        </div>

        <div>
          <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.5rem" }}>
            Bronartikelen
            <span style={{ fontWeight: 400, color: "rgb(var(--faint))", marginLeft: "0.375rem" }}>
              (minimaal 1)
            </span>
          </label>
          <WetSelectorInForm />
        </div>

        <div>
          <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.25rem" }}>
            Analysefocus
            <span style={{ fontWeight: 400, color: "rgb(var(--faint))", marginLeft: "0.375rem" }}>
              (optioneel — hoofdvraag of aandachtspunt)
            </span>
          </label>
          <textarea
            className="field-input"
            rows={3}
            placeholder="Beschrijf de specifieke vraag of focus voor deze analyse..."
            style={{ width: "100%", resize: "vertical", fontFamily: "inherit" }}
          />
        </div>

        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button className="btn btn-primary">Analyse starten</button>
          <button className="btn btn-secondary">Annuleer</button>
        </div>
      </div>
    </div>
  );
}

function AnalyseLijst({ analyses }: { analyses: AnalyseOverzicht[] }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: 600 }}>Mijn analyses</h2>
        <button className="btn btn-primary" style={{ fontSize: "0.8125rem" }}>
          + Nieuwe analyse
        </button>
      </div>

      {analyses.length === 0 ? (
        <LeegePlaceholder tekst="Nog geen analyses aangemaakt." />
      ) : (
        <table className="tabel" style={{ width: "100%" }}>
          <thead>
            <tr>
              <th>Naam</th>
              <th>Status</th>
              <th>Bijgewerkt</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {analyses.map((a) => (
              <tr key={a.id}>
                <td style={{ fontWeight: 500 }}>{a.naam}</td>
                <td><StatusBadge status={a.status} /></td>
                <td style={{ color: "rgb(var(--muted))", fontSize: "0.875rem" }}>
                  {new Date(a.bijgewerkt).toLocaleString("nl-NL", {
                    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"
                  })}
                </td>
                <td>
                  <button className="btn btn-secondary" style={{ fontSize: "0.75rem", padding: "0.25rem 0.625rem" }}>
                    Bekijk →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function StatusScherm({
  status,
  naam,
  huidigeFase,
  foutmelding,
}: {
  status: AnalyseStatus;
  naam: string;
  huidigeFase?: string;
  foutmelding?: string;
}) {
  return (
    <div style={{ maxWidth: "40rem" }}>
      <div style={{ marginBottom: "0.5rem" }}>
        <button
          className="btn btn-secondary"
          style={{ fontSize: "0.8125rem", marginBottom: "1rem" }}
        >
          ← Terug naar analyses
        </button>
      </div>

      <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "0.5rem" }}>{naam}</h2>

      <div style={{ marginBottom: "1.5rem" }}>
        <StatusBadge status={status} />
      </div>

      {status === "actief" && (
        <div
          style={{
            padding: "1.25rem",
            background: "rgb(var(--surface))",
            border: "1px solid rgb(var(--line))",
            borderRadius: "8px",
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div
              style={{
                width: "16px",
                height: "16px",
                borderRadius: "50%",
                border: "2px solid rgb(var(--info))",
                borderTopColor: "transparent",
                animation: "spin 1s linear infinite",
                flexShrink: 0,
              }}
            />
            <span style={{ fontSize: "0.875rem", fontWeight: 500 }}>
              Analyse loopt
              {huidigeFase && (
                <span style={{ fontWeight: 400, color: "rgb(var(--muted))", marginLeft: "0.375rem" }}>
                  — {huidigeFase}
                </span>
              )}
            </span>
          </div>
          <div
            style={{
              height: "6px",
              background: "rgb(var(--line))",
              borderRadius: "99px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: "45%",
                background: "rgb(var(--info))",
                borderRadius: "99px",
              }}
            />
          </div>
          <p style={{ fontSize: "0.8125rem", color: "rgb(var(--muted))" }}>
            Live updates via SSE — de pagina hoeft niet te worden herladen.
          </p>
        </div>
      )}

      {status === "klaar" && (
        <div>
          <div className="melding" style={{ background: "rgb(var(--succes) / 0.1)", borderColor: "rgb(var(--succes))", marginBottom: "1rem" }}>
            De analyse is succesvol afgerond.
          </div>
          <button className="btn btn-primary">Bekijk rapport →</button>
        </div>
      )}

      {status === "fout" && (
        <div>
          <div className="melding melding-fout" style={{ marginBottom: "1rem" }}>
            {foutmelding ?? "Er is een onverwachte fout opgetreden tijdens de analyse."}
          </div>
          <button className="btn btn-secondary">← Terug naar analyses</button>
        </div>
      )}
    </div>
  );
}

export default function AnalyseMockup() {
  const [variant, setVariant] = useState<Variant>("formulier");

  return (
    <div className="main">
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>

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
        Mockup — Analyse aanmaken en volgen (story 012)
      </div>

      <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" }}>Analyses</h1>

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

      {variant === "formulier"     && <AanmakenFormulier />}
      {variant === "lijst"         && <AnalyseLijst analyses={NEP_ANALYSES} />}
      {variant === "status-lopend" && (
        <StatusScherm
          status="actief"
          naam="SUWI uitwisseling persoonsgegevens"
          huidigeFase="act 2 — bronverkenning"
        />
      )}
      {variant === "status-klaar" && (
        <StatusScherm status="klaar" naam="Wwb participatieplicht 2026" />
      )}
      {variant === "status-fout" && (
        <StatusScherm
          status="fout"
          naam="Test met verkeerde API-sleutel"
          foutmelding="Authenticatie mislukt bij het LLM-model (HTTP 401). Controleer de API-sleutel in het LLM-profiel."
        />
      )}
    </div>
  );
}
