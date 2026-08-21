"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { components } from "@/generated/types";
import { VerwijderKnop } from "@/components/projecten/VerwijderKnop";

type AnalyseDetail = components["schemas"]["AnalyseDetail"];

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

  useEffect(() => {
    params.then(({ id: resolvedId }) => setId(resolvedId));
  }, [params]);

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
              : "Fout bij het ophalen van het werkgebied.",
          );
      }
    }

    void laden_();
    return () => {
      cancelled = true;
    };
  }, [id, router]);

  async function verwijder() {
    if (!id) return;
    const res = await fetch(`/api/projecten/${id}`, { method: "DELETE" });
    if (res.ok || res.status === 204) {
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

  return (
    <div style={{ maxWidth: "40rem" }}>
      <button
        className="btn btn-secondary"
        style={{ fontSize: "0.8125rem", marginBottom: "1rem" }}
        onClick={() => router.push("/projecten")}
      >
        ← Terug naar werkgebieden
      </button>

      <h2
        style={{
          fontSize: "1.125rem",
          fontWeight: 600,
          marginBottom: "1.5rem",
          color: "rgb(var(--lint))",
        }}
      >
        {analyse.naam}
      </h2>

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
          {analyse.omschrijving && (
            <>
              <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>
                Context
              </dt>
              <dd style={{ margin: 0 }}>{analyse.omschrijving}</dd>
            </>
          )}
        </dl>
      </div>

      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <Link
          className="btn btn-primary"
          href={`/werkplek/${analyse.id}`}
          style={{ fontWeight: 600 }}
        >
          Naar werkplek →
        </Link>
        <VerwijderKnop onClick={verwijder} />
      </div>
    </div>
  );
}
