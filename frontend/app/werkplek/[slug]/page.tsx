"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "@/generated/types";
import { ElementenKolom } from "@/components/annotatie/ElementenKolom";
import { AuditlogTabblad } from "@/components/annotatie/AuditlogTabblad";

type AnnotatieDocument = components["schemas"]["AnnotatieDocument"];
type AuditRegel = components["schemas"]["AuditRegel"];

type Tabblad = "elementen" | "auditlog";

const TABBLAD_LABELS: Record<Tabblad, string> = {
  elementen: "Elementen",
  auditlog: "Auditlog",
};

export default function WerkplekDetailPagina({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const router = useRouter();
  const [slug, setSlug] = useState<string | null>(null);
  const [document_, setDocument] = useState<AnnotatieDocument | null>(null);
  const [audit, setAudit] = useState<AuditRegel[] | null>(null);
  const [fout, setFout] = useState<string | null>(null);
  const [tabblad, setTabblad] = useState<Tabblad>("elementen");
  const laden = document_ === null && fout === null;

  // Resolve params (Next.js 16)
  useEffect(() => {
    params.then(({ slug: s }) => setSlug(s));
  }, [params]);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;

    async function laad() {
      setFout(null);
      try {
        const res = await fetch(`/api/annotatie/documenten/${slug}`);
        if (cancelled) return;
        if (res.status === 401) {
          router.push("/login");
          return;
        }
        if (res.status === 404) {
          router.push("/werkplek");
          return;
        }
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        setDocument((await res.json()) as AnnotatieDocument);
      } catch (err) {
        if (!cancelled)
          setFout(
            err instanceof Error
              ? err.message
              : "Fout bij het ophalen van het document.",
          );
      }
    }

    void laad();
    return () => {
      cancelled = true;
    };
  }, [slug, router]);

  useEffect(() => {
    if (!slug || tabblad !== "auditlog") return;
    let cancelled = false;

    async function laadAudit() {
      try {
        const res = await fetch(`/api/annotatie/documenten/${slug}/audit`);
        if (cancelled) return;
        if (res.status === 401) {
          router.push("/login");
          return;
        }
        if (res.ok) setAudit((await res.json()) as AuditRegel[]);
      } catch {
        // Auditlog-fout is niet-blokkerend (netwerkfout of ontbrekende data)
      }
    }

    void laadAudit();
    return () => {
      cancelled = true;
    };
  }, [slug, tabblad, router]);

  async function verwijder() {
    if (!slug) return;
    if (!confirm("Dit document en alle elementen verwijderen?")) return;
    const res = await fetch(`/api/annotatie/documenten/${slug}`, {
      method: "DELETE",
    });
    if (res.status === 401) {
      router.push("/login");
      return;
    }
    if (res.ok || res.status === 204) {
      router.push("/werkplek");
    }
  }

  function naBeslissing(bijgewerkt: AnnotatieDocument) {
    setDocument(bijgewerkt);
    // Reset auditlog zodat het opnieuw geladen wordt als je erop klikt
    setAudit(null);
  }

  if (laden) {
    return (
      <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Laden…</p>
    );
  }

  if (fout) {
    return (
      <div className="melding melding-fout">
        <p role="alert">{fout}</p>
      </div>
    );
  }

  if (!document_) return null;

  return (
    <div>
      {/* Terug-knop + koptitel */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
        }}
      >
        <button
          className="btn btn-secondary"
          style={{ fontSize: "0.8125rem" }}
          onClick={() => router.push("/werkplek")}
        >
          ← Werkplek
        </button>
        <div style={{ flex: 1 }}>
          <h2
            style={{
              fontSize: "1.125rem",
              fontWeight: 600,
              color: "rgb(var(--lint))",
              margin: 0,
            }}
          >
            {document_.werkgebied}
          </h2>
          <p
            style={{
              fontSize: "0.8125rem",
              color: "rgb(var(--muted))",
              margin: "0.125rem 0 0",
            }}
          >
            {document_.bwb_id} · art. {document_.artikel}
            {document_.lid ? ` · lid ${document_.lid}` : ""} · {document_.slug}
          </p>
        </div>
        <button
          className="btn btn-secondary"
          style={{ fontSize: "0.8125rem", color: "rgb(var(--gevaar))" }}
          onClick={() => void verwijder()}
        >
          Verwijder document
        </button>
      </div>

      {/* Tabbladen */}
      <div
        style={{
          display: "flex",
          gap: "0",
          borderBottom: "1px solid rgb(var(--line))",
          marginBottom: "1.25rem",
        }}
      >
        {(["elementen", "auditlog"] as Tabblad[]).map((t) => (
          <button
            key={t}
            onClick={() => setTabblad(t)}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "0.875rem",
              fontWeight: tabblad === t ? 600 : 400,
              color: tabblad === t ? "rgb(var(--lint))" : "rgb(var(--muted))",
              background: "none",
              border: "none",
              borderBottom:
                tabblad === t
                  ? "2px solid rgb(var(--lint))"
                  : "2px solid transparent",
              cursor: "pointer",
              marginBottom: "-1px",
            }}
          >
            {TABBLAD_LABELS[t]}
          </button>
        ))}
      </div>

      {/* Inhoud */}
      {tabblad === "elementen" && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "1.5rem",
            alignItems: "start",
          }}
        >
          {/* Linkerkolom: wetsartikeltekst */}
          <div
            className="card"
            style={{
              position: "sticky",
              top: "1rem",
              maxHeight: "calc(100vh - 8rem)",
              overflowY: "auto",
            }}
          >
            <h3
              style={{
                fontSize: "0.875rem",
                fontWeight: 600,
                color: "rgb(var(--lint))",
                marginBottom: "0.75rem",
              }}
            >
              Wetsartikeltekst
            </h3>
            <p
              style={{
                fontSize: "0.8125rem",
                color: "rgb(var(--muted))",
                fontStyle: "italic",
              }}
            >
              {document_.bwb_id} · art. {document_.artikel}
              {document_.lid ? ` · lid ${document_.lid}` : ""}
            </p>
            <p
              style={{
                fontSize: "0.8125rem",
                color: "rgb(var(--faint))",
                marginTop: "0.75rem",
              }}
            >
              De volledige wetsartikeltekst is beschikbaar via de
              Wettenbank-koppeling (nog niet ingebouwd in deze versie).
            </p>
          </div>

          {/* Rechterkolom: elementen */}
          <ElementenKolom
            slug={document_.slug}
            elementen={document_.elementen ?? []}
            onBeslissing={naBeslissing}
            router={router}
          />
        </div>
      )}

      {tabblad === "auditlog" && <AuditlogTabblad audit={audit} />}
    </div>
  );
}
