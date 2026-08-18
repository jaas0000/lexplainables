"use client";

import { useState, useEffect } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

type AnalyseStatus = "wachtrij" | "actief" | "review" | "klaar" | "fout";

type BronKeuze = { bwb_id: string; artikel: string; lid: string };

type AnalyseOverzicht = {
  id: string;
  naam: string;
  bronnen: BronKeuze[];
  status: AnalyseStatus;
  bijgewerkt: string;
};

// ─── Nep-data ─────────────────────────────────────────────────────────────────

const NEP_PROFIELEN = [
  { naam: "azure-sonnet (default)", is_default: true },
  { naam: "azure-gpt4o", is_default: false },
];

const NEP_WETTEN = [
  { bwb_id: "BWBR0011823", naam: "Wet werk en bijstand" },
  { bwb_id: "BWBR0015703", naam: "Wet structuur uitvoeringsorganisatie werk en inkomen" },
  { bwb_id: "BWBR0020183", naam: "Participatiewet" },
];

// O(1) bwb_id → naam lookup
const WETTEN_NAAM = new Map(NEP_WETTEN.map((w) => [w.bwb_id, w.naam]));

const INIT_ANALYSES: AnalyseOverzicht[] = [
  {
    id: "a1b2c3",
    naam: "Wwb participatieplicht 2026",
    bronnen: [{ bwb_id: "BWBR0011823", artikel: "9", lid: "1" }],
    status: "klaar",
    bijgewerkt: "2026-08-14T11:30:00Z",
  },
  {
    id: "d4e5f6",
    naam: "SUWI uitwisseling persoonsgegevens",
    bronnen: [
      { bwb_id: "BWBR0015703", artikel: "7", lid: "" },
      { bwb_id: "BWBR0015703", artikel: "33", lid: "" },
    ],
    status: "actief",
    bijgewerkt: "2026-08-14T10:15:00Z",
  },
  {
    id: "g7h8i9",
    naam: "Participatiewet art. 8a–10",
    bronnen: [
      { bwb_id: "BWBR0020183", artikel: "8a", lid: "" },
      { bwb_id: "BWBR0020183", artikel: "10", lid: "" },
    ],
    status: "wachtrij",
    bijgewerkt: "2026-08-14T09:00:00Z",
  },
  {
    id: "j0k1l2",
    naam: "Test met verkeerde API-sleutel",
    bronnen: [{ bwb_id: "BWBR0020183", artikel: "44", lid: "3" }],
    status: "fout",
    bijgewerkt: "2026-08-13T16:45:00Z",
  },
];

const STATUS_META: Record<AnalyseStatus, { label: string; kleur: string }> = {
  wachtrij: { label: "Wachtrij", kleur: "rgb(var(--waarschuwing))" },
  actief:   { label: "Actief",   kleur: "rgb(var(--info))" },
  review:   { label: "Review",   kleur: "rgb(var(--info))" },
  klaar:    { label: "Klaar",    kleur: "rgb(var(--succes))" },
  fout:     { label: "Fout",     kleur: "rgb(var(--fout))" },
};

// Gesimuleerde SSE-fases voor het lopend-scherm
const SSE_FASES: { tekst: string; pct: number }[] = [
  { tekst: "stap 1/4 — bronnen ophalen",      pct: 15 },
  { tekst: "stap 2/4 — artikelen doorlezen",  pct: 38 },
  { tekst: "stap 3/4 — verbanden leggen",     pct: 65 },
  { tekst: "stap 4/4 — rapport samenstellen", pct: 88 },
];

// ─── Variant-definitie ─────────────────────────────────────────────────────────

type Variant =
  | "lijst"
  | "formulier"
  | "status-wachtrij"
  | "status-lopend"
  | "status-klaar"
  | "status-fout";

const VARIANTEN: { id: Variant; label: string }[] = [
  { id: "lijst",           label: "Analyselijst" },
  { id: "formulier",       label: "Aanmaken-formulier" },
  { id: "status-wachtrij", label: "Status — wachtrij" },
  { id: "status-lopend",   label: "Status — lopend" },
  { id: "status-klaar",    label: "Status — klaar" },
  { id: "status-fout",     label: "Status — fout" },
];

// ─── Hulpfuncties ─────────────────────────────────────────────────────────────

