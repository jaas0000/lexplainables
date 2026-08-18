"use client";

import React, { useState } from "react";
import { SectieHeader } from "@/components/beheer/SectieHeader";

// Lokale interfaces — nepdata, geen gegenereerde types nodig in fase 1
interface BoolInstelling {
  sleutel: string;
  label: string;
  beschrijving: string;
  type: "bool";
  waarde: boolean;
}

type Instelling = BoolInstelling;

type Variant = "overzicht" | "inline-bewerken" | "opgeslagen" | "fout";

const NEPDATA: Instelling[] = [
  {
    sleutel: "capture_llm_calls",
    label: "LLM-calls vastleggen",
    beschrijving:
      "Sla alle LLM-aanroepen (prompt + respons) op in de database voor later inzage. Schakel alleen in als dat nodig is — de opgeslagen inhoud kan gevoelige tekst bevatten.",
    type: "bool",
    waarde: false,
  },
];

export default function InstellingenMockup() {
  const [variant, setVariant] = useState<Variant>("overzicht");
  const [instellingen, setInstellingen] = useState<Instelling[]>(NEPDATA);
  const [bewerkSleutel, setBewerkSleutel] = useState<string | null>(null);
  const [bewerkWaarde, setBewerkWaarde] = useState<boolean>(false);
  const [melding, setMelding] = useState<{ type: "succes" | "fout"; tekst: string } | null>(null);

  function bewerkStarten(inst: BoolInstelling) {
    setBewerkSleutel(inst.sleutel);
    setBewerkWaarde(inst.waarde);
    setMelding(null);
    setVariant("inline-bewerken");
  }

  function annuleren() {
    setBewerkSleutel(null);
    setVariant("overzicht");
  }

  function opslaan() {
    if (variant === "fout") {
      setMelding({ type: "fout", tekst: "Kon instelling niet opslaan. Probeer opnieuw." });
      setBewerkSleutel(null);
      setVariant("overzicht");
      return;
    }

    setInstellingen((prev) =>
      prev.map((inst) =>
        inst.sleutel === bewerkSleutel && inst.type === "bool"
          ? { ...inst, waarde: bewerkWaarde }
          : inst
      )
    );
    setBewerkSleutel(null);
    setMelding({ type: "succes", tekst: "Instelling opgeslagen." });
    setVariant("opgeslagen");
    setTimeout(() => {
      setVariant("overzicht");
      setMelding(null);
    }, 3000);
  }

  const VARIANTEN: { waarde: Variant; label: string }[] = [
    { waarde: "overzicht", label: "Overzicht" },
    { waarde: "inline-bewerken", label: "Inline bewerken" },
    { waarde: "opgeslagen", label: "Na opslaan (succes)" },
    { waarde: "fout", label: "Na opslaan (fout)" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Paginakop + badge */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <div>
          <h1 style={{ fontSize: "1.375rem" }}>Instellingen</h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgb(var(--muted))",
            }}
          >
            Runtime-configuratie van de applicatie. Wijzigingen zijn direct actief.
          </p>
        </div>
        <span
          style={{
            flexShrink: 0,
            fontSize: "0.75rem",
            padding: "0.125rem 0.625rem",
            background: "rgb(var(--waarschuwing) / 0.1)",
            color: "rgb(var(--waarschuwing))",
            border: "1px solid rgb(var(--waarschuwing) / 0.3)",
            borderRadius: "9999px",
            fontWeight: 500,
          }}
        >
          mockup — nepdata
        </span>
      </div>

      {/* Variant-schakelaar */}
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          flexWrap: "wrap",
          alignItems: "center",
          padding: "0.75rem 1rem",
          background: "rgb(var(--surface))",
          borderRadius: "6px",
          border: "1px solid rgb(var(--line))",
          fontSize: "0.8rem",
        }}
      >
        <span
          style={{
            color: "rgb(var(--faint))",
            alignSelf: "center",
            marginRight: "0.25rem",
          }}
        >
          Variant:
        </span>
        {VARIANTEN.map((v) => (
          <button
            key={v.waarde}
            type="button"
            onClick={() => {
              setMelding(null);
              setBewerkSleutel(null);
              if (v.waarde === "inline-bewerken") {
                bewerkStarten(instellingen[0] as BoolInstelling);
              } else if (v.waarde === "opgeslagen") {
                setMelding({ type: "succes", tekst: "Instelling opgeslagen." });
                setVariant("opgeslagen");
              } else if (v.waarde === "fout") {
                setMelding({
                  type: "fout",
                  tekst: "Kon instelling niet opslaan. Probeer opnieuw.",
                });
                setVariant("fout");
              } else {
                setVariant("overzicht");
              }
            }}
            style={{
              padding: "0.25rem 0.625rem",
              borderRadius: "4px",
              border: "1px solid",
              fontSize: "0.8rem",
              cursor: "pointer",
              fontFamily: "inherit",
              background:
                variant === v.waarde
                  ? "rgb(var(--lint))"
                  : "rgb(var(--paper))",
              color:
                variant === v.waarde
                  ? "rgb(var(--paper))"
                  : "rgb(var(--muted))",
              borderColor:
                variant === v.waarde
                  ? "rgb(var(--lint))"
                  : "rgb(var(--line))",
            }}
          >
            {v.label}
          </button>
        ))}
      </div>

      {/* Sectie: Instellingen */}
      <section>
        <SectieHeader
          titel="Instellingen"
          subtitel="Wijzigingen zijn direct van kracht (max. 10 seconden cache)."
        />

        {/* Melding na opslaan */}
        {melding && (
          <div
            className={melding.type === "succes" ? "" : "melding melding-fout"}
            style={
              melding.type === "succes"
                ? {
                    marginBottom: "1rem",
                    padding: "0.625rem 1rem",
                    borderRadius: "4px",
                    background: "rgb(var(--succes) / 0.08)",
                    border: "1px solid rgb(var(--succes) / 0.3)",
                    color: "rgb(var(--succes))",
                    fontSize: "0.875rem",
                  }
                : { marginBottom: "1rem" }
            }
            role="alert"
          >
            {melding.tekst}
          </div>
        )}

        {/* Tabel */}
        <div
          style={{
            border: "1px solid rgb(var(--line))",
            borderRadius: "6px",
            overflow: "hidden",
          }}
        >
          <table className="tabel">
            <thead>
              <tr>
                <th style={{ width: "14rem" }}>Sleutel</th>
                <th>Omschrijving</th>
                <th style={{ width: "8rem", textAlign: "center" }}>Waarde</th>
                <th style={{ width: "8rem" }}>Acties</th>
              </tr>
            </thead>
            <tbody>
              {instellingen.map((inst) => {
                const isBewerken = bewerkSleutel === inst.sleutel;
                return (
                  <tr key={inst.sleutel}>
                    {/* Sleutel */}
                    <td>
                      <span
                        style={{
                          fontFamily: "monospace",
                          fontSize: "0.8125rem",
                          color: "rgb(var(--muted))",
                        }}
                      >
                        {inst.sleutel}
                      </span>
                      <div
                        style={{
                          fontSize: "0.8125rem",
                          fontWeight: 500,
                          color: "rgb(var(--ink))",
                          marginTop: "0.125rem",
                        }}
                      >
                        {inst.label}
                      </div>
                    </td>

                    {/* Beschrijving */}
                    <td>
                      <span
                        style={{
                          fontSize: "0.8125rem",
                          color: "rgb(var(--muted))",
                          lineHeight: 1.4,
                        }}
                      >
                        {inst.beschrijving}
                      </span>
                    </td>

                    {/* Waarde / inline edit */}
                    <td style={{ textAlign: "center" }}>
                      {isBewerken && inst.type === "bool" ? (
                        /* Toggle in bewerkingsmodus */
                        <button
                          type="button"
                          aria-label={bewerkWaarde ? "Aan — klik om uit te zetten" : "Uit — klik om aan te zetten"}
                          onClick={() => setBewerkWaarde((v) => !v)}
                          style={{
                            position: "relative",
                            display: "inline-flex",
                            width: "2.75rem",
                            height: "1.5rem",
                            borderRadius: "9999px",
                            border: "none",
                            cursor: "pointer",
                            background: bewerkWaarde
                              ? "rgb(var(--succes))"
                              : "rgb(var(--line))",
                            transition: "background 0.2s",
                            padding: 0,
                          }}
                        >
                          <span
                            style={{
                              position: "absolute",
                              top: "0.1875rem",
                              left: bewerkWaarde ? "1.3125rem" : "0.1875rem",
                              width: "1.125rem",
                              height: "1.125rem",
                              borderRadius: "9999px",
                              background: "white",
                              boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                              transition: "left 0.2s",
                            }}
                          />
                        </button>
                      ) : (
                        /* Waarde in leesmodus */
                        inst.type === "bool" && (
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "0.25rem",
                              fontSize: "0.8125rem",
                              fontWeight: 500,
                              color: inst.waarde
                                ? "rgb(var(--succes))"
                                : "rgb(var(--muted))",
                            }}
                          >
                            <span
                              style={{
                                display: "inline-block",
                                width: "0.5rem",
                                height: "0.5rem",
                                borderRadius: "9999px",
                                background: inst.waarde
                                  ? "rgb(var(--succes))"
                                  : "rgb(var(--faint))",
                              }}
                            />
                            {inst.waarde ? "Aan" : "Uit"}
                          </span>
                        )
                      )}
                    </td>

                    {/* Acties */}
                    <td>
                      {isBewerken ? (
                        <div className="acties">
                          <button
                            type="button"
                            className="btn btn-primary"
                            style={{ fontSize: "0.8125rem" }}
                            onClick={opslaan}
                          >
                            Opslaan
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ fontSize: "0.8125rem" }}
                            onClick={annuleren}
                          >
                            Annuleren
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ fontSize: "0.8125rem" }}
                          onClick={() => bewerkStarten(inst as BoolInstelling)}
                        >
                          Bewerken
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <p
          style={{
            marginTop: "0.75rem",
            fontSize: "0.75rem",
            color: "rgb(var(--faint))",
          }}
        >
          Klik op &ldquo;Bewerken&rdquo; om een instelling aan te passen. Wijzigingen worden direct in de database opgeslagen.
        </p>
      </section>
    </div>
  );
}
