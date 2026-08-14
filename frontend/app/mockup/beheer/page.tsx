"use client";

import React, { useState } from "react";
import Link from "next/link";

type BerichtType = "info" | "update" | "waarschuwing" | "kritiek";

interface Bericht {
  id: number;
  titel: string;
  inhoud: string;
  type: BerichtType;
  versie: string | null;
  gepubliceerd: boolean;
  gepubliceerd_op: string | null;
  aangemaakt_door: string;
  created: string;
}

const BERICHT_TYPES: BerichtType[] = ["info", "update", "waarschuwing", "kritiek"];
const LEEG = { titel: "", inhoud: "", type: "info" as BerichtType, versie: null as string | null };

const NEPPE_BERICHTEN: Bericht[] = [
  {
    id: 1,
    titel: "Nieuwe analysemethode beschikbaar",
    inhoud: "De verbeterde LLM-analyse is nu beschikbaar voor alle projecten. Pas de instellingen aan via het modelprofielen-scherm.",
    type: "update",
    versie: "2.4.0",
    gepubliceerd: true,
    gepubliceerd_op: "2026-08-10T10:00:00Z",
    aangemaakt_door: "beheerder",
    created: "2026-08-09T09:00:00Z",
  },
  {
    id: 2,
    titel: "Gepland onderhoud op 20 augustus",
    inhoud: "Het systeem is op 20 augustus van 02:00–04:00 niet bereikbaar wegens database-migraties.",
    type: "waarschuwing",
    versie: null,
    gepubliceerd: true,
    gepubliceerd_op: "2026-08-12T08:00:00Z",
    aangemaakt_door: "beheerder",
    created: "2026-08-12T08:00:00Z",
  },
  {
    id: 3,
    titel: "Nieuwe exportfunctie (concept)",
    inhoud: "PDF-export is in ontwikkeling en wordt volgende sprint uitgerold.",
    type: "info",
    versie: null,
    gepubliceerd: false,
    gepubliceerd_op: null,
    aangemaakt_door: "beheerder",
    created: "2026-08-13T14:00:00Z",
  },
];

let _volgendId = 4;

const NEPPE_GEBRUIKERS = [
  { id: 1, gebruikersnaam: "beheerder", rol: "beheerder", actief: true },
  { id: 2, gebruikersnaam: "analist.jan", rol: "analist", actief: true },
  { id: 3, gebruikersnaam: "analist.lisa", rol: "analist", actief: false },
];

const TYPE_META: Record<BerichtType, { label: string; kleurVar: string }> = {
  info:         { label: "Info",         kleurVar: "--info" },
  update:       { label: "Update",       kleurVar: "--succes" },
  waarschuwing: { label: "Waarschuwing", kleurVar: "--waarschuwing" },
  kritiek:      { label: "Kritiek",      kleurVar: "--fout" },
};

function TypeBadge({ type }: { type: BerichtType }) {
  const { label, kleurVar } = TYPE_META[type];
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

function SectieHeader({
  titel,
  subtitel,
  aantal,
}: {
  titel: string;
  subtitel?: string;
  aantal?: number;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        gap: "0.75rem",
        borderBottom: "1px solid rgb(var(--line))",
        paddingBottom: "0.5rem",
        marginBottom: "1.25rem",
      }}
    >
      <h2 style={{ fontSize: "1.125rem", fontWeight: 600, color: "rgb(var(--lint))" }}>
        {titel}
      </h2>
      {aantal !== undefined && (
        <span style={{ fontSize: "0.75rem", fontFamily: "monospace", color: "rgb(var(--faint))" }}>
          {aantal}
        </span>
      )}
      {subtitel && (
        <span style={{ marginLeft: "auto", fontSize: "0.75rem", color: "rgb(var(--faint))" }}>
          {subtitel}
        </span>
      )}
    </div>
  );
}

function LeegePlaceholder({ tekst }: { tekst: string }) {
  return (
    <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))", fontStyle: "italic", padding: "1.5rem 0" }}>
      {tekst}
    </p>
  );
}

// false = toon knoppen; null = nieuw bericht formulier; number = bewerk bericht id
type EditState = false | null | number;

