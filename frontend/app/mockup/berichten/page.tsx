import { TypeBadge } from "@/components/berichten/TypeBadge";
import { TYPE_META, type BerichtType } from "@/lib/bericht-types";

interface Bericht {
  id: number;
  titel: string;
  inhoud: string;
  type: BerichtType;
  versie: string | null;
  gepubliceerd_op: string;
  gelezen: boolean;
}

const NEPPE_BERICHTEN: Bericht[] = [
  {
    id: 1,
    titel: "Nieuwe analysemethode beschikbaar",
    inhoud: "De verbeterde LLM-analyse is nu beschikbaar voor alle projecten. Pas de instellingen aan via het modelprofielen-scherm.",
    type: "update",
    versie: "2.4.0",
    gepubliceerd_op: "2026-08-10T10:00:00Z",
    gelezen: false,
  },
  {
    id: 2,
    titel: "Gepland onderhoud op 20 augustus",
    inhoud: "Het systeem is op 20 augustus van 02:00–04:00 niet bereikbaar wegens database-migraties.",
    type: "waarschuwing",
    versie: null,
    gepubliceerd_op: "2026-08-12T08:00:00Z",
    gelezen: false,
  },
  {
    id: 3,
    titel: "Nieuwe exportfunctie aangekondigd",
    inhoud: "PDF-export wordt volgende sprint uitgerold. Meer informatie volgt via het beheerteam.",
    type: "info",
    versie: null,
    gepubliceerd_op: "2026-08-05T09:00:00Z",
    gelezen: true,
  },
];

export default function BerichtenPagina() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h1 style={{ fontSize: "1.375rem" }}>Berichten</h1>
        <span
          style={{
            fontSize: "0.75rem",
            padding: "0.125rem 0.625rem",
            background: "rgb(var(--waarschuwing) / 0.1)",
            color: "rgb(var(--waarschuwing))",
            border: "1px solid rgb(var(--waarschuwing) / 0.3)",
            borderRadius: "9999px",
          }}
        >
          mockup — nepdata
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {NEPPE_BERICHTEN.map((b) => {
          const { kleurVar } = TYPE_META[b.type];
          const datum = new Date(b.gepubliceerd_op).toLocaleDateString("nl-NL", {
            day: "numeric",
            month: "long",
            year: "numeric",
          });

          return (
            <div
              key={b.id}
              className="card"
              style={{
                position: "relative",
                paddingLeft: "1.75rem",
                background: b.gelezen ? "rgb(var(--paper))" : "rgb(var(--surface))",
              }}
            >
              {/* Gekleurde linkerbalk voor ongelezen */}
              {!b.gelezen && (
                <span
                  aria-hidden
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: "4px",
                    background: `rgb(var(${kleurVar}))`,
                    borderRadius: "6px 0 0 6px",
                  }}
                />
              )}

              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.5rem" }}>
                <TypeBadge type={b.type} />
                {b.versie && (
                  <span
                    style={{
                      fontSize: "0.6875rem",
                      fontFamily: "monospace",
                      padding: "0.125rem 0.4rem",
                      borderRadius: "3px",
                      color: "rgb(var(--faint))",
                      border: "1px solid rgb(var(--line))",
                      background: "rgb(var(--surface))",
                    }}
                  >
                    {b.versie}
                  </span>
                )}
                <span style={{ fontSize: "0.75rem", color: "rgb(var(--faint))", marginLeft: "auto" }}>
                  {datum}
                </span>
              </div>

              <p style={{ fontSize: "1rem", fontWeight: 600, color: "rgb(var(--ink))", marginBottom: "0.375rem" }}>
                {b.titel}
              </p>
              <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))", lineHeight: 1.6 }}>
                {b.inhoud}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
