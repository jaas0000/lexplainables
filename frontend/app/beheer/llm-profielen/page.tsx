"use client";

import { useEffect, useState } from "react";
import type { components } from "@/generated/types";
import {
  SectieHeader,
  LeegePlaceholder,
} from "@/components/beheer/SectieHeader";
import { beheerFetch, BeheerFetchFout } from "@/lib/beheer-fetch";

type LlmProfielRead = components["schemas"]["LlmProfielRead"];
type LlmProfielCreate = components["schemas"]["LlmProfielCreate"];
type LlmProfielUpdate = components["schemas"]["LlmProfielUpdate"];
// LlmProfielUpdate wordt direct geïnitialiseerd vanuit het profiel (BewerkenFormulier), niet via een constante.

const PROVIDERS = ["azure_ai", "openai", "anthropic"];

const LEEG_AANMAKEN: LlmProfielCreate = {
  naam: "",
  provider: "openai",
  model: "",
  api_base: "",
  api_versie: null,
  temperatuur: 0.0,
  api_sleutel: null,
  is_standaard: false,
};

function veldfout(fout: unknown): string {
  if (fout instanceof BeheerFetchFout) return fout.message;
  if (fout instanceof Error) return fout.message;
  return "Onbekende fout.";
}

function BewerkenFormulier({
  profiel,
  onOpgeslagen,
  onAnnuleer,
}: {
  profiel: LlmProfielRead;
  onOpgeslagen: (bijgewerkt: LlmProfielRead) => void;
  onAnnuleer: () => void;
}) {
  const [formulier, setFormulier] = useState<LlmProfielUpdate>({
    provider: profiel.provider,
    model: profiel.model,
    api_base: profiel.api_base,
    api_versie: profiel.api_versie,
    temperatuur: profiel.temperatuur,
    api_sleutel: null,
    is_standaard: profiel.is_standaard,
  });
  const [bezig, setBezig] = useState(false);
  const [fout, setFout] = useState<string | null>(null);

  async function verzenden(e: React.FormEvent) {
    e.preventDefault();
    setBezig(true);
    setFout(null);
    try {
      const bijgewerkt = (await beheerFetch(
        `/api/admin/profielen/${profiel.naam}`,
        {
          method: "PUT",
          body: JSON.stringify(formulier),
        },
      )) as LlmProfielRead;
      onOpgeslagen(bijgewerkt);
    } catch (err) {
      setFout(veldfout(err));
    } finally {
      setBezig(false);
    }
  }

  return (
    <form
      onSubmit={(e) => void verzenden(e)}
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
        Bewerk: {profiel.naam}
      </p>

      {fout && (
        <div
          className="melding melding-fout"
          style={{ marginBottom: "0.75rem" }}
        >
          <p role="alert">{fout}</p>
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "0.75rem",
        }}
      >
        <div>
          <label className="field-label" htmlFor={`provider-${profiel.naam}`}>
            Provider
          </label>
          <select
            id={`provider-${profiel.naam}`}
            className="field-input"
            value={formulier.provider}
            onChange={(e) =>
              setFormulier((f) => ({ ...f, provider: e.target.value }))
            }
            style={{ width: "100%", marginTop: "0.25rem" }}
          >
            {PROVIDERS.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="field-label" htmlFor={`model-${profiel.naam}`}>
            Model
          </label>
          <input
            id={`model-${profiel.naam}`}
            className="field-input"
            value={formulier.model}
            onChange={(e) =>
              setFormulier((f) => ({ ...f, model: e.target.value }))
            }
            required
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div style={{ gridColumn: "span 2" }}>
          <label className="field-label" htmlFor={`api_base-${profiel.naam}`}>
            API base URL
          </label>
          <input
            id={`api_base-${profiel.naam}`}
            className="field-input"
            value={formulier.api_base}
            onChange={(e) =>
              setFormulier((f) => ({ ...f, api_base: e.target.value }))
            }
            required
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div>
          <label className="field-label" htmlFor={`api_versie-${profiel.naam}`}>
            API versie{" "}
            <span style={{ color: "rgb(var(--faint))", fontWeight: 400 }}>
              (opt.)
            </span>
          </label>
          <input
            id={`api_versie-${profiel.naam}`}
            className="field-input"
            value={formulier.api_versie ?? ""}
            onChange={(e) =>
              setFormulier((f) => ({
                ...f,
                api_versie: e.target.value || null,
              }))
            }
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div>
          <label
            className="field-label"
            htmlFor={`temperatuur-${profiel.naam}`}
          >
            Temperatuur
          </label>
          <input
            id={`temperatuur-${profiel.naam}`}
            className="field-input"
            type="number"
            step="0.1"
            min="0"
            max="2"
            value={formulier.temperatuur}
            onChange={(e) =>
              setFormulier((f) => ({
                ...f,
                temperatuur: parseFloat(e.target.value) || 0,
              }))
            }
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div style={{ gridColumn: "span 2" }}>
          <label className="field-label" htmlFor={`sleutel-${profiel.naam}`}>
            API-sleutel{" "}
            <span style={{ color: "rgb(var(--faint))", fontWeight: 400 }}>
              (leeg = ongewijzigd)
            </span>
          </label>
          <input
            id={`sleutel-${profiel.naam}`}
            className="field-input"
            type="password"
            placeholder={profiel.sleutel_ingesteld ? "••••••••" : ""}
            onChange={(e) =>
              setFormulier((f) => ({
                ...f,
                api_sleutel: e.target.value || null,
              }))
            }
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            gridColumn: "span 2",
          }}
        >
          <input
            type="checkbox"
            id={`standaard-${profiel.naam}`}
            checked={formulier.is_standaard}
            onChange={(e) =>
              setFormulier((f) => ({ ...f, is_standaard: e.target.checked }))
            }
          />
          <label
            htmlFor={`standaard-${profiel.naam}`}
            style={{ fontSize: "0.875rem" }}
          >
            Instellen als standaard-profiel
          </label>
        </div>

        <div style={{ gridColumn: "span 2", display: "flex", gap: "0.5rem" }}>
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
      </div>
    </form>
  );
}

