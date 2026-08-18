"use client";

import { useState } from "react";
import Link from "next/link";

// ---- Varianten ----

type Variant = "leeg-formulier" | "al-ingericht" | "succes";

const VARIANTEN: { id: Variant; label: string }[] = [
  { id: "leeg-formulier", label: "Leeg formulier" },
  { id: "al-ingericht",   label: "Al ingericht — redirect-melding" },
  { id: "succes",         label: "Succesbericht na aanmaken" },
];

// ---- Formulier (leeg formulier-variant) ----

function SetupFormulier() {
  const [naam, setNaam]                 = useState("");
  const [gebruikersnaam, setGebruikersnaam] = useState("");
  const [email, setEmail]               = useState("");
  const [wachtwoord, setWachtwoord]     = useState("");
  const [bevestiging, setBevestiging]   = useState("");
  const [veldFouten, setVeldFouten]     = useState<Record<string, string>>({});
  const [formulierFout, setFormulierFout] = useState<string | null>(null);
  const [bezig, setBezig]               = useState(false);

  function valideer(): boolean {
    const fouten: Record<string, string> = {};

    if (!naam.trim()) {
      fouten.naam = "Naam is verplicht.";
    }

    if (!/^[a-z0-9._-]{3,64}$/.test(gebruikersnaam)) {
      fouten.gebruikersnaam =
        "Gebruikersnaam moet 3–64 tekens lang zijn en alleen a–z, 0–9, punt, underscore of koppelteken bevatten.";
    }

    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      fouten.email = "Vul een geldig e-mailadres in.";
    }

    if (wachtwoord.length < 8) {
      fouten.wachtwoord = "Wachtwoord moet minimaal 8 tekens lang zijn.";
    }

    if (wachtwoord !== bevestiging) {
      fouten.bevestiging = "Wachtwoorden komen niet overeen.";
    }

    setVeldFouten(fouten);
    return Object.keys(fouten).length === 0;
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormulierFout(null);
    if (!valideer()) return;

    setBezig(true);
    // Simulatie: in de mockup doen we alsof het verzoek mislukt
    setTimeout(() => {
      setBezig(false);
      setFormulierFout(
        "Mockup: in de echte app worden de gegevens hier naar de API gestuurd. " +
        "Gebruik de 'Succesbericht'-variant om het resultaat te bekijken."
      );
    }, 800);
  }

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
    >
      {formulierFout && (
        <p role="alert" className="melding melding-info" style={{ margin: 0 }}>
          {formulierFout}
        </p>
      )}

      {/* Naam */}
      <div>
        <label className="field-label" htmlFor="s-naam">
          Naam
        </label>
        <input
          id="s-naam"
          type="text"
          autoComplete="name"
          required
          value={naam}
          onChange={(e) => setNaam(e.target.value)}
          className="field-input"
          aria-describedby={veldFouten.naam ? "s-naam-fout" : undefined}
          aria-invalid={!!veldFouten.naam}
        />
        {veldFouten.naam && (
          <p id="s-naam-fout" role="alert" style={{ margin: "0.25rem 0 0", fontSize: "0.8125rem", color: "rgb(var(--fout))" }}>
            {veldFouten.naam}
          </p>
        )}
      </div>

      {/* Gebruikersnaam */}
      <div>
        <label className="field-label" htmlFor="s-gebruikersnaam">
          Gebruikersnaam
        </label>
        <input
          id="s-gebruikersnaam"
          type="text"
          autoComplete="username"
          autoCapitalize="none"
          required
          value={gebruikersnaam}
          onChange={(e) => setGebruikersnaam(e.target.value)}
          className="field-input"
          aria-describedby={veldFouten.gebruikersnaam ? "s-gebruikersnaam-fout" : undefined}
          aria-invalid={!!veldFouten.gebruikersnaam}
        />
        {veldFouten.gebruikersnaam && (
          <p id="s-gebruikersnaam-fout" role="alert" style={{ margin: "0.25rem 0 0", fontSize: "0.8125rem", color: "rgb(var(--fout))" }}>
            {veldFouten.gebruikersnaam}
          </p>
        )}
      </div>

      {/* E-mail */}
      <div>
        <label className="field-label" htmlFor="s-email">
          E-mailadres
        </label>
        <input
          id="s-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="field-input"
          aria-describedby={veldFouten.email ? "s-email-fout" : undefined}
          aria-invalid={!!veldFouten.email}
        />
        {veldFouten.email && (
          <p id="s-email-fout" role="alert" style={{ margin: "0.25rem 0 0", fontSize: "0.8125rem", color: "rgb(var(--fout))" }}>
            {veldFouten.email}
          </p>
        )}
      </div>

      {/* Wachtwoord */}
      <div>
        <label className="field-label" htmlFor="s-wachtwoord">
          Wachtwoord
        </label>
        <input
          id="s-wachtwoord"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={wachtwoord}
          onChange={(e) => setWachtwoord(e.target.value)}
          className="field-input"
          aria-describedby={veldFouten.wachtwoord ? "s-wachtwoord-fout" : "s-wachtwoord-hint"}
          aria-invalid={!!veldFouten.wachtwoord}
        />
        {veldFouten.wachtwoord ? (
          <p id="s-wachtwoord-fout" role="alert" style={{ margin: "0.25rem 0 0", fontSize: "0.8125rem", color: "rgb(var(--fout))" }}>
            {veldFouten.wachtwoord}
          </p>
        ) : (
          <p id="s-wachtwoord-hint" style={{ margin: "0.25rem 0 0", fontSize: "0.8125rem", color: "rgb(var(--faint))" }}>
            Minimaal 8 tekens.
          </p>
        )}
      </div>

      {/* Wachtwoord bevestigen */}
      <div>
        <label className="field-label" htmlFor="s-bevestiging">
          Wachtwoord bevestigen
        </label>
        <input
          id="s-bevestiging"
          type="password"
          autoComplete="new-password"
          required
          value={bevestiging}
          onChange={(e) => setBevestiging(e.target.value)}
          className="field-input"
          aria-describedby={veldFouten.bevestiging ? "s-bevestiging-fout" : undefined}
          aria-invalid={!!veldFouten.bevestiging}
        />
        {veldFouten.bevestiging && (
          <p id="s-bevestiging-fout" role="alert" style={{ margin: "0.25rem 0 0", fontSize: "0.8125rem", color: "rgb(var(--fout))" }}>
            {veldFouten.bevestiging}
          </p>
        )}
      </div>

      <p style={{ fontSize: "0.8125rem", color: "rgb(var(--muted))", margin: 0 }}>
        Stel de eerste beheerder in — dit formulier is na de eerste aanmelding niet meer beschikbaar.
      </p>

      <button
        type="submit"
        disabled={bezig}
        className="btn btn-primary"
        style={{ width: "100%" }}
      >
        {bezig ? "Aanmaken…" : "Aanmaken"}
      </button>
    </form>
  );
}