function bronnenSamenvatting(bronnen: BronKeuze[]): string {
  if (bronnen.length === 0) return "—";
  const eerste = bronnen[0];
  const wetnaam = WETTEN_NAAM.get(eerste.bwb_id) ?? eerste.bwb_id;
  // Korte afkorting zodat de kolom niet te breed wordt
  const kort = wetnaam.length > 22 ? wetnaam.slice(0, 22) + "…" : wetnaam;
  const lidSuffix = eerste.lid ? ` lid ${eerste.lid}` : "";
  const rest = bronnen.length > 1 ? ` +${bronnen.length - 1}` : "";
  return `${kort} art. ${eerste.artikel}${lidSuffix}${rest}`;
}

function formatDatum(iso: string): string {
  return new Date(iso).toLocaleString("nl-NL", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ─── Kleine hulpcomponenten ───────────────────────────────────────────────────

// Status-dot: gekleurde cirkel + tekst, zoals in de wetsanalyse-ai tabel
function StatusDot({ status }: { status: AnalyseStatus }) {
  const { label, kleur } = STATUS_META[status];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
      <span
        style={{
          width: "8px",
          height: "8px",
          borderRadius: "50%",
          background: kleur,
          flexShrink: 0,
        }}
      />
      <span style={{ fontSize: "0.875rem", color: "rgb(var(--ink))" }}>{label}</span>
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

// Verwijderknop met één bevestiging (compact voor tabelrijen, normaal voor detailschermen)
function VerwijderKnop({
  onClick,
  compact = false,
}: {
  onClick: () => void;
  compact?: boolean;
}) {
  const [bevestig, setBevestig] = useState(false);
  if (bevestig) {
    return (
      <span style={{ display: "inline-flex", gap: "0.5rem", alignItems: "center" }}>
        <button
          className="btn btn-danger"
          style={{
            fontSize: compact ? "0.75rem" : "0.8125rem",
            padding: compact ? "0.25rem 0.625rem" : "0.375rem 0.875rem",
          }}
          onClick={onClick}
        >
          {compact ? "Verwijder ✓" : "Bevestig verwijderen"}
        </button>
        <button
          className="btn btn-secondary"
          style={{
            fontSize: compact ? "0.75rem" : "0.8125rem",
            padding: compact ? "0.25rem 0.625rem" : undefined,
          }}
          onClick={() => setBevestig(false)}
        >
          Annuleer
        </button>
      </span>
    );
  }
  return (
    <button
      className="btn btn-danger"
      style={{
        fontSize: compact ? "0.75rem" : "0.8125rem",
        padding: compact ? "0.25rem 0.625rem" : undefined,
      }}
      onClick={() => setBevestig(true)}
    >
      Verwijder
    </button>
  );
}

// Gedeelde shell voor alle vier status-schermen
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
      <h2
        style={{
          fontSize: "1.125rem",
          fontWeight: 600,
          marginBottom: "0.5rem",
          color: "rgb(var(--lint))",
        }}
      >
        {naam}
      </h2>
      <div style={{ marginBottom: "1.5rem" }}>
        <StatusDot status={status} />
      </div>
      {children}
    </div>
  );
}

// ─── Hero-banner (bovenaan de analyselijst) ────────────────────────────────────

function HeroBanner({ onNieuw }: { onNieuw: () => void }) {
  return (
    <div
      style={{
        background: "rgb(var(--communicatiekleur))",
        borderRadius: "8px",
        padding: "2rem 2.5rem",
        marginBottom: "1.5rem",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "1.25rem",
        }}
      >
        <div>
          <p
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "rgba(255,255,255,0.7)",
              marginBottom: "0.5rem",
            }}
          >
            Juridisch Analyseschema
          </p>
          <h1
            style={{
              fontSize: "1.75rem",
              fontWeight: 700,
              color: "white",
              margin: 0,
            }}
          >
            Analyses
          </h1>
          <p
            style={{
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.85)",
              marginTop: "0.5rem",
              maxWidth: "36rem",
            }}
          >
            Elke analyse duidt een werkgebied — één of meer bronnen (wetsartikel of lid) —
            brongetrouw volgens het Juridisch Analyseschema: markeren &amp; classificeren, daarna
            begrippen &amp; afleidingsregels.
          </p>
        </div>
        <div>
          <button
            className="btn"
            style={{
              background: "white",
              color: "rgb(var(--lint))",
              fontWeight: 600,
              border: "none",
            }}
            onClick={onNieuw}
          >
            Nieuwe analyse
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Filterbar (zoekbalk + dropdowns) ─────────────────────────────────────────

