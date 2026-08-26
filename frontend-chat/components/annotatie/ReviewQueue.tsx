"use client";

import { useState } from "react";
import { jasStyle, jasVolgorde, JAS_KLASSEN } from "@/lib/jas";
import type {
  AnnotatieElement,
  BeoordelingsReden,
} from "@/lib/annotatie-types";

const BESLIST = new Set(["human_goedgekeurd", "bewerkt", "afgewezen"]);
const REDENEN: { waarde: BeoordelingsReden; label: string }[] = [
  { waarde: "onduidelijk", label: "Onduidelijk" },
  { waarde: "fout_klasse", label: "Verkeerde klasse" },
  { waarde: "fout_tekst", label: "Verkeerd fragment" },
  { waarde: "dubbeling", label: "Dubbeling" },
  { waarde: "overig", label: "Overig" },
];

function gesorteerd(elementen: AnnotatieElement[]): AnnotatieElement[] {
  return [...elementen].sort((a, b) => {
    const kv = jasVolgorde(a.klasse) - jasVolgorde(b.klasse);
    if (kv !== 0) return kv;
    return a.lid.localeCompare(b.lid);
  });
}

export function ReviewQueue({
  elementen,
  actiefId,
  vergrendeld,
  onSelecteer,
  onBeslissing,
  onVerwijder,
}: {
  elementen: AnnotatieElement[];
  actiefId: string | null;
  vergrendeld: boolean;
  onSelecteer: (el: AnnotatieElement) => void;
  onBeslissing: (
    elementId: string,
    body: {
      type: "goedkeuren" | "bewerken" | "afwijzen" | "opmerking";
      reden?: BeoordelingsReden;
      opmerking?: string;
      wijziging?: {
        klasse?: string;
        tekst?: string;
        toelichting?: string;
        lid?: string;
      };
    },
  ) => void;
  onVerwijder: (elementId: string) => void;
}) {
  if (elementen.length === 0) {
    return <p className="p-4 text-sm text-faint">Nog geen markeringen.</p>;
  }

  return (
    <ul className="space-y-2 p-4">
      {gesorteerd(elementen).map((el) => (
        <ElementKaart
          key={el.id}
          el={el}
          actief={el.id === actiefId}
          vergrendeld={vergrendeld}
          onSelecteer={() => onSelecteer(el)}
          onBeslissing={(body) => onBeslissing(el.id, body)}
          onVerwijder={() => onVerwijder(el.id)}
        />
      ))}
    </ul>
  );
}

