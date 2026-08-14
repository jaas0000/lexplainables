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

      <button type="submit" disabled={bezig} className="btn btn-primary" style={{ width: "100%" }}>
        {bezig ? "Bezig met inloggen…" : "Inloggen"}
      </button>
    </form>
  );
}
