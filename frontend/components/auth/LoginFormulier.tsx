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
      // Harde navigatie zodat de middleware-sessiecheck opnieuw loopt.
      // Alleen relatieve URLs toestaan om open redirect te voorkomen.
      const callback = params.get("callbackUrl");
      window.location.href = callback?.startsWith("/") ? callback : "/";
    } finally {
      setBezig(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {fout && (
        <p role="alert" style={{ color: "rgb(213 43 30)", margin: 0 }}>
          {fout}
        </p>
      )}
      <div>
        <label
          htmlFor="gebruikersnaam"
          style={{ display: "block", marginBottom: "0.25rem" }}
        >
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
          style={{ width: "100%" }}
        />
      </div>
      <div>
        <label
          htmlFor="wachtwoord"
          style={{ display: "block", marginBottom: "0.25rem" }}
        >
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
          style={{ width: "100%" }}
        />
      </div>
      <button
        type="submit"
        disabled={bezig}
        className="btn btn-primary"
        style={{ width: "100%" }}
      >
        {bezig ? "Bezig met inloggen…" : "Inloggen"}
      </button>
    </form>
  );
}
