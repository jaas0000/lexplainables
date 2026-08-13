"use client";

import { useState } from "react";
import type { components } from "@/generated/types";

type BerichtAdminRead = components["schemas"]["BerichtAdminRead"];
type BerichtType = components["schemas"]["BerichtCreate"]["type"];

const BERICHT_TYPES: BerichtType[] = [
  "info",
  "update",
  "waarschuwing",
  "kritiek",
];

// Fase 1 (frontend-bouwen regel 2): nepdata op basis van het gegenereerde `BerichtAdminRead`-
// type, ter visuele validatie vóór de echte API-aanroepen (fase 2) erbij komen.
const NEPDATA: BerichtAdminRead[] = [
  {
    id: 1,
    titel: "Onderhoud gepland op zaterdag",
    inhoud:
      "De omgeving is zaterdag 10:00-12:00 niet bereikbaar wegens onderhoud.",
    type: "waarschuwing",
    versie: null,
    gepubliceerd: true,
    gepubliceerd_op: "2026-08-01T09:00:00Z",
    aangemaakt_door: "beheerder-a",
    created: "2026-07-30T14:00:00Z",
    updated: "2026-08-01T09:00:00Z",
  },
  {
    id: 2,
    titel: "Nieuwe versie 2.4.0",
    inhoud: "Verbeterde zoekfunctie en een aantal bugfixes.",
    type: "update",
    versie: "2.4.0",
    gepubliceerd: false,
    gepubliceerd_op: null,
    aangemaakt_door: "beheerder-b",
    created: "2026-08-05T11:00:00Z",
    updated: "2026-08-05T11:00:00Z",
  },
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

export default function BerichtenAdminPagina() {
  const [berichten, setBerichten] = useState<BerichtAdminRead[]>(NEPDATA);
  const [formulier, setFormulier] = useState(LEEG_FORMULIER);
  const [bewerktId, setBewerktId] = useState<number | null>(null);

  function formulierVerzenden() {
    if (bewerktId === null) {
      const nieuw: BerichtAdminRead = {
        id: Math.max(0, ...berichten.map((b) => b.id)) + 1,
        titel: formulier.titel,
        inhoud: formulier.inhoud,
        type: formulier.type,
        versie: formulier.versie || null,
        gepubliceerd: false,
        gepubliceerd_op: null,
        aangemaakt_door: "jij",
        created: new Date().toISOString(),
        updated: new Date().toISOString(),
      };
      setBerichten((huidig) => [nieuw, ...huidig]);
    } else {
      setBerichten((huidig) =>
        huidig.map((b) =>
          b.id === bewerktId
            ? {
                ...b,
                titel: formulier.titel,
                inhoud: formulier.inhoud,
                type: formulier.type,
                versie: formulier.versie || null,
                updated: new Date().toISOString(),
              }
            : b,
        ),
      );
      setBewerktId(null);
    }
    setFormulier(LEEG_FORMULIER);
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

  function publicatieWisselen(id: number) {
    setBerichten((huidig) =>
      huidig.map((b) =>
        b.id === id ? { ...b, gepubliceerd: !b.gepubliceerd } : b,
      ),
    );
  }

  function berichtVerwijderen(id: number) {
    setBerichten((huidig) => huidig.filter((b) => b.id !== id));
  }

  return (
    <main
      style={{
        maxWidth: 900,
        margin: "2rem auto",
        padding: "0 1rem",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <h1>Berichten beheren</h1>

      <section style={{ marginTop: "2rem" }}>
        <h2>
          {bewerktId === null
            ? "Nieuw bericht"
            : `Bericht #${bewerktId} bewerken`}
        </h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            formulierVerzenden();
          }}
          style={{ display: "grid", gap: "0.5rem", maxWidth: 500 }}
        >
          <label>
            Titel
            <input
              value={formulier.titel}
              onChange={(e) =>
                setFormulier((f) => ({ ...f, titel: e.target.value }))
              }
              required
              style={{ display: "block", width: "100%" }}
            />
          </label>
          <label>
            Inhoud
            <textarea
              value={formulier.inhoud}
              onChange={(e) =>
                setFormulier((f) => ({ ...f, inhoud: e.target.value }))
              }
              required
              rows={3}
              style={{ display: "block", width: "100%" }}
            />
          </label>
          <label>
            Type
            <select
              value={formulier.type}
              onChange={(e) =>
                setFormulier((f) => ({
                  ...f,
                  type: e.target.value as BerichtType,
                }))
              }
              style={{ display: "block" }}
            >
              {BERICHT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label>
            Versie (optioneel)
            <input
              value={formulier.versie ?? ""}
              onChange={(e) =>
                setFormulier((f) => ({ ...f, versie: e.target.value || null }))
              }
              style={{ display: "block" }}
            />
          </label>
          <button type="submit">
            {bewerktId === null ? "Aanmaken" : "Opslaan"}
          </button>{" "}
          {bewerktId !== null && (
            <button type="button" onClick={bewerkenAnnuleren}>
              Annuleren
            </button>
          )}
        </form>
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h2>Alle berichten</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
              <th>Titel</th>
              <th>Type</th>
              <th>Status</th>
              <th>Aangemaakt door</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {berichten.map((b) => (
              <tr key={b.id} style={{ borderBottom: "1px solid #eee" }}>
                <td>{b.titel}</td>
                <td>{b.type}</td>
                <td>{b.gepubliceerd ? "gepubliceerd" : "concept"}</td>
                <td>{b.aangemaakt_door}</td>
                <td style={{ whiteSpace: "nowrap" }}>
                  <button onClick={() => bewerkenStarten(b)}>Bewerken</button>{" "}
                  <button onClick={() => publicatieWisselen(b.id)}>
                    {b.gepubliceerd ? "Depubliceren" : "Publiceren"}
                  </button>{" "}
                  <button onClick={() => berichtVerwijderen(b.id)}>
                    Verwijderen
                  </button>
                </td>
              </tr>
            ))}
            {berichten.length === 0 && (
              <tr>
                <td colSpan={5}>Geen berichten.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
