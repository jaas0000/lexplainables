"use client";

import React, { useState } from "react";

// --- Types -----------------------------------------------------------------

interface WetRead {
  bwb_id: string;
  naam: string;
  bijgewerkt_door: string;
  bijgewerkt: string;
  artikelen: number; // mockup: nepgetal
}

type ResolveStatus =
  | { fase: "idle" }
  | { fase: "bezig" }
  | { fase: "resultaat"; naam: string }
  | { fase: "fout"; bericht: string };

type Foutmelding = string | null;

// --- Nepdata ---------------------------------------------------------------

const NEPPE_WETTEN: WetRead[] = [
  {
    bwb_id: "BWBR0005290",
    naam: "Algemene wet bestuursrecht",
    bijgewerkt_door: "beheerder",
    bijgewerkt: "2026-08-01T09:00:00Z",
    artikelen: 184,
  },
  {
    bwb_id: "BWBR0011823",
    naam: "Wet open overheid",
    bijgewerkt_door: "beheerder",
    bijgewerkt: "2026-08-10T14:30:00Z",
    artikelen: 47,
  },
];

const LEEG_FORMULIER = { bwb_id: "", naam: "" };

// --- Hulpcomponenten -------------------------------------------------------

function MockupBadge() {
  return (
    <span
      style={{
        fontSize: "0.75rem",
        padding: "0.125rem 0.625rem",
        background: "rgb(var(--waarschuwing) / 0.1)",
        color: "rgb(var(--waarschuwing))",
        border: "1px solid rgb(var(--waarschuwing) / 0.3)",
        borderRadius: "9999px",
        flexShrink: 0,
        marginTop: "0.25rem",
      }}
    >
      mockup — nepdata
    </span>
  );
}

function FoutBalk({ bericht, onSluit }: { bericht: string; onSluit: () => void }) {
  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0.625rem 1rem",
        borderRadius: "4px",
        background: "rgb(var(--gevaar) / 0.08)",
        border: "1px solid rgb(var(--gevaar) / 0.3)",
        color: "rgb(var(--gevaar))",
        fontSize: "0.875rem",
        marginBottom: "1rem",
      }}
    >
      <span>{bericht}</span>
      <button
        type="button"
        onClick={onSluit}
        aria-label="Sluit foutmelding"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "inherit",
          fontSize: "1rem",
          lineHeight: 1,
        }}
      >
        ×
      </button>
    </div>
  );
}

function SuccesBalk({ bericht }: { bericht: string }) {
  return (
    <div
      style={{
        padding: "0.625rem 1rem",
        borderRadius: "4px",
        background: "rgb(var(--succes) / 0.08)",
        border: "1px solid rgb(var(--succes) / 0.3)",
        color: "rgb(var(--succes))",
        fontSize: "0.875rem",
        marginBottom: "1rem",
      }}
    >
      {bericht}
    </div>
  );
}

// --- Resolve-paneel --------------------------------------------------------

