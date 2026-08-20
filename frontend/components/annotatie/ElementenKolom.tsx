"use client";

import { useMemo, useState } from "react";
import type { components } from "@/generated/types";

type AnnotatieDocument = components["schemas"]["AnnotatieDocument"];
type AnnotatieElement = components["schemas"]["AnnotatieElement"];
type Aandacht = components["schemas"]["Aandacht"];
type Levenscyclus = components["schemas"]["Levenscyclus"];
type BeslissingType = components["schemas"]["BeslissingType"];
type BeoordelingsReden = components["schemas"]["BeoordelingsReden"];

// ─── Aandacht-stijlen (één lookup, drie keer gebruikt) ────────────────────────

const AANDACHT_STIJL: Record<
  Aandacht,
  { bg: string; border: string; fg: string }
> = {
  rood: { bg: "#fef2f2", border: "#fca5a5", fg: "#dc2626" },
  geel: { bg: "#fefce8", border: "#fde047", fg: "#ca8a04" },
  groen: { bg: "#f0fdf4", border: "#86efac", fg: "#16a34a" },
};

const AANDACHT_STANDAARD = {
  bg: "rgb(var(--surface))",
  border: "rgb(var(--line))",
  fg: "rgb(var(--muted))",
};

function aandachtStijl(a: Aandacht | null | undefined) {
  return a ? AANDACHT_STIJL[a] : AANDACHT_STANDAARD;
}

// ─── Badges ──────────────────────────────────────────────────────────────────

function AandachtBadge({
  aandacht,
}: {
  aandacht: Aandacht | null | undefined;
}) {
  if (!aandacht) return null;
  const { bg, border, fg } = AANDACHT_STIJL[aandacht];
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.125rem 0.5rem",
        borderRadius: "99px",
        fontSize: "0.6875rem",
        fontWeight: 600,
        background: bg,
        color: fg,
        border: `1px solid ${border}`,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
      }}
    >
      {aandacht}
    </span>
  );
}

function levenscyclusLabel(l: Levenscyclus): string {
  switch (l) {
    case "voorgesteld":
      return "Voorgesteld";
    case "critic_gecheckt":
      return "Critic gecheckt";
    case "human_goedgekeurd":
      return "Goedgekeurd";
    case "bewerkt":
      return "Bewerkt";
    case "afgewezen":
      return "Afgewezen";
  }
}

function levenscyclusKleur(l: Levenscyclus): { bg: string; fg: string } {
  switch (l) {
    case "human_goedgekeurd":
      return { bg: "#f0fdf4", fg: "#16a34a" };
    case "bewerkt":
      return { bg: "#eff6ff", fg: "#2563eb" };
    case "afgewezen":
      return { bg: "#fef2f2", fg: "#dc2626" };
    case "critic_gecheckt":
      return { bg: "#fefce8", fg: "#ca8a04" };
    default:
      return { bg: "rgb(var(--surface))", fg: "rgb(var(--muted))" };
  }
}

function LevenscyclusBadge({ levenscyclus }: { levenscyclus: Levenscyclus }) {
  const { bg, fg } = levenscyclusKleur(levenscyclus);
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.125rem 0.5rem",
        borderRadius: "99px",
        fontSize: "0.6875rem",
        fontWeight: 500,
        background: bg,
        color: fg,
        border: `1px solid ${fg}33`,
      }}
    >
      {levenscyclusLabel(levenscyclus)}
    </span>
  );
}

// ─── Sortering ────────────────────────────────────────────────────────────────

const AANDACHT_VOLGORDE: Record<string, number> = {
  rood: 0,
  geel: 1,
  groen: 2,
};

function sorteerElementen(elementen: AnnotatieElement[]): AnnotatieElement[] {
  return [...elementen].sort((a, b) => {
    const oa = AANDACHT_VOLGORDE[a.aandacht ?? ""] ?? 3;
    const ob = AANDACHT_VOLGORDE[b.aandacht ?? ""] ?? 3;
    return oa - ob;
  });
}

// ─── BeslissingFormulier ──────────────────────────────────────────────────────

const REDENEN: { value: BeoordelingsReden; label: string }[] = [
  { value: "onduidelijk", label: "Onduidelijk" },
  { value: "fout_klasse", label: "Foute klasse" },
  { value: "fout_tekst", label: "Foute tekst" },
  { value: "dubbeling", label: "Dubbeling" },
  { value: "overig", label: "Overig" },
];

