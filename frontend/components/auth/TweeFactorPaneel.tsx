"use client";

import { useEffect, useState } from "react";
import QRCode from "qrcode";

/** 2FA-paneel voor de account-pagina — activeren via wizard, uitschakelen via code-invoer.
 *
 * De QR-code wordt client-side gerenderd zodat de plaintext-secret uit de `otpauth://`-URI
 * nooit door een derde partij hoeft. `TweeFactorPaneel` accepteert `ingeschakeld` als initial
 * state en spiegelt lokaal, zodat de account-pagina niet hoeft te herladen na een wijziging. */
export function TweeFactorPaneel({
  ingeschakeld: ingeschakeldStart,
}: {
  ingeschakeld: boolean;
}) {
  const [ingeschakeld, setIngeschakeld] = useState(ingeschakeldStart);
  const [otpauthUri, setOtpauthUri] = useState<string | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [fout, setFout] = useState<string | null>(null);
  const [bezig, setBezig] = useState(false);
  const [modus, setModus] = useState<"idle" | "koppelen" | "uitschakelen">(
    "idle",
  );

  useEffect(() => {
    if (!otpauthUri) {
      return;
    }
    let cancelled = false;
    QRCode.toDataURL(otpauthUri, { width: 220 })
      .then((url) => {
        if (!cancelled) setQrDataUrl(url);
      })
      .catch(() => {
        if (!cancelled) setQrDataUrl(null);
      });
    return () => {
      cancelled = true;
    };
  }, [otpauthUri]);

  async function startKoppelen() {
    setFout(null);
    setBezig(true);
    try {
      const res = await fetch("/api/auth/2fa/begin", { method: "POST" });
      if (!res.ok) {
        const detail =
          (await res.json().catch(() => null))?.detail ??
          "Kon 2FA niet starten.";
        setFout(detail);
        return;
      }
      const data = (await res.json()) as { otpauth_uri: string };
      setOtpauthUri(data.otpauth_uri);
      setModus("koppelen");
    } finally {
      setBezig(false);
    }
  }

  async function bevestig() {
    setFout(null);
    setBezig(true);
    try {
      const res = await fetch("/api/auth/2fa/activeer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ totp: code }),
      });
      if (!res.ok) {
        setFout("Ongeldige code. Probeer opnieuw.");
        return;
      }
      setIngeschakeld(true);
      setOtpauthUri(null);
      setCode("");
      setModus("idle");
    } finally {
      setBezig(false);
    }
  }

  async function uitschakel() {
    setFout(null);
    setBezig(true);
    try {
      const res = await fetch("/api/auth/2fa/uitschakel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ totp: code }),
      });
      if (!res.ok) {
        setFout("Ongeldige code. Probeer opnieuw.");
        return;
      }
      setIngeschakeld(false);
      setCode("");
      setModus("idle");
    } finally {
      setBezig(false);
    }
  }

  return (
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
        <span
          className="badge"
          style={{ fontSize: "0.7rem" }}
          aria-label={ingeschakeld ? "Actief" : "Niet actief"}
        >
          {ingeschakeld ? "Actief" : "Niet actief"}
        </span>
      </div>

      <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
        Tweestapsverificatie voegt een extra beveiligingslaag toe aan uw
        account. Na het inloggen vraagt het systeem om een tijdelijke code uit
        uw authenticator-app.
      </p>

      {fout && (
        <p role="alert" className="melding melding-fout" style={{ margin: 0 }}>
          {fout}
        </p>
      )}

      {modus === "idle" && !ingeschakeld && (
        <button
          className="btn btn-primary"
          onClick={startKoppelen}
          disabled={bezig}
          style={{ alignSelf: "flex-start" }}
        >
          {bezig ? "Bezig…" : "Activeer 2FA"}
        </button>
      )}

      {modus === "idle" && ingeschakeld && (
        <button
          className="btn btn-secondary"
          onClick={() => setModus("uitschakelen")}
          disabled={bezig}
          style={{ alignSelf: "flex-start" }}
        >
          2FA uitschakelen
        </button>
      )}

      {modus === "koppelen" && (
        <div
          style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
        >
          <p style={{ fontSize: "0.875rem" }}>
            Scan de QR-code met uw authenticator-app en voer de resulterende
            code hieronder in.
          </p>
          {qrDataUrl && (
            <img
              src={qrDataUrl}
              alt="QR-code voor 2FA-koppeling"
              width={220}
              height={220}
              style={{ background: "white", padding: "0.5rem" }}
            />
          )}
          <label className="field-label" htmlFor="totp-koppel">
            TOTP-code
          </label>
          <input
            id="totp-koppel"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="field-input"
            style={{ maxWidth: "12rem" }}
          />
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              className="btn btn-primary"
              onClick={bevestig}
              disabled={bezig || code.length < 6}
            >
              {bezig ? "Bezig…" : "Bevestig"}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setModus("idle");
                setOtpauthUri(null);
                setCode("");
              }}
              disabled={bezig}
            >
              Annuleer
            </button>
          </div>
        </div>
      )}

      {modus === "uitschakelen" && (
        <div
          style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
        >
          <label className="field-label" htmlFor="totp-uit">
            Voer een geldige TOTP-code in om 2FA uit te schakelen
          </label>
          <input
            id="totp-uit"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="field-input"
            style={{ maxWidth: "12rem" }}
          />
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              className="btn btn-primary"
              onClick={uitschakel}
              disabled={bezig || code.length < 6}
            >
              {bezig ? "Bezig…" : "Uitschakelen"}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setModus("idle");
                setCode("");
              }}
              disabled={bezig}
            >
              Annuleer
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
