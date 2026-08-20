"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const HELPTEKST_STIJL = {
  margin: "0.25rem 0 0",
  fontSize: "0.8125rem",
} as const;

function VeldFout({ id, tekst }: { id: string; tekst: string }) {
  return (
    <p
      id={id}
      role="alert"
      style={{ ...HELPTEKST_STIJL, color: "rgb(var(--fout))" }}
    >
      {tekst}
    </p>
  );
}

export default function SetupFormulier() {
  const router = useRouter();

  const [gebruikersnaam, setGebruikersnaam] = useState("");
  const [email, setEmail] = useState("");
  const [wachtwoord, setWachtwoord] = useState("");
  const [bevestiging, setBevestiging] = useState("");
  const [veldFouten, setVeldFouten] = useState<Record<string, string>>({});
  const [formulierFout, setFormulierFout] = useState<string | null>(null);
  const [bezig, setBezig] = useState(false);

  function valideer(): boolean {
    const fouten: Record<string, string> = {};

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

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormulierFout(null);
    if (!valideer()) return;

    setBezig(true);
    try {
      const res = await fetch("/api/auth/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gebruikersnaam, email, wachtwoord }),
      });

      if (res.ok) {
        router.push("/login");
        return;
      }

      if (res.status === 409) {
        const data = (await res.json()) as { detail?: string };
        setFormulierFout(
          data.detail ?? "Setup al voltooid. Ga naar de loginpagina.",
        );
        return;
      }

      setFormulierFout(
        "Er is een fout opgetreden. Controleer de invoer en probeer het opnieuw.",
      );
    } catch {
      setFormulierFout(
        "Netwerkfout — controleer de verbinding en probeer het opnieuw.",
      );
    } finally {
      setBezig(false);
    }
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
          aria-describedby={
            veldFouten.gebruikersnaam ? "s-gebruikersnaam-fout" : undefined
          }
          aria-invalid={!!veldFouten.gebruikersnaam}
        />
        {veldFouten.gebruikersnaam && (
          <VeldFout
            id="s-gebruikersnaam-fout"
            tekst={veldFouten.gebruikersnaam}
          />
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
          <VeldFout id="s-email-fout" tekst={veldFouten.email} />
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
          aria-describedby={
            veldFouten.wachtwoord ? "s-wachtwoord-fout" : "s-wachtwoord-hint"
          }
          aria-invalid={!!veldFouten.wachtwoord}
        />
        {veldFouten.wachtwoord ? (
          <VeldFout id="s-wachtwoord-fout" tekst={veldFouten.wachtwoord} />
        ) : (
          <p
            id="s-wachtwoord-hint"
            style={{ ...HELPTEKST_STIJL, color: "rgb(var(--faint))" }}
          >
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
          aria-describedby={
            veldFouten.bevestiging ? "s-bevestiging-fout" : undefined
          }
          aria-invalid={!!veldFouten.bevestiging}
        />
        {veldFouten.bevestiging && (
          <VeldFout id="s-bevestiging-fout" tekst={veldFouten.bevestiging} />
        )}
      </div>

      <p
        style={{
          fontSize: "0.8125rem",
          color: "rgb(var(--muted))",
          margin: 0,
        }}
      >
        Stel de eerste beheerder in — dit formulier is na de eerste aanmelding
        niet meer beschikbaar.
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
