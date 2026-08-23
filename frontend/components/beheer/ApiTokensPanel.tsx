"use client";

import React, { useEffect, useState } from "react";
import { SectieHeader } from "@/components/beheer/SectieHeader";
import { beheerFetch, BeheerFetchFout } from "@/lib/beheer-fetch";

// ---- Types -------------------------------------------------------------------

interface ApiTokenRead {
  id: string;
  label: string;
  token_prefix: string;
  scope: string;
  actief: boolean;
  aangemaakt_door: string;
  aangemaakt_op: string;
  laatste_gebruik: string | null;
}

interface ApiTokenAangemaakt extends ApiTokenRead {
  token: string;
}

// ---- Hulpfuncties ------------------------------------------------------------

function datumLabel(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("nl-NL", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ---- Nieuw-token-modal -------------------------------------------------------

function NieuwTokenModal({
  token,
  onSluiten,
}: {
  token: string;
  onSluiten: () => void;
}) {
  const [gekopieerd, setGekopieerd] = useState(false);

  async function kopieer() {
    await navigator.clipboard.writeText(token);
    setGekopieerd(true);
    setTimeout(() => setGekopieerd(false), 2000);
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Nieuw API-token"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0,0,0,0.4)",
        padding: "1rem",
      }}
    >
      <div
        className="card"
        style={{ maxWidth: "36rem", width: "100%", padding: "1.5rem" }}
      >
        <h2
          style={{
            fontSize: "1.125rem",
            fontWeight: 600,
            marginBottom: "0.5rem",
          }}
        >
          Nieuw API-token aangemaakt
        </h2>
        <p
          style={{
            fontSize: "0.875rem",
            color: "rgb(var(--fout))",
            marginBottom: "1rem",
            fontWeight: 500,
          }}
        >
          Sla dit token op — het is maar één keer zichtbaar:
        </p>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginBottom: "1.25rem",
          }}
        >
          <code
            style={{
              flex: 1,
              padding: "0.625rem 0.875rem",
              borderRadius: "4px",
              background: "rgb(var(--surface))",
              border: "1px solid rgb(var(--line))",
              fontFamily: "monospace",
              fontSize: "0.8125rem",
              wordBreak: "break-all",
              color: "rgb(var(--ink))",
            }}
          >
            {token}
          </code>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ flexShrink: 0, fontSize: "0.8125rem" }}
            onClick={() => void kopieer()}
          >
            {gekopieerd ? "Gekopieerd" : "Kopieer"}
          </button>
        </div>
        <button type="button" className="btn btn-primary" onClick={onSluiten}>
          Ik heb het token opgeslagen
        </button>
      </div>
    </div>
  );
}

// ---- Hoofdcomponent ------------------------------------------------------------

/** API-tokens-tab van het instellingenvenster. Verplaatst uit
 *  `app/beheer/api-tokens/page.tsx` (werkwijze-story 042), inhoud ongewijzigd. */