interface BewerkFormulierProps {
  element: AnnotatieElement;
  onVerzend: (
    type: BeslissingType,
    reden: BeoordelingsReden | null,
    opmerking: string | null,
    wijziging: {
      klasse: string | null;
      tekst: string | null;
      toelichting: string | null;
      lid: string | null;
    } | null,
  ) => Promise<void>;
  onAnnuleren: () => void;
  bezig: boolean;
  fout: string | null;
}

function BewerkFormulier({
  element,
  onVerzend,
  onAnnuleren,
  bezig,
  fout,
}: BewerkFormulierProps) {
  const [klasse, setKlasse] = useState(element.klasse);
  const [tekst, setTekst] = useState(element.tekst);
  const [toelichting, setToelichting] = useState(element.toelichting ?? "");
  const [reden, setReden] = useState<BeoordelingsReden | "">("");

  const heeftWijziging =
    klasse !== element.klasse ||
    tekst !== element.tekst ||
    toelichting !== (element.toelichting ?? "");

  const kanVerzenden = reden !== "" && heeftWijziging && !bezig;

  return (
    <div
      style={{
        background: "rgb(var(--paper))",
        border: "1px solid rgb(var(--info))",
        borderRadius: "6px",
        padding: "0.75rem",
        marginTop: "0.5rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.625rem",
      }}
    >
      {fout && (
        <div
          className="melding melding-fout"
          role="alert"
          style={{ fontSize: "0.8125rem" }}
        >
          {fout}
        </div>
      )}
      <label
        style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}
      >
        <span style={{ fontSize: "0.75rem", fontWeight: 500 }}>Klasse</span>
        <input
          className="field-input"
          style={{ fontSize: "0.8125rem" }}
          value={klasse}
          onChange={(e) => setKlasse(e.target.value)}
        />
      </label>
      <label
        style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}
      >
        <span style={{ fontSize: "0.75rem", fontWeight: 500 }}>Tekst</span>
        <textarea
          className="field-input"
          style={{
            fontSize: "0.8125rem",
            minHeight: "3rem",
            resize: "vertical",
          }}
          value={tekst}
          onChange={(e) => setTekst(e.target.value)}
        />
      </label>
      <label
        style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}
      >
        <span style={{ fontSize: "0.75rem", fontWeight: 500 }}>
          Toelichting
        </span>
        <textarea
          className="field-input"
          style={{
            fontSize: "0.8125rem",
            minHeight: "2.5rem",
            resize: "vertical",
          }}
          value={toelichting}
          onChange={(e) => setToelichting(e.target.value)}
        />
      </label>
      <label
        style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}
      >
        <span style={{ fontSize: "0.75rem", fontWeight: 500 }}>
          Reden <span style={{ color: "rgb(var(--gevaar))" }}>*</span>
        </span>
        <select
          className="field-input"
          style={{ fontSize: "0.8125rem" }}
          value={reden}
          onChange={(e) => setReden(e.target.value as BeoordelingsReden | "")}
        >
          <option value="">Kies een reden…</option>
          {REDENEN.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </label>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          className="btn btn-primary"
          style={{ fontSize: "0.8125rem", padding: "0.25rem 0.75rem" }}
          disabled={!kanVerzenden}
          onClick={() =>
            void onVerzend("bewerken", reden as BeoordelingsReden, null, {
              klasse: klasse !== element.klasse ? klasse : null,
              tekst: tekst !== element.tekst ? tekst : null,
              toelichting:
                toelichting !== (element.toelichting ?? "")
                  ? toelichting
                  : null,
              lid: null,
            })
          }
        >
          {bezig ? "Opslaan…" : "Bewerking opslaan"}
        </button>
        <button
          className="btn btn-secondary"
          style={{ fontSize: "0.8125rem", padding: "0.25rem 0.75rem" }}
          disabled={bezig}
          onClick={onAnnuleren}
        >
          Annuleren
        </button>
      </div>
    </div>
  );
}

interface AfwijzenFormulierProps {
  onVerzend: (
    type: BeslissingType,
    reden: BeoordelingsReden | null,
    opmerking: string | null,
    wijziging: null,
  ) => Promise<void>;
  onAnnuleren: () => void;
  bezig: boolean;
  fout: string | null;
}