function FilterBar({
  zoek,
  setZoek,
  statusFilter,
  setStatusFilter,
  wetFilter,
  setWetFilter,
}: {
  zoek: string;
  setZoek: (v: string) => void;
  statusFilter: string;
  setStatusFilter: (v: string) => void;
  wetFilter: string;
  setWetFilter: (v: string) => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        gap: "0.75rem",
        flexWrap: "wrap",
        marginBottom: "1rem",
        alignItems: "center",
      }}
    >
      <input
        className="field-input"
        style={{ flex: "1 1 16rem", minWidth: "14rem" }}
        type="search"
        placeholder="Zoek op naam, BWB-id of artikel..."
        value={zoek}
        onChange={(e) => setZoek(e.target.value)}
      />
      <select
        className="field-input"
        style={{ width: "10rem", flex: "0 0 auto" }}
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
      >
        <option value="">Alle statussen</option>
        <option value="wachtrij">Wachtrij</option>
        <option value="actief">Actief</option>
        <option value="review">Review</option>
        <option value="klaar">Klaar</option>
        <option value="fout">Fout</option>
      </select>
      <select
        className="field-input"
        style={{ width: "14rem", flex: "0 0 auto" }}
        value={wetFilter}
        onChange={(e) => setWetFilter(e.target.value)}
      >
        <option value="">Alle wetten</option>
        {NEP_WETTEN.map((w) => (
          <option key={w.bwb_id} value={w.bwb_id}>
            {w.naam}
          </option>
        ))}
      </select>
    </div>
  );
}

// ─── BronRij (één bron in het aanmaakformulier) ────────────────────────────────

