import type { components } from "@/generated/types";
import { CategorieBadge } from "./CategorieBadge";

type FeedbackRead = components["schemas"]["FeedbackRead"];

export function FeedbackItem({
  item,
  onVerwijderen = () => {},
}: {
  item: FeedbackRead;
  onVerwijderen?: (id: number) => void;
}) {
  const datum = new Date(item.created).toLocaleDateString("nl-NL", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  return (
    <div
      style={{
        padding: "1rem 0",
        borderBottom: "1px solid rgb(var(--line))",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: "1rem",
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            flexWrap: "wrap",
            marginBottom: "0.375rem",
          }}
        >
          <CategorieBadge categorie={item.categorie} />
          <span style={{ fontSize: "0.75rem", color: "rgb(var(--faint))" }}>
            {item.userid}
            {item.pagina ? ` · ${item.pagina}` : ""}
            {" · "}
            {datum}
          </span>
        </div>
        <p
          style={{
            margin: 0,
            fontSize: "0.875rem",
            lineHeight: 1.5,
            color: "rgb(var(--ink))",
            overflowWrap: "break-word",
          }}
        >
          {item.tekst}
        </p>
      </div>
      <button
        className="btn btn-secondary"
        style={{
          fontSize: "0.8125rem",
          minHeight: "1.875rem",
          padding: "0.25rem 0.625rem",
          flexShrink: 0,
        }}
        onClick={() => onVerwijderen(item.id)}
      >
        Verwijderen
      </button>
    </div>
  );
}
