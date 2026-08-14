"use client";

import { useState } from "react";
import { SectieHeader, LeegePlaceholder } from "@/components/beheer/SectieHeader";

type LlmProfielRead = {
  naam: string;
  provider: string;
  model: string;
  api_base: string;
  api_versie: string | null;
  temperatuur: number;
  sleutel_ingesteld: boolean;
  is_standaard: boolean;
  updated: string;
};

const NEP_PROFIELEN: LlmProfielRead[] = [
  {
    naam: "azure-gpt4o",
    provider: "azure_ai",
    model: "gpt-4o",
    api_base: "https://mijn-resource.openai.azure.com/",
    api_versie: "2024-08-01-preview",
    temperatuur: 0.0,
    sleutel_ingesteld: true,
    is_standaard: true,
    updated: "2026-08-14T10:00:00Z",
  },
  {
    naam: "openai-gpt4o-mini",
    provider: "openai",
    model: "gpt-4o-mini",
    api_base: "https://api.openai.com/v1",
    api_versie: null,
    temperatuur: 0.2,
    sleutel_ingesteld: true,
    is_standaard: false,
    updated: "2026-08-13T08:30:00Z",
  },
];

type Variant = "lijst-leeg" | "lijst-gevuld" | "aanmaken-formulier";

const VARIANTEN: { id: Variant; label: string }[] = [
  { id: "lijst-leeg", label: "Lijst — leeg" },
  { id: "lijst-gevuld", label: "Lijst — gevuld" },
  { id: "aanmaken-formulier", label: "Aanmaken-formulier" },
];

const PROVIDERS = ["azure_ai", "openai", "anthropic"];

function ProfielTabel({
  profielen,
  onVerwijder,
}: {
  profielen: LlmProfielRead[];
  onVerwijder: (naam: string) => void;
}) {
  const [bewerkt, setBewerkt] = useState<string | null>(null);

  return (
    <div>
      <table className="tabel" style={{ width: "100%" }}>
        <thead>
          <tr>
            <th>Naam</th>
            <th>Provider</th>
            <th>Model</th>
            <th>Standaard</th>
            <th>Sleutel</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {profielen.map((p) => (
            <tr key={p.naam}>
              <td style={{ fontWeight: 500 }}>{p.naam}</td>
              <td>
                <code style={{ fontSize: "0.8rem" }}>{p.provider}</code>
              </td>
              <td>{p.model}</td>
              <td>
                {p.is_standaard ? (
                  <span className="badge badge-succes">standaard</span>
                ) : (
                  <span style={{ color: "rgb(var(--faint))", fontSize: "0.875rem" }}>—</span>
                )}
              </td>
              <td>
                {p.sleutel_ingesteld ? (
                  <span style={{ color: "rgb(var(--succes))", fontSize: "0.8rem" }}>✓ ingesteld</span>
                ) : (
                  <span style={{ color: "rgb(var(--fout))", fontSize: "0.8rem" }}>niet ingesteld</span>
                )}
              </td>
              <td>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: "0.75rem", padding: "0.25rem 0.625rem" }}
                    onClick={() => setBewerkt(bewerkt === p.naam ? null : p.naam)}
                  >
                    {bewerkt === p.naam ? "Annuleer" : "Bewerk"}
                  </button>
                  <button
                    className="btn"
                    style={{
                      fontSize: "0.75rem",
                      padding: "0.25rem 0.625rem",
                      background: "rgb(var(--fout))",
                      color: "white",
                      border: "none",
                    }}
                    onClick={() => onVerwijder(p.naam)}
                  >
                    Verwijder
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {bewerkt && (
        <div
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
            Bewerk: {bewerkt}
          </p>
          <BewerkenFormulier />
        </div>
      )}
    </div>
  );
}

function BewerkenFormulier() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
      {[
        { label: "Provider", val: "azure_ai", type: "select" },
        { label: "Model", val: "gpt-4o", type: "text" },
        { label: "API base URL", val: "https://mijn-resource.openai.azure.com/", type: "text" },
        { label: "API versie", val: "2024-08-01-preview", type: "text" },
        { label: "Temperatuur", val: "0.0", type: "number" },
        { label: "API-sleutel (leeg = ongewijzigd)", val: "", type: "password" },
      ].map(({ label, val, type }) => (
        <div key={label}>
          <label
            style={{
              display: "block",
              fontSize: "0.75rem",
              fontWeight: 500,
              marginBottom: "0.25rem",
            }}
          >
            {label}
          </label>
          {type === "select" ? (
            <select className="field-input" defaultValue={val} style={{ width: "100%" }}>
              {PROVIDERS.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          ) : (
            <input
              className="field-input"
              type={type}
              defaultValue={val}
              style={{ width: "100%" }}
            />
          )}
        </div>
      ))}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", gridColumn: "span 2" }}>
        <input type="checkbox" id="is_standaard_bewerk" />
        <label htmlFor="is_standaard_bewerk" style={{ fontSize: "0.875rem" }}>
          Instellen als standaard-profiel
        </label>
      </div>
      <div style={{ gridColumn: "span 2", display: "flex", gap: "0.5rem" }}>
        <button className="btn btn-primary" style={{ fontSize: "0.8125rem" }}>
          Opslaan
        </button>
        <button className="btn btn-secondary" style={{ fontSize: "0.8125rem" }}>
          Annuleer
        </button>
      </div>
    </div>
  );
}

