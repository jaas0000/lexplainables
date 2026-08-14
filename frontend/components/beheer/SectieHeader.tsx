export function SectieHeader({ titel, subtitel, aantal }: { titel: string; subtitel?: string; aantal?: number }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem", borderBottom: "1px solid rgb(var(--line))", paddingBottom: "0.5rem", marginBottom: "1.25rem" }}>
      <h2 style={{ fontSize: "1.125rem", fontWeight: 600, color: "rgb(var(--lint))" }}>{titel}</h2>
      {aantal !== undefined && <span style={{ fontSize: "0.75rem", fontFamily: "monospace", color: "rgb(var(--faint))" }}>{aantal}</span>}
      {subtitel && <span style={{ marginLeft: "auto", fontSize: "0.75rem", color: "rgb(var(--faint))" }}>{subtitel}</span>}
    </div>
  );
}

export function LeegePlaceholder({ tekst }: { tekst: string }) {
  return <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))", fontStyle: "italic", padding: "1.5rem 0" }}>{tekst}</p>;
}
