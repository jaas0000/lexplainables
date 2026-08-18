"use client";

import { useState, useEffect } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

type AnalyseStatus = "wachtrij" | "actief" | "review" | "klaar" | "fout";

type BronKeuze = { bwb_id: string; artikel: string; pad: string };

type AnalyseOverzicht = {
  id: string;
  naam: string;
  status: AnalyseStatus;
  bijgewerkt: string;
};

// ─── Nep-data ─────────────────────────────────────────────────────────────────

const INIT_ANALYSES: AnalyseOverzicht[] = [
  { id: "a1b2c3", naam: "Wwb participatieplicht 2026",           status: "klaar",    bijgewerkt: "2026-08-14T11:30:00Z" },
  { id: "d4e5f6", naam: "SUWI uitwisseling persoonsgegevens",    status: "actief",   bijgewerkt: "2026-08-14T10:15:00Z" },
  { id: "g7h8i9", naam: "Participatiewet art. 8a–10",            status: "wachtrij", bijgewerkt: "2026-08-14T09:00:00Z" },
  { id: "j0k1l2", naam: "Test met verkeerde API-sleutel",        status: "fout",     bijgewerkt: "2026-08-13T16:45:00Z" },
];

const NEP_WETTEN = [
  { bwb_id: "BWBR0011823", naam: "Wet werk en bijstand" },
  { bwb_id: "BWBR0015703", naam: "Wet structuur uitvoeringsorganisatie werk en inkomen" },
  { bwb_id: "BWBR0020183", naam: "Participatiewet" },
];

// O(1) bwb_id → naam lookup voor de bronnen-chips (E3)
const NEP_WETTEN_NAAM = new Map(NEP_WETTEN.map((w) => [w.bwb_id, w.naam]));