function BronRij({
  bron,
  onUpdate,
  onVerwijder,
  verwijderDisabled,
}: {
  bron: BronKeuze;
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
      {/* Wet-dropdown */}
      <div>
        <label className="field-label">Wet</label>
        <select
          className="field-input"
          value={bron.bwb_id}
          onChange={(e) =>
            onUpdate({ bwb_id: e.target.value, artikel: "", lid: "" })
          }
        >
          <option value="">— kies een wet —</option>
          {NEP_WETTEN.map((w) => (
            <option key={w.bwb_id} value={w.bwb_id}>
              {w.naam}
            </option>
          ))}
        </select>
      </div>

      {/* Artikel */}
      <div>
        <label className="field-label">
          Artikel{" "}
          <span style={{ color: "rgb(var(--fout))", fontWeight: 700 }}>*</span>
        </label>
        <input
          className="field-input"
          style={{ width: "6rem" }}
          type="text"
          placeholder="9"
          value={bron.artikel}
          onChange={(e) => onUpdate({ artikel: e.target.value, lid: "" })}
          autoComplete="off"
        />
      </div>

      {/* Lid (optioneel) */}
      <div>
        <label className="field-label" style={{ color: "rgb(var(--muted))" }}>
          Lid
        </label>
        <input
          className="field-input"
          style={{ width: "5rem" }}
          type="text"
          placeholder="1"
          value={bron.lid}
          onChange={(e) => onUpdate({ lid: e.target.value })}
          autoComplete="off"
        />
      </div>

      {/* Verwijder */}
      <div>
        {/* Lege label zodat de ×-knop op gelijke hoogte staat */}
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

// ─── Aanmaken-formulier ───────────────────────────────────────────────────────

function AanmakenFormulier({ onNavigeer }: { onNavigeer: (v: Variant) => void }) {
  const [bronnen, setBronnen] = useState<BronKeuze[]>([
    { bwb_id: "", artikel: "", lid: "" },
  ]);
  const [naam, setNaam] = useState("");
  const [omschrijving, setOmschrijving] = useState("");
  const [analysefocus, setAnalysefocus] = useState("");
  const [begrippenTekst, setBegrippenTekst] = useState("");
  const [profiel, setProfiel] = useState("azure-sonnet (default)");
  const [review, setReview] = useState(true);
  const [geprobeerd, setGeprobeerd] = useState(false);

  const heeftGeldigeBron = bronnen.some(
    (b) => b.bwb_id.length > 0 && b.artikel.trim().length > 0
  );

  function updateBron(i: number, patch: Partial<BronKeuze>) {
    setBronnen((bs) => bs.map((b, j) => (j === i ? { ...b, ...patch } : b)));
  }
  function voegBronToe() {
    setBronnen((bs) => [...bs, { bwb_id: "", artikel: "", lid: "" }]);
  }
  function verwijderBron(i: number) {
    setBronnen((bs) => (bs.length > 1 ? bs.filter((_, j) => j !== i) : bs));
  }

  function handleVerzenden(e: React.FormEvent) {
    e.preventDefault();
    setGeprobeerd(true);
    if (!heeftGeldigeBron) return;
    // Simuleer 202-response → navigeer naar wachtrij-variant
    onNavigeer("status-wachtrij");
  }

  const begrippenRegels = begrippenTekst.trim().split("\n").filter(Boolean).length;

  return (
    <div style={{ maxWidth: "40rem" }}>
      <TerugKnop onClick={() => onNavigeer("lijst")} />

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
        De orchestrator haalt de wettekst op via de wettenbank en doorloopt activiteit 2 en 3.
        Met review aan pauzeert hij na elke activiteit voor jouw akkoord.
      </p>

      <div className="card">
        <form
          onSubmit={handleVerzenden}
          style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}
        >
          {/* Bronnen in het werkgebied */}
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
                Voeg minimaal 1 bronartikel toe (wet + artikel verplicht).
              </p>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem" }}>
              {bronnen.map((b, i) => (
                <BronRij
                  key={i}
                  bron={b}
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
            <select
              className="field-input"
              value={profiel}
              onChange={(e) => setProfiel(e.target.value)}
            >
              {NEP_PROFIELEN.map((p) => (
                <option key={p.naam} value={p.naam}>
                  {p.naam}
                </option>
              ))}
            </select>
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

          {/* Omschrijving / context */}
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

          {/* Hoofdvraag / analysefocus */}
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

          {/* Bestaande begrippenlijst (inklapbaar) */}
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
              <span style={{ fontWeight: 400, color: "rgb(var(--muted))" }}>(optioneel)</span>
              {begrippenRegels > 0 && (
                <span
                  style={{
                    marginLeft: "0.5rem",
                    fontFamily: "monospace",
                    fontSize: "0.75rem",
                    color: "rgb(var(--faint))",
                  }}
                >
                  {begrippenRegels} regel{begrippenRegels === 1 ? "" : "s"} ingevoerd
                </span>
              )}
            </summary>
            <div
              style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}
            >
              <p style={{ fontSize: "0.8125rem", color: "rgb(var(--muted))" }}>
                Plak of upload een bestaande begrippenlijst als suggestieve invoer voor activiteit 3:
                JSON (<code>{`{"begrippen": [...]}`}</code>), CSV met kopregel (kolom{" "}
                <code>naam</code> verplicht), of één begrip per regel (
                <code>naam; definitie</code>). De analyse hergebruikt waar de betekenis past en
                registreert per begrip de herkomst.
              </p>
              <textarea
                className="field-input"
                rows={4}
                placeholder={
                  "belastingplichtige; degene die aangifte moet doen\nbijdrage-inkomen"
                }
                value={begrippenTekst}
                onChange={(e) => setBegrippenTekst(e.target.value)}
                style={{ resize: "vertical", fontFamily: "monospace", fontSize: "0.8125rem" }}
              />
            </div>
          </details>

          {/* Human-in-the-loop review */}
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
              style={{
                marginTop: "0.125rem",
                width: "1rem",
                height: "1rem",
                accentColor: "rgb(var(--accent))",
              }}
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
                Pauzeer na activiteit 2 en 3 voor jouw beoordeling. Uit = volautomatisch tot het
                rapport (brongetrouwheid blijft hard afgedwongen).
              </span>
            </span>
          </label>

          {/* Submit */}
          <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.5rem" }}>
            <button className="btn btn-primary" type="submit" style={{ fontWeight: 600 }}>
              Analyse starten
            </button>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={() => onNavigeer("lijst")}
            >
              Annuleer
            </button>
          </div>
        </form>
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
  const [zoek, setZoek] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [wetFilter, setWetFilter] = useState("");
  const [geselecteerd, setGeselecteerd] = useState<Set<string>>(new Set());

  const gefilterd = analyses.filter((a) => {
    if (statusFilter && a.status !== statusFilter) return false;
    if (wetFilter && !a.bronnen.some((b) => b.bwb_id === wetFilter)) return false;
    if (zoek) {
      const q = zoek.toLowerCase();
      if (
        !a.naam.toLowerCase().includes(q) &&
        !a.id.toLowerCase().includes(q) &&
        !a.bronnen.some(
          (b) =>
            b.bwb_id.toLowerCase().includes(q) || b.artikel.toLowerCase().includes(q)
        )
      )
        return false;
    }
    return true;
  });

  const alleGeselecteerd =
    gefilterd.length > 0 && gefilterd.every((a) => geselecteerd.has(a.id));
  const enkeleGeselecteerd = gefilterd.some((a) => geselecteerd.has(a.id));

  function toggleAlles() {
    setGeselecteerd((prev) => {
      const next = new Set(prev);
      if (alleGeselecteerd) gefilterd.forEach((a) => next.delete(a.id));
      else gefilterd.forEach((a) => next.add(a.id));
      return next;
    });
  }

  function toggleEen(id: string) {
    setGeselecteerd((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div>
      <HeroBanner onNieuw={onNieuw} />
      <FilterBar
        zoek={zoek}
        setZoek={setZoek}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        wetFilter={wetFilter}
        setWetFilter={setWetFilter}
      />

      {gefilterd.length === 0 ? (
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
          {analyses.length === 0 ? (
            <>
              Nog geen analyses aangemaakt.
              <br />
              <button
                className="btn btn-primary"
                style={{ marginTop: "1rem" }}
                onClick={onNieuw}
              >
                + Eerste analyse starten
              </button>
            </>
          ) : (
            "Geen analyses gevonden met deze filters."
          )}
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="tabel">
              <thead>
                <tr>
                  <th style={{ width: "2.5rem" }}>
                    <input
                      type="checkbox"
                      aria-label="Selecteer alle analyses op deze pagina"
                      checked={alleGeselecteerd}
                      ref={(el) => {
                        if (el)
                          el.indeterminate = enkeleGeselecteerd && !alleGeselecteerd;
                      }}
                      onChange={toggleAlles}
                    />
                  </th>
                  <th>Naam</th>
                  <th>Bron</th>
                  <th>Status</th>
                  <th>Bijgewerkt</th>
                  <th style={{ textAlign: "right" }}></th>
                </tr>
              </thead>
              <tbody>
                {gefilterd.map((a) => (
                  <tr
                    key={a.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => onBekijk(a.id)}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        aria-label={`Selecteer ${a.naam}`}
                        checked={geselecteerd.has(a.id)}
                        onChange={() => toggleEen(a.id)}
                      />
                    </td>
                    <td>
                      <span style={{ fontWeight: 500 }}>{a.naam}</span>
                      <span
                        style={{
                          display: "block",
                          fontFamily: "monospace",
                          fontSize: "0.75rem",
                          color: "rgb(var(--faint))",
                          marginTop: "0.1rem",
                        }}
                      >
                        {a.id}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: "0.8125rem", color: "rgb(var(--muted))" }}>
                        {bronnenSamenvatting(a.bronnen)}
                      </span>
                    </td>
                    <td>
                      <StatusDot status={a.status} />
                    </td>
                    <td
                      style={{
                        color: "rgb(var(--muted))",
                        fontSize: "0.8125rem",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {formatDatum(a.bijgewerkt)}
                    </td>
                    <td
                      style={{ textAlign: "right" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <span style={{ display: "inline-flex", gap: "0.375rem" }}>
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
          </div>
        </div>
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
      <div className="card" style={{ marginBottom: "1.25rem" }}>
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
        className="card"
        style={{
          marginBottom: "1.25rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.875rem",
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

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
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
          border: "1px solid rgb(var(--succes))",
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

  // Per-variant lookup — dient voor zowel rendering als disabled-state in de switcher
  const analyseVoor = {
    wachtrij: analyses.find((a) => a.status === "wachtrij"),
    lopend:   analyses.find((a) => a.status === "actief" || a.status === "review"),
    klaar:    analyses.find((a) => a.status === "klaar"),
    fout:     analyses.find((a) => a.status === "fout"),
  };

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
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      {/* Mockup-badge rechtsboven (verplicht) */}
      <div
        style={{
          position: "fixed",
          top: "1rem",
          right: "1rem",
          zIndex: 999,
          background: "rgb(var(--lint))",
          color: "white",
          borderRadius: "4px",
          padding: "0.2rem 0.625rem",
          fontSize: "0.6875rem",
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          boxShadow: "0 1px 4px rgba(0,0,0,0.2)",
        }}
      >
        Mockup — nepdata (story 012)
      </div>

      {/* Variant-switcher */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1.5rem" }}>
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
      {variant === "lijst" && (
        <AnalyseLijst
          analyses={analyses}
          onBekijk={bekijkAnalyse}
          onVerwijder={verwijderAnalyse}
          onNieuw={() => setVariant("formulier")}
        />
      )}

      {variant === "formulier" && (
        <AanmakenFormulier onNavigeer={setVariant} />
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
