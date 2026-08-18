"use client";

import { useState } from "react";

// Lokale interfaces — nepdata, geen gegenereerde types nodig in fase 1
interface EigenAccountInfo {
  gebruikersnaam: string;
  email: string;
  rol: string;
  totp_ingeschakeld: boolean;
}

type Variant = "standaard" | "succes" | "fout-wachtwoord";

const NEPPE_ACCOUNT: EigenAccountInfo = {
  gebruikersnaam: "j.de.vries",
  email: "j.de.vries@belastingdienst.nl",
  rol: "analist",
  totp_ingeschakeld: false,
};

export default function AccountMockup() {
  const [variant, setVariant] = useState<Variant>("standaard");
  const [huidigWachtwoord, setHuidigWachtwoord] = useState("");
  const [nieuwWachtwoord, setNieuwWachtwoord] = useState("");
  const [bevestigWachtwoord, setBevestigWachtwoord] = useState("");
  const [veldFout, setVeldFout] = useState<string | null>(null);

  function handleWachtwoordWijzigen(e: React.FormEvent) {
    e.preventDefault();
    setVeldFout(null);

    if (nieuwWachtwoord.length < 8) {
      setVeldFout("Het nieuwe wachtwoord moet minimaal 8 tekens zijn.");
      return;
    }
    if (nieuwWachtwoord !== bevestigWachtwoord) {
      setVeldFout("Het nieuwe wachtwoord en de bevestiging komen niet overeen.");
      return;
    }

    // Simuleer: verkeerd huidig wachtwoord als het veld leeg is of exact "fout"
    if (variant === "fout-wachtwoord" || huidigWachtwoord === "fout") {
      setVeldFout("Huidig wachtwoord klopt niet.");
      return;
    }

    setVariant("succes");
    setHuidigWachtwoord("");
    setNieuwWachtwoord("");
    setBevestigWachtwoord("");
  }

  function reset() {
    setVariant("standaard");
    setVeldFout(null);
    setHuidigWachtwoord("");
    setNieuwWachtwoord("");
    setBevestigWachtwoord("");
  }

  const rolLabel: Record<string, string> = {
    beheerder: "Beheerder",
    analist: "Analist",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header met badge */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem" }}>
        <h1 style={{ fontSize: "1.375rem" }}>Account</h1>
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

      {/* Variant-schakelaar */}
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          flexWrap: "wrap",
          padding: "0.75rem 1rem",
          background: "rgb(var(--surface))",
          borderRadius: "6px",
          border: "1px solid rgb(var(--line))",
          fontSize: "0.8rem",
        }}
      >
        <span style={{ color: "rgb(var(--faint))", alignSelf: "center", marginRight: "0.25rem" }}>
          Variant:
        </span>
        {(["standaard", "succes", "fout-wachtwoord"] as Variant[]).map((v) => (
          <button
            key={v}
            className={`btn btn-${variant === v ? "primary" : "secondary"}`}
            style={{ fontSize: "0.75rem", minHeight: "1.75rem", padding: "0.125rem 0.625rem" }}
            onClick={() => { setVariant(v); setVeldFout(null); }}
          >
            {v === "standaard" ? "Standaard" : v === "succes" ? "Wachtwoord gewijzigd" : "Verkeerd wachtwoord"}
          </button>
        ))}
      </div>

      {/* Sectie 1: Mijn gegevens */}
      <section className="card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>Mijn gegevens</h2>
        <dl style={{ display: "flex", flexDirection: "column", gap: "0.625rem", fontSize: "0.875rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "10rem 1fr", gap: "0.25rem 1rem", alignItems: "baseline" }}>
            <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>Gebruikersnaam</dt>
            <dd style={{ color: "rgb(var(--ink))" }}>{NEPPE_ACCOUNT.gebruikersnaam}</dd>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "10rem 1fr", gap: "0.25rem 1rem", alignItems: "baseline" }}>
            <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>E-mail</dt>
            <dd style={{ color: "rgb(var(--ink))" }}>{NEPPE_ACCOUNT.email}</dd>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "10rem 1fr", gap: "0.25rem 1rem", alignItems: "baseline" }}>
            <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>Rol</dt>
            <dd>
              <span className="badge badge-concept">
                {rolLabel[NEPPE_ACCOUNT.rol] ?? NEPPE_ACCOUNT.rol}
              </span>
            </dd>
          </div>
        </dl>
      </section>

      {/* Sectie 2: Wachtwoord wijzigen */}
      <section className="card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>Wachtwoord wijzigen</h2>

        {variant === "succes" && (
          <div
            className="melding"
            style={{
              background: "rgb(var(--succes) / 0.07)",
              border: "1px solid rgb(var(--succes) / 0.3)",
              color: "rgb(var(--succes))",
            }}
          >
            <span>✓</span>
            <span>Wachtwoord succesvol gewijzigd.</span>
          </div>
        )}

        <form
          onSubmit={handleWachtwoordWijzigen}
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <div>
            <label className="field-label" htmlFor="huidig-wachtwoord">
              Huidig wachtwoord
            </label>
            <input
              id="huidig-wachtwoord"
              type="password"
              className="field-input"
              value={huidigWachtwoord}
              onChange={(e) => {
                setHuidigWachtwoord(e.target.value);
                if (veldFout) setVeldFout(null);
              }}
              autoComplete="current-password"
              required
              style={{
                maxWidth: "24rem",
                borderColor: veldFout === "Huidig wachtwoord klopt niet." ? "rgb(var(--fout))" : undefined,
              }}
            />
            {veldFout === "Huidig wachtwoord klopt niet." && (
              <p style={{ marginTop: "0.25rem", fontSize: "0.8rem", color: "rgb(var(--fout))" }}>
                {veldFout}
              </p>
            )}
          </div>

          <div>
            <label className="field-label" htmlFor="nieuw-wachtwoord">
              Nieuw wachtwoord
              <span style={{ fontWeight: 400, color: "rgb(var(--faint))", marginLeft: "0.375rem" }}>
                (minimaal 8 tekens)
              </span>
            </label>
            <input
              id="nieuw-wachtwoord"
              type="password"
              className="field-input"
              value={nieuwWachtwoord}
              onChange={(e) => {
                setNieuwWachtwoord(e.target.value);
                if (veldFout) setVeldFout(null);
              }}
              autoComplete="new-password"
              required
              minLength={8}
              style={{ maxWidth: "24rem" }}
            />
          </div>

          <div>
            <label className="field-label" htmlFor="bevestig-wachtwoord">
              Bevestig nieuw wachtwoord
            </label>
            <input
              id="bevestig-wachtwoord"
              type="password"
              className="field-input"
              value={bevestigWachtwoord}
              onChange={(e) => {
                setBevestigWachtwoord(e.target.value);
                if (veldFout) setVeldFout(null);
              }}
              autoComplete="new-password"
              required
              style={{
                maxWidth: "24rem",
                borderColor:
                  veldFout && veldFout !== "Huidig wachtwoord klopt niet." ? "rgb(var(--fout))" : undefined,
              }}
            />
            {veldFout && veldFout !== "Huidig wachtwoord klopt niet." && (
              <p style={{ marginTop: "0.25rem", fontSize: "0.8rem", color: "rgb(var(--fout))" }}>
                {veldFout}
              </p>
            )}
          </div>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button type="submit" className="btn btn-primary">
              Wachtwoord opslaan
            </button>
            {variant === "succes" && (
              <button type="button" className="btn btn-secondary" onClick={reset}>
                Reset mockup
              </button>
            )}
          </div>
        </form>
      </section>

      {/* Sectie 3: Tweestapsverificatie (2FA) — vooruitblik story 017 */}
      <section className="card" style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>Tweestapsverificatie (2FA)</h2>
          <span
            className="badge badge-concept"
            style={{ fontSize: "0.7rem" }}
          >
            Nog niet actief
          </span>
        </div>
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Tweestapsverificatie voegt een extra beveiligingslaag toe aan uw account. Na het inloggen
          vraagt het systeem om een tijdelijke code uit uw authenticator-app.
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <span style={{ fontSize: "0.875rem", color: "rgb(var(--faint))" }}>
            Status: <strong style={{ color: "rgb(var(--ink))" }}>Niet ingeschakeld</strong>
          </span>
          <button
            className="btn btn-secondary"
            disabled
            title="2FA-activering is beschikbaar in story 017"
            style={{ opacity: 0.45, cursor: "not-allowed" }}
          >
            Activeer 2FA
          </button>
        </div>
        <p style={{ fontSize: "0.75rem", color: "rgb(var(--faint))" }}>
          Activatie via instellingen — beschikbaar in een volgende versie (story 017).
        </p>
      </section>
    </div>
  );
}
