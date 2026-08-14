"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";

export function LoginFormulier() {
  const params = useSearchParams();
  const [gebruikersnaam, setGebruikersnaam] = useState("");
  const [wachtwoord, setWachtwoord] = useState("");
  const [fout, setFout] = useState<string | null>(null);
  const [bezig, setBezig] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFout(null);
    setBezig(true);
    try {
      const res = await signIn("credentials", {
        redirect: false,
        gebruikersnaam,
        wachtwoord,
      });
      if (res?.error) {
        setFout("Onjuiste gebruikersnaam of wachtwoord.");
        return;
      }
      const callback = params.get("callbackUrl");
      window.location.href = callback?.startsWith("/") ? callback : "/";
    } finally {
      setBezig(false);
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {fout && (
        <p role="alert" className="melding melding-fout" style={{ margin: 0 }}>
          {fout}
        </p>
      )}

      <div>
        <label className="field-label" htmlFor="gebruikersnaam">
          Gebruikersnaam
        </label>
        <input
          id="gebruikersnaam"
          type="text"
          autoComplete="username"
          autoCapitalize="none"
          required
          value={gebruikersnaam}
          onChange={(e) => setGebruikersnaam(e.target.value)}
          className="field-input"
        />
      </div>

      <div>
        <label className="field-label" htmlFor="wachtwoord">
          Wachtwoord
        </label>
        <input
          id="wachtwoord"
          type="password"
          autoComplete="current-password"
          required
          value={wachtwoord}
          onChange={(e) => setWachtwoord(e.target.value)}
          className="field-input"
        />
      </div>

      <label style={{ display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.875rem", color: "rgb(var(--ink))", cursor: "pointer" }}>
        <input
          type="checkbox"
          style={{ marginTop: "0.125rem", width: "1rem", height: "1rem", accentColor: "rgb(var(--lint))", flexShrink: 0 }}
        />
        <span>
          Ingelogd blijven op dit apparaat
          <span style={{ display: "block", fontSize: "0.75rem", color: "rgb(var(--muted))", marginTop: "0.125rem" }}>
            30 dagen ingelogd blijven en 2FA overslaan op dit apparaat.
          </span>
        </span>
      </label>

      <button type="submit" disabled={bezig} className="btn btn-primary" style={{ width: "100%" }}>
        {bezig ? "Bezig met inloggen…" : "Inloggen"}
      </button>
    </form>
  );
}