function AanmakenFormulier({
  onAangemaakt,
}: {
  onAangemaakt: (nieuw: LlmProfielRead) => void;
}) {
  const [formulier, setFormulier] = useState<LlmProfielCreate>(LEEG_AANMAKEN);
  const [bezig, setBezig] = useState(false);
  const [fout, setFout] = useState<string | null>(null);

  async function verzenden(e: React.FormEvent) {
    e.preventDefault();
    setBezig(true);
    setFout(null);
    try {
      const nieuw = (await beheerFetch("/api/admin/profielen", {
        method: "POST",
        body: JSON.stringify(formulier),
      })) as LlmProfielRead;
      onAangemaakt(nieuw);
      setFormulier(LEEG_AANMAKEN);
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
        Nieuw LLM-profiel aanmaken
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
          gridTemplateColumns: "1fr 1fr",
          gap: "0.75rem",
        }}
      >
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
            placeholder="bijv. azure-gpt4o"
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div>
          <label className="field-label" htmlFor="nieuw-provider">
            Provider
          </label>
          <select
            id="nieuw-provider"
            className="field-input"
            value={formulier.provider}
            onChange={(e) =>
              setFormulier((f) => ({ ...f, provider: e.target.value }))
            }
            style={{ width: "100%", marginTop: "0.25rem" }}
          >
            {PROVIDERS.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="field-label" htmlFor="nieuw-model">
            Model <span style={{ color: "rgb(var(--fout))" }}>*</span>
          </label>
          <input
            id="nieuw-model"
            className="field-input"
            value={formulier.model}
            onChange={(e) =>
              setFormulier((f) => ({ ...f, model: e.target.value }))
            }
            required
            placeholder="bijv. gpt-4o"
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div>
          <label className="field-label" htmlFor="nieuw-api-versie">
            API versie{" "}
            <span style={{ color: "rgb(var(--faint))", fontWeight: 400 }}>
              (opt.)
            </span>
          </label>
          <input
            id="nieuw-api-versie"
            className="field-input"
            value={formulier.api_versie ?? ""}
            onChange={(e) =>
              setFormulier((f) => ({
                ...f,
                api_versie: e.target.value || null,
              }))
            }
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div style={{ gridColumn: "span 2" }}>
          <label className="field-label" htmlFor="nieuw-api-base">
            API base URL <span style={{ color: "rgb(var(--fout))" }}>*</span>
          </label>
          <input
            id="nieuw-api-base"
            className="field-input"
            value={formulier.api_base}
            onChange={(e) =>
              setFormulier((f) => ({ ...f, api_base: e.target.value }))
            }
            required
            placeholder="bijv. https://api.openai.com/v1"
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div>
          <label className="field-label" htmlFor="nieuw-temperatuur">
            Temperatuur
          </label>
          <input
            id="nieuw-temperatuur"
            className="field-input"
            type="number"
            step="0.1"
            min="0"
            max="2"
            value={formulier.temperatuur}
            onChange={(e) =>
              setFormulier((f) => ({
                ...f,
                temperatuur: parseFloat(e.target.value) || 0,
              }))
            }
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div>
          <label className="field-label" htmlFor="nieuw-api-sleutel">
            API-sleutel{" "}
            <span style={{ color: "rgb(var(--faint))", fontWeight: 400 }}>
              (opt.)
            </span>
          </label>
          <input
            id="nieuw-api-sleutel"
            className="field-input"
            type="password"
            onChange={(e) =>
              setFormulier((f) => ({
                ...f,
                api_sleutel: e.target.value || null,
              }))
            }
            style={{ width: "100%", marginTop: "0.25rem" }}
          />
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            gridColumn: "span 2",
          }}
        >
          <input
            type="checkbox"
            id="nieuw-standaard"
            checked={formulier.is_standaard}
            onChange={(e) =>
              setFormulier((f) => ({ ...f, is_standaard: e.target.checked }))
            }
          />
          <label htmlFor="nieuw-standaard" style={{ fontSize: "0.875rem" }}>
            Instellen als standaard-profiel
          </label>
        </div>

        <div style={{ gridColumn: "span 2" }}>
          <button type="submit" className="btn btn-primary" disabled={bezig}>
            {bezig ? "Aanmaken…" : "Aanmaken"}
          </button>
        </div>
      </form>
    </div>
  );
}