export default function BeheerMockup() {
  const [berichten, setBerichten] = useState<Bericht[]>(NEPPE_BERICHTEN);
  const [toonLijst, setToonLijst] = useState(false);
  const [uitgeklapt, setUitgeklapt] = useState<Set<number>>(new Set());
  const [editState, setEditState] = useState<EditState>(false);
  const [formulier, setFormulier] = useState(LEEG);
  const [opgeslagen, setOpgeslagen] = useState(false);

  function toggleUitgeklapt(id: number) {
    setUitgeklapt((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function bewerkStarten(b: Bericht) {
    setFormulier({ titel: b.titel, inhoud: b.inhoud, type: b.type, versie: b.versie });
    setEditState(b.id);
  }

  function annuleren() {
    setEditState(false);
    setFormulier(LEEG);
  }

  function formulierVerzenden() {
    if (!formulier.titel || !formulier.inhoud) return;
    if (editState === null) {
      setBerichten((h) => [
        {
          id: _volgendId++,
          ...formulier,
          gepubliceerd: false,
          gepubliceerd_op: null,
          aangemaakt_door: "beheerder",
          created: new Date().toISOString(),
        },
        ...h,
      ]);
    } else if (typeof editState === "number") {
      setBerichten((h) =>
        h.map((b) => (b.id === editState ? { ...b, ...formulier } : b)),
      );
    }
    setEditState(false);
    setFormulier(LEEG);
    setToonLijst(true);
    setOpgeslagen(true);
    setTimeout(() => setOpgeslagen(false), 3000);
  }

  function publicatieWisselen(b: Bericht) {
    setBerichten((h) =>
      h.map((r) =>
        r.id === b.id
          ? { ...r, gepubliceerd: !r.gepubliceerd, gepubliceerd_op: !r.gepubliceerd ? new Date().toISOString() : null }
          : r,
      ),
    );
  }

  function berichtVerwijderen(id: number) {
    setBerichten((h) => h.filter((b) => b.id !== id));
    setUitgeklapt((prev) => { const next = new Set(prev); next.delete(id); return next; });
  }

  const formulierTitel = editState === null ? "Nieuw bericht" : "Bericht bewerken";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2.5rem" }}>
      {/* Paginaheader */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem" }}>Beheer</h1>
          <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
            Berichten, gebruikers en systeeminstellingen voor beheerders.
          </p>
        </div>
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
      </div>

      {/* ---- Sectie: Berichten ---- */}
      <section>
        <SectieHeader titel="Berichten" subtitel="Release notes en aankondigingen voor analisten." />

        {opgeslagen && (
          <div
            style={{
              marginBottom: "1rem",
              padding: "0.625rem 1rem",
              borderRadius: "4px",
              background: "rgb(var(--succes) / 0.08)",
              border: "1px solid rgb(var(--succes) / 0.3)",
              color: "rgb(var(--succes))",
              fontSize: "0.875rem",
            }}
          >
            Bericht opgeslagen.
          </div>
        )}

        {/* Formulier (nieuw of bewerken) */}
        {editState !== false && (
          <div className="card" style={{ marginBottom: "1.25rem" }}>
            <h3 style={{ marginBottom: "1rem", fontSize: "0.9375rem", fontWeight: 600 }}>
              {formulierTitel}
            </h3>
            <form
              onSubmit={(e) => { e.preventDefault(); formulierVerzenden(); }}
              style={{ display: "grid", gap: "0.75rem", maxWidth: 480 }}
            >
              <div>
                <label className="field-label" htmlFor="titel">Titel</label>
                <input
                  id="titel"
                  className="field-input"
                  value={formulier.titel}
                  onChange={(e) => setFormulier((f) => ({ ...f, titel: e.target.value }))}
                  required
                  style={{ marginTop: "0.25rem" }}
                />
              </div>
              <div>
                <label className="field-label" htmlFor="inhoud">Inhoud</label>
                <textarea
                  id="inhoud"
                  className="field-input"
                  value={formulier.inhoud}
                  onChange={(e) => setFormulier((f) => ({ ...f, inhoud: e.target.value }))}
                  required
                  rows={3}
                  style={{ marginTop: "0.25rem", resize: "vertical" }}
                />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div>
                  <label className="field-label" htmlFor="type">Type</label>
                  <select
                    id="type"
                    className="field-input"
                    value={formulier.type}
                    onChange={(e) => setFormulier((f) => ({ ...f, type: e.target.value as BerichtType }))}
                    style={{ marginTop: "0.25rem" }}
                  >
                    {BERICHT_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="field-label" htmlFor="versie">
                    Versie <span style={{ color: "rgb(var(--faint))", fontWeight: 400 }}>(opt.)</span>
                  </label>
                  <input
                    id="versie"
                    className="field-input"
                    value={formulier.versie ?? ""}
                    onChange={(e) => setFormulier((f) => ({ ...f, versie: e.target.value || null }))}
                    style={{ marginTop: "0.25rem" }}
                  />
                </div>
              </div>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.25rem" }}>
                <button type="submit" className="btn btn-primary">Opslaan</button>
                <button type="button" className="btn btn-secondary" onClick={annuleren}>
                  Annuleren
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Knoppen (altijd zichtbaar tenzij formulier open is) */}
        {editState === false && (
          <div style={{ display: "flex", gap: "0.75rem", marginBottom: toonLijst ? "1.25rem" : 0 }}>
            <button className="btn btn-primary" onClick={() => { setEditState(null); setFormulier(LEEG); }}>
              Nieuw bericht
            </button>
            {!toonLijst && (
              <button className="btn btn-secondary" onClick={() => setToonLijst(true)}>
                Toon berichten
              </button>
            )}
          </div>
        )}

        {/* Inline beheerlijst */}
        {toonLijst && editState === false && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {berichten.length === 0 && (
              <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Nog geen berichten.</p>
            )}
            {berichten.map((b) => {
              const open = uitgeklapt.has(b.id);
              const datum = new Date(b.gepubliceerd_op ?? b.created).toLocaleDateString("nl-NL", {
                day: "numeric", month: "long", year: "numeric",
              });
              return (
                <div
                  key={b.id}
                  className="card"
                  style={{ padding: 0, overflow: "hidden" }}
                >
                  <button
                    type="button"
                    onClick={() => toggleUitgeklapt(b.id)}
                    aria-expanded={open}
                    style={{
                      display: "flex",
                      width: "100%",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: "0.75rem",
                      padding: "0.75rem 1rem",
                      background: "transparent",
                      border: "none",
                      cursor: "pointer",
                      textAlign: "left",
                    }}
                  >
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                        <TypeBadge type={b.type} />
                        {b.versie && (
                          <span style={{ fontSize: "0.6875rem", fontFamily: "monospace", padding: "0.125rem 0.4rem", borderRadius: "3px", color: "rgb(var(--faint))", border: "1px solid rgb(var(--line))", background: "rgb(var(--surface))" }}>
                            {b.versie}
                          </span>
                        )}
                        <span style={{ fontSize: "0.75rem", fontWeight: 500, color: b.gepubliceerd ? "rgb(var(--succes))" : "rgb(var(--muted))" }}>
                          {b.gepubliceerd ? "Gepubliceerd" : "Concept"}
                        </span>
                        <span style={{ fontSize: "0.75rem", color: "rgb(var(--faint))" }}>{datum}</span>
                      </div>
                      <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", fontWeight: 600, color: "rgb(var(--ink))" }}>
                        {b.titel}
                      </p>
                    </div>
                    <svg
                      width="16" height="16" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                      aria-hidden="true"
                      style={{ flexShrink: 0, marginTop: "0.25rem", color: "rgb(var(--muted))", transition: "transform 0.15s", transform: open ? "rotate(180deg)" : "none" }}
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </button>

                  {open && (
                    <div style={{ borderTop: "1px solid rgb(var(--line))", padding: "0.75rem 1rem 1rem" }}>
                      <p style={{ fontSize: "0.875rem", color: "rgb(var(--ink))", marginBottom: "0.75rem" }}>
                        {b.inhoud}
                      </p>
                      <div className="acties">
                        <button className="btn btn-secondary" style={{ fontSize: "0.8125rem" }} onClick={() => bewerkStarten(b)}>
                          Bewerken
                        </button>
                        <button className="btn btn-secondary" style={{ fontSize: "0.8125rem" }} onClick={() => publicatieWisselen(b)}>
                          {b.gepubliceerd ? "Depubliceren" : "Publiceren"}
                        </button>
                        <button className="btn btn-danger" style={{ fontSize: "0.8125rem" }} onClick={() => berichtVerwijderen(b.id)}>
                          Verwijderen
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ---- Sectie: Gebruikers ---- */}
      <section>
        <SectieHeader
          titel="Gebruikers"
          aantal={NEPPE_GEBRUIKERS.length}
          subtitel={`${NEPPE_GEBRUIKERS.filter((g) => g.actief).length} actief`}
        />
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="tabel">
            <thead>
              <tr>
                <th>Gebruikersnaam</th>
                <th>Rol</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {NEPPE_GEBRUIKERS.map((g) => (
                <tr key={g.id}>
                  <td style={{ fontWeight: 500, fontFamily: "monospace", fontSize: "0.8125rem" }}>
                    {g.gebruikersnaam}
                  </td>
                  <td style={{ color: "rgb(var(--muted))" }}>{g.rol}</td>
                  <td>
                    <span className={`badge ${g.actief ? "badge-gepubliceerd" : "badge-concept"}`}>
                      {g.actief ? "actief" : "inactief"}
                    </span>
                  </td>
                  <td>
                    <div className="acties">
                      <button className="btn btn-secondary" disabled style={{ opacity: 0.4 }}>
                        Wachtwoord resetten
                      </button>
                      <button className="btn btn-secondary" disabled style={{ opacity: 0.4 }}>
                        {g.actief ? "Deactiveren" : "Activeren"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ marginTop: "1rem" }}>
          <button className="btn btn-secondary" disabled style={{ opacity: 0.4 }}>
            + Nieuwe gebruiker
          </button>
        </div>
      </section>

      {/* ---- Sectie: Gebruikersfeedback ---- */}
      <section>
        <SectieHeader titel="Gebruikersfeedback" subtitel="nog niet gebouwd" />
        <LeegePlaceholder tekst="Ingezonden feedback van analisten verschijnt hier." />
      </section>

      {/* ---- Sectie: Instellingen ---- */}
      <section>
        <SectieHeader titel="Instellingen" subtitel="nog niet gebouwd" />
        <LeegePlaceholder tekst="Systeeminstellingen en configuratie verschijnen hier." />
      </section>
    </div>
  );
}
