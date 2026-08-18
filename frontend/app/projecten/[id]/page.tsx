"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "@/generated/types";
import { StatusDot } from "@/components/projecten/StatusPill";
import { VerwijderKnop } from "@/components/projecten/VerwijderKnop";

type AnalyseDetail = components["schemas"]["AnalyseDetail"];
type AnalyseStatus = AnalyseDetail["status"];

// SSE-event dat de API stuurt
type SsePayload = {
  status?: AnalyseStatus;
  huidige_fase?: string | null;
  foutmelding?: string | null;
  fout?: string;
};

const LOPENDE_STATUSSEN = new Set<AnalyseStatus>([
  "wachtrij",
  "actief",
  "review",
]);
const MAX_POGINGEN = 3;

// ─── Hoofd-component ──────────────────────────────────────────────────────────

export default function AnalyseDetailPagina({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const [id, setId] = useState<string | null>(null);
  const [analyse, setAnalyse] = useState<AnalyseDetail | null>(null);
  const [foutBericht, setFoutBericht] = useState<string | null>(null);
  const laden = analyse === null && foutBericht === null;

  // SSE-reconnect: verhoog de teller om een herverbinding te triggeren
  const [herverbindCounter, setHerverbindCounter] = useState(0);
  const herverbindPogingen = useRef(0);
  const esRef = useRef<EventSource | null>(null);

  // Resolve async params (Next.js 16)
  useEffect(() => {
    params.then(({ id: resolvedId }) => setId(resolvedId));
  }, [params]);

  // Initieel laden van de analyse
  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function laden_() {
      setFoutBericht(null);
      try {
        const res = await fetch(`/api/projecten/${id}`);
        if (cancelled) return;
        if (res.status === 401) {
          router.push("/login");
          return;
        }
        if (res.status === 404) {
          router.push("/projecten");
          return;
        }
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        setAnalyse((await res.json()) as AnalyseDetail);
      } catch (err) {
        if (!cancelled)
          setFoutBericht(
            err instanceof Error
              ? err.message
              : "Fout bij het ophalen van de analyse.",
          );
      }
    }

    void laden_();
    return () => {
      cancelled = true;
    };
  }, [id, router]);

  // SSE-stroom — herstart bij herverbindCounter-toename of status-change.
  // Afhankelijkheid is `analyse?.status` (niet `analyse`) om te voorkomen dat de stroom
  // bij elke status-update via SSE opnieuw wordt opgebouwd.
  const analyseStatus = analyse?.status;
  useEffect(() => {
    if (!id || !analyseStatus || !LOPENDE_STATUSSEN.has(analyseStatus)) return;

    const es = new EventSource(`/api/projecten/${id}/events`);
    esRef.current = es;

    es.onmessage = (evt: MessageEvent<string>) => {
      try {
        const data = JSON.parse(evt.data) as SsePayload;
        if ("fout" in data) {
          es.close();
          return;
        }
        herverbindPogingen.current = 0;
        if (data.status) {
          setAnalyse((prev) =>
            prev
              ? {
                  ...prev,
                  status: data.status!,
                  huidige_fase: data.huidige_fase ?? prev.huidige_fase,
                  foutmelding: data.foutmelding ?? prev.foutmelding,
                }
              : prev,
          );
          if (data.status === "klaar" || data.status === "fout") {
            es.close();
          }
        }
      } catch {
        // JSON-parsefout — negeer
      }
    };

    es.onerror = () => {
      es.close();
      herverbindPogingen.current += 1;
      if (herverbindPogingen.current <= MAX_POGINGEN) {
        const vertraging = Math.pow(2, herverbindPogingen.current) * 1000;
        setTimeout(() => setHerverbindCounter((c) => c + 1), vertraging);
      }
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [id, analyseStatus, herverbindCounter]);

  async function verwijder() {
    if (!id) return;
    const res = await fetch(`/api/projecten/${id}`, { method: "DELETE" });
    if (res.ok || res.status === 204) {
      esRef.current?.close();
      router.push("/projecten");
    }
  }

  if (laden) {
    return (
      <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Laden…</p>
    );
  }

  if (foutBericht) {
    return (
      <div className="melding melding-fout">
        <p role="alert">{foutBericht}</p>
      </div>
    );
  }

  if (!analyse) return null;

  const isLopend = LOPENDE_STATUSSEN.has(analyse.status);

  return (
    <div style={{ maxWidth: "40rem" }}>
      <button
        className="btn btn-secondary"
        style={{ fontSize: "0.8125rem", marginBottom: "1rem" }}
        onClick={() => router.push("/projecten")}
      >
        ← Terug naar analyses
      </button>

      <h2
        style={{
          fontSize: "1.125rem",
          fontWeight: 600,
          marginBottom: "0.5rem",
          color: "rgb(var(--lint))",
        }}
      >
        {analyse.naam}
      </h2>
      <div style={{ marginBottom: "1.5rem" }}>
        <StatusDot status={analyse.status} />
      </div>

      {/* Lopende analyse — voortgang */}
      {isLopend && (
        <div
          className="card"
          style={{
            marginBottom: "1.25rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.875rem",
          }}
        >
          <div
            style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}
          >
            <div
              style={{
                width: "16px",
                height: "16px",
                borderRadius: "50%",
                border: "2px solid rgb(var(--info))",
                borderTopColor: "transparent",
                animation: "spin 1s linear infinite",
                flexShrink: 0,
              }}
            />
            <span style={{ fontSize: "0.875rem", fontWeight: 500 }}>
              {analyse.status === "review"
                ? "Wacht op review"
                : "Analyse loopt"}
              {analyse.huidige_fase && (
                <span
                  style={{
                    fontWeight: 400,
                    color: "rgb(var(--muted))",
                    marginLeft: "0.375rem",
                  }}
                >
                  — {analyse.huidige_fase}
                </span>
              )}
            </span>
          </div>
          {analyse.status === "actief" && (
            <div
              style={{
                height: "6px",
                background: "rgb(var(--line))",
                borderRadius: "99px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: "60%",
                  background: "rgb(var(--info))",
                  borderRadius: "99px",
                  animation: "pulse-bar 2s ease-in-out infinite",
                }}
              />
            </div>
          )}
          <p style={{ fontSize: "0.8125rem", color: "rgb(var(--muted))" }}>
            Live updates via SSE — de pagina hoeft niet te worden herladen.
          </p>
        </div>
      )}

      {/* Klaar */}
      {analyse.status === "klaar" && (
        <div
          className="melding"
          style={{
            background: "rgb(var(--succes) / 0.1)",
            border: "1px solid rgb(var(--succes))",
            marginBottom: "1.25rem",
          }}
        >
          De analyse is succesvol afgerond.
        </div>
      )}

      {/* Fout */}
      {analyse.status === "fout" && (
        <div
          className="melding melding-fout"
          style={{ marginBottom: "1.25rem" }}
        >
          <p role="alert">
            {analyse.foutmelding ??
              "Er is een onbekende fout opgetreden tijdens de analyse."}
          </p>
        </div>
      )}

      {/* Detail-sectie */}
      <div
        className="card"
        style={{ marginBottom: "1.25rem", fontSize: "0.875rem" }}
      >
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "8rem 1fr",
            gap: "0.5rem 1rem",
            color: "rgb(var(--ink))",
          }}
        >
          <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>
            Bronnen
          </dt>
          <dd style={{ margin: 0 }}>
            {analyse.bronnen.map((b, i) => (
              <span key={i} style={{ display: "block" }}>
                {b.bwb_id} art. {b.artikel}
                {b.lid ? ` lid ${b.lid}` : ""}
              </span>
            ))}
          </dd>
          {analyse.model_profiel && (
            <>
              <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>
                Profiel
              </dt>
              <dd style={{ margin: 0 }}>{analyse.model_profiel}</dd>
            </>
          )}
          {analyse.omschrijving && (
            <>
              <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>
                Context
              </dt>
              <dd style={{ margin: 0 }}>{analyse.omschrijving}</dd>
            </>
          )}
          {analyse.analysefocus && (
            <>
              <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>
                Analysefocus
              </dt>
              <dd style={{ margin: 0 }}>{analyse.analysefocus}</dd>
            </>
          )}
          <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>
            Review
          </dt>
          <dd style={{ margin: 0 }}>
            {analyse.human_in_the_loop ? "Aan" : "Uit"}
          </dd>
        </dl>
      </div>

      {/* Acties */}
      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        {analyse.status === "klaar" && (
          <button
            className="btn btn-primary"
            onClick={() => router.push(`/projecten/${analyse.id}/rapport`)}
          >
            Bekijk rapport →
          </button>
        )}
        <VerwijderKnop onClick={verwijder} />
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse-bar {
          0%, 100% { width: 40%; }
          50% { width: 80%; }
        }
      `}</style>
    </div>
  );
}
