"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "@/generated/types";
import { NieuwDocumentFormulier } from "@/components/annotatie/NieuwDocumentFormulier";
import { VerwijderKnop } from "@/components/projecten/VerwijderKnop";
import { formatDatum } from "@/lib/datum";

type AnnotatieDocument = components["schemas"]["AnnotatieDocument"];
type DocumentStatus = components["schemas"]["DocumentStatus"];

function statusLabel(s: DocumentStatus): string {
  switch (s) {
    case "voorgesteld":
      return "Voorgesteld";
    case "gedeeltelijk_gereviewd":
      return "Gedeeltelijk gereviewd";
    case "klaar":
      return "Klaar";
  }
}

function statusKleur(s: DocumentStatus): string {
  switch (s) {
    case "klaar":
      return "rgb(var(--succes))";
    case "gedeeltelijk_gereviewd":
      return "rgb(var(--info))";
    default:
      return "rgb(var(--muted))";
  }
}

export default function WerkplekPagina() {
  const router = useRouter();
  const [documenten, setDocumenten] = useState<AnnotatieDocument[] | null>(
    null,
  );
  const [fout, setFout] = useState<string | null>(null);
  const [toonFormulier, setToonFormulier] = useState(false);
  const laden = documenten === null && fout === null;

  useEffect(() => {
    async function laad() {
      setFout(null);
      try {
        const res = await fetch("/api/annotatie/documenten");
        if (res.status === 401) {
          router.push("/login");
          return;
        }
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        setDocumenten((await res.json()) as AnnotatieDocument[]);
      } catch (err) {
        setFout(
          err instanceof Error
            ? err.message
            : "Fout bij het ophalen van documenten.",
        );
      }
    }
    void laad();
  }, [router]);

  async function verwijder(slug: string) {
    const res = await fetch(`/api/annotatie/documenten/${slug}`, {
      method: "DELETE",
    });
    if (res.status === 401) {
      router.push("/login");
      return;
    }
    if (res.ok || res.status === 204) {
      setDocumenten((prev) => prev?.filter((d) => d.slug !== slug) ?? null);
    }
  }

  function naDokumentAangemaakt(doc: AnnotatieDocument) {
    setToonFormulier(false);
    setDocumenten((prev) => (prev ? [doc, ...prev] : [doc]));
  }

  return (
    <div>
      {/* Hero */}
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
              Annotatie
            </p>
            <h1
              style={{
                fontSize: "1.75rem",
                fontWeight: 700,
                color: "white",
                margin: 0,
              }}
            >
              Werkplek
            </h1>
            <p
              style={{
                fontSize: "0.875rem",
                color: "rgba(255,255,255,0.85)",
                marginTop: "0.5rem",
                maxWidth: "36rem",
              }}
            >
              Bekijk en beheer annotatie-documenten. Keur per element de
              voorgestelde JAS-elementen goed, bewerk of wijs ze af.
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
              onClick={() => setToonFormulier(true)}
            >
              + Nieuw document
            </button>
          </div>
        </div>
      </div>

      {/* Aanmaakformulier */}
      {toonFormulier && (
        <div
          className="card"
          style={{ marginBottom: "1.5rem", maxWidth: "36rem" }}
        >
          <h2
            style={{
              fontSize: "1rem",
              fontWeight: 600,
              marginBottom: "1rem",
              color: "rgb(var(--lint))",
            }}
          >
            Nieuw annotatie-document
          </h2>
          <NieuwDocumentFormulier
            onAangemaakt={naDokumentAangemaakt}
            onAnnuleren={() => setToonFormulier(false)}
          />
        </div>
      )}

      {/* Fout */}
      {fout && (
        <div className="melding melding-fout" style={{ marginBottom: "1rem" }}>
          <p role="alert">{fout}</p>
        </div>
      )}

      {/* Laden */}
      {laden && (
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Laden…
        </p>
      )}

      {/* Lege staat */}
      {documenten !== null && documenten.length === 0 && (
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
          Nog geen annotatie-documenten aangemaakt.
          <br />
          <button
            className="btn btn-primary"
            style={{ marginTop: "1rem" }}
            onClick={() => setToonFormulier(true)}
          >
            + Eerste document aanmaken
          </button>
        </div>
      )}

      {/* Documentenlijst */}
      {documenten !== null && documenten.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="tabel">
              <thead>
                <tr>
                  <th>Werkgebied</th>
                  <th>Bron</th>
                  <th>Status</th>
                  <th>Aangemaakt</th>
                  <th style={{ textAlign: "right" }}></th>
                </tr>
              </thead>
              <tbody>
                {documenten.map((doc) => (
                  <tr
                    key={doc.slug}
                    style={{ cursor: "pointer" }}
                    onClick={() => router.push(`/werkplek/${doc.slug}`)}
                  >
                    <td>
                      <span style={{ fontWeight: 500 }}>{doc.werkgebied}</span>
                      <span
                        style={{
                          display: "block",
                          fontFamily: "monospace",
                          fontSize: "0.75rem",
                          color: "rgb(var(--faint))",
                          marginTop: "0.1rem",
                        }}
                      >
                        {doc.slug}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: "0.8125rem",
                          color: "rgb(var(--muted))",
                        }}
                      >
                        {doc.bwb_id} art. {doc.artikel}
                        {doc.lid ? ` lid ${doc.lid}` : ""}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "0.375rem",
                          fontSize: "0.8125rem",
                        }}
                      >
                        <span
                          style={{
                            width: "8px",
                            height: "8px",
                            borderRadius: "50%",
                            background: statusKleur(doc.status),
                            flexShrink: 0,
                          }}
                        />
                        {statusLabel(doc.status)}
                      </span>
                    </td>
                    <td
                      style={{
                        color: "rgb(var(--muted))",
                        fontSize: "0.8125rem",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {formatDatum(doc.aangemaakt)}
                    </td>
                    <td
                      style={{ textAlign: "right" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <VerwijderKnop
                        compact
                        onClick={() => void verwijder(doc.slug)}
                      />
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