function AanmakenFormulier() {
  return (
    <div
      style={{
        padding: "1.25rem",
        background: "rgb(var(--surface))",
        border: "1px solid rgb(var(--line))",
        borderRadius: "6px",
      }}
    >
      <p style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "1rem" }}>
        Nieuw LLM-profiel aanmaken
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
        {[
          { label: "Naam (uniek)", val: "", type: "text" },
          { label: "Provider", val: "azure_ai", type: "select" },
          { label: "Model", val: "", type: "text" },
          { label: "API base URL", val: "", type: "text" },
          { label: "API versie (optioneel)", val: "", type: "text" },
          { label: "Temperatuur", val: "0.0", type: "number" },
          { label: "API-sleutel", val: "", type: "password" },
        ].map(({ label, val, type }) => (
          <div key={label} style={{ gridColumn: label === "API base URL" || label === "API-sleutel" ? "span 2" : undefined }}>
            <label
              style={{
                display: "block",
                fontSize: "0.75rem",
                fontWeight: 500,
                marginBottom: "0.25rem",
              }}
            >
              {label}
            </label>
            {type === "select" ? (
              <select className="field-input" defaultValue={val} style={{ width: "100%" }}>
                {PROVIDERS.map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            ) : (
              <input
                className="field-input"
                type={type}
                defaultValue={val}
                style={{ width: "100%" }}
              />
            )}
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", gridColumn: "span 2" }}>
          <input type="checkbox" id="is_standaard_nieuw" />
          <label htmlFor="is_standaard_nieuw" style={{ fontSize: "0.875rem" }}>
            Instellen als standaard-profiel
          </label>
        </div>
        <div style={{ gridColumn: "span 2" }}>
          <button className="btn btn-primary" style={{ fontSize: "0.8125rem" }}>
            Aanmaken
          </button>
        </div>
      </div>
    </div>
  );
}

export default function LlmProfielenMockup() {
  const [variant, setVariant] = useState<Variant>("lijst-gevuld");
  const [profielen, setProfielen] = useState(NEP_PROFIELEN);

  function verwijder(naam: string) {
    setProfielen((prev) => prev.filter((p) => p.naam !== naam));
  }

  return (
    <div className="main">
      <div
        style={{
          display: "inline-flex",
          background: "rgb(var(--lint))",
          color: "white",
          borderRadius: "4px",
          padding: "0.2rem 0.625rem",
          fontSize: "0.6875rem",
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: "1.25rem",
        }}
      >
        Mockup — LLM-profielen (story 011)
      </div>

      <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" }}>
        LLM-profielen
      </h1>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "2rem" }}>
        {VARIANTEN.map((v) => (
          <button
            key={v.id}
            className={variant === v.id ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => setVariant(v.id)}
          >
            {v.label}
          </button>
        ))}
      </div>

      {variant === "lijst-leeg" && (
        <div>
          <SectieHeader titel="LLM-profielen" aantal={0} />
          <LeegePlaceholder tekst="Geen profielen aangemaakt." />
          <div style={{ marginTop: "1rem" }}>
            <AanmakenFormulier />
          </div>
        </div>
      )}

      {variant === "lijst-gevuld" && (
        <div>
          <SectieHeader titel="LLM-profielen" aantal={profielen.length} />
          {profielen.length === 0 ? (
            <LeegePlaceholder tekst="Geen profielen meer aanwezig." />
          ) : (
            <ProfielTabel profielen={profielen} onVerwijder={verwijder} />
          )}
          <div style={{ marginTop: "1.5rem" }}>
            <AanmakenFormulier />
          </div>
        </div>
      )}

      {variant === "aanmaken-formulier" && (
        <div>
          <SectieHeader titel="LLM-profielen" aantal={2} />
          <AanmakenFormulier />
        </div>
      )}
    </div>
  );
}
