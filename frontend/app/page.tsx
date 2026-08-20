export default function StartPagina() {
  return (
    <div>
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
          Brongetrouwe analyse van wetgeving — per artikel, lid en
          bronreferentie — volgens het Juridisch Analyseschema van Ausems,
          Bulles &amp; Lokin.
        </p>
      </div>
    </div>
  );
}
