"use client";

import React, { useState } from "react";
import {
  SectieHeader,
  LeegePlaceholder,
} from "@/components/beheer/SectieHeader";

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

function FoutMelding({
  bericht,
  onSluit,
}: {
  bericht: string;
  onSluit: () => void;
}) {
  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0.75rem 1rem",
        borderRadius: "4px",
        background: "rgb(var(--fout) / 0.08)",
        border: "1px solid rgb(var(--fout) / 0.3)",
        color: "rgb(var(--fout))",
        fontSize: "0.875rem",
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

function SuccesMelding({ bericht }: { bericht: string }) {
  return (
    <div
      style={{
        padding: "0.75rem 1rem",
        borderRadius: "4px",
        background: "rgb(var(--succes) / 0.08)",
        border: "1px solid rgb(var(--succes) / 0.3)",
        color: "rgb(var(--succes))",
        fontSize: "0.875rem",
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
        setStatus({
          fase: "fout",
          bericht: "Wet niet gevonden in de Wettenbank.",
        });
      } else if (bwb_id === "BWBR0000000") {
        setStatus({
          fase: "fout",
          bericht: "Wettenbank tijdelijk niet bereikbaar.",
        });
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
      style={{
        padding: "1rem",
        borderRadius: "4px",
        border: "1px solid rgb(var(--line))",
        background: "rgb(var(--surface))",
      }}
    >
      <p
        style={{
          fontSize: "0.8125rem",
          color: "rgb(var(--muted))",
          marginBottom: "0.75rem",
        }}
      >
        Haal de officiële citeertitel op voor{" "}
        <span
          style={{
            fontFamily: "monospace",
            fontWeight: 600,
            color: "rgb(var(--ink))",
          }}
        >
          {bwb_id}
        </span>{" "}
        via de Wettenbank-MCP.
        {huidigenaam && (
          <>
            {" "}
            Huidige naam:{" "}
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
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Resolving…
        </p>
      )}

      {status.fase === "fout" && (
        <div
          style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
        >
          <p
            style={{
              fontSize: "0.875rem",
              color: "rgb(var(--fout))",
              padding: "0.5rem 0.75rem",
              borderRadius: "4px",
              background: "rgb(var(--fout) / 0.08)",
              border: "1px solid rgb(var(--fout) / 0.3)",
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
        <div
          style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
        >
          <div
            style={{
              padding: "0.625rem 0.875rem",
              borderRadius: "4px",
              background: "rgb(var(--succes) / 0.08)",
              border: "1px solid rgb(var(--succes) / 0.3)",
            }}
          >
            <p
              style={{
                fontSize: "0.75rem",
                color: "rgb(var(--succes))",
                marginBottom: "0.25rem",
              }}
            >
              Citeertitel gevonden
            </p>
            <p
              style={{
                fontSize: "0.9375rem",
                fontWeight: 600,
                color: "rgb(var(--ink))",
              }}
            >
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

// --- Wet-formulier (toevoegen én bewerken) ---------------------------------
// Visueel identiek aan WetEditor in wetsanalyse-ai/frontend/components/admin/WetEditor.tsx

function WetFormulier({
  wet,
  bestaandeBwbIds,
  onOpslaan,
  onAnnuleren,
}: {
  wet: WetRead | null; // null = nieuw
  bestaandeBwbIds: string[];
  onOpslaan: (bwb_id: string, naam: string) => void;
  onAnnuleren: () => void;
}) {
  const nieuw = wet === null;
  const [bwb_id, setBwbId] = useState(wet?.bwb_id ?? "");
  const [naam, setNaam] = useState(wet?.naam ?? "");
  const [fout, setFout] = useState<Foutmelding>(null);
  const [resolveOpen, setResolveOpen] = useState(false);

  function verzenden(e: React.FormEvent) {
    e.preventDefault();
    setFout(null);
    const id = nieuw ? bwb_id.trim().toUpperCase() : bwb_id.trim();
    const n = naam.trim();
    if (!id || !n) return;
    if (nieuw && bestaandeBwbIds.includes(id)) {
      setFout(
        `Conflict (409): wet met bwb-id "${id}" bestaat al in de catalogus.`,
      );
      return;
    }
    onOpslaan(id, n);
  }

  return (
    <div
      style={{
        background: "rgb(var(--paper))",
        border: "1px solid rgb(var(--line))",
        borderRadius: "5px",
        padding: "1.5rem",
      }}
    >
      <form
        onSubmit={verzenden}
        style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}
      >
        <h3
          style={{
            fontSize: "1.125rem",
            fontWeight: 600,
            color: "rgb(var(--lint))",
          }}
        >
          {nieuw ? "Nieuwe wet" : `Wet bewerken — ${wet?.bwb_id}`}
        </h3>

        {fout && <FoutMelding bericht={fout} onSluit={() => setFout(null)} />}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "1.25rem",
          }}
        >
          {/* BWB-ID veld */}
          <div>
            <label
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: "0.375rem",
                marginBottom: "0.25rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "rgb(var(--ink))",
              }}
              htmlFor="bwb-id"
            >
              BWB-ID
              <span
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 400,
                  color: "rgb(var(--faint))",
                }}
              >
                {nieuw ? "bv. BWBR0005290" : "vast"}
              </span>
            </label>
            <input
              id="bwb-id"
              className="field-input"
              style={{ fontFamily: "monospace" }}
              placeholder="BWBR0005290"
              value={bwb_id}
              onChange={(e) => setBwbId(e.target.value)}
              disabled={!nieuw}
              required
              autoComplete="off"
            />
          </div>

          {/* Naam veld */}
          <div>
            <label
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: "0.375rem",
                marginBottom: "0.25rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "rgb(var(--ink))",
              }}
              htmlFor="wet-naam"
            >
              Naam
              <span
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 400,
                  color: "rgb(var(--faint))",
                }}
              >
                leesbaar label
              </span>
            </label>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
              }}
              className="sm:flex-row"
            >
              <input
                id="wet-naam"
                className="field-input"
                style={{ flex: 1 }}
                placeholder="Algemene wet bestuursrecht"
                value={naam}
                onChange={(e) => setNaam(e.target.value)}
                required
                maxLength={256}
                autoComplete="off"
              />
              <button
                type="button"
                className="btn btn-secondary"
                style={{ whiteSpace: "nowrap" }}
                onClick={() => setResolveOpen((v) => !v)}
                title="Citeertitel ophalen via Wettenbank-MCP"
              >
                Naam ophalen
              </button>
            </div>
          </div>
        </div>

        {resolveOpen && (
          <ResolvePaneel
            bwb_id={bwb_id || (wet?.bwb_id ?? "")}
            huidigenaam={naam}
            onNaamToepassen={(n) => {
              setNaam(n);
              setResolveOpen(false);
            }}
            onSluiten={() => setResolveOpen(false)}
          />
        )}

        <div style={{ display: "flex", gap: "0.5rem", paddingTop: "0.5rem" }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onAnnuleren}
          >
            Annuleren
          </button>
          <button type="submit" className="btn btn-primary">
            {nieuw ? "Toevoegen" : "Opslaan"}
          </button>
        </div>
      </form>
    </div>
  );
}

