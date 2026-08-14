import Link from "next/link";

export default function StartPagina() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <nav
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "0.5rem",
          padding: "1rem 1.5rem",
          background: "rgb(var(--surface))",
          borderRadius: "6px",
          border: "1px solid rgb(var(--line))",
        }}
      >
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            color: "rgb(var(--faint))",
            alignSelf: "center",
            marginRight: "0.5rem",
          }}
        >
          Mockups
        </span>
        <Link href="/mockup/feedback" style={{ fontSize: "0.875rem", color: "rgb(var(--lint))" }}>
          Feedback (story 009)
        </Link>
        <Link href="/mockup/wetcatalogus" style={{ fontSize: "0.875rem", color: "rgb(var(--lint))" }}>
          Wetcatalogus (story 010)
        </Link>
        <Link href="/mockup/llm-profielen" style={{ fontSize: "0.875rem", color: "rgb(var(--lint))" }}>
          LLM-profielen (story 011)
        </Link>
        <Link href="/mockup/analyse" style={{ fontSize: "0.875rem", color: "rgb(var(--lint))" }}>
          Analyse (story 012)
        </Link>
        <Link href="/mockup/rapport" style={{ fontSize: "0.875rem", color: "rgb(var(--lint))" }}>
          Rapport (story 013)
        </Link>
      </nav>

      <div
        style={{
          background: "rgb(var(--lint))",
          borderRadius: "6px",
          padding: "2rem 2.5rem",
        }}
      >
        <p
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.18em",
            color: "rgba(255 255 255 / 0.7)",
          }}
        >
          Juridisch Analyseschema
        </p>
        <h1
          style={{
            marginTop: "0.5rem",
            fontSize: "1.875rem",
            fontWeight: 600,
            color: "rgb(255 255 255)",
          }}
        >
          Wetsanalyse
        </h1>
        <p
          style={{
            marginTop: "0.5rem",
            fontSize: "0.875rem",
            color: "rgba(255 255 255 / 0.85)",
            maxWidth: "48ch",
          }}
        >
          Brongetrouwe analyse van wetgeving — per artikel, lid en bronreferentie — volgens het
          Juridisch Analyseschema van Ausems, Bulles &amp; Lokin.
        </p>
      </div>
    </div>
  );
}