function AfwijzenFormulier({
  onVerzend,
  onAnnuleren,
  bezig,
  fout,
}: AfwijzenFormulierProps) {
  const [reden, setReden] = useState<BeoordelingsReden | "">("");
  const [opmerking, setOpmerking] = useState("");

  return (
    <div
      style={{
        background: "rgb(var(--paper))",
        border: "1px solid #fca5a5",
        borderRadius: "6px",
        padding: "0.75rem",
        marginTop: "0.5rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.625rem",
      }}
    >
      {fout && (
        <div
          className="melding melding-fout"
          role="alert"
          style={{ fontSize: "0.8125rem" }}
        >
          {fout}
        </div>
      )}
      <label
        style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}
      >
        <span style={{ fontSize: "0.75rem", fontWeight: 500 }}>
          Reden <span style={{ color: "rgb(var(--gevaar))" }}>*</span>
        </span>
        <select
          className="field-input"
          style={{ fontSize: "0.8125rem" }}
          value={reden}
          onChange={(e) => setReden(e.target.value as BeoordelingsReden | "")}
        >
          <option value="">Kies een reden…</option>
          {REDENEN.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </label>
      <label
        style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}
      >
        <span style={{ fontSize: "0.75rem", fontWeight: 500 }}>
          Opmerking{" "}
          <span style={{ fontSize: "0.75rem", color: "rgb(var(--muted))" }}>
            (optioneel)
          </span>
        </span>
        <textarea
          className="field-input"
          style={{
            fontSize: "0.8125rem",
            minHeight: "2.5rem",
            resize: "vertical",
          }}
          value={opmerking}
          onChange={(e) => setOpmerking(e.target.value)}
          placeholder="Optionele toelichting…"
        />
      </label>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          className="btn btn-primary"
          style={{
            fontSize: "0.8125rem",
            padding: "0.25rem 0.75rem",
            background: "rgb(var(--gevaar))",
          }}
          disabled={reden === "" || bezig}
          onClick={() =>
            void onVerzend(
              "afwijzen",
              reden as BeoordelingsReden,
              opmerking.trim() || null,
              null,
            )
          }
        >
          {bezig ? "Afwijzen…" : "Afwijzen bevestigen"}
        </button>
        <button
          className="btn btn-secondary"
          style={{ fontSize: "0.8125rem", padding: "0.25rem 0.75rem" }}
          disabled={bezig}
          onClick={onAnnuleren}
        >
          Annuleren
        </button>
      </div>
    </div>
  );
}

// ─── ElementKaart ─────────────────────────────────────────────────────────────

interface ElementKaartProps {
  element: AnnotatieElement;
  slug: string;
  onBeslissing: (bijgewerkt: AnnotatieDocument) => void;
  router: { push: (url: string) => void };
}

