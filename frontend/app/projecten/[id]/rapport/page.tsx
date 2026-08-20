"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

// ─── Typen (defensief: alles optioneel) ──────────────────────────────────────

type Bron = {
  bron_id?: string;
  label?: string;
  wet?: string;
  bwbId?: string;
  artikel?: string;
  lid?: string | null;
  versiedatum?: string;
  samenhang?: string;
  markeringen?: Markering[];
};

type Markering = {
  tekst?: string;
  formulering?: string;
};

type Begrip = {
  id?: string;
  naam?: string;
  definitie?: string;
  klasse?: string;
  synoniemen?: string[];
  voorbeeld?: string;
};

type Afleidingsregel = {
  id?: string;
  naam?: string;
  omschrijving?: string;
};

type Werkgebied = {
  naam?: string;
  hoofdvraag?: string;
  omschrijving?: string;
  analysefocus?: string;
};

type Rapport = {
  naam?: string;
  werkgebied?: Werkgebied;
  bronnen?: Bron[];
  begrippen?: Begrip[];
  afleidingsregels?: Afleidingsregel[];
};

// ─── Hulpcomponenten ─────────────────────────────────────────────────────────

function SectieKop({ children }: { children: React.ReactNode }) {
  return (
    <h2
      style={{
        fontSize: "1.125rem",
        fontWeight: 600,
        marginBottom: "0.75rem",
        borderBottom: "1px solid rgb(var(--line))",
        paddingBottom: "0.375rem",
      }}
    >
      {children}
    </h2>
  );
}