// --- Wettenlijst (cards per wet) -------------------------------------------
// Visueel identiek aan de "Wetten"-sectie in wetsanalyse-ai BeheerClient.tsx

function WettenLijst({
  wetten,
  onBewerken,
  onVerwijderen,
}: {
  wetten: WetRead[];
  onBewerken: (bwb_id: string) => void;
  onVerwijderen: (wet: WetRead) => void;
}) {
  if (wetten.length === 0) {
    return (
      <LeegePlaceholder tekst="Nog geen wetten. Voeg er een toe om de dropdown te vullen." />
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {wetten.map((wet) => (
        <div
          key={wet.bwb_id}
          style={{
            background: "rgb(var(--surface))",
            border: "1px solid rgb(var(--line))",
            borderRadius: "5px",
            padding: "1rem",
          }}
        >
          {/* Naam + BWB-badge + metadata */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "0.75rem",
            }}
          >
            <span
              style={{
                fontWeight: 600,
                color: "rgb(var(--ink))",
              }}
            >
              {wet.naam || "(geen naam)"}
            </span>
            {/* BWB-id badge — gelijk aan Tag in wetsanalyse-ai */}
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "0.125rem 0.5rem",
                borderRadius: "9999px",
                border: "1px solid rgb(var(--line))",
                background: "rgb(var(--paper))",
                fontFamily: "monospace",
                fontSize: "0.75rem",
                color: "rgb(var(--muted))",
              }}
            >
              {wet.bwb_id}
            </span>
            <span
              style={{
                marginLeft: "auto",
                fontSize: "0.75rem",
                color: "rgb(var(--faint))",
              }}
            >
              {wet.artikelen} artikelen · {wet.bijgewerkt_door}
            </span>
          </div>

          {/* Actieknopen */}
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
            <button
              className="btn btn-secondary"
              style={{ fontSize: "0.8125rem" }}
              onClick={() => onBewerken(wet.bwb_id)}
            >
              Bewerken
            </button>
            <button
              className="btn btn-danger"
              style={{ fontSize: "0.8125rem" }}
              onClick={() => onVerwijderen(wet)}
            >
              Verwijderen
            </button>
          </div>
        </div>
      ))}
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
      <div
        style={{
          background: "rgb(var(--paper))",
          border: "1px solid rgb(var(--line))",
          borderRadius: "5px",
          padding: "1.5rem",
          maxWidth: 420,
          width: "90%",
          boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
        }}
      >
        <h3
          style={{
            fontSize: "1rem",
            fontWeight: 600,
            color: "rgb(var(--lint))",
            marginBottom: "0.75rem",
          }}
        >
          Wet verwijderen?
        </h3>
        <p
          style={{
            fontSize: "0.875rem",
            color: "rgb(var(--muted))",
            marginBottom: "1.25rem",
          }}
        >
          Weet je zeker dat je{" "}
          <strong style={{ color: "rgb(var(--ink))" }}>{wet.naam}</strong> (
          <span style={{ fontFamily: "monospace" }}>{wet.bwb_id}</span>) wilt
          verwijderen uit de catalogus? Bestaande analyses worden niet geraakt.
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