function ElementKaart({
  element,
  slug,
  onBeslissing,
  router,
}: ElementKaartProps) {
  type Actie = "bewerken" | "afwijzen" | null;
  const [actieformulier, setActieformulier] = useState<Actie>(null);
  const [bezig, setBezig] = useState(false);
  const [fout, setFout] = useState<string | null>(null);

  const { bg, border } = aandachtStijl(element.aandacht);

  async function registreerBeslissing(
    type: BeslissingType,
    reden: BeoordelingsReden | null,
    opmerking: string | null,
    wijziging: {
      klasse: string | null;
      tekst: string | null;
      toelichting: string | null;
      lid: string | null;
    } | null,
  ) {
    setFout(null);
    setBezig(true);
    try {
      const res = await fetch(
        `/api/annotatie/documenten/${slug}/elementen/${element.id}/beslissing`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type, reden, opmerking, wijziging }),
        },
      );
      if (res.status === 401) {
        router.push("/login");
        return;
      }
      if (!res.ok) {
        const data = (await res.json()) as { detail?: string };
        throw new Error(data.detail ?? `${res.status} ${res.statusText}`);
      }
      const bijgewerkt = (await res.json()) as AnnotatieDocument;
      setActieformulier(null);
      onBeslissing(bijgewerkt);
    } catch (err) {
      setFout(
        err instanceof Error
          ? err.message
          : "Beslissing kon niet worden opgeslagen.",
      );
    } finally {
      setBezig(false);
    }
  }

  const isAfgesloten =
    element.levenscyclus === "human_goedgekeurd" ||
    element.levenscyclus === "bewerkt" ||
    element.levenscyclus === "afgewezen";

  return (
    <div
      style={{
        background: bg,
        border: `1px solid ${border}`,
        borderRadius: "8px",
        padding: "0.875rem",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          flexWrap: "wrap",
          alignItems: "center",
          marginBottom: "0.5rem",
        }}
      >
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            fontFamily: "monospace",
            background: "rgb(var(--paper))",
            border: "1px solid rgb(var(--line))",
            borderRadius: "4px",
            padding: "0.125rem 0.375rem",
            color: "rgb(var(--ink))",
          }}
        >
          {element.klasse}
        </span>
        <AandachtBadge aandacht={element.aandacht} />
        <LevenscyclusBadge levenscyclus={element.levenscyclus} />
      </div>

      {/* Tekst */}
      <p
        style={{
          fontSize: "0.875rem",
          color: "rgb(var(--ink))",
          margin: "0 0 0.375rem",
          lineHeight: 1.5,
        }}
      >
        {element.tekst}
      </p>

      {/* Toelichting */}
      {element.toelichting && (
        <p
          style={{
            fontSize: "0.8125rem",
            color: "rgb(var(--muted))",
            margin: "0 0 0.625rem",
            fontStyle: "italic",
          }}
        >
          {element.toelichting}
        </p>
      )}

      {/* Foutbericht buiten formulieren */}
      {fout && !actieformulier && (
        <div
          className="melding melding-fout"
          role="alert"
          style={{ fontSize: "0.8125rem", marginBottom: "0.5rem" }}
        >
          {fout}
        </div>
      )}

      {/* Beslissingsacties (alleen als nog niet afgesloten) */}
      {!isAfgesloten && !actieformulier && (
        <div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap" }}>
          <button
            className="btn btn-secondary"
            style={{
              fontSize: "0.75rem",
              padding: "0.25rem 0.625rem",
              color: "#16a34a",
              borderColor: "#86efac",
            }}
            disabled={bezig}
            onClick={() =>
              void registreerBeslissing("goedkeuren", null, null, null)
            }
          >
            {bezig ? "…" : "Goedkeuren"}
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: "0.75rem", padding: "0.25rem 0.625rem" }}
            disabled={bezig}
            onClick={() => setActieformulier("bewerken")}
          >
            Bewerken
          </button>
          <button
            className="btn btn-secondary"
            style={{
              fontSize: "0.75rem",
              padding: "0.25rem 0.625rem",
              color: "rgb(var(--gevaar))",
            }}
            disabled={bezig}
            onClick={() => setActieformulier("afwijzen")}
          >
            Afwijzen
          </button>
        </div>
      )}

      {/* Bewerkformulier */}
      {actieformulier === "bewerken" && (
        <BewerkFormulier
          element={element}
          onVerzend={registreerBeslissing}
          onAnnuleren={() => {
            setActieformulier(null);
            setFout(null);
          }}
          bezig={bezig}
          fout={fout}
        />
      )}

      {/* Afwijzenformulier */}
      {actieformulier === "afwijzen" && (
        <AfwijzenFormulier
          onVerzend={registreerBeslissing}
          onAnnuleren={() => {
            setActieformulier(null);
            setFout(null);
          }}
          bezig={bezig}
          fout={fout}
        />
      )}
    </div>
  );
}

// ─── ElementenKolom ──────────────────────────────────────────────────────────

interface Props {
  slug: string;
  elementen: AnnotatieElement[];
  onBeslissing: (bijgewerkt: AnnotatieDocument) => void;
  router: { push: (url: string) => void };
}

export function ElementenKolom({
  slug,
  elementen,
  onBeslissing,
  router,
}: Props) {
  const gesorteerd = useMemo(() => sorteerElementen(elementen), [elementen]);

  if (gesorteerd.length === 0) {
    return (
      <div
        style={{
          padding: "2rem",
          textAlign: "center",
          color: "rgb(var(--muted))",
          fontSize: "0.875rem",
          background: "rgb(var(--surface))",
          border: "1px solid rgb(var(--line))",
          borderRadius: "8px",
        }}
      >
        Geen elementen voorgesteld door de agent.
        <br />
        <span style={{ fontSize: "0.8125rem", color: "rgb(var(--faint))" }}>
          De agent kan in een volgende versie elementen inladen via de
          Wettenbank-koppeling.
        </span>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      <p
        style={{
          fontSize: "0.8125rem",
          color: "rgb(var(--muted))",
          margin: 0,
        }}
      >
        {gesorteerd.length} {gesorteerd.length === 1 ? "element" : "elementen"}{" "}
        — gesorteerd op aandacht (rood → geel → groen → geen)
      </p>
      {gesorteerd.map((el) => (
        <ElementKaart
          key={el.id}
          element={el}
          slug={slug}
          onBeslissing={onBeslissing}
          router={router}
        />
      ))}
    </div>
  );
}