function ResolvePaneel({
  bwb_id,
  huidigenaam,
  onNaamToepassen,
  onSluiten,
}: {
  bwb_id: string;
  huidigenaam: string;
  onNaamToepassen: (naam: string) => void;
  onSluiten: () => void;
}) {
  const [status, setStatus] = useState<ResolveStatus>({ fase: "idle" });

  function startResolve() {
    setStatus({ fase: "bezig" });
    // Simuleer een asynchrone MCP-aanroep (mockup)
    setTimeout(() => {
      if (bwb_id === "BWBR0099999") {
        setStatus({ fase: "fout", bericht: "Wet niet gevonden in de Wettenbank." });
      } else if (bwb_id === "BWBR0000000") {
        setStatus({ fase: "fout", bericht: "Wettenbank tijdelijk niet bereikbaar." });
      } else {
        const resolvedNaam =
          bwb_id === "BWBR0005290"
            ? "Algemene wet bestuursrecht"
            : bwb_id === "BWBR0011823"
              ? "Wet open overheid"
              : `Wet (citeertitel voor ${bwb_id})`;
        setStatus({ fase: "resultaat", naam: resolvedNaam });
      }
    }, 1200);
  }

  return (
    <div
      className="card"
      style={{ marginTop: "0.5rem", padding: "1rem", background: "rgb(var(--surface))" }}
    >
      <p style={{ fontSize: "0.8125rem", color: "rgb(var(--muted))", marginBottom: "0.75rem" }}>
        Haal de officiële citeertitel op voor{" "}
        <span style={{ fontFamily: "monospace", fontWeight: 600, color: "rgb(var(--ink))" }}>
          {bwb_id}
        </span>{" "}
        via de Wettenbank-MCP.
        {huidigenaam && (
          <>
            {" "}Huidige naam:{" "}
            <em style={{ color: "rgb(var(--ink))" }}>{huidigenaam}</em>.
          </>
        )}
      </p>

      {status.fase === "idle" && (
        <button
          className="btn btn-secondary"
          style={{ fontSize: "0.8125rem" }}
          onClick={startResolve}
        >
          Resolve starten
        </button>
      )}

      {status.fase === "bezig" && (
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Resolving…</p>
      )}

      {status.fase === "fout" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <p
            style={{
              fontSize: "0.875rem",
              color: "rgb(var(--gevaar))",
              padding: "0.5rem 0.75rem",
              borderRadius: "4px",
              background: "rgb(var(--gevaar) / 0.08)",
              border: "1px solid rgb(var(--gevaar) / 0.3)",
            }}
          >
            {status.bericht}
          </p>
          <button
            className="btn btn-secondary"
            style={{ fontSize: "0.8125rem" }}
            onClick={startResolve}
          >
            Opnieuw proberen
          </button>
        </div>
      )}

      {status.fase === "resultaat" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <div
            style={{
              padding: "0.625rem 0.875rem",
              borderRadius: "4px",
              background: "rgb(var(--succes) / 0.08)",
              border: "1px solid rgb(var(--succes) / 0.3)",
            }}
          >
            <p
              style={{ fontSize: "0.75rem", color: "rgb(var(--succes))", marginBottom: "0.25rem" }}
            >
              Citeertitel gevonden
            </p>
            <p style={{ fontSize: "0.9375rem", fontWeight: 600, color: "rgb(var(--ink))" }}>
              {status.naam}
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              className="btn btn-primary"
              style={{ fontSize: "0.8125rem" }}
              onClick={() => onNaamToepassen(status.naam)}
            >
              Naam overnemen
            </button>
            <button
              className="btn btn-secondary"
              style={{ fontSize: "0.8125rem" }}
              onClick={startResolve}
            >
              Opnieuw resolven
            </button>
          </div>
        </div>
      )}

      <div style={{ marginTop: "0.75rem" }}>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ fontSize: "0.8125rem" }}
          onClick={onSluiten}
        >
          Sluiten
        </button>
      </div>
    </div>
  );
}

// --- Inline bewerken -------------------------------------------------------

function BewerkRij({
  wet,
  onOpslaan,
  onAnnuleren,
}: {
  wet: WetRead;
  onOpslaan: (bwb_id: string, naam: string) => void;
  onAnnuleren: () => void;
}) {
  const [naam, setNaam] = useState(wet.naam);
  const [resolveOpen, setResolveOpen] = useState(false);

  function resolveNaamToepassen(gevondenNaam: string) {
    setNaam(gevondenNaam);
    setResolveOpen(false);
  }

  return (
    <tr style={{ background: "rgb(var(--surface))" }}>
      <td style={{ fontFamily: "monospace", fontSize: "0.8125rem", color: "rgb(var(--muted))" }}>
        {wet.bwb_id}
      </td>
      <td colSpan={2}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (naam.trim()) onOpslaan(wet.bwb_id, naam.trim());
          }}
          style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
        >
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <input
              className="field-input"
              value={naam}
              onChange={(e) => setNaam(e.target.value)}
              required
              aria-label="Naam wet"
              style={{ flex: 1 }}
            />
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: "0.8125rem", flexShrink: 0 }}
              onClick={() => setResolveOpen((v) => !v)}
              title="Citeertitel ophalen via Wettenbank-MCP"
            >
              Resolve
            </button>
          </div>
          {resolveOpen && (
            <ResolvePaneel
              bwb_id={wet.bwb_id}
              huidigenaam={naam}
              onNaamToepassen={resolveNaamToepassen}
              onSluiten={() => setResolveOpen(false)}
            />
          )}
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button type="submit" className="btn btn-primary" style={{ fontSize: "0.8125rem" }}>
              Opslaan
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: "0.8125rem" }}
              onClick={onAnnuleren}
            >
              Annuleren
            </button>
          </div>
        </form>
      </td>
      <td style={{ textAlign: "center", color: "rgb(var(--muted))", fontSize: "0.8125rem" }}>
        {wet.artikelen}
      </td>
      <td></td>
    </tr>
  );
}

