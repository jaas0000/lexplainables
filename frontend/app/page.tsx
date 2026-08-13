"use client";

import { useCallback, useEffect, useState } from "react";
import type { components } from "@/generated/types";

type BerichtAdminRead = components["schemas"]["BerichtAdminRead"];
type BerichtCreate = components["schemas"]["BerichtCreate"];
type BerichtType = BerichtCreate["type"];

const BERICHT_TYPES: BerichtType[] = [
  "info",
  "update",
  "waarschuwing",
  "kritiek",
];

const LEEG_FORMULIER: Pick<
  BerichtAdminRead,
  "titel" | "inhoud" | "type" | "versie"
> = {
  titel: "",
  inhoud: "",
  type: "info",
  versie: null,
};

async function beheerFetch(pad: string, init: RequestInit = {}) {
  const response = await fetch(pad, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  if (response.status === 401) {
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login";
    throw new Error("Niet geautoriseerd.");
  }
  if (!response.ok) {
    const detail = await response
      .json()
      .then((d: { detail?: string }) => d.detail)
      .catch(() => null);
    throw new Error(detail ?? `${response.status} ${response.statusText}`);
  }
  if (response.status === 204) return undefined;
  return response.json();
}

function foutmelding(err: unknown, fallback: string) {
  return err instanceof Error ? err.message : fallback;
}

export default function BerichtenAdminPagina() {
  const [berichten, setBerichten] = useState<BerichtAdminRead[] | null>(null);
  const [laden, setLaden] = useState(false);
  const [fout, setFout] = useState<string | null>(null);
  const [formulier, setFormulier] = useState(LEEG_FORMULIER);
  const [bewerktId, setBewerktId] = useState<number | null>(null);

  const berichtenOphalen = useCallback(async () => {
    setLaden(true);
    setFout(null);
    try {
      const pagina = await beheerFetch("/api/admin/berichten");
      setBerichten((pagina as { items: BerichtAdminRead[] }).items);
    } catch (err) {
      setFout(
        foutmelding(err, "Onbekende fout bij het ophalen van berichten."),
      );
    } finally {
      setLaden(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    berichtenOphalen();
  }, [berichtenOphalen]);

  async function formulierVerzenden() {
    setFout(null);
    const body: BerichtCreate = {
      titel: formulier.titel,
      inhoud: formulier.inhoud,
      type: formulier.type,
      versie: formulier.versie || null,
    };
    try {
      if (bewerktId === null) {
        const nieuw: BerichtAdminRead = await beheerFetch(
          "/api/admin/berichten",
          { method: "POST", body: JSON.stringify(body) },
        );
        setBerichten((huidig) => [nieuw, ...(huidig ?? [])]);
      } else {
        const bijgewerkt: BerichtAdminRead = await beheerFetch(
          `/api/admin/berichten/${bewerktId}`,
          { method: "PUT", body: JSON.stringify(body) },
        );
        setBerichten((huidig) =>
          (huidig ?? []).map((b) => (b.id === bijgewerkt.id ? bijgewerkt : b)),
        );
        setBewerktId(null);
      }
      setFormulier(LEEG_FORMULIER);
    } catch (err) {
      setFout(
        foutmelding(err, "Onbekende fout bij het opslaan van het bericht."),
      );
    }
  }

  function bewerkenStarten(b: BerichtAdminRead) {
    setBewerktId(b.id);
    setFormulier({
      titel: b.titel,
      inhoud: b.inhoud,
      type: b.type,
      versie: b.versie,
    });
  }

  function bewerkenAnnuleren() {
    setBewerktId(null);
    setFormulier(LEEG_FORMULIER);
  }

  async function publicatieWisselen(b: BerichtAdminRead) {
    setFout(null);
    try {
      const bijgewerkt: BerichtAdminRead = await beheerFetch(
        `/api/admin/berichten/${b.id}/publicatie`,
        {
          method: "PATCH",
          body: JSON.stringify({ gepubliceerd: !b.gepubliceerd }),
        },
      );
      setBerichten((huidig) =>
        (huidig ?? []).map((r) => (r.id === bijgewerkt.id ? bijgewerkt : r)),
      );
    } catch (err) {
      setFout(
        foutmelding(
          err,
          "Onbekende fout bij het wijzigen van de publicatiestatus.",
        ),
      );
    }
  }

  async function berichtVerwijderen(id: number) {
    setFout(null);
    try {
      await beheerFetch(`/api/admin/berichten/${id}`, {
        method: "DELETE",
      });
      setBerichten((huidig) => (huidig ?? []).filter((b) => b.id !== id));
    } catch (err) {
      setFout(
        foutmelding(err, "Onbekende fout bij het verwijderen van het bericht."),
      );
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Foutmelding */}
      {fout && (
        <div className="melding melding-fout">
          <p role="alert">{fout}</p>
        </div>
      )}

      {/* Formulier */}
      <div className="card">
        <h2 style={{ marginBottom: "1rem", fontSize: "1.1rem" }}>
          {bewerktId === null
            ? "Nieuw bericht"
            : `Bericht #${bewerktId} bewerken`}
        </h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            formulierVerzenden();
          }}
          style={{ display: "grid", gap: "0.75rem", maxWidth: 480 }}
        >
          <div>
            <label className="field-label" htmlFor="titel">
              Titel
            </label>
            <input
              id="titel"
              className="field-input"
              value={formulier.titel}
              onChange={(e) =>
                setFormulier((f) => ({ ...f, titel: e.target.value }))
              }
              required
              style={{ marginTop: "0.25rem" }}
            />
          </div>
          <div>
            <label className="field-label" htmlFor="inhoud">
              Inhoud
            </label>
            <textarea
              id="inhoud"
              className="field-input"
              value={formulier.inhoud}
              onChange={(e) =>
                setFormulier((f) => ({ ...f, inhoud: e.target.value }))
              }
              required
              rows={3}
              style={{ marginTop: "0.25rem", resize: "vertical" }}
            />
          </div>
          <div>
            <label className="field-label" htmlFor="type">
              Type
            </label>
            <select
              id="type"
              className="field-input"
              value={formulier.type}
              onChange={(e) =>
                setFormulier((f) => ({
                  ...f,
                  type: e.target.value as BerichtType,
                }))
              }
              style={{ marginTop: "0.25rem" }}
            >
              {BERICHT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label" htmlFor="versie">
              Versie{" "}
              <span style={{ color: "rgb(var(--faint))", fontWeight: 400 }}>
                (optioneel)
              </span>
            </label>
            <input
              id="versie"
              className="field-input"
              value={formulier.versie ?? ""}
              onChange={(e) =>
                setFormulier((f) => ({
                  ...f,
                  versie: e.target.value || null,
                }))
              }
              style={{ marginTop: "0.25rem" }}
            />
          </div>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.25rem" }}>
            <button type="submit" className="btn btn-primary">
              {bewerktId === null ? "Aanmaken" : "Opslaan"}
            </button>
            {bewerktId !== null && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={bewerkenAnnuleren}
              >
                Annuleren
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Berichtenlijst */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div
          style={{
            padding: "1.25rem 1.5rem",
            borderBottom: "1px solid rgb(var(--line))",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <h2 style={{ fontSize: "1.1rem" }}>
            Alle berichten
            {berichten !== null && (
              <span
                style={{
                  marginLeft: "0.5rem",
                  fontSize: "0.85rem",
                  fontWeight: 400,
                  color: "rgb(var(--muted))",
                }}
              >
                ({berichten.length})
              </span>
            )}
          </h2>
          {laden && (
            <span style={{ fontSize: "0.8rem", color: "rgb(var(--muted))" }}>
              Laden…
            </span>
          )}
        </div>
        <table className="tabel">
          <thead>
            <tr>
              <th>Titel</th>
              <th>Type</th>
              <th>Status</th>
              <th>Aangemaakt door</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(berichten ?? []).map((b) => (
              <tr key={b.id}>
                <td style={{ fontWeight: 500 }}>{b.titel}</td>
                <td style={{ color: "rgb(var(--muted))" }}>{b.type}</td>
                <td>
                  <span
                    className={`badge ${b.gepubliceerd ? "badge-gepubliceerd" : "badge-concept"}`}
                  >
                    {b.gepubliceerd ? "gepubliceerd" : "concept"}
                  </span>
                </td>
                <td style={{ color: "rgb(var(--muted))" }}>
                  {b.aangemaakt_door}
                </td>
                <td>
                  <div className="acties">
                    <button
                      className="btn btn-secondary"
                      onClick={() => bewerkenStarten(b)}
                    >
                      Bewerken
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={() => publicatieWisselen(b)}
                    >
                      {b.gepubliceerd ? "Depubliceren" : "Publiceren"}
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={() => berichtVerwijderen(b.id)}
                    >
                      Verwijderen
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {berichten?.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  style={{
                    color: "rgb(var(--muted))",
                    textAlign: "center",
                    padding: "2rem",
                  }}
                >
                  Geen berichten.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
