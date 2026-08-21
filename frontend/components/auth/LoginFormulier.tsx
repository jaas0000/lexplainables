"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";

export function LoginFormulier() {
  const params = useSearchParams();
  const [gebruikersnaam, setGebruikersnaam] = useState("");
  const [wachtwoord, setWachtwoord] = useState("");
  const [totp, setTotp] = useState("");
  const [totpVereist, setTotpVereist] = useState(false);
  const [fout, setFout] = useState<string | null>(null);
  const [bezig, setBezig] = useState(false);

  async function verstuur(totpCode?: string) {
    const res = await signIn("credentials", {
      redirect: false,
      gebruikersnaam,
      wachtwoord,
      totp: totpCode,
    });
    if (res?.error === "TotpRequired") {
      // Wachtwoord klopt maar 2FA aan → toon tweede scherm.
      setTotpVereist(true);
      setFout(null);
      return;
    }
    if (res?.error) {
      setFout(
        totpVereist
          ? "Ongeldige TOTP-code."
          : "Onjuiste gebruikersnaam of wachtwoord.",
      );
      return;
    }
    const callback = params.get("callbackUrl");
    window.location.href = callback?.startsWith("/") ? callback : "/";
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFout(null);
    setBezig(true);
    try {
      await verstuur(totpVereist ? totp : undefined);
    } finally {
      setBezig(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
    >
      {fout && (
        <p role="alert" className="melding melding-fout" style={{ margin: 0 }}>
          {fout}
        </p>
      )}

      {!totpVereist && (
        <>
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
        </>
      )}

      {totpVereist && (
        <div>
          <label className="field-label" htmlFor="totp">
            Tweestapsverificatiecode
          </label>
          <input
            id="totp"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            required
            minLength={6}
            maxLength={16}
            value={totp}
            onChange={(e) => setTotp(e.target.value)}
            className="field-input"
            placeholder="6-cijferige code uit de app"
          />
          <p
            style={{
              marginTop: "0.5rem",
              fontSize: "0.8rem",
              color: "rgb(var(--muted))",
            }}
          >
            Voer de code in uit uw authenticator-app.
          </p>
        </div>
      )}

      <button
        type="submit"
        disabled={bezig}
        className="btn btn-primary"
        style={{ width: "100%" }}
      >
        {bezig
          ? "Bezig met inloggen…"
          : totpVereist
            ? "Code bevestigen"
            : "Inloggen"}
      </button>
    </form>
  );
}