// --- Toevoeg-formulier -----------------------------------------------------

function ToevoegFormulier({
  bestaandeBwbIds,
  onToevoegen,
  onAnnuleren,
}: {
  bestaandeBwbIds: string[];
  onToevoegen: (wet: { bwb_id: string; naam: string }) => void;
  onAnnuleren: () => void;
}) {
  const [formulier, setFormulier] = useState(LEEG_FORMULIER);
  const [fout, setFout] = useState<Foutmelding>(null);

  function verzenden(e: React.FormEvent) {
    e.preventDefault();
    setFout(null);
    const bwb_id = formulier.bwb_id.trim().toUpperCase();
    const naam = formulier.naam.trim();
    if (!bwb_id || !naam) return;
    if (bestaandeBwbIds.includes(bwb_id)) {
      setFout(`Conflict (409): wet met bwb-id "${bwb_id}" bestaat al in de catalogus.`);
      return;
    }
    onToevoegen({ bwb_id, naam });
    setFormulier(LEEG_FORMULIER);
  }

  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <h3 style={{ fontSize: "0.9375rem", fontWeight: 600, marginBottom: "0.875rem" }}>
        Wet toevoegen
      </h3>
      {fout && <FoutBalk bericht={fout} onSluit={() => setFout(null)} />}
      <form onSubmit={verzenden} style={{ display: "grid", gap: "0.75rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "0.75rem" }}>
          <div>
            <label className="field-label" htmlFor="bwb-id">
              BWB-ID
            </label>
            <input
              id="bwb-id"
              className="field-input"
              placeholder="bijv. BWBR0005290"
              value={formulier.bwb_id}
              onChange={(e) => setFormulier((f) => ({ ...f, bwb_id: e.target.value }))}
              required
              style={{ marginTop: "0.25rem", fontFamily: "monospace" }}
            />
          </div>
          <div>
            <label className="field-label" htmlFor="wet-naam">
              Naam
            </label>
            <input
              id="wet-naam"
              className="field-input"
              placeholder="bijv. Algemene wet bestuursrecht"
              value={formulier.naam}
              onChange={(e) => setFormulier((f) => ({ ...f, naam: e.target.value }))}
              required
              maxLength={256}
              style={{ marginTop: "0.25rem" }}
            />
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button type="submit" className="btn btn-primary">
            Toevoegen
          </button>
          <button type="button" className="btn btn-secondary" onClick={onAnnuleren}>
            Annuleren
          </button>
        </div>
      </form>
    </div>
  );
}

// --- Bevestigingsdialoog verwijderen ---------------------------------------

function BevestigVerwijderen({
  wet,
  onBevestigen,
  onAnnuleren,
}: {
  wet: WetRead;
  onBevestigen: () => void;
  onAnnuleren: () => void;
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0 0 0 / 0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
      }}
    >
      <div className="card" style={{ maxWidth: 420, width: "90%", padding: "1.5rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
          Wet verwijderen?
        </h3>
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))", marginBottom: "1.25rem" }}>
          Weet je zeker dat je{" "}
          <strong style={{ color: "rgb(var(--ink))" }}>{wet.naam}</strong> (
          <span style={{ fontFamily: "monospace" }}>{wet.bwb_id}</span>) wilt verwijderen uit de
          catalogus? Bestaande analyses worden niet geraakt.
        </p>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-danger" onClick={onBevestigen}>
            Verwijderen
          </button>
          <button className="btn btn-secondary" onClick={onAnnuleren}>
            Annuleren
          </button>
        </div>
      </div>
    </div>
  );
}

// --- Wettenlijst-tabel -----------------------------------------------------