function ElementKaart({
  el,
  actief,
  vergrendeld,
  onSelecteer,
  onBeslissing,
  onVerwijder,
}: {
  el: AnnotatieElement;
  actief: boolean;
  vergrendeld: boolean;
  onSelecteer: () => void;
  onBeslissing: (body: {
    type: "goedkeuren" | "bewerken" | "afwijzen" | "opmerking";
    reden?: BeoordelingsReden;
    opmerking?: string;
    wijziging?: {
      klasse?: string;
      tekst?: string;
      toelichting?: string;
      lid?: string;
    };
  }) => void;
  onVerwijder: () => void;
}) {
  const [modus, setModus] = useState<
    "geen" | "bewerken" | "verwerpen" | "opmerking"
  >("geen");
  const [nieuweKlasse, setNieuweKlasse] = useState(el.klasse);
  const [nieuweTekst, setNieuweTekst] = useState(el.tekst);
  const [reden, setReden] = useState<BeoordelingsReden>("onduidelijk");
  const [opmerking, setOpmerking] = useState("");

  const beslist = BESLIST.has(el.levenscyclus);

  function bevestigBewerken() {
    onBeslissing({
      type: "bewerken",
      reden,
      wijziging: { klasse: nieuweKlasse, tekst: nieuweTekst },
    });
    setModus("geen");
  }

  function bevestigVerwerpen() {
    onBeslissing({ type: "afwijzen", reden });
    setModus("geen");
  }

  function bevestigOpmerking() {
    if (!opmerking.trim()) return;
    onBeslissing({ type: "opmerking", opmerking: opmerking.trim() });
    setModus("geen");
    setOpmerking("");
  }

  return (
    <li
      className={`card cursor-pointer ${actief ? "border-lint" : ""}`}
      onClick={onSelecteer}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          className={`rounded border px-1.5 py-0.5 text-xs font-medium ${jasStyle(el.klasse)}`}
        >
          {el.klasse}
        </span>
        <div className="flex items-center gap-1">
          {el.aandacht && (
            <span className="rounded bg-surface px-1.5 py-0.5 text-xs text-muted">
              {el.aandacht === "groen" && "Geen bezwaar"}
              {el.aandacht === "geel" && "Even kijken"}
              {el.aandacht === "rood" && "Waarschijnlijk fout"}
            </span>
          )}
          {el.lid && <span className="text-xs text-faint">lid {el.lid}</span>}
        </div>
      </div>

      <p className="mt-1 whitespace-pre-wrap text-sm">{el.tekst}</p>
      {el.toelichting && (
        <p className="mt-1 text-xs text-faint">{el.toelichting}</p>
      )}
      {el.critic && (
        <p className="mt-1 text-xs text-faint">Critic: {el.critic}</p>
      )}

      <p className="mt-2 text-xs text-faint">
        {el.herkomst === "mens" ? "Door jou gemarkeerd" : "Voorstel van Lex"}
        {beslist &&
          ` — ${
            el.levenscyclus === "human_goedgekeurd"
              ? "goedgekeurd"
              : el.levenscyclus === "bewerkt"
                ? "bewerkt"
                : "afgewezen"
          }`}
      </p>

      {!vergrendeld && (
        <div
          className="mt-2 flex flex-wrap gap-1"
          onClick={(e) => e.stopPropagation()}
        >
          {!beslist && modus === "geen" && (
            <>
              <button
                type="button"
                className="btn btn-primary text-xs"
                onClick={() => onBeslissing({ type: "goedkeuren" })}
              >
                Akkoord
              </button>
              <button
                type="button"
                className="btn btn-secondary text-xs"
                onClick={() => setModus("bewerken")}
              >
                Bewerken
              </button>
              <button
                type="button"
                className="btn btn-secondary text-xs"
                onClick={() => setModus("verwerpen")}
              >
                Verwerpen
              </button>
            </>
          )}
          {modus === "geen" && (
            <button
              type="button"
              className="btn btn-secondary text-xs"
              onClick={() => setModus("opmerking")}
            >
              Opmerking
            </button>
          )}
          {el.herkomst === "mens" && modus === "geen" && (
            <button
              type="button"
              className="btn btn-secondary text-xs"
              onClick={onVerwijder}
            >
              Verwijderen
            </button>
          )}

          {modus === "bewerken" && (
            <div className="w-full space-y-1">
              <select
                className="field-input text-xs"
                value={nieuweKlasse}
                onChange={(e) => setNieuweKlasse(e.target.value)}
              >
                {JAS_KLASSEN.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
              <input
                className="field-input text-xs"
                value={nieuweTekst}
                onChange={(e) => setNieuweTekst(e.target.value)}
              />
              <select
                className="field-input text-xs"
                value={reden}
                onChange={(e) => setReden(e.target.value as BeoordelingsReden)}
              >
                {REDENEN.map((r) => (
                  <option key={r.waarde} value={r.waarde}>
                    {r.label}
                  </option>
                ))}
              </select>
              <div className="flex gap-1">
                <button
                  type="button"
                  className="btn btn-primary text-xs"
                  onClick={bevestigBewerken}
                >
                  Opslaan
                </button>
                <button
                  type="button"
                  className="btn btn-secondary text-xs"
                  onClick={() => setModus("geen")}
                >
                  Annuleren
                </button>
              </div>
            </div>
          )}

          {modus === "verwerpen" && (
            <div className="w-full space-y-1">
              <select
                className="field-input text-xs"
                value={reden}
                onChange={(e) => setReden(e.target.value as BeoordelingsReden)}
              >
                {REDENEN.map((r) => (
                  <option key={r.waarde} value={r.waarde}>
                    {r.label}
                  </option>
                ))}
              </select>
              <div className="flex gap-1">
                <button
                  type="button"
                  className="btn btn-primary text-xs"
                  onClick={bevestigVerwerpen}
                >
                  Bevestigen
                </button>
                <button
                  type="button"
                  className="btn btn-secondary text-xs"
                  onClick={() => setModus("geen")}
                >
                  Annuleren
                </button>
              </div>
            </div>
          )}

          {modus === "opmerking" && (
            <div className="w-full space-y-1">
              <input
                className="field-input text-xs"
                placeholder="Opmerking…"
                value={opmerking}
                onChange={(e) => setOpmerking(e.target.value)}
              />
              <div className="flex gap-1">
                <button
                  type="button"
                  className="btn btn-primary text-xs"
                  onClick={bevestigOpmerking}
                >
                  Plaatsen
                </button>
                <button
                  type="button"
                  className="btn btn-secondary text-xs"
                  onClick={() => setModus("geen")}
                >
                  Annuleren
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </li>
  );
}