function ProfielTabel({
  profielen,
  onBijgewerkt,
  onVerwijderd,
}: {
  profielen: LlmProfielRead[];
  onBijgewerkt: (bijgewerkt: LlmProfielRead) => void;
  onVerwijderd: (naam: string) => void;
}) {
  const [bewerkt, setBewerkt] = useState<string | null>(null);
  const [verwijderFout, setVerwijderFout] = useState<{
    naam: string;
    bericht: string;
  } | null>(null);

  async function verwijder(naam: string) {
    setVerwijderFout(null);
    try {
      await beheerFetch(`/api/admin/profielen/${naam}`, { method: "DELETE" });
      onVerwijderd(naam);
    } catch (err) {
      setVerwijderFout({ naam, bericht: veldfout(err) });
    }
  }

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
                  <span
                    style={{ color: "rgb(var(--faint))", fontSize: "0.875rem" }}
                  >
                    —
                  </span>
                )}
              </td>
              <td>
                {p.sleutel_ingesteld ? (
                  <span
                    style={{ color: "rgb(var(--succes))", fontSize: "0.8rem" }}
                  >
                    ✓ ingesteld
                  </span>
                ) : (
                  <span
                    style={{ color: "rgb(var(--fout))", fontSize: "0.8rem" }}
                  >
                    niet ingesteld
                  </span>
                )}
              </td>
              <td>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: "0.75rem", padding: "0.25rem 0.625rem" }}
                    onClick={() =>
                      setBewerkt(bewerkt === p.naam ? null : p.naam)
                    }
                  >
                    {bewerkt === p.naam ? "Annuleer" : "Bewerk"}
                  </button>
                  <button
                    className="btn btn-danger"
                    style={{ fontSize: "0.75rem", padding: "0.25rem 0.625rem" }}
                    onClick={() => void verwijder(p.naam)}
                  >
                    Verwijder
                  </button>
                </div>
                {verwijderFout?.naam === p.naam && (
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
          profiel={profielen.find((p) => p.naam === bewerkt)!}
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

export default function LlmProfielenPagina() {
  const [profielen, setProfielen] = useState<LlmProfielRead[] | null>(null);
  const [laden, setLaden] = useState(true);
  const [fout, setFout] = useState<string | null>(null);

  useEffect(() => {
    // laden begint als true (initiële state) — geen synchrone setState hier om de
    // react-hooks/set-state-in-effect-regel te respecteren; state-updates lopen alleen
    // via de promise-callbacks.
    beheerFetch("/api/admin/profielen")
      .then((data) => setProfielen(data as LlmProfielRead[]))
      .catch((err) => setFout(veldfout(err)))
      .finally(() => setLaden(false));
  }, []);

  function profielBijgewerkt(bijgewerkt: LlmProfielRead) {
    setProfielen((prev) => {
      if (!prev) return [bijgewerkt];
      // Standaard-flip: als bijgewerkt.is_standaard true is, reset alle anderen.
      return prev.map((p) =>
        p.naam === bijgewerkt.naam
          ? bijgewerkt
          : bijgewerkt.is_standaard
            ? { ...p, is_standaard: false }
            : p,
      );
    });
  }

  function profielAangemaakt(nieuw: LlmProfielRead) {
    setProfielen((prev) => {
      if (!prev) return [nieuw];
      const base = nieuw.is_standaard
        ? prev.map((p) => ({ ...p, is_standaard: false }))
        : prev;
      return [...base, nieuw].sort((a, b) => a.naam.localeCompare(b.naam));
    });
  }

  function profielVerwijderd(naam: string) {
    setProfielen((prev) => (prev ? prev.filter((p) => p.naam !== naam) : null));
  }

  return (
    <div>
      <h1
        style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" }}
      >
        LLM-profielen
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

      {!laden && profielen !== null && (
        <>
          <SectieHeader titel="LLM-profielen" aantal={profielen.length} />

          {profielen.length === 0 ? (
            <LeegePlaceholder tekst="Geen profielen aangemaakt." />
          ) : (
            <ProfielTabel
              profielen={profielen}
              onBijgewerkt={profielBijgewerkt}
              onVerwijderd={profielVerwijderd}
            />
          )}

          <AanmakenFormulier onAangemaakt={profielAangemaakt} />
        </>
      )}
    </div>
  );
}