// ---- Al ingericht ----

function AlIngericht() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        padding: "1.5rem",
        background: "rgb(var(--surface))",
        borderRadius: "6px",
        border: "1px solid rgb(var(--line))",
      }}
    >
      <p style={{ margin: 0, fontSize: "0.9375rem", color: "rgb(var(--ink))" }}>
        De setup is al voltooid — er bestaat al een beheerdersaccount. U kunt
        inloggen via de loginpagina.
      </p>
      <Link
        href="/login"
        className="btn btn-secondary"
        style={{ display: "inline-block", textAlign: "center" }}
      >
        Naar inloggen →
      </Link>
    </div>
  );
}

// ---- Succesbericht ----

function Succes() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "1rem",
        padding: "2rem 1.5rem",
        background: "rgb(var(--surface))",
        borderRadius: "6px",
        border: "1px solid rgb(var(--line))",
        textAlign: "center",
      }}
    >
      <svg
        width="40"
        height="40"
        viewBox="0 0 24 24"
        fill="currentColor"
        aria-hidden
        style={{ color: "rgb(var(--succes))" }}
      >
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.59L5.41 12l1.42-1.42L10 13.17l7.17-7.17 1.42 1.42L10 16.59z" />
      </svg>
      <p
        style={{
          margin: 0,
          fontSize: "1rem",
          fontWeight: 600,
          color: "rgb(var(--ink))",
        }}
      >
        Beheerdersaccount aangemaakt
      </p>
      <p style={{ margin: 0, fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
        Het account is succesvol aangemaakt. U kunt nu inloggen.
      </p>
      <Link
        href="/login"
        className="btn btn-primary"
        style={{ display: "inline-block" }}
      >
        Naar inloggen
      </Link>
    </div>
  );
}

// ---- Hoofd-component ----

export default function SetupMockup() {
  const [variant, setVariant] = useState<Variant>("leeg-formulier");

  return (
    <div className="main">
      {/* Oranje mockup-badge */}
      <div
        style={{
          display: "inline-flex",
          background: "rgb(var(--waarschuwing))",
          color: "white",
          borderRadius: "4px",
          padding: "0.2rem 0.625rem",
          fontSize: "0.6875rem",
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: "1.25rem",
        }}
      >
        Mockup — nepdata · Setup-flow (story 015)
      </div>

      <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" }}>
        Setup — initiële beheerder aanmaken
      </h1>

      {/* Variant-knoppen */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "2rem" }}>
        {VARIANTEN.map((v) => (
          <button
            key={v.id}
            className={variant === v.id ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => setVariant(v.id)}
          >
            {v.label}
          </button>
        ))}
      </div>

      {/* Inhoud per variant */}
      <div style={{ maxWidth: "24rem" }}>
        {variant === "leeg-formulier" && (
          <>
            <div style={{ marginBottom: "1.5rem" }}>
              <h2
                style={{
                  fontSize: "1.875rem",
                  fontWeight: 600,
                  lineHeight: 1.2,
                  marginBottom: "0.25rem",
                }}
              >
                Eerste beheerder aanmaken
              </h2>
              <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
                Er bestaat nog geen account. Maak hier eenmalig de eerste beheerder
                aan; daarna voeg je verdere gebruikers toe via het beheerscherm.
              </p>
            </div>
            <SetupFormulier />
          </>
        )}

        {variant === "al-ingericht" && (
          <>
            <div style={{ marginBottom: "1.5rem" }}>
              <h2
                style={{
                  fontSize: "1.875rem",
                  fontWeight: 600,
                  lineHeight: 1.2,
                  marginBottom: "0.25rem",
                }}
              >
                Setup al voltooid
              </h2>
            </div>
            <AlIngericht />
          </>
        )}

        {variant === "succes" && (
          <>
            <div style={{ marginBottom: "1.5rem" }}>
              <h2
                style={{
                  fontSize: "1.875rem",
                  fontWeight: 600,
                  lineHeight: 1.2,
                  marginBottom: "0.25rem",
                }}
              >
                Eerste beheerder aanmaken
              </h2>
            </div>
            <Succes />
          </>
        )}
      </div>
    </div>
  );
}
