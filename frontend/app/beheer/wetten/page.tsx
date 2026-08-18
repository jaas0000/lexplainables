"use client";

import { useEffect, useState } from "react";
import type { components } from "@/generated/types";
import {
  SectieHeader,
  LeegePlaceholder,
} from "@/components/beheer/SectieHeader";
import { beheerFetch, BeheerFetchFout } from "@/lib/beheer-fetch";

type WetRead = components["schemas"]["WetRead"];
type WetCreate = components["schemas"]["WetCreate"];

function veldfout(fout: unknown): string {
  if (fout instanceof BeheerFetchFout) return fout.message;
  if (fout instanceof Error) return fout.message;
  return "Onbekende fout.";
}

function BewerkenFormulier({
  wet,
  onOpgeslagen,
  onAnnuleer,
}: {
  wet: WetRead;
  onOpgeslagen: (bijgewerkt: WetRead) => void;
  onAnnuleer: () => void;
}) {
  const [naam, setNaam] = useState(wet.naam);
  const [bezig, setBezig] = useState(false);
  const [fout, setFout] = useState<string | null>(null);
  const [resolveBezig, setResolveBezig] = useState(false);

  async function opslaan(e: React.FormEvent) {
    e.preventDefault();
    if (!naam.trim()) return;
    setBezig(true);
    setFout(null);
    try {
      const bijgewerkt = (await beheerFetch(
        `/api/admin/wetten/${wet.bwb_id}`,
        {
          method: "PUT",
          body: JSON.stringify({ bwb_id: wet.bwb_id, naam: naam.trim() }),
        },
      )) as WetRead;
      onOpgeslagen(bijgewerkt);
    } catch (err) {
      setFout(veldfout(err));
    } finally {
      setBezig(false);
    }
  }

  async function resolve() {
    setResolveBezig(true);
    setFout(null);
    try {
      const resultaat = (await beheerFetch(
        `/api/admin/wetten/${wet.bwb_id}/resolve`,
        { method: "POST" },
      )) as { naam: string };
      setNaam(resultaat.naam);
    } catch (err) {
      setFout(veldfout(err));
    } finally {
      setResolveBezig(false);
    }
  }

  return (
    <form
      onSubmit={(e) => void opslaan(e)}
      style={{
        marginTop: "1rem",
        padding: "1rem",
        background: "rgb(var(--surface))",
        border: "1px solid rgb(var(--line))",
        borderRadius: "6px",
      }}
    >
      <p
        style={{
          fontSize: "0.8125rem",
          fontWeight: 600,
          marginBottom: "0.75rem",
          color: "rgb(var(--ink))",
        }}
      >
        Bewerk: {wet.bwb_id}
      </p>

      {fout && (
        <div
          className="melding melding-fout"
          style={{ marginBottom: "0.75rem" }}
        >
          <p role="alert">{fout}</p>
        </div>
      )}

      <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-end" }}>
        <div style={{ flex: 1 }}>
          <label className="field-label" htmlFor={`naam-${wet.bwb_id}`}>
            Naam
          </label>
          <input
            id={`naam-${wet.bwb_id}`}
            className="field-input"
            value={naam}
            onChange={(e) => setNaam(e.target.value)}
            required
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ fontSize: "0.8125rem", whiteSpace: "nowrap" }}
          onClick={() => void resolve()}
          disabled={resolveBezig}
        >
          {resolveBezig ? "Ophalen…" : "Resolve"}
        </button>
      </div>

      <div
        style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}
      >
        <button type="submit" className="btn btn-primary" disabled={bezig}>
          {bezig ? "Opslaan…" : "Opslaan"}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onAnnuleer}
        >
          Annuleer
        </button>
      </div>
    </form>
  );
}

function ToevoegenFormulier({
  onToegevoegd,
}: {
  onToegevoegd: (nieuw: WetRead) => void;
}) {
  const [formulier, setFormulier] = useState<WetCreate>({
    bwb_id: "",
    naam: "",
  });
  const [bezig, setBezig] = useState(false);
  const [fout, setFout] = useState<string | null>(null);

  async function verzenden(e: React.FormEvent) {
    e.preventDefault();
    if (!formulier.bwb_id.trim() || !formulier.naam.trim()) return;
    setBezig(true);
    setFout(null);
    try {
      const nieuw = (await beheerFetch(
        `/api/admin/wetten/${formulier.bwb_id.trim()}`,
        {
          method: "PUT",
          body: JSON.stringify({
            bwb_id: formulier.bwb_id.trim(),
            naam: formulier.naam.trim(),
          }),
        },
      )) as WetRead;
      onToegevoegd(nieuw);
      setFormulier({ bwb_id: "", naam: "" });
    } catch (err) {
      setFout(veldfout(err));
    } finally {
      setBezig(false);
    }
  }

  return (
    <div
      style={{
        padding: "1.25rem",
        background: "rgb(var(--surface))",
        border: "1px solid rgb(var(--line))",
        borderRadius: "6px",
        marginTop: "1.5rem",
      }}
    >
      <p
        style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "1rem" }}
      >
        Wet toevoegen
      </p>

      {fout && (
        <div
          className="melding melding-fout"
          style={{ marginBottom: "0.75rem" }}
        >
          <p role="alert">{fout}</p>
        </div>
      )}

      <form
        onSubmit={(e) => void verzenden(e)}
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 2fr",
          gap: "0.75rem",
        }}
      >
        <div>
          <label className="field-label" htmlFor="nieuw-bwb-id">
            BWB-id <span style={{ color: "rgb(var(--fout))" }}>*</span>
          </label>
          <input
            id="nieuw-bwb-id"
            className="field-input"
            value={formulier.bwb_id}
            onChange={(e) =>
              setFormulier((f) => ({ ...f, bwb_id: e.target.value }))
            }
            required
            placeholder="bijv. BWBR0011823"
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div>
          <label className="field-label" htmlFor="nieuw-naam">
            Naam <span style={{ color: "rgb(var(--fout))" }}>*</span>
          </label>
          <input
            id="nieuw-naam"
            className="field-input"
            value={formulier.naam}
            onChange={(e) =>
              setFormulier((f) => ({ ...f, naam: e.target.value }))
            }
            required
            placeholder="bijv. Wet werk en bijstand"
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div style={{ gridColumn: "span 2" }}>
          <button type="submit" className="btn btn-primary" disabled={bezig}>
            {bezig ? "Toevoegen…" : "Toevoegen"}
          </button>
        </div>
      </form>
    </div>
  );
}