// --- Scenario-knoppen (mockup-only) ----------------------------------------

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

  function wetToevoegen(bwb_id: string, naam: string) {
    const wet: WetRead = {
      bwb_id,
      naam,
      bijgewerkt_door: "beheerder",
      bijgewerkt: new Date().toISOString(),
      artikelen: 0,
    };
    setWetten((prev) => [...prev, wet]);
    setToonToevoegen(false);
    toonSucces(`Wet "${naam}" (${bwb_id}) toegevoegd.`);
  }

  function wetOpslaan(bwb_id: string, naam: string) {
    setWetten((prev) =>
      prev.map((w) =>
        w.bwb_id === bwb_id
          ? {
              ...w,
              naam,
              bijgewerkt_door: "beheerder",
              bijgewerkt: new Date().toISOString(),
            }
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
        toonSucces(
          "Klik op 'Naam ophalen' in het bewerkformulier om het resolve-paneel te openen.",
        );
        break;
    }
  }

  const bewerkWet = bewerkId
    ? (wetten.find((w) => w.bwb_id === bewerkId) ?? null)
    : null;
  const formulierOpen = toonToevoegen || bewerkId !== null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Paginaheader */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
        <div>
          <h1 style={{ fontSize: "1.875rem", fontWeight: 600 }}>
            Wettenbank-beheer
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgb(var(--muted))",
            }}
          >
            Wetten toevoegen, bijwerken, resolven en verwijderen uit de
            catalogus.
          </p>
        </div>
        <MockupBadge />
      </div>

      {/* Scenario-knoppen */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "0.5rem",
          padding: "0.75rem 1rem",
          background: "rgb(var(--surface))",
          border: "1px solid rgb(var(--line))",
          borderRadius: "5px",
        }}
      >
        <span
          style={{
            fontSize: "0.6875rem",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "rgb(var(--faint))",
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
      {succesmelding && <SuccesMelding bericht={succesmelding} />}
      {foutmelding && (
        <FoutMelding
          bericht={foutmelding}
          onSluit={() => setFoutmelding(null)}
        />
      )}

      {/* Wetten-sectie */}
      <section>
        <SectieHeader
          titel="Wetten"
          aantal={wetten.length}
          subtitel="Selecteerbaar bij nieuwe analyse"
        />

        {formulierOpen ? (
          /* Formulier (toevoegen of bewerken) vervangt de lijst — zelfde patroon als WetEditor */
          <WetFormulier
            wet={toonToevoegen ? null : bewerkWet}
            bestaandeBwbIds={wetten.map((w) => w.bwb_id)}
            onOpslaan={toonToevoegen ? wetToevoegen : wetOpslaan}
            onAnnuleren={() => {
              setToonToevoegen(false);
              setBewerkId(null);
            }}
          />
        ) : (
          <>
            <div style={{ marginBottom: "1rem" }}>
              <button
                className="btn btn-primary"
                onClick={() => {
                  setBewerkId(null);
                  setToonToevoegen(true);
                }}
              >
                Nieuwe wet
              </button>
            </div>
            <WettenLijst
              wetten={wetten}
              onBewerken={(id) => {
                setToonToevoegen(false);
                setBewerkId(id);
              }}
              onVerwijderen={(wet) => setTeVerwijderen(wet)}
            />
          </>
        )}
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