function WettenTabel({
  wetten,
  onBewerken,
  onVerwijderen,
  bewerkId,
  onOpslaan,
  onAnnuleren,
}: {
  wetten: WetRead[];
  onBewerken: (bwb_id: string) => void;
  onVerwijderen: (wet: WetRead) => void;
  bewerkId: string | null;
  onOpslaan: (bwb_id: string, naam: string) => void;
  onAnnuleren: () => void;
}) {
  if (wetten.length === 0) {
    return (
      <div
        style={{
          padding: "2rem 1.5rem",
          textAlign: "center",
          border: "1px dashed rgb(var(--line))",
          borderRadius: "6px",
          color: "rgb(var(--muted))",
          fontSize: "0.875rem",
        }}
      >
        Nog geen wetten in de catalogus. Voeg een wet toe via het formulier hierboven.
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <table className="tabel">
        <thead>
          <tr>
            <th style={{ width: "14ch" }}>BWB-ID</th>
            <th>Naam</th>
            <th style={{ width: "12ch" }}>Bijgewerkt door</th>
            <th style={{ width: "6ch", textAlign: "center" }}>Artikelen</th>
            <th style={{ width: "14ch" }}>Acties</th>
          </tr>
        </thead>
        <tbody>
          {wetten.map((wet) =>
            wet.bwb_id === bewerkId ? (
              <BewerkRij
                key={wet.bwb_id}
                wet={wet}
                onOpslaan={onOpslaan}
                onAnnuleren={onAnnuleren}
              />
            ) : (
              <tr key={wet.bwb_id}>
                <td style={{ fontFamily: "monospace", fontSize: "0.8125rem" }}>{wet.bwb_id}</td>
                <td style={{ fontWeight: 500 }}>{wet.naam}</td>
                <td style={{ color: "rgb(var(--muted))", fontSize: "0.8125rem" }}>
                  {wet.bijgewerkt_door}
                </td>
                <td style={{ textAlign: "center", color: "rgb(var(--muted))", fontSize: "0.8125rem" }}>
                  {wet.artikelen}
                </td>
                <td>
                  <div className="acties">
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: "0.8125rem" }}
                      onClick={() => onBewerken(wet.bwb_id)}
                    >
                      Bewerk
                    </button>
                    <button
                      className="btn btn-danger"
                      style={{ fontSize: "0.8125rem" }}
                      onClick={() => onVerwijderen(wet)}
                    >
                      Verwijder
                    </button>
                  </div>
                </td>
              </tr>
            ),
          )}
        </tbody>
      </table>
    </div>
  );
}

// --- Scenario-knoppen (voor snel schakelen) --------------------------------

type Scenario = "leeg" | "gevuld" | "toevoegen" | "bewerken" | "resolve";

// --- Hoofd-component -------------------------------------------------------