export function ApiTokensPanel() {
  const [tokens, setTokens] = useState<ApiTokenRead[] | null>(null);
  const [laden, setLaden] = useState(true);
  const [fout, setFout] = useState<string | null>(null);

  // Formulier
  const [label, setLabel] = useState("");
  const [aanmaakenBezig, setAanmaakenBezig] = useState(false);
  const [formulierFout, setFormulierFout] = useState<string | null>(null);

  // Eenmalig token
  const [nieuwToken, setNieuwToken] = useState<string | null>(null);

  // Intrekken
  const [intrekBezig, setIntrekBezig] = useState<string | null>(null);

  useEffect(() => {
    beheerFetch("/api/admin/api-tokens")
      .then((data) => setTokens(data as ApiTokenRead[]))
      .catch((err) =>
        setFout(
          err instanceof Error ? err.message : "Kon API-tokens niet ophalen.",
        ),
      )
      .finally(() => setLaden(false));
  }, []);

  async function tokenAanmaken(e: React.FormEvent) {
    e.preventDefault();
    setAanmaakenBezig(true);
    setFormulierFout(null);
    try {
      const aangemaakt = (await beheerFetch("/api/admin/api-tokens", {
        method: "POST",
        body: JSON.stringify({ label }),
      })) as ApiTokenAangemaakt;

      const { token, ...rest } = aangemaakt;
      setTokens((prev) => (prev ? [rest, ...prev] : [rest]));
      setLabel("");
      setNieuwToken(token);
    } catch (err) {
      setFormulierFout(
        err instanceof Error ? err.message : "Fout bij aanmaken.",
      );
    } finally {
      setAanmaakenBezig(false);
    }
  }

  async function tokenIntrekken(id: string) {
    setIntrekBezig(id);
    setFout(null);
    try {
      await beheerFetch(`/api/admin/api-tokens/${id}`, { method: "DELETE" });
      setTokens((prev) => prev?.filter((t) => t.id !== id) ?? null);
    } catch (err) {
      if (err instanceof BeheerFetchFout && err.status === 404) {
        setFout("Token niet gevonden of al ingetrokken.");
      } else {
        setFout(err instanceof Error ? err.message : "Fout bij intrekken.");
      }
    } finally {
      setIntrekBezig(null);
    }
  }

  return (
    <div style={{ maxWidth: "64rem", margin: "0 auto", width: "100%" }}>
      {nieuwToken && (
        <NieuwTokenModal
          token={nieuwToken}
          onSluiten={() => setNieuwToken(null)}
        />
      )}

      <div style={{ marginBottom: "1.5rem" }}>
        <h1
          style={{
            fontSize: "1.875rem",
            fontWeight: 600,
            color: "rgb(var(--lint))",
          }}
        >
          API-tokens
        </h1>
        <p
          style={{
            marginTop: "0.25rem",
            fontSize: "0.875rem",
            color: "rgb(var(--muted))",
          }}
        >
          Programmatische toegangstokens voor externe tools zoals de Admin-MCP.
          Het volledige token is alleen bij aanmaken zichtbaar.
        </p>
      </div>

      {/* ---- Nieuw token aanmaken ---- */}
      <section style={{ marginBottom: "2rem" }}>
        <SectieHeader titel="Nieuw token aanmaken" />
        <form
          onSubmit={(e) => void tokenAanmaken(e)}
          style={{
            display: "flex",
            gap: "0.75rem",
            alignItems: "flex-end",
            flexWrap: "wrap",
          }}
        >
          <div style={{ flex: 1, minWidth: "16rem" }}>
            <label className="field-label" htmlFor="label">
              Label{" "}
              <span style={{ color: "rgb(var(--faint))", fontWeight: 400 }}>
                (optioneel)
              </span>
            </label>
            <input
              id="label"
              className="field-input"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="bijv. admin-mcp"
              maxLength={128}
              style={{ marginTop: "0.25rem" }}
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={aanmaakenBezig}
          >
            {aanmaakenBezig ? "Aanmaken…" : "Nieuw token aanmaken"}
          </button>
        </form>
        {formulierFout && (
          <div
            role="alert"
            className="melding melding-fout"
            style={{ marginTop: "0.75rem" }}
          >
            <p>{formulierFout}</p>
          </div>
        )}
      </section>

      {/* ---- Tokenlijst ---- */}
      <section>
        <SectieHeader titel="Actieve tokens" />

        {fout && (
          <div
            className="melding melding-fout"
            role="alert"
            style={{ marginBottom: "1rem" }}
          >
            <p>{fout}</p>
          </div>
        )}

        {laden && (
          <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
            Laden…
          </p>
        )}

        {!laden && tokens !== null && tokens.length === 0 && (
          <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
            Nog geen actieve tokens.
          </p>
        )}

        {!laden && tokens && tokens.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.875rem",
              }}
            >
              <thead>
                <tr
                  style={{
                    borderBottom: "1px solid rgb(var(--line))",
                    textAlign: "left",
                  }}
                >
                  {[
                    "Label",
                    "Prefix",
                    "Aangemaakt door",
                    "Aangemaakt op",
                    "Laatste gebruik",
                    "",
                  ].map((kop) => (
                    <th
                      key={kop}
                      style={{
                        padding: "0.5rem 0.75rem",
                        fontWeight: 600,
                        color: "rgb(var(--muted))",
                        fontSize: "0.75rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {kop}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tokens.map((t) => (
                  <tr
                    key={t.id}
                    style={{ borderBottom: "1px solid rgb(var(--line))" }}
                  >
                    <td style={{ padding: "0.625rem 0.75rem" }}>
                      {t.label || (
                        <span style={{ color: "rgb(var(--faint))" }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: "0.625rem 0.75rem" }}>
                      <code
                        style={{
                          fontFamily: "monospace",
                          fontSize: "0.8125rem",
                          padding: "0.125rem 0.375rem",
                          borderRadius: "3px",
                          background: "rgb(var(--surface))",
                          border: "1px solid rgb(var(--line))",
                        }}
                      >
                        {t.token_prefix}…
                      </code>
                    </td>
                    <td
                      style={{
                        padding: "0.625rem 0.75rem",
                        color: "rgb(var(--muted))",
                      }}
                    >
                      {t.aangemaakt_door || "—"}
                    </td>
                    <td
                      style={{
                        padding: "0.625rem 0.75rem",
                        color: "rgb(var(--muted))",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {datumLabel(t.aangemaakt_op)}
                    </td>
                    <td
                      style={{
                        padding: "0.625rem 0.75rem",
                        color: "rgb(var(--faint))",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {datumLabel(t.laatste_gebruik)}
                    </td>
                    <td
                      style={{
                        padding: "0.625rem 0.75rem",
                        textAlign: "right",
                      }}
                    >
                      <button
                        type="button"
                        className="btn btn-danger"
                        style={{ fontSize: "0.8125rem" }}
                        disabled={intrekBezig === t.id}
                        onClick={() => void tokenIntrekken(t.id)}
                      >
                        {intrekBezig === t.id ? "Bezig…" : "Intrekken"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
