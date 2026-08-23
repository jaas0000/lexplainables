"use client";

import { useState } from "react";
import type { components } from "@/generated/types";
import { SectieHeader } from "@/components/beheer/SectieHeader";
import { beheerFetch } from "@/lib/beheer-fetch";

type LlmCallRead = components["schemas"]["LlmCallRead"];

function CallRij({ call }: { call: LlmCallRead }) {
  const [open, setOpen] = useState(false);

  const datum = new Date(call.aangemaakt).toLocaleString("nl-NL", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <tr>
      <td colSpan={6} style={{ padding: 0 }}>
        <div>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            style={{
              display: "grid",
              gridTemplateColumns: "8rem 8rem 10rem 5rem 5rem 1fr",
              gap: "0.5rem",
              width: "100%",
              padding: "0.625rem 1rem",
              background: "transparent",
              border: "none",
              borderBottom: "1px solid rgb(var(--line))",
              cursor: "pointer",
              textAlign: "left",
              fontSize: "0.875rem",
              color: "rgb(var(--ink))",
            }}
          >
            <span>
              <code style={{ fontSize: "0.8rem" }}>{call.activiteit}</code>
            </span>
            <span style={{ color: "rgb(var(--muted))", fontSize: "0.8rem" }}>
              {call.bron_id ?? "—"}
            </span>
            <span style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
              {call.model}
            </span>
            <span style={{ textAlign: "right" }}>{call.tokens_in}</span>
            <span style={{ textAlign: "right" }}>{call.tokens_out}</span>
            <span
              style={{
                fontSize: "0.75rem",
                color: "rgb(var(--faint))",
                textAlign: "right",
              }}
            >
              {datum}
              <span
                style={{
                  marginLeft: "0.5rem",
                  display: "inline-block",
                  transition: "transform 0.15s",
                  transform: open ? "rotate(180deg)" : "none",
                }}
              >
                ▾
              </span>
            </span>
          </button>

          {open && (
            <div
              style={{
                padding: "0.75rem 1rem 1rem",
                background: "rgb(var(--surface))",
                borderBottom: "1px solid rgb(var(--line))",
                display: "grid",
                gap: "1rem",
              }}
            >
              {(
                [
                  ["System-prompt", call.system_prompt],
                  ["User-prompt", call.user_prompt],
                  ["Ruwe respons", call.ruwe_respons],
                ] as [string, string][]
              ).map(([label, inhoud]) => (
                <div key={label}>
                  <p
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: "rgb(var(--muted))",
                      marginBottom: "0.25rem",
                    }}
                  >
                    {label}
                  </p>
                  <pre
                    style={{
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      fontSize: "0.75rem",
                      fontFamily: "monospace",
                      padding: "0.625rem",
                      background: "rgb(var(--bg))",
                      border: "1px solid rgb(var(--line))",
                      borderRadius: "4px",
                      maxHeight: "16rem",
                      overflow: "auto",
                      color: "rgb(var(--ink))",
                    }}
                  >
                    {inhoud}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

/** LLM-calls-log-tab van het instellingenvenster. Verplaatst uit
 *  `app/beheer/llm-calls/page.tsx` (werkwijze-story 042), inhoud ongewijzigd. */
export function LlmCallsPanel() {
  const [analyseId, setAnalyseId] = useState("");
  const [calls, setCalls] = useState<LlmCallRead[] | null>(null);
  const [laden, setLaden] = useState(false);
  const [fout, setFout] = useState<string | null>(null);

  async function laadCalls(e: React.FormEvent) {
    e.preventDefault();
    if (!analyseId.trim()) return;
    setLaden(true);
    setFout(null);
    setCalls(null);
    try {
      const data = (await beheerFetch(
        `/api/projecten/${analyseId.trim()}/llm-calls`,
      )) as LlmCallRead[];
      setCalls(data);
    } catch (err) {
      setFout(err instanceof Error ? err.message : "Fout bij ophalen.");
    } finally {
      setLaden(false);
    }
  }

  return (
    <div>
      <h1
        style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" }}
      >
        LLM-calls log
      </h1>

      <SectieHeader
        titel="Vastgelegde LLM-aanroepen"
        subtitel="Voer een analyse-id in om de bijbehorende LLM-aanroepen te bekijken."
      />

      <form
        onSubmit={(e) => void laadCalls(e)}
        style={{
          display: "flex",
          gap: "0.75rem",
          alignItems: "flex-end",
          marginBottom: "1.5rem",
        }}
      >
        <div style={{ flex: 1, maxWidth: "28rem" }}>
          <label
            className="field-label"
            htmlFor="analyse-id"
            style={{ display: "block", marginBottom: "0.25rem" }}
          >
            Analyse-id (UUID)
          </label>
          <input
            id="analyse-id"
            className="field-input"
            value={analyseId}
            onChange={(e) => setAnalyseId(e.target.value)}
            placeholder="bijv. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
            style={{ width: "100%" }}
            required
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={laden}>
          {laden ? "Laden…" : "Toon calls"}
        </button>
      </form>

      {fout && (
        <div className="melding melding-fout" style={{ marginBottom: "1rem" }}>
          <p role="alert">{fout}</p>
        </div>
      )}

      {calls !== null && (
        <>
          {calls.length === 0 ? (
            <p
              style={{
                fontSize: "0.875rem",
                color: "rgb(var(--muted))",
                padding: "1rem",
                border: "1px solid rgb(var(--line))",
                borderRadius: "6px",
              }}
            >
              Geen LLM-calls gevonden voor dit analyse-id. Mogelijk is capture
              uitgeschakeld of is het id onbekend.
            </p>
          ) : (
            <div
              style={{
                border: "1px solid rgb(var(--line))",
                borderRadius: "6px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "8rem 8rem 10rem 5rem 5rem 1fr",
                  gap: "0.5rem",
                  padding: "0.5rem 1rem",
                  background: "rgb(var(--surface))",
                  borderBottom: "1px solid rgb(var(--line))",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: "rgb(var(--muted))",
                }}
              >
                <span>Activiteit</span>
                <span>Bron</span>
                <span>Model</span>
                <span style={{ textAlign: "right" }}>Tokens in</span>
                <span style={{ textAlign: "right" }}>Tokens uit</span>
                <span style={{ textAlign: "right" }}>Aangemaakt</span>
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <tbody>
                  {calls.map((call) => (
                    <CallRij key={call.id} call={call} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p
            style={{
              marginTop: "0.5rem",
              fontSize: "0.75rem",
              color: "rgb(var(--faint))",
            }}
          >
            {calls.length} call{calls.length !== 1 ? "s" : ""} gevonden.
          </p>
        </>
      )}
    </div>
  );
}