function WettenTabel({
  wetten,
  onBijgewerkt,
  onVerwijderd,
}: {
  wetten: WetRead[];
  onBijgewerkt: (bijgewerkt: WetRead) => void;
  onVerwijderd: (bwbId: string) => void;
}) {
  const [bewerkt, setBewerkt] = useState<string | null>(null);
  const [verwijderFout, setVerwijderFout] = useState<{
    bwbId: string;
    bericht: string;
  } | null>(null);

  async function verwijder(bwbId: string) {
    if (!confirm(`Wet ${bwbId} verwijderen?`)) return;
    setVerwijderFout(null);
    try {
      await beheerFetch(`/api/admin/wetten/${bwbId}`, { method: "DELETE" });
      onVerwijderd(bwbId);
    } catch (err) {
      setVerwijderFout({ bwbId, bericht: veldfout(err) });
    }
  }

  return (
    <div>
      <table className="tabel" style={{ width: "100%" }}>
        <thead>
          <tr>
            <th>BWB-id</th>
            <th>Naam</th>
            <th>Bijgewerkt door</th>
            <th>Datum</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {wetten.map((w) => (
            <tr key={w.bwb_id}>
              <td>
                <code style={{ fontSize: "0.8rem" }}>{w.bwb_id}</code>
              </td>
              <td style={{ fontWeight: 500 }}>{w.naam}</td>
              <td style={{ color: "rgb(var(--muted))", fontSize: "0.875rem" }}>
                {w.bijgewerkt_door || "—"}
              </td>
              <td style={{ fontSize: "0.8125rem", color: "rgb(var(--faint))" }}>
                {new Date(w.bijgewerkt).toLocaleDateString("nl-NL", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </td>
              <td>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: "0.75rem", padding: "0.25rem 0.625rem" }}
                    onClick={() =>
                      setBewerkt(bewerkt === w.bwb_id ? null : w.bwb_id)
                    }
                  >
                    {bewerkt === w.bwb_id ? "Annuleer" : "Bewerk"}
                  </button>
                  <button
                    className="btn btn-danger"
                    style={{ fontSize: "0.75rem", padding: "0.25rem 0.625rem" }}
                    onClick={() => void verwijder(w.bwb_id)}
                  >
                    Verwijder
                  </button>
                </div>
                {verwijderFout?.bwbId === w.bwb_id && (
                  <p
                    role="alert"
                    style={{
                      fontSize: "0.75rem",
                      color: "rgb(var(--fout))",
                      marginTop: "0.25rem",
                    }}
                  >
                    {verwijderFout.bericht}
                  </p>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {bewerkt && (
        <BewerkenFormulier
          wet={wetten.find((w) => w.bwb_id === bewerkt)!}
          onOpgeslagen={(bijgewerkt) => {
            onBijgewerkt(bijgewerkt);
            setBewerkt(null);
          }}
          onAnnuleer={() => setBewerkt(null)}
        />
      )}
    </div>
  );
}

export default function WettenPagina() {
  const [wetten, setWetten] = useState<WetRead[] | null>(null);
  const [laden, setLaden] = useState(true);
  const [fout, setFout] = useState<string | null>(null);

  useEffect(() => {
    beheerFetch("/api/admin/wetten")
      .then((data) => setWetten(data as WetRead[]))
      .catch((err) => setFout(veldfout(err)))
      .finally(() => setLaden(false));
  }, []);

  function wetBijgewerkt(bijgewerkt: WetRead) {
    setWetten((prev) =>
      prev ? prev.map((w) => (w.bwb_id === bijgewerkt.bwb_id ? bijgewerkt : w)) : [bijgewerkt],
    );
  }

  function wetToegevoegd(nieuw: WetRead) {
    setWetten((prev) => {
      if (!prev) return [nieuw];
      const zonder = prev.filter((w) => w.bwb_id !== nieuw.bwb_id);
      return [...zonder, nieuw].sort((a, b) => a.naam.localeCompare(b.naam));
    });
  }

  function wetVerwijderd(bwbId: string) {
    setWetten((prev) => (prev ? prev.filter((w) => w.bwb_id !== bwbId) : null));
  }

  return (
    <div>
      <h1
        style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" }}
      >
        Wetcatalogus
      </h1>

      {fout && (
        <div className="melding melding-fout" style={{ marginBottom: "1rem" }}>
          <p role="alert">{fout}</p>
        </div>
      )}

      {laden && (
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Laden…
        </p>
      )}

      {!laden && wetten !== null && (
        <>
          <SectieHeader titel="Wetten in de catalogus" aantal={wetten.length} />

          {wetten.length === 0 ? (
            <LeegePlaceholder tekst="Geen wetten in de catalogus." />
          ) : (
            <WettenTabel
              wetten={wetten}
              onBijgewerkt={wetBijgewerkt}
              onVerwijderd={wetVerwijderd}
            />
          )}

          <ToevoegenFormulier onToegevoegd={wetToegevoegd} />
        </>
      )}
    </div>
  );
}
