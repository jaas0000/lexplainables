"use client";

import { useEffect, useState } from "react";
import type { components } from "@/generated/types";

type MijnProfiel = components["schemas"]["MijnProfiel"];

const rijStijl = {
  display: "grid",
  gridTemplateColumns: "10rem 1fr",
  gap: "0.25rem 1rem",
  alignItems: "baseline",
} as const;

export default function AccountPagina() {
  const [profiel, setProfiel] = useState<MijnProfiel | null>(null);
  const [laden, setLaden] = useState(true);

  const [huidigWachtwoord, setHuidigWachtwoord] = useState("");
  const [nieuwWachtwoord, setNieuwWachtwoord] = useState("");
  const [bevestigWachtwoord, setBevestigWachtwoord] = useState("");

  // Twee aparte fout-states zodat het veld voor "huidig" en het veld voor "nieuw/bevestig"
  // elk hun eigen foutmelding tonen zonder string-vergelijking als discriminator.
  const [huidigFout, setHuidigFout] = useState<string | null>(null);
  const [nieuwFout, setNieuwFout] = useState<string | null>(null);
  const [succes, setSucces] = useState(false);
  const [bezig, setBezig] = useState(false);

  useEffect(() => {
    async function laadProfiel() {
      try {
        const res = await fetch("/api/auth/me");
        if (res.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!res.ok) throw new Error(`${res.status}`);
        setProfiel(await res.json());
      } catch {
        // Fout tonen is niet nodig — 401 redirect vangt het meeste op.
      } finally {
        setLaden(false);
      }
    }
    laadProfiel();
  }, []);

  async function handleWachtwoordWijzigen(e: React.FormEvent) {
    e.preventDefault();
    setHuidigFout(null);
    setNieuwFout(null);
    setSucces(false);

    if (nieuwWachtwoord.length < 8) {
      setNieuwFout("Het nieuwe wachtwoord moet minimaal 8 tekens zijn.");
      return;
    }
    if (nieuwWachtwoord !== bevestigWachtwoord) {
      setNieuwFout(
        "Het nieuwe wachtwoord en de bevestiging komen niet overeen.",
      );
      return;
    }

    setBezig(true);
    try {
      const res = await fetch("/api/auth/wijzig-wachtwoord", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          huidig_wachtwoord: huidigWachtwoord,
          nieuw_wachtwoord: nieuwWachtwoord,
        }),
      });

      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (res.status === 400) {
        const data = await res.json().catch(() => ({}));
        setHuidigFout(
          (data as { detail?: string }).detail ?? "Huidig wachtwoord klopt niet.",
        );
        return;
      }
      if (!res.ok) {
        setNieuwFout("Er is een fout opgetreden. Probeer het opnieuw.");
        return;
      }

      setSucces(true);
      setHuidigWachtwoord("");
      setNieuwWachtwoord("");
      setBevestigWachtwoord("");
    } finally {
      setBezig(false);
    }
  }

  const rolLabel: Record<string, string> = {
    beheerder: "Beheerder",
    analist: "Analist",
  };

  if (laden) {
    return (
      <div style={{ color: "rgb(var(--muted))", fontSize: "0.875rem" }}>
        Laden…
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <h1 style={{ fontSize: "1.375rem" }}>Account</h1>

      {/* Sectie 1: Mijn gegevens */}
      <section
        className="card"
        style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
      >
        <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>Mijn gegevens</h2>
        {profiel ? (
          <dl
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.625rem",
              fontSize: "0.875rem",
            }}
          >
            <div style={rijStijl}>
              <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>
                Gebruikersnaam
              </dt>
              <dd style={{ color: "rgb(var(--ink))" }}>
                {profiel.gebruikersnaam}
              </dd>
            </div>
            <div style={rijStijl}>
              <dt style={{ color: "rgb(var(--muted))", fontWeight: 500 }}>
                Rol
              </dt>
              <dd>
                <span className="badge badge-concept">
                  {rolLabel[profiel.rol] ?? profiel.rol}
                </span>
              </dd>
            </div>
          </dl>
        ) : (
          <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
            Gegevens konden niet worden geladen.
          </p>
        )}
      </section>

      {/* Sectie 2: Wachtwoord wijzigen */}
      <section
        className="card"
        style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
      >
        <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>
          Wachtwoord wijzigen
        </h2>

        {succes && (
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
                if (huidigFout) setHuidigFout(null);
              }}
              autoComplete="current-password"
              required
              style={{
                maxWidth: "24rem",
                borderColor: huidigFout ? "rgb(var(--fout))" : undefined,
              }}
            />
            {huidigFout && (
              <p
                role="alert"
                style={{
                  marginTop: "0.25rem",
                  fontSize: "0.8rem",
                  color: "rgb(var(--fout))",
                }}
              >
                {huidigFout}
              </p>
            )}
          </div>

          <div>
            <label className="field-label" htmlFor="nieuw-wachtwoord">
              Nieuw wachtwoord
              <span
                style={{
                  fontWeight: 400,
                  color: "rgb(var(--faint))",
                  marginLeft: "0.375rem",
                }}
              >
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
                if (nieuwFout) setNieuwFout(null);
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
                if (nieuwFout) setNieuwFout(null);
              }}
              autoComplete="new-password"
              required
              style={{
                maxWidth: "24rem",
                borderColor: nieuwFout ? "rgb(var(--fout))" : undefined,
              }}
            />
            {nieuwFout && (
              <p
                role="alert"
                style={{
                  marginTop: "0.25rem",
                  fontSize: "0.8rem",
                  color: "rgb(var(--fout))",
                }}
              >
                {nieuwFout}
              </p>
            )}
          </div>

          <div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={bezig}
            >
              {bezig ? "Bezig…" : "Wachtwoord opslaan"}
            </button>
          </div>
        </form>
      </section>

      {/* Sectie 3: Tweestapsverificatie (2FA) — vooruitblik story 017 */}
      <section
        className="card"
        style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}
        >
          <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>
            Tweestapsverificatie (2FA)
          </h2>
          <span className="badge badge-concept" style={{ fontSize: "0.7rem" }}>
            Nog niet actief
          </span>
        </div>
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Tweestapsverificatie voegt een extra beveiligingslaag toe aan uw
          account. Na het inloggen vraagt het systeem om een tijdelijke code uit
          uw authenticator-app.
        </p>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            flexWrap: "wrap",
          }}
        >
          <span style={{ fontSize: "0.875rem", color: "rgb(var(--faint))" }}>
            Status:{" "}
            <strong style={{ color: "rgb(var(--ink))" }}>
              Niet ingeschakeld
            </strong>
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
          Activatie via instellingen — beschikbaar in een volgende versie (story
          017).
        </p>
      </section>
    </div>
  );
}
