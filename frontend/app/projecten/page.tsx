"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "@/generated/types";
import { StatusDot } from "@/components/projecten/StatusPill";
import { VerwijderKnop } from "@/components/projecten/VerwijderKnop";

type AnalyseOverzicht = components["schemas"]["AnalyseOverzicht"];

// ─── Hulpfuncties ─────────────────────────────────────────────────────────────

function bronnenSamenvatting(bronnen: AnalyseOverzicht["bronnen"]): string {
  if (bronnen.length === 0) return "—";
  const eerste = bronnen[0];
  const lidSuffix = eerste.lid ? ` lid ${eerste.lid}` : "";
  const rest = bronnen.length > 1 ? ` +${bronnen.length - 1}` : "";
  return `${eerste.bwb_id} art. ${eerste.artikel}${lidSuffix}${rest}`;
}

function formatDatum(iso: string): string {
  return new Date(iso).toLocaleString("nl-NL", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ─── Hoofd-component ──────────────────────────────────────────────────────────

export default function ProjectenPagina() {
  const router = useRouter();
  const [analyses, setAnalyses] = useState<AnalyseOverzicht[] | null>(null);
  const [fout, setFout] = useState<string | null>(null);
  const laden = analyses === null && fout === null;

  // Filters
  const [zoek, setZoek] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [wetFilter, setWetFilter] = useState("");
  const [sortering, setSortering] = useState<"nieuwste" | "oudste">("nieuwste");

  useEffect(() => {
    async function laad() {
      setFout(null);
      try {
        const res = await fetch("/api/projecten");
        if (res.status === 401) {
          router.push("/login");
          return;
        }
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        setAnalyses((await res.json()) as AnalyseOverzicht[]);
      } catch (err) {
        setFout(
          err instanceof Error
            ? err.message
            : "Fout bij het ophalen van analyses.",
        );
      }
    }
    void laad();
  }, [router]);

  async function verwijder(id: string) {
    const res = await fetch(`/api/projecten/${id}`, { method: "DELETE" });
    if (res.ok || res.status === 204) {
      setAnalyses((prev) => prev?.filter((a) => a.id !== id) ?? null);
    }
  }

  const gefilterd = useMemo(
    () =>
      (analyses ?? [])
        .filter((a) => {
          if (statusFilter && a.status !== statusFilter) return false;
          if (wetFilter && !a.bronnen.some((b) => b.bwb_id === wetFilter))
            return false;
          if (zoek) {
            const q = zoek.toLowerCase();
            if (
              !a.naam.toLowerCase().includes(q) &&
              !a.id.toLowerCase().includes(q) &&
              !a.bronnen.some(
                (b) =>
                  b.bwb_id.toLowerCase().includes(q) ||
                  b.artikel.toLowerCase().includes(q),
              )
            )
              return false;
          }
          return true;
        })
        .sort((a, b) =>
          sortering === "nieuwste"
            ? b.bijgewerkt.localeCompare(a.bijgewerkt)
            : a.bijgewerkt.localeCompare(b.bijgewerkt),
        ),
    [analyses, statusFilter, wetFilter, zoek, sortering],
  );

  // Unieke wetten voor de wet-filter-dropdown
  const wetten = useMemo(
    () =>
      Array.from(
        new Map(
          (analyses ?? [])
            .flatMap((a) => a.bronnen)
            .map((b) => [b.bwb_id, b.bwb_id]),
        ).values(),
      ),
    [analyses],
  );

  return (
    <div>
      {/* Hero-banner */}
      <div
        style={{
          background: "rgb(var(--communicatiekleur))",
          borderRadius: "8px",
          padding: "2rem 2.5rem",
          marginBottom: "1.5rem",
        }}
      >
        <div
          style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}
        >
          <div>
            <p
              style={{
                fontSize: "0.75rem",
                fontWeight: 600,
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                color: "rgba(255,255,255,0.7)",
                marginBottom: "0.5rem",
              }}
            >
              Juridisch Analyseschema
            </p>
            <h1
              style={{
                fontSize: "1.75rem",
                fontWeight: 700,
                color: "white",
                margin: 0,
              }}
            >
              Analyses
            </h1>
            <p
              style={{
                fontSize: "0.875rem",
                color: "rgba(255,255,255,0.85)",
                marginTop: "0.5rem",
                maxWidth: "36rem",
              }}
            >
              Elke analyse duidt een werkgebied — één of meer bronnen
              (wetsartikel of lid) — brongetrouw volgens het Juridisch
              Analyseschema.
            </p>
          </div>
          <div>
            <button
              className="btn"
              style={{
                background: "white",
                color: "rgb(var(--lint))",
                fontWeight: 600,
                border: "none",
              }}
              onClick={() => router.push("/projecten/nieuw")}
            >
              Nieuwe analyse
            </button>
          </div>
        </div>
      </div>

      {/* Fout */}
      {fout && (
        <div className="melding melding-fout" style={{ marginBottom: "1rem" }}>
          <p role="alert">{fout}</p>
        </div>
      )}

      {/* Filterbar */}
      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          flexWrap: "wrap",
          marginBottom: "1rem",
          alignItems: "center",
        }}
      >
        <input
          className="field-input"
          style={{ flex: "1 1 16rem", minWidth: "14rem" }}
          type="search"
          placeholder="Zoek op naam, BWB-id of artikel..."
          value={zoek}
          onChange={(e) => setZoek(e.target.value)}
        />
        <select
          className="field-input"
          style={{ width: "13rem", flex: "0 0 auto" }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">Alle statussen</option>
          <option value="wachtrij">In wachtrij</option>
          <option value="actief">Actief</option>
          <option value="review">Wacht op review</option>
          <option value="klaar">Klaar</option>
          <option value="fout">Fout</option>
        </select>
        <select
          className="field-input"
          style={{ width: "14rem", flex: "0 0 auto" }}
          value={wetFilter}
          onChange={(e) => setWetFilter(e.target.value)}
        >
          <option value="">Alle wetten</option>
          {wetten.map((bwb_id) => (
            <option key={bwb_id} value={bwb_id}>
              {bwb_id}
            </option>
          ))}
        </select>
        <select
          className="field-input"
          style={{ width: "10rem", flex: "0 0 auto" }}
          value={sortering}
          onChange={(e) =>
            setSortering(e.target.value as "nieuwste" | "oudste")
          }
        >
          <option value="nieuwste">Nieuwste eerst</option>
          <option value="oudste">Oudste eerst</option>
        </select>
      </div>

      {/* Laden */}
      {laden && (
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Laden…
        </p>
      )}

      {/* Lege staat */}
      {!laden && analyses !== null && analyses.length === 0 && (
        <div
          style={{
            padding: "2.5rem",
            textAlign: "center",
            color: "rgb(var(--muted))",
            fontSize: "0.875rem",
            background: "rgb(var(--surface))",
            border: "1px solid rgb(var(--line))",
            borderRadius: "8px",
          }}
        >
          Nog geen analyses aangemaakt.
          <br />
          <button
            className="btn btn-primary"
            style={{ marginTop: "1rem" }}
            onClick={() => router.push("/projecten/nieuw")}
          >
            + Eerste analyse starten
          </button>
        </div>
      )}

      {/* Filter levert niets op */}
      {!laden &&
        analyses !== null &&
        analyses.length > 0 &&
        gefilterd.length === 0 && (
          <div
            style={{
              padding: "2.5rem",
              textAlign: "center",
              color: "rgb(var(--muted))",
              fontSize: "0.875rem",
              background: "rgb(var(--surface))",
              border: "1px solid rgb(var(--line))",
              borderRadius: "8px",
            }}
          >
            Geen analyses gevonden met deze filters.
          </div>
        )}

      {/* Tabel */}
      {!laden && gefilterd.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="tabel">
              <thead>
                <tr>
                  <th>Naam</th>
                  <th>Bron</th>
                  <th>Status</th>
                  <th>Bijgewerkt</th>
                  <th style={{ textAlign: "right" }}></th>
                </tr>
              </thead>
              <tbody>
                {gefilterd.map((a) => (
                  <tr
                    key={a.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => router.push(`/projecten/${a.id}`)}
                  >
                    <td>
                      <span style={{ fontWeight: 500 }}>{a.naam}</span>
                      <span
                        style={{
                          display: "block",
                          fontFamily: "monospace",
                          fontSize: "0.75rem",
                          color: "rgb(var(--faint))",
                          marginTop: "0.1rem",
                        }}
                      >
                        {a.id.slice(0, 8)}…
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: "0.8125rem",
                          color: "rgb(var(--muted))",
                        }}
                      >
                        {bronnenSamenvatting(a.bronnen)}
                      </span>
                    </td>
                    <td>
                      <StatusDot status={a.status} />
                    </td>
                    <td
                      style={{
                        color: "rgb(var(--muted))",
                        fontSize: "0.8125rem",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {formatDatum(a.bijgewerkt)}
                    </td>
                    <td
                      style={{ textAlign: "right" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <span style={{ display: "inline-flex", gap: "0.375rem" }}>
                        <button
                          className="btn btn-secondary"
                          style={{
                            fontSize: "0.75rem",
                            padding: "0.25rem 0.625rem",
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            router.push(`/projecten/${a.id}`);
                          }}
                        >
                          Bekijk →
                        </button>
                        <VerwijderKnop
                          compact
                          onClick={() => verwijder(a.id)}
                        />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