const NEP_STRUCTUUR: Record<string, { artikel: string; pad: string }[]> = {
  BWBR0011823: [
    { artikel: "1",  pad: "Hoofdstuk 1 / Artikel 1" },
    { artikel: "2",  pad: "Hoofdstuk 1 / Artikel 2" },
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

// Simulated SSE events: fase-tekst + bijbehorend voortgangspercentage
const SSE_FASES: { tekst: string; pct: number }[] = [
  { tekst: "stap 1/4 — bronnen ophalen",       pct: 15 },
  { tekst: "stap 2/4 — artikelen doorlezen",   pct: 38 },
  { tekst: "stap 3/4 — verbanden leggen",      pct: 65 },
  { tekst: "stap 4/4 — rapport samenstellen",  pct: 88 },
];

// ─── Variants ─────────────────────────────────────────────────────────────────

type Variant =
  | "formulier"
  | "lijst"
  | "status-wachtrij"
  | "status-lopend"
  | "status-klaar"
  | "status-fout";

const VARIANTEN: { id: Variant; label: string }[] = [
  { id: "formulier",       label: "Aanmaken-formulier" },
  { id: "lijst",           label: "Analyselijst" },
  { id: "status-wachtrij", label: "Status — wachtrij" },
  { id: "status-lopend",   label: "Status — lopend" },
  { id: "status-klaar",    label: "Status — klaar" },
  { id: "status-fout",     label: "Status — fout" },
];

// ─── Kleine hulpcomponenten ───────────────────────────────────────────────────

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

function TerugKnop({ onClick }: { onClick: () => void }) {
  return (
    <button
      className="btn btn-secondary"
      style={{ fontSize: "0.8125rem", marginBottom: "1rem" }}
      onClick={onClick}
    >
      ← Terug naar analyses
    </button>
  );
}

// A1: één bevestig-patroon voor zowel status-schermen als de lijst-rijen
function VerwijderKnop({ onClick, compact = false }: { onClick: () => void; compact?: boolean }) {
  const [bevestig, setBevestig] = useState(false);
  if (bevestig) {
    return (
      <span style={{ display: "inline-flex", gap: "0.5rem", alignItems: "center" }}>
        <button
          className="btn"
          style={{
            fontSize: compact ? "0.75rem" : "0.8125rem",
            padding: compact ? "0.25rem 0.625rem" : "0.375rem 0.875rem",
            background: "rgb(var(--fout))",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
          onClick={onClick}
        >
          {compact ? "Verwijder ✓" : "Bevestig verwijderen"}
        </button>
        <button
          className="btn btn-secondary"
          style={{ fontSize: compact ? "0.75rem" : "0.8125rem",
                   padding: compact ? "0.25rem 0.625rem" : undefined }}
          onClick={() => setBevestig(false)}
        >
          Annuleer
        </button>
      </span>
    );
  }
  return (
    <button
      className="btn btn-secondary"
      style={{
        fontSize: compact ? "0.75rem" : "0.8125rem",
        padding: compact ? "0.25rem 0.625rem" : undefined,
        color: "rgb(var(--fout))",
      }}
      onClick={() => setBevestig(true)}
    >
      Verwijder
    </button>
  );
}

// S2: gedeelde schil voor alle vier status-schermen
function StatusSchermShell({
  naam,
  status,
  onTerug,
  children,
}: {
  naam: string;
  status: AnalyseStatus;
  onTerug: () => void;
  children: React.ReactNode;
}) {
  return (
    <div style={{ maxWidth: "40rem" }}>
      <TerugKnop onClick={onTerug} />
      <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "0.5rem" }}>{naam}</h2>
      <div style={{ marginBottom: "1.5rem" }}>
        <StatusBadge status={status} />
      </div>
      {children}
    </div>
  );
}

// ─── WetSelector ─────────────────────────────────────────────────────────────

function WetSelectorInForm({
  bronnen,
  setBronnen,
}: {
  bronnen: BronKeuze[];
  setBronnen: (b: BronKeuze[]) => void;
}) {
  const [gekozenWet, setGekozenWet] = useState("");
  const artikelen = gekozenWet ? (NEP_STRUCTUUR[gekozenWet] ?? []) : [];

  // S4: één helper voor zowel toggleArtikel als het chip-kruisje
  function verwijderArtikel(bwb_id: string, artikel: string) {
    setBronnen(bronnen.filter((b) => !(b.bwb_id === bwb_id && b.artikel === artikel)));
  }

  function toggleArtikel(artikel: string, pad: string) {
    if (bronnen.some((b) => b.bwb_id === gekozenWet && b.artikel === artikel)) {
      verwijderArtikel(gekozenWet, artikel);
    } else {
      setBronnen([...bronnen, { bwb_id: gekozenWet, artikel, pad }]);
    }
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
          onChange={(e) => setGekozenWet(e.target.value)}
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
        <div style={{ marginBottom: "0.75rem" }}>
          <label
            style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.25rem" }}
          >
            Artikelen
          </label>
          <div style={{ border: "1px solid rgb(var(--line))", borderRadius: "6px", overflow: "hidden" }}>
            {artikelen.map((a, i) => {
              // S5/E2: één keer berekenen, twee keer gebruiken
              const geselecteerd = bronnen.some(
                (b) => b.bwb_id === gekozenWet && b.artikel === a.artikel
              );
              return (
                <label
                  key={a.artikel}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    padding: "0.4rem 0.75rem",
                    cursor: "pointer",
                    background: geselecteerd ? "rgb(var(--surface))" : "rgb(var(--paper))",
                    borderTop: i > 0 ? "1px solid rgb(var(--line))" : "none",
                    fontSize: "0.875rem",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={geselecteerd}
                    onChange={() => toggleArtikel(a.artikel, a.pad)}
                  />
                  <span style={{ fontWeight: 500, minWidth: "3rem" }}>art. {a.artikel}</span>
                  <span style={{ color: "rgb(var(--muted))", fontSize: "0.8125rem" }}>{a.pad}</span>
                </label>
              );
            })}
          </div>
        </div>
      )}

      {bronnen.length > 0 && (
        <div>
          <p
            style={{
              fontSize: "0.75rem",
              fontWeight: 500,
              color: "rgb(var(--muted))",
              marginBottom: "0.375rem",
            }}
          >
            Geselecteerde bronnen ({bronnen.length}):
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
            {bronnen.map((b) => (
              <span
                key={`${b.bwb_id}-${b.artikel}`}
                style={{
                  fontSize: "0.75rem",
                  padding: "0.125rem 0.375rem 0.125rem 0.5rem",
                  background: "rgb(var(--surface))",
                  border: "1px solid rgb(var(--line))",
                  borderRadius: "4px",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.375rem",
                }}
              >
                {/* E3: O(1) map-lookup i.p.v. .find() per chip per render */}
                {NEP_WETTEN_NAAM.get(b.bwb_id)} art. {b.artikel}
                <button
                  onClick={() => verwijderArtikel(b.bwb_id, b.artikel)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "rgb(var(--muted))",
                    padding: "0",
                    fontSize: "0.75rem",
                    lineHeight: 1,
                  }}
                  aria-label={`Verwijder art. ${b.artikel}`}
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Aanmaken-formulier ───────────────────────────────────────────────────────

function AanmakenFormulier({ onNavigeer }: { onNavigeer: (v: Variant) => void }) {
  const [naam, setNaam] = useState("");
  const [bronnen, setBronnen] = useState<BronKeuze[]>([]);
  const [analysefocus, setAnalysefocus] = useState("");
  const [geprobeerd, setGeprobeerd] = useState(false);

  const kanVerzenden = naam.trim().length > 0 && bronnen.length > 0;

  function handleVerzenden() {
    setGeprobeerd(true);
    if (!kanVerzenden) return;
    // Simuleer 202-response: navigeer naar wachtrij-variant
    onNavigeer("status-wachtrij");
  }

  return (
    <div style={{ maxWidth: "40rem" }}>
      {/* S1: TerugKnop heeft al marginBottom — geen wrapper div nodig */}
      <TerugKnop onClick={() => onNavigeer("lijst")} />
      <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1.5rem" }}>
        Nieuwe analyse
      </h2>

      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <div>
          <label
            style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.25rem" }}
          >
            Naam werkgebied
          </label>
          <input
            className="field-input"
            type="text"
            placeholder="bv. Participatieplicht 2026"
            value={naam}
            onChange={(e) => setNaam(e.target.value)}
            style={{ width: "100%" }}
          />
          {geprobeerd && naam.trim().length === 0 && (
            <p style={{ fontSize: "0.75rem", color: "rgb(var(--fout))", marginTop: "0.25rem" }}>
              Naam is verplicht.
            </p>
          )}
        </div>

        <div>
          <label
            style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.5rem" }}
          >
            Bronartikelen
            <span
              style={{ fontWeight: 400, color: "rgb(var(--faint))", marginLeft: "0.375rem" }}
            >
              (minimaal 1)
            </span>
          </label>
          <WetSelectorInForm bronnen={bronnen} setBronnen={setBronnen} />
          {geprobeerd && bronnen.length === 0 && (
            <p style={{ fontSize: "0.75rem", color: "rgb(var(--fout))", marginTop: "0.375rem" }}>
              Selecteer minimaal 1 bronartikel.
            </p>
          )}
        </div>

        <div>
          <label
            style={{ display: "block", fontSize: "0.8125rem", fontWeight: 500, marginBottom: "0.25rem" }}
          >
            Analysefocus
            <span
              style={{ fontWeight: 400, color: "rgb(var(--faint))", marginLeft: "0.375rem" }}
            >
              (optioneel — hoofdvraag of aandachtspunt)
            </span>
          </label>
          <textarea
            className="field-input"
            rows={3}
            placeholder="Beschrijf de specifieke vraag of focus voor deze analyse..."
            value={analysefocus}
            onChange={(e) => setAnalysefocus(e.target.value)}
            style={{ width: "100%", resize: "vertical", fontFamily: "inherit" }}
          />
        </div>

        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button className="btn btn-primary" onClick={handleVerzenden}>
            Analyse starten
          </button>
          <button className="btn btn-secondary" onClick={() => onNavigeer("lijst")}>
            Annuleer
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Analyselijst ─────────────────────────────────────────────────────────────

function AnalyseLijst({
  analyses,
  onBekijk,
  onVerwijder,
  onNieuw,
}: {
  analyses: AnalyseOverzicht[];
  onBekijk: (id: string) => void;
  onVerwijder: (id: string) => void;
  onNieuw: () => void;
}) {
  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <h2 style={{ fontSize: "1.125rem", fontWeight: 600 }}>
          Mijn analyses
          <span
            style={{
              fontSize: "0.8125rem",
              fontWeight: 400,
              color: "rgb(var(--muted))",
              marginLeft: "0.5rem",
            }}
          >
            ({analyses.length})
          </span>
        </h2>
        <button
          className="btn btn-primary"
          style={{ fontSize: "0.8125rem" }}
          onClick={onNieuw}
        >
          + Nieuwe analyse
        </button>
      </div>

      {analyses.length === 0 ? (
        <div
          style={{
            padding: "2.5rem",
            textAlign: "center",
            color: "rgb(var(--muted))",
            fontSize: "0.875rem",
            background: "rgb(var(--surface))",
            border: "1px solid rgb(var(--line))",
            borderRadius: "8px",
          }}
        >
          Nog geen analyses aangemaakt.
          <br />
          <button
            className="btn btn-primary"
            style={{ marginTop: "1rem", fontSize: "0.875rem" }}
            onClick={onNieuw}
          >
            + Nieuwe analyse starten
          </button>
        </div>
      ) : (
        <table className="tabel" style={{ width: "100%" }}>
          <thead>
            <tr>
              <th>Naam</th>
              <th>Status</th>
              <th>Bijgewerkt</th>
              <th style={{ textAlign: "right" }}></th>
            </tr>
          </thead>
          <tbody>
            {analyses.map((a) => (
              <tr key={a.id}>
                <td style={{ fontWeight: 500 }}>{a.naam}</td>
                <td>
                  <StatusBadge status={a.status} />
                </td>
                <td style={{ color: "rgb(var(--muted))", fontSize: "0.875rem", whiteSpace: "nowrap" }}>
                  {new Date(a.bijgewerkt).toLocaleString("nl-NL", {
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </td>
                {/* A1: VerwijderKnop compact=true i.p.v. eigen bevestigId-state */}
                <td style={{ textAlign: "right" }}>
                  <span style={{ display: "inline-flex", gap: "0.375rem", alignItems: "center" }}>
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: "0.75rem", padding: "0.25rem 0.625rem" }}
                      onClick={() => onBekijk(a.id)}
                    >
                      Bekijk →
                    </button>
                    <VerwijderKnop compact onClick={() => onVerwijder(a.id)} />
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ─── Status-schermen ──────────────────────────────────────────────────────────

function StatusSchermWachtrij({
  naam,
  onTerug,
  onVerwijder,
}: {
  naam: string;
  onTerug: () => void;
  onVerwijder: () => void;
}) {
  return (
    <StatusSchermShell naam={naam} status="wachtrij" onTerug={onTerug}>
      <div
        style={{
          padding: "1.25rem",
          background: "rgb(var(--surface))",
          border: "1px solid rgb(var(--line))",
          borderRadius: "8px",
          marginBottom: "1.25rem",
        }}
      >
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          De analyse staat in de wachtrij en wacht op beschikbare verwerkingscapaciteit. De pagina
          wordt automatisch bijgewerkt via SSE zodra de verwerking begint.
        </p>
      </div>
      <VerwijderKnop onClick={onVerwijder} />
    </StatusSchermShell>
  );
}

function StatusSchermLopend({
  naam,
  onTerug,
  onVerwijder,
}: {
  naam: string;
  onTerug: () => void;
  onVerwijder: () => void;
}) {
  const [faseIdx, setFaseIdx] = useState(0);
  const fase = SSE_FASES[faseIdx];

  // Simuleert SSE-events: elke 2,4 s een nieuw fase-event
  useEffect(() => {
    const id = setInterval(() => {
      setFaseIdx((prev) => (prev + 1) % SSE_FASES.length);
    }, 2400);
    return () => clearInterval(id);
  }, []);

  return (
    <StatusSchermShell naam={naam} status="actief" onTerug={onTerug}>
      <div
        style={{
          padding: "1.25rem",
          background: "rgb(var(--surface))",
          border: "1px solid rgb(var(--line))",
          borderRadius: "8px",
          display: "flex",
          flexDirection: "column",
          gap: "0.875rem",
          marginBottom: "1.25rem",
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
            <span
              style={{ fontWeight: 400, color: "rgb(var(--muted))", marginLeft: "0.375rem" }}
            >
              — {fase.tekst}
            </span>
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
              width: `${fase.pct}%`,
              background: "rgb(var(--info))",
              borderRadius: "99px",
              transition: "width 0.6s ease",
            }}
          />
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <p style={{ fontSize: "0.8125rem", color: "rgb(var(--muted))" }}>
            Live updates via SSE — de pagina hoeft niet te worden herladen.
          </p>
          <span
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "rgb(var(--info))",
              minWidth: "2.5rem",
              textAlign: "right",
            }}
          >
            {fase.pct}%
          </span>
        </div>
      </div>

      <VerwijderKnop onClick={onVerwijder} />
    </StatusSchermShell>
  );
}

function StatusSchermKlaar({
  naam,
  onTerug,
  onVerwijder,
}: {
  naam: string;
  onTerug: () => void;
  onVerwijder: () => void;
}) {
  return (
    <StatusSchermShell naam={naam} status="klaar" onTerug={onTerug}>
      <div
        className="melding"
        style={{
          background: "rgb(var(--succes) / 0.1)",
          borderColor: "rgb(var(--succes))",
          marginBottom: "1.25rem",
        }}
      >
        De analyse is succesvol afgerond.
      </div>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
        <button className="btn btn-primary">Bekijk rapport →</button>
        <VerwijderKnop onClick={onVerwijder} />
      </div>
    </StatusSchermShell>
  );
}

function StatusSchermFout({
  naam,
  foutmelding,
  onTerug,
  onVerwijder,
}: {
  naam: string;
  foutmelding: string;
  onTerug: () => void;
  onVerwijder: () => void;
}) {
  return (
    <StatusSchermShell naam={naam} status="fout" onTerug={onTerug}>
      <div className="melding melding-fout" style={{ marginBottom: "1.25rem" }}>
        {foutmelding}
      </div>
      <VerwijderKnop onClick={onVerwijder} />
    </StatusSchermShell>
  );
}

// ─── Hoofd-mockup-component ───────────────────────────────────────────────────

export default function AnalyseMockup() {
  const [variant, setVariant] = useState<Variant>("lijst");
  const [analyses, setAnalyses] = useState<AnalyseOverzicht[]>(INIT_ANALYSES);

  function verwijderAnalyse(id: string) {
    setAnalyses((prev) => prev.filter((a) => a.id !== id));
    setVariant("lijst");
  }

  function bekijkAnalyse(id: string) {
    const a = analyses.find((x) => x.id === id);
    if (!a) return;
    const variantMap: Record<AnalyseStatus, Variant> = {
      wachtrij: "status-wachtrij",
      actief:   "status-lopend",
      review:   "status-lopend",
      klaar:    "status-klaar",
      fout:     "status-fout",
    };
    setVariant(variantMap[a.status]);
  }

  // S3/A2: per-variant lookup — dient voor zowel rendering als disabled-state in de switcher.
  // Elke lookup is O(n) over max 4 analyses; geen precomputed object nodig.
  const analyseVoor = {
    wachtrij: analyses.find((a) => a.status === "wachtrij"),
    lopend:   analyses.find((a) => a.status === "actief" || a.status === "review"),
    klaar:    analyses.find((a) => a.status === "klaar"),
    fout:     analyses.find((a) => a.status === "fout"),
  };

  // A2: status-variant is alleen beschikbaar als er data is
  function isVariantBeschikbaar(v: Variant): boolean {
    if (v === "formulier" || v === "lijst") return true;
    if (v === "status-wachtrij") return analyseVoor.wachtrij !== undefined;
    if (v === "status-lopend")   return analyseVoor.lopend !== undefined;
    if (v === "status-klaar")    return analyseVoor.klaar !== undefined;
    if (v === "status-fout")     return analyseVoor.fout !== undefined;
    return false;
  }

  return (
    <div className="main">
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>

      {/* Mockup-badge */}
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
        Mockup — nepdata (story 012)
      </div>

      <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" }}>
        Analyse aanmaken en volgen
      </h1>

      {/* Variant-switcher — A2: status-varianten worden gedimd als er geen passende data is */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "2rem" }}>
        {VARIANTEN.map((v) => {
          const beschikbaar = isVariantBeschikbaar(v.id);
          return (
            <button
              key={v.id}
              className={variant === v.id ? "btn btn-primary" : "btn btn-secondary"}
              onClick={() => beschikbaar && setVariant(v.id)}
              disabled={!beschikbaar}
              title={beschikbaar ? undefined : "Geen analyse met deze status"}
              style={{ opacity: beschikbaar ? 1 : 0.4 }}
            >
              {v.label}
            </button>
          );
        })}
      </div>

      {/* Actieve variant */}
      {variant === "formulier" && (
        <AanmakenFormulier onNavigeer={setVariant} />
      )}

      {variant === "lijst" && (
        <AnalyseLijst
          analyses={analyses}
          onBekijk={bekijkAnalyse}
          onVerwijder={verwijderAnalyse}
          onNieuw={() => setVariant("formulier")}
        />
      )}

      {variant === "status-wachtrij" && analyseVoor.wachtrij && (
        <StatusSchermWachtrij
          naam={analyseVoor.wachtrij.naam}
          onTerug={() => setVariant("lijst")}
          onVerwijder={() => verwijderAnalyse(analyseVoor.wachtrij!.id)}
        />
      )}

      {variant === "status-lopend" && analyseVoor.lopend && (
        <StatusSchermLopend
          naam={analyseVoor.lopend.naam}
          onTerug={() => setVariant("lijst")}
          onVerwijder={() => verwijderAnalyse(analyseVoor.lopend!.id)}
        />
      )}

      {variant === "status-klaar" && analyseVoor.klaar && (
        <StatusSchermKlaar
          naam={analyseVoor.klaar.naam}
          onTerug={() => setVariant("lijst")}
          onVerwijder={() => verwijderAnalyse(analyseVoor.klaar!.id)}
        />
      )}

      {variant === "status-fout" && analyseVoor.fout && (
        <StatusSchermFout
          naam={analyseVoor.fout.naam}
          foutmelding="Authenticatie mislukt bij het LLM-model (HTTP 401). Controleer de API-sleutel in het LLM-profiel."
          onTerug={() => setVariant("lijst")}
          onVerwijder={() => verwijderAnalyse(analyseVoor.fout!.id)}
        />
      )}
    </div>
  );
}
