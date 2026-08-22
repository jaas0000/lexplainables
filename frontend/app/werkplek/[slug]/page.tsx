"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "@/generated/types";
import { ElementenKolom } from "@/components/annotatie/ElementenKolom";
import { AuditlogTabblad } from "@/components/annotatie/AuditlogTabblad";

type AnnotatieDocument = components["schemas"]["AnnotatieDocument"];
type AuditRegel = components["schemas"]["AuditRegel"];
type Wetsartikel = components["schemas"]["Wetsartikel"];
type WetsartikelOnderdeel = components["schemas"]["WetsartikelOnderdeel"];

type Tabblad = "elementen" | "auditlog";

const TABBLAD_LABELS: Record<Tabblad, string> = {
  elementen: "Elementen",
  auditlog: "Auditlog",
};

/** Opsommings-/definitieonderdelen (a/b/c) onder een lid of rechtstreeks onder een artikel
 * zonder leden — zonder dit was een definitieartikel nagenoeg leeg (alleen de inleidende zin
 * van het lid, bv. "Deze wet verstaat onder:", zonder de a-t.-definities zelf). */
function OnderdeelLijst({
  onderdelen,
}: {
  onderdelen: WetsartikelOnderdeel[];
}) {
  if (onderdelen.length === 0) return null;
  return (
    <div
      style={{
        marginTop: "0.375rem",
        marginLeft: "1rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.25rem",
      }}
    >
      {onderdelen.map((onderdeel, i) => (
        <p
          key={onderdeel.nummer ?? i}
          style={{ fontSize: "0.8125rem", lineHeight: 1.6, margin: 0 }}
        >
          {onderdeel.nummer && (
            <strong style={{ marginRight: "0.375rem" }}>
              {onderdeel.nummer}
            </strong>
          )}
          {onderdeel.tekst}
        </p>
      ))}
    </div>
  );
}

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
  const [wetsartikel, setWetsartikel] = useState<Wetsartikel | null>(null);
  const [wetsartikelFout, setWetsartikelFout] = useState<string | null>(null);
  const [wetsartikelLaden, setWetsartikelLaden] = useState(true);
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
    if (!slug) return;
    let cancelled = false;

    async function laadWetsartikel() {
      setWetsartikelLaden(true);
      setWetsartikelFout(null);
      try {
        const res = await fetch(
          `/api/annotatie/documenten/${slug}/wetsartikel`,
        );
        if (cancelled) return;
        if (res.status === 401) {
          router.push("/login");
          return;
        }
        if (res.status === 404) {
          setWetsartikelFout("Wetsartikel niet gevonden in de kennisgraaf.");
          return;
        }
        if (!res.ok) {
          setWetsartikelFout("Wetsartikeltekst tijdelijk niet beschikbaar.");
          return;
        }
        setWetsartikel((await res.json()) as Wetsartikel);
      } catch {
        if (!cancelled)
          setWetsartikelFout("Wetsartikeltekst tijdelijk niet beschikbaar.");
      } finally {
        if (!cancelled) setWetsartikelLaden(false);
      }
    }

    void laadWetsartikel();
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

            {wetsartikelLaden && (
              <p
                style={{
                  fontSize: "0.8125rem",
                  color: "rgb(var(--muted))",
                  marginTop: "0.75rem",
                }}
              >
                Wetsartikeltekst laden…
              </p>
            )}

            {!wetsartikelLaden && wetsartikelFout && (
              <p
                style={{
                  fontSize: "0.8125rem",
                  color: "rgb(var(--faint))",
                  marginTop: "0.75rem",
                }}
              >
                Wetsartikeltekst niet beschikbaar: {wetsartikelFout}
              </p>
            )}

            {!wetsartikelLaden && wetsartikel && (
              <div style={{ marginTop: "0.75rem" }}>
                {wetsartikel.opschrift && (
                  <h4
                    style={{
                      fontSize: "0.875rem",
                      fontWeight: 600,
                      margin: "0 0 0.5rem",
                    }}
                  >
                    {wetsartikel.opschrift}
                  </h4>
                )}
                {wetsartikel.tekst && (
                  <p
                    style={{
                      fontSize: "0.8125rem",
                      lineHeight: 1.6,
                      marginBottom:
                        (wetsartikel.leden ?? []).length > 0 ||
                        (wetsartikel.onderdelen ?? []).length > 0
                          ? "0.5rem"
                          : 0,
                    }}
                  >
                    {wetsartikel.tekst}
                  </p>
                )}

                {(wetsartikel.leden ?? []).length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.5rem",
                    }}
                  >
                    {(wetsartikel.leden ?? []).map((lid, i) => {
                      const gemarkeerd =
                        document_.lid && lid.nummer === document_.lid;
                      return (
                        <div
                          key={lid.nummer ?? i}
                          style={{
                            fontSize: "0.8125rem",
                            lineHeight: 1.6,
                            padding: gemarkeerd ? "0.375rem 0.5rem" : 0,
                            borderLeft: gemarkeerd
                              ? "3px solid rgb(var(--lint))"
                              : "none",
                            background: gemarkeerd
                              ? "rgba(var(--lint), 0.06)"
                              : "transparent",
                          }}
                        >
                          <p style={{ margin: 0 }}>
                            {lid.nummer && (
                              <strong style={{ marginRight: "0.375rem" }}>
                                {lid.nummer}.
                              </strong>
                            )}
                            {lid.tekst}
                          </p>
                          <OnderdeelLijst onderdelen={lid.onderdelen ?? []} />
                        </div>
                      );
                    })}
                  </div>
                )}

                {(wetsartikel.leden ?? []).length === 0 && (
                  <OnderdeelLijst onderdelen={wetsartikel.onderdelen ?? []} />
                )}
              </div>
            )}
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
