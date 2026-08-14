"use client";

import React, { useCallback, useState } from "react";
import type { components } from "@/generated/types";

type BerichtAdminRead = components["schemas"]["BerichtAdminRead"];
type BerichtCreate = components["schemas"]["BerichtCreate"];
type BerichtType = BerichtCreate["type"];

const BERICHT_TYPES: BerichtType[] = ["info", "update", "waarschuwing", "kritiek"];
const LEEG = { titel: "", inhoud: "", type: "info" as BerichtType, versie: null as string | null };

const TYPE_META: Record<BerichtType, { label: string; kleurVar: string }> = {
  info:         { label: "Info",         kleurVar: "--info" },
  update:       { label: "Update",       kleurVar: "--succes" },
  waarschuwing: { label: "Waarschuwing", kleurVar: "--waarschuwing" },
  kritiek:      { label: "Kritiek",      kleurVar: "--fout" },
};

async function beheerFetch(pad: string, init: RequestInit = {}) {
  const res = await fetch(pad, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (res.status === 401) { window.location.href = "/login"; throw new Error("Niet geautoriseerd."); }
  if (!res.ok) {
    const detail = await res.json().then((d: { detail?: string }) => d.detail).catch(() => null);
    throw new Error(detail ?? `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined;
  return res.json();
}

function TypeBadge({ type }: { type: BerichtType }) {
  const { label, kleurVar } = TYPE_META[type];
  return (
    <span style={{ fontSize: "0.6875rem", fontWeight: 600, padding: "0.125rem 0.4rem", borderRadius: "3px", color: `rgb(var(${kleurVar}))`, border: `1px solid rgb(var(${kleurVar}) / 0.4)`, background: `rgb(var(${kleurVar}) / 0.08)` }}>
      {label}
    </span>
  );
}

function SectieHeader({ titel, subtitel, aantal }: { titel: string; subtitel?: string; aantal?: number }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem", borderBottom: "1px solid rgb(var(--line))", paddingBottom: "0.5rem", marginBottom: "1.25rem" }}>
      <h2 style={{ fontSize: "1.125rem", fontWeight: 600, color: "rgb(var(--lint))" }}>{titel}</h2>
      {aantal !== undefined && <span style={{ fontSize: "0.75rem", fontFamily: "monospace", color: "rgb(var(--faint))" }}>{aantal}</span>}
      {subtitel && <span style={{ marginLeft: "auto", fontSize: "0.75rem", color: "rgb(var(--faint))" }}>{subtitel}</span>}
    </div>
  );
}

function LeegePlaceholder({ tekst }: { tekst: string }) {
  return <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))", fontStyle: "italic", padding: "1.5rem 0" }}>{tekst}</p>;
}

type EditState = false | null | number;

export default function BeheerPagina() {
  const [berichten, setBerichten] = useState<BerichtAdminRead[] | null>(null);
  const [laden, setLaden] = useState(false);
  const [fout, setFout] = useState<string | null>(null);
  const [toonLijst, setToonLijst] = useState(false);
  const [uitgeklapt, setUitgeklapt] = useState<Set<number>>(new Set());
  const [editState, setEditState] = useState<EditState>(false);
  const [formulier, setFormulier] = useState(LEEG);
  const [opgeslagen, setOpgeslagen] = useState(false);

  const laadBerichten = useCallback(async () => {
    setLaden(true);
    setFout(null);
    try {
      const data = await beheerFetch("/api/admin/berichten") as { items: BerichtAdminRead[] };
      setBerichten(data.items);
    } catch (err) {
      setFout(err instanceof Error ? err.message : "Fout bij het ophalen van berichten.");
    } finally {
      setLaden(false);
    }
  }, []);

  function toggleUitgeklapt(id: number) {
    setUitgeklapt((prev) => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next; });
  }

  function bewerkStarten(b: BerichtAdminRead) {
    setFormulier({ titel: b.titel, inhoud: b.inhoud, type: b.type as BerichtType, versie: b.versie ?? null });
    setEditState(b.id);
  }

  function annuleren() { setEditState(false); setFormulier(LEEG); }

  async function formulierVerzenden() {
    if (!formulier.titel || !formulier.inhoud) return;
    setFout(null);
    const body: BerichtCreate = { titel: formulier.titel, inhoud: formulier.inhoud, type: formulier.type, versie: formulier.versie ?? null };
    try {
      if (editState === null) {
        await beheerFetch("/api/admin/berichten", { method: "POST", body: JSON.stringify(body) });
      } else if (typeof editState === "number") {
        await beheerFetch(`/api/admin/berichten/${editState}`, { method: "PUT", body: JSON.stringify(body) });
      }
      setEditState(false);
      setFormulier(LEEG);
      setToonLijst(true);
      setOpgeslagen(true);
      setTimeout(() => setOpgeslagen(false), 3000);
      await laadBerichten();
    } catch (err) {
      setFout(err instanceof Error ? err.message : "Fout bij het opslaan.");
    }
  }

  async function publicatieWisselen(b: BerichtAdminRead) {
    setFout(null);
    try {
      await beheerFetch(`/api/admin/berichten/${b.id}/publicatie`, { method: "PATCH", body: JSON.stringify({ gepubliceerd: !b.gepubliceerd }) });
      await laadBerichten();
    } catch (err) {
      setFout(err instanceof Error ? err.message : "Fout bij publicatiestatus wijzigen.");
    }
  }

  async function berichtVerwijderen(id: number) {
    setFout(null);
    try {
      await beheerFetch(`/api/admin/berichten/${id}`, { method: "DELETE" });
      setUitgeklapt((prev) => { const next = new Set(prev); next.delete(id); return next; });
      await laadBerichten();
    } catch (err) {
      setFout(err instanceof Error ? err.message : "Fout bij verwijderen.");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2.5rem" }}>
      <div>
        <h1 style={{ fontSize: "1.75rem" }}>Beheer</h1>
        <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Berichten, gebruikers en systeeminstellingen voor beheerders.
        </p>
      </div>

      {/* ---- Sectie: Berichten ---- */}
      <section>
        <SectieHeader titel="Berichten" subtitel="Release notes en aankondigingen voor analisten." />

        {fout && (
          <div className="melding melding-fout" style={{ marginBottom: "1rem" }}>
            <p role="alert">{fout}</p>
          </div>
        )}

        {opgeslagen && (
          <div style={{ marginBottom: "1rem", padding: "0.625rem 1rem", borderRadius: "4px", background: "rgb(var(--succes) / 0.08)", border: "1px solid rgb(var(--succes) / 0.3)", color: "rgb(var(--succes))", fontSize: "0.875rem" }}>
            Bericht opgeslagen.
          </div>
        )}

        {editState !== false && (
          <div className="card" style={{ marginBottom: "1.25rem" }}>
            <h3 style={{ marginBottom: "1rem", fontSize: "0.9375rem", fontWeight: 600 }}>
              {editState === null ? "Nieuw bericht" : "Bericht bewerken"}
            </h3>
            <form onSubmit={(e) => { e.preventDefault(); void formulierVerzenden(); }} style={{ display: "grid", gap: "0.75rem", maxWidth: 480 }}>
              <div>
                <label className="field-label" htmlFor="titel">Titel</label>
                <input id="titel" className="field-input" value={formulier.titel} onChange={(e) => setFormulier((f) => ({ ...f, titel: e.target.value }))} required style={{ marginTop: "0.25rem" }} />
              </div>
              <div>
                <label className="field-label" htmlFor="inhoud">Inhoud</label>
                <textarea id="inhoud" className="field-input" value={formulier.inhoud} onChange={(e) => setFormulier((f) => ({ ...f, inhoud: e.target.value }))} required rows={3} style={{ marginTop: "0.25rem", resize: "vertical" }} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                <div>
                  <label className="field-label" htmlFor="type">Type</label>
                  <select id="type" className="field-input" value={formulier.type} onChange={(e) => setFormulier((f) => ({ ...f, type: e.target.value as BerichtType }))} style={{ marginTop: "0.25rem" }}>
                    {BERICHT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="field-label" htmlFor="versie">Versie <span style={{ color: "rgb(var(--faint))", fontWeight: 400 }}>(opt.)</span></label>
                  <input id="versie" className="field-input" value={formulier.versie ?? ""} onChange={(e) => setFormulier((f) => ({ ...f, versie: e.target.value || null }))} style={{ marginTop: "0.25rem" }} />
                </div>
              </div>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.25rem" }}>
                <button type="submit" className="btn btn-primary">Opslaan</button>
                <button type="button" className="btn btn-secondary" onClick={annuleren}>Annuleren</button>
              </div>
            </form>
          </div>
        )}

        {editState === false && (
          <div style={{ display: "flex", gap: "0.75rem", marginBottom: toonLijst ? "1.25rem" : 0 }}>
            <button className="btn btn-primary" onClick={() => { setEditState(null); setFormulier(LEEG); }}>Nieuw bericht</button>
            {!toonLijst && (
              <button className="btn btn-secondary" onClick={() => { setToonLijst(true); void laadBerichten(); }}>Toon berichten</button>
            )}
          </div>
        )}

        {toonLijst && editState === false && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {laden && <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Laden…</p>}
            {!laden && berichten?.length === 0 && <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Nog geen berichten.</p>}
            {berichten?.map((b) => {
              const open = uitgeklapt.has(b.id);
              const type = b.type as BerichtType;
              const datum = new Date(b.gepubliceerd_op ?? b.created).toLocaleDateString("nl-NL", { day: "numeric", month: "long", year: "numeric" });
              return (
                <div key={b.id} className="card" style={{ padding: 0, overflow: "hidden" }}>
                  <button type="button" onClick={() => toggleUitgeklapt(b.id)} aria-expanded={open} style={{ display: "flex", width: "100%", alignItems: "flex-start", justifyContent: "space-between", gap: "0.75rem", padding: "0.75rem 1rem", background: "transparent", border: "none", cursor: "pointer", textAlign: "left" }}>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                        <TypeBadge type={type} />
                        {b.versie && <span style={{ fontSize: "0.6875rem", fontFamily: "monospace", padding: "0.125rem 0.4rem", borderRadius: "3px", color: "rgb(var(--faint))", border: "1px solid rgb(var(--line))", background: "rgb(var(--surface))" }}>{b.versie}</span>}
                        <span style={{ fontSize: "0.75rem", fontWeight: 500, color: b.gepubliceerd ? "rgb(var(--succes))" : "rgb(var(--muted))" }}>{b.gepubliceerd ? "Gepubliceerd" : "Concept"}</span>
                        <span style={{ fontSize: "0.75rem", color: "rgb(var(--faint))" }}>{datum}</span>
                      </div>
                      <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", fontWeight: 600, color: "rgb(var(--ink))" }}>{b.titel}</p>
                    </div>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0, marginTop: "0.25rem", color: "rgb(var(--muted))", transition: "transform 0.15s", transform: open ? "rotate(180deg)" : "none" }}>
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </button>
                  {open && (
                    <div style={{ borderTop: "1px solid rgb(var(--line))", padding: "0.75rem 1rem 1rem" }}>
                      <p style={{ fontSize: "0.875rem", color: "rgb(var(--ink))", marginBottom: "0.75rem" }}>{b.inhoud}</p>
                      <div className="acties">
                        <button className="btn btn-secondary" style={{ fontSize: "0.8125rem" }} onClick={() => bewerkStarten(b)}>Bewerken</button>
                        <button className="btn btn-secondary" style={{ fontSize: "0.8125rem" }} onClick={() => void publicatieWisselen(b)}>{b.gepubliceerd ? "Depubliceren" : "Publiceren"}</button>
                        <button className="btn btn-danger" style={{ fontSize: "0.8125rem" }} onClick={() => void berichtVerwijderen(b.id)}>Verwijderen</button>
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
        <SectieHeader titel="Gebruikers" subtitel="nog niet gebouwd" />
        <LeegePlaceholder tekst="Gebruikersbeheer wordt hier weergegeven zodra de API beschikbaar is." />
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
