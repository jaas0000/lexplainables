"use client";

import { useState } from "react";

export function VerwijderKnop({
  onClick,
  compact = false,
}: {
  onClick: () => void;
  compact?: boolean;
}) {
  const [bevestig, setBevestig] = useState(false);
  if (bevestig) {
    return (
      <span
        style={{ display: "inline-flex", gap: "0.5rem", alignItems: "center" }}
      >
        <button
          className="btn btn-danger"
          style={{
            fontSize: compact ? "0.75rem" : "0.8125rem",
            padding: compact ? "0.25rem 0.625rem" : "0.375rem 0.875rem",
          }}
          onClick={onClick}
        >
          {compact ? "Verwijder ✓" : "Bevestig verwijderen"}
        </button>
        <button
          className="btn btn-secondary"
          style={{ fontSize: compact ? "0.75rem" : "0.8125rem" }}
          onClick={() => setBevestig(false)}
        >
          Annuleer
        </button>
      </span>
    );
  }
  return (
    <button
      className="btn btn-danger"
      style={{
        fontSize: compact ? "0.75rem" : "0.8125rem",
        padding: compact ? "0.25rem 0.625rem" : undefined,
      }}
      onClick={() => setBevestig(true)}
    >
      Verwijder
    </button>
  );
}