function BronKaart({ bron }: { bron: Bron }) {
  const label = bron.label ?? bron.wet ?? "Onbekende bron";
  const artikel = bron.artikel ? ` art. ${bron.artikel}` : "";
  const lid = bron.lid ? ` lid ${bron.lid}` : "";

  return (
    <div
      className="card"
      style={{ marginBottom: "1rem", fontSize: "0.875rem" }}
    >
      <h3
        style={{
          fontSize: "1rem",
          fontWeight: 600,
          marginBottom: "0.5rem",
          color: "rgb(var(--lint))",
        }}
      >
        {label}
        {artikel}
        {lid}
      </h3>
      {bron.versiedatum && (
        <p style={{ color: "rgb(var(--muted))", marginBottom: "0.5rem" }}>
          Versiedatum: {bron.versiedatum}
        </p>
      )}
      {bron.samenhang && (
        <p style={{ marginBottom: "0.5rem" }}>{bron.samenhang}</p>
      )}
      {bron.markeringen && bron.markeringen.length > 0 && (
        <ul style={{ paddingLeft: "1.25rem", margin: 0 }}>
          {bron.markeringen.map((m, i) => (
            <li key={i} style={{ marginBottom: "0.25rem" }}>
              {m.tekst ?? m.formulering ?? ""}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function BegrippenTabel({ begrippen }: { begrippen: Begrip[] }) {
  if (begrippen.length === 0) {
    return (
      <p style={{ color: "rgb(var(--muted))", fontSize: "0.875rem" }}>
        Geen begrippen gevonden.
      </p>
    );
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "0.875rem",
        }}
      >
        <thead>
          <tr>
            {["Naam", "Definitie", "Klasse"].map((h) => (
              <th
                key={h}
                style={{
                  textAlign: "left",
                  padding: "0.5rem 0.75rem",
                  borderBottom: "2px solid rgb(var(--line))",
                  fontWeight: 600,
                  color: "rgb(var(--muted))",
                  whiteSpace: "nowrap",
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {begrippen.map((b, i) => (
            <tr
              key={b.id ?? i}
              style={{ borderBottom: "1px solid rgb(var(--line))" }}
            >
              <td style={{ padding: "0.5rem 0.75rem", fontWeight: 500 }}>
                {b.naam ?? ""}
              </td>
              <td style={{ padding: "0.5rem 0.75rem" }}>{b.definitie ?? ""}</td>
              <td
                style={{
                  padding: "0.5rem 0.75rem",
                  color: "rgb(var(--muted))",
                }}
              >
                {b.klasse ?? ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RegelLijst({ regels }: { regels: Afleidingsregel[] }) {
  if (regels.length === 0) {
    return (
      <p style={{ color: "rgb(var(--muted))", fontSize: "0.875rem" }}>
        Geen afleidingsregels gevonden.
      </p>
    );
  }
  return (
    <ol style={{ paddingLeft: "1.5rem", margin: 0 }}>
      {regels.map((r, i) => (
        <li key={r.id ?? i} style={{ marginBottom: "0.75rem" }}>
          <span style={{ fontWeight: 600 }}>{r.naam ?? `Regel ${i + 1}`}</span>
          {r.omschrijving && (
            <p
              style={{
                margin: "0.25rem 0 0",
                fontSize: "0.875rem",
                color: "rgb(var(--ink))",
              }}
            >
              {r.omschrijving}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}

// ─── Hoofd-component ──────────────────────────────────────────────────────────

export default function RapportPagina({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const [id, setId] = useState<string | null>(null);
  const [rapport, setRapport] = useState<Rapport | null>(null);
  const [foutStatus, setFoutStatus] = useState<number | null>(null);
  const [foutBericht, setFoutBericht] = useState<string | null>(null);
  const laden = rapport === null && foutStatus === null && foutBericht === null;

  // Resolve async params (Next.js 16)
  useEffect(() => {
    params.then(({ id: resolvedId }) => setId(resolvedId));
  }, [params]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function laadRapport() {
      try {
        const res = await fetch(`/api/projecten/${id}/rapport`);
        if (cancelled) return;
        if (res.status === 401) {
          router.push("/login");
          return;
        }
        if (res.status === 404) {
          router.push("/projecten");
          return;
        }
        if (res.status === 409) {
          setFoutStatus(409);
          return;
        }
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        setRapport((await res.json()) as Rapport);
      } catch (err) {
        if (!cancelled)
          setFoutBericht(
            err instanceof Error
              ? err.message
              : "Fout bij het ophalen van het rapport.",
          );
      }
    }

    void laadRapport();
    return () => {
      cancelled = true;
    };
  }, [id, router]);

  // ── Laadstatus ────────────────────────────────────────────────────────────

  if (laden) {
    return (
      <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Laden…</p>
    );
  }

  // ── 409: rapport nog niet beschikbaar ────────────────────────────────────

  if (foutStatus === 409) {
    return (
      <div style={{ maxWidth: "40rem" }}>
        <div className="melding melding-fout" style={{ marginBottom: "1rem" }}>
          <p role="alert">
            Rapport nog niet beschikbaar. De analyse is nog niet afgerond.
          </p>
        </div>
        {id && (
          <Link
            href={`/projecten/${id}`}
            style={{ fontSize: "0.875rem", color: "rgb(var(--info))" }}
          >
            ← Terug naar analyse
          </Link>
        )}
      </div>
    );
  }

  // ── Generieke fout ────────────────────────────────────────────────────────

  if (foutBericht) {
    return (
      <div className="melding melding-fout">
        <p role="alert">{foutBericht}</p>
      </div>
    );
  }

  if (!rapport) return null;

  const bronnen = rapport.bronnen ?? [];
  const begrippen = rapport.begrippen ?? [];
  const regels = rapport.afleidingsregels ?? [];
  const werkgebied = rapport.werkgebied;
  const naam = rapport.naam || "Rapport";

  // ── Volledig rapport ──────────────────────────────────────────────────────

  return (
    <div style={{ maxWidth: "56rem" }}>
      {/* Navigatie */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        {id && (
          <Link
            href={`/projecten/${id}`}
            style={{ fontSize: "0.875rem", color: "rgb(var(--info))" }}
          >
            ← Terug naar analyse
          </Link>
        )}
        {id && (
          <a
            href={`/api/projecten/${id}/rapport.md`}
            download
            className="btn btn-secondary"
            style={{ fontSize: "0.8125rem" }}
          >
            Download als Markdown
          </a>
        )}
      </div>

      {/* Kop */}
      <h1
        style={{
          fontSize: "1.5rem",
          fontWeight: 700,
          marginBottom: "0.5rem",
          color: "rgb(var(--lint))",
        }}
      >
        {naam}
      </h1>

      {/* Werkgebied */}
      {werkgebied && (
        <section style={{ marginBottom: "2rem" }}>
          <SectieKop>Werkgebied</SectieKop>
          {werkgebied.hoofdvraag && (
            <p
              style={{
                fontStyle: "italic",
                color: "rgb(var(--muted))",
                marginBottom: "0.5rem",
              }}
            >
              {werkgebied.hoofdvraag}
            </p>
          )}
          {werkgebied.omschrijving && (
            <p style={{ marginBottom: "0.5rem" }}>{werkgebied.omschrijving}</p>
          )}
          {werkgebied.analysefocus && (
            <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
              Analysefocus: {werkgebied.analysefocus}
            </p>
          )}
        </section>
      )}

      {/* Bronnen */}
      {bronnen.length > 0 && (
        <section style={{ marginBottom: "2rem" }}>
          <SectieKop>Bronnen</SectieKop>
          {bronnen.map((b, i) => (
            <BronKaart key={b.bron_id ?? i} bron={b} />
          ))}
        </section>
      )}

      {/* Begrippen */}
      <section style={{ marginBottom: "2rem" }}>
        <SectieKop>Begrippen</SectieKop>
        <BegrippenTabel begrippen={begrippen} />
      </section>

      {/* Afleidingsregels */}
      <section style={{ marginBottom: "2rem" }}>
        <SectieKop>Afleidingsregels</SectieKop>
        <RegelLijst regels={regels} />
      </section>
    </div>
  );
}