export default function WettenbankBeheerMockup() {
  const [wetten, setWetten] = useState<WetRead[]>(NEPPE_WETTEN);
  const [toonToevoegen, setToonToevoegen] = useState(false);
  const [bewerkId, setBewerkId] = useState<string | null>(null);
  const [teVerwijderen, setTeVerwijderen] = useState<WetRead | null>(null);
  const [succesmelding, setSuccesmelding] = useState<string | null>(null);
  const [foutmelding, setFoutmelding] = useState<Foutmelding>(null);

  function toonSucces(tekst: string) {
    setSuccesmelding(tekst);
    setTimeout(() => setSuccesmelding(null), 3000);
  }

  function wetToevoegen(nieuw: { bwb_id: string; naam: string }) {
    const wet: WetRead = {
      ...nieuw,
      bijgewerkt_door: "beheerder",
      bijgewerkt: new Date().toISOString(),
      artikelen: 0,
    };
    setWetten((prev) => [...prev, wet]);
    setToonToevoegen(false);
    toonSucces(`Wet "${nieuw.naam}" (${nieuw.bwb_id}) toegevoegd.`);
  }

  function wetOpslaan(bwb_id: string, naam: string) {
    setWetten((prev) =>
      prev.map((w) =>
        w.bwb_id === bwb_id
          ? { ...w, naam, bijgewerkt_door: "beheerder", bijgewerkt: new Date().toISOString() }
          : w,
      ),
    );
    setBewerkId(null);
    toonSucces(`Wet "${naam}" bijgewerkt.`);
  }

  function wetVerwijderenBevestigen() {
    if (!teVerwijderen) return;
    setWetten((prev) => prev.filter((w) => w.bwb_id !== teVerwijderen.bwb_id));
    toonSucces(`Wet "${teVerwijderen.naam}" verwijderd.`);
    setTeVerwijderen(null);
  }

  function laadScenario(s: Scenario) {
    setFoutmelding(null);
    setSuccesmelding(null);
    setBewerkId(null);
    setTeVerwijderen(null);
    setToonToevoegen(false);
    switch (s) {
      case "leeg":
        setWetten([]);
        break;
      case "gevuld":
        setWetten(NEPPE_WETTEN);
        break;
      case "toevoegen":
        setWetten(NEPPE_WETTEN);
        setToonToevoegen(true);
        break;
      case "bewerken":
        setWetten(NEPPE_WETTEN);
        setBewerkId("BWBR0011823");
        break;
      case "resolve":
        setWetten(NEPPE_WETTEN);
        setBewerkId("BWBR0005290");
        toonSucces("Klik op 'Resolve' in de bewerkrij om het resolve-paneel te openen.");
        break;
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Paginaheader */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem" }}>Wettenbank-beheer</h1>
          <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
            Wetten toevoegen, bijwerken, resolven en verwijderen uit de catalogus.
          </p>
        </div>
        <MockupBadge />
      </div>

      {/* Scenario-knoppen */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "0.5rem",
          padding: "0.75rem 1rem",
          background: "rgb(var(--surface))",
          border: "1px solid rgb(var(--line))",
          borderRadius: "6px",
        }}
      >
        <span
          style={{
            fontSize: "0.6875rem",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "rgb(var(--faint))",
            alignSelf: "center",
            marginRight: "0.25rem",
          }}
        >
          Variant
        </span>
        {(
          [
            ["leeg", "Lege catalogus"],
            ["gevuld", "Lijst met wetten"],
            ["toevoegen", "Toevoegen-formulier"],
            ["bewerken", "Inline bewerken"],
            ["resolve", "Resolve-paneel"],
          ] as [Scenario, string][]
        ).map(([s, label]) => (
          <button
            key={s}
            type="button"
            className="btn btn-secondary"
            style={{ fontSize: "0.75rem" }}
            onClick={() => laadScenario(s)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Feedback-balken */}
      {succesmelding && <SuccesBalk bericht={succesmelding} />}
      {foutmelding && <FoutBalk bericht={foutmelding} onSluit={() => setFoutmelding(null)} />}

      {/* Wet toevoegen */}
      {toonToevoegen ? (
        <ToevoegFormulier
          bestaandeBwbIds={wetten.map((w) => w.bwb_id)}
          onToevoegen={wetToevoegen}
          onAnnuleren={() => setToonToevoegen(false)}
        />
      ) : (
        <div>
          <button
            className="btn btn-primary"
            onClick={() => {
              setBewerkId(null);
              setToonToevoegen(true);
            }}
          >
            + Wet toevoegen
          </button>
        </div>
      )}

      {/* Cataloguslijst */}
      <section>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            marginBottom: "0.875rem",
          }}
        >
          <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>Catalogus</h2>
          <span
            style={{
              fontSize: "0.6875rem",
              fontWeight: 600,
              padding: "0.125rem 0.5rem",
              borderRadius: "9999px",
              background: "rgb(var(--lint) / 0.1)",
              color: "rgb(var(--lint))",
              border: "1px solid rgb(var(--lint) / 0.25)",
            }}
          >
            {wetten.length} {wetten.length === 1 ? "wet" : "wetten"}
          </span>
        </div>

        <WettenTabel
          wetten={wetten}
          bewerkId={bewerkId}
          onBewerken={(id) => {
            setToonToevoegen(false);
            setBewerkId(id);
          }}
          onVerwijderen={(wet) => setTeVerwijderen(wet)}
          onOpslaan={wetOpslaan}
          onAnnuleren={() => setBewerkId(null)}
        />
      </section>

      {/* Bevestigingsdialoog */}
      {teVerwijderen && (
        <BevestigVerwijderen
          wet={teVerwijderen}
          onBevestigen={wetVerwijderenBevestigen}
          onAnnuleren={() => setTeVerwijderen(null)}
        />
      )}
    </div>
  );
}
