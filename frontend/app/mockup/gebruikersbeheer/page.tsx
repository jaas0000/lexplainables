"use client";

import React, { useState } from "react";
import { SectieHeader } from "@/components/beheer/SectieHeader";

// ---- Types ---------------------------------------------------------------

type Rol = "analist" | "beheerder";

interface Gebruiker {
  gebruikersnaam: string;
  email: string;
  rol: Rol;
  actief: boolean;
  totp: boolean;
}

// ---- Nepdata -------------------------------------------------------------

const NEPPE_GEBRUIKERS: Gebruiker[] = [
  {
    gebruikersnaam: "beheerder",
    email: "beheerder@belastingdienst.nl",
    rol: "beheerder",
    actief: true,
    totp: false,
  },
  {
    gebruikersnaam: "j.smeets",
    email: "j.smeets@belastingdienst.nl",
    rol: "analist",
    actief: true,
    totp: true,
  },
  {
    gebruikersnaam: "l.vandijk",
    email: "l.vandijk@belastingdienst.nl",
    rol: "analist",
    actief: true,
    totp: false,
  },
  {
    gebruikersnaam: "m.bakker",
    email: "m.bakker@belastingdienst.nl",
    rol: "analist",
    actief: false,
    totp: false,
  },
];

// ---- Hulpfuncties --------------------------------------------------------

function genereerTijdelijkWachtwoord(): string {
  const chars =
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  return Array.from(
    { length: 14 },
    () => chars[Math.floor(Math.random() * chars.length)],
  ).join("");
}

// ---- Tag-stijl (wetsanalyse-ai Tag component equivalent) -----------------

const tagStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  borderRadius: "3px",
  border: "1px solid rgb(var(--line))",
  background: "rgb(var(--surface))",
  padding: "0.125rem 0.5rem",
  fontFamily: "monospace",
  fontSize: "0.75rem",
  color: "rgb(var(--muted))",
  flexShrink: 0,
};

// ---- Component -----------------------------------------------------------

export default function GebruikersbeheerMockup() {
  const [gebruikers, setGebruikers] =
    useState<Gebruiker[]>(NEPPE_GEBRUIKERS);

  // Nieuw-gebruiker-formulier
  const [nieuwGebruikersnaam, setNieuwGebruikersnaam] = useState("");
  const [nieuwEmail, setNieuwEmail] = useState("");
  const [nieuwRol, setNieuwRol] = useState<Rol>("analist");

  // Tijdelijk wachtwoord (eenmalig getoond)
  const [tijdelijk, setTijdelijk] = useState<{
    gebruikersnaam: string;
    wachtwoord: string;
  } | null>(null);

  // Foutmelding
  const [fout, setFout] = useState<string | null>(null);

  // ---- Berekende waarden -------------------------------------------------

  const actieveBeheerders = gebruikers.filter(
    (g) => g.rol === "beheerder" && g.actief,
  );

  function isLaatsteActieveBeheerder(gebruikersnaam: string): boolean {
    return (
      actieveBeheerders.length === 1 &&
      actieveBeheerders[0].gebruikersnaam === gebruikersnaam
    );
  }

  // ---- Acties ------------------------------------------------------------

  function onAanmaken(e: React.FormEvent) {
    e.preventDefault();
    if (!nieuwGebruikersnaam.trim()) return;
    const nieuw: Gebruiker = {
      gebruikersnaam: nieuwGebruikersnaam.trim(),
      email:
        nieuwEmail.trim() ||
        `${nieuwGebruikersnaam.trim()}@belastingdienst.nl`,
      rol: nieuwRol,
      actief: true,
      totp: false,
    };
    const wachtwoord = genereerTijdelijkWachtwoord();
    setGebruikers((prev) => [...prev, nieuw]);
    setTijdelijk({ gebruikersnaam: nieuw.gebruikersnaam, wachtwoord });
    setNieuwGebruikersnaam("");
    setNieuwEmail("");
    setNieuwRol("analist");
    setFout(null);
  }

  function onRol(gebruikersnaam: string) {
    const g = gebruikers.find((u) => u.gebruikersnaam === gebruikersnaam);
    if (!g) return;
    if (
      g.rol === "beheerder" &&
      isLaatsteActieveBeheerder(gebruikersnaam)
    ) {
      setFout(
        "Kan de laatste actieve beheerder niet degraderen tot analist.",
      );
      return;
    }
    setFout(null);
    const nieuweRol: Rol = g.rol === "beheerder" ? "analist" : "beheerder";
    setGebruikers((prev) =>
      prev.map((u) =>
        u.gebruikersnaam === gebruikersnaam ? { ...u, rol: nieuweRol } : u,
      ),
    );
  }

  function onActief(gebruikersnaam: string) {
    const g = gebruikers.find((u) => u.gebruikersnaam === gebruikersnaam);
    if (!g) return;
    if (g.actief && isLaatsteActieveBeheerder(gebruikersnaam)) {
      setFout("Kan de laatste actieve beheerder niet deactiveren.");
      return;
    }
    setFout(null);
    setGebruikers((prev) =>
      prev.map((u) =>
        u.gebruikersnaam === gebruikersnaam
          ? { ...u, actief: !u.actief }
          : u,
      ),
    );
  }

  function onReset(gebruikersnaam: string) {
    setFout(null);
    setTijdelijk({
      gebruikersnaam,
      wachtwoord: genereerTijdelijkWachtwoord(),
    });
  }

  function onVerwijder(gebruikersnaam: string) {
    if (isLaatsteActieveBeheerder(gebruikersnaam)) {
      setFout("Kan de laatste actieve beheerder niet verwijderen.");
      return;
    }
    if (!confirm(`Gebruiker "${gebruikersnaam}" verwijderen?`)) return;
    setFout(null);
    setGebruikers((prev) =>
      prev.filter((u) => u.gebruikersnaam !== gebruikersnaam),
    );
  }

  // ---- Render ------------------------------------------------------------

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* ---- Paginaheader ---- */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
        <div>
          <h1
            style={{ fontSize: "1.875rem", fontWeight: 600 }}
          >
            Gebruikersbeheer
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgb(var(--muted))",
            }}
          >
            Beheer accounts, rollen, actief-status en wachtwoorden.
          </p>
        </div>
        <span
          style={{
            fontSize: "0.75rem",
            padding: "0.125rem 0.625rem",
            background: "rgb(var(--waarschuwing) / 0.1)",
            color: "rgb(var(--waarschuwing))",
            border: "1px solid rgb(var(--waarschuwing) / 0.3)",
            borderRadius: "9999px",
            flexShrink: 0,
            marginTop: "0.25rem",
          }}
        >
          mockup — nepdata
        </span>
      </div>

      {/* ---- Foutmelding ---- */}
      {fout && (
        <div
          className="melding melding-fout"
          role="alert"
          style={{ justifyContent: "space-between" }}
        >
          <p>{fout}</p>
          <button
            type="button"
            onClick={() => setFout(null)}
            aria-label="Sluiten"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: "1rem",
              color: "inherit",
              lineHeight: 1,
              padding: "0 0.25rem",
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* ---- Tijdelijk wachtwoord ---- */}
      {tijdelijk && (
        <div
          className="melding melding-waarschuwing"
          style={{ flexDirection: "column", gap: "0.5rem" }}
        >
          <strong style={{ fontSize: "0.9375rem" }}>
            Tijdelijk wachtwoord — noteer dit nu
          </strong>
          <p style={{ fontSize: "0.875rem" }}>
            Voor{" "}
            <span style={{ fontWeight: 500 }}>
              {tijdelijk.gebruikersnaam}
            </span>
            :{" "}
            <code
              style={{
                borderRadius: "3px",
                background: "rgb(var(--paper))",
                padding: "0.125rem 0.375rem",
                fontFamily: "monospace",
                fontSize: "0.875rem",
              }}
            >
              {tijdelijk.wachtwoord}
            </code>
          </p>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.75rem",
              color: "rgb(var(--muted))",
            }}
          >
            Dit wachtwoord wordt niet opnieuw getoond. Deel het veilig; de
            gebruiker logt er meteen mee in.
          </p>
          <div style={{ marginTop: "0.25rem" }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: "0.8125rem" }}
              onClick={() => setTijdelijk(null)}
            >
              Sluiten
            </button>
          </div>
        </div>
      )}

      {/* ---- Gebruikerssectie ---- */}
      <section>
        <SectieHeader
          titel="Gebruikers"
          aantal={gebruikers.length}
          subtitel="Toegang tot de webapp"
        />

        {/* Toevoeg-formulier */}
        <form
          onSubmit={onAanmaken}
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "0.75rem",
            alignItems: "flex-end",
            marginBottom: "1rem",
          }}
        >
          <div>
            <label
              className="field-label"
              htmlFor="nieuw-gebruikersnaam"
            >
              Gebruikersnaam
            </label>
            <input
              id="nieuw-gebruikersnaam"
              type="text"
              className="field-input"
              required
              autoCapitalize="none"
              placeholder="jdoe"
              value={nieuwGebruikersnaam}
              onChange={(e) => setNieuwGebruikersnaam(e.target.value)}
              style={{ width: "12rem" }}
            />
          </div>
          <div style={{ flex: 1, minWidth: "14rem" }}>
            <label className="field-label" htmlFor="nieuw-email">
              E-mailadres
            </label>
            <input
              id="nieuw-email"
              type="email"
              className="field-input"
              required
              placeholder="naam@belastingdienst.nl"
              value={nieuwEmail}
              onChange={(e) => setNieuwEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="field-label" htmlFor="nieuw-rol">
              Rol
            </label>
            <select
              id="nieuw-rol"
              className="field-input"
              value={nieuwRol}
              onChange={(e) => setNieuwRol(e.target.value as Rol)}
              style={{ width: "auto" }}
            >
              <option value="analist">analist</option>
              <option value="beheerder">beheerder</option>
            </select>
          </div>
          <button type="submit" className="btn btn-primary">
            Gebruiker toevoegen
          </button>
        </form>

        {/* Gebruikerslijst */}
        {gebruikers.length === 0 ? (
          <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
            Nog geen gebruikers.
          </p>
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
            }}
          >
            {gebruikers.map((g) => (
              <div
                key={g.gebruikersnaam}
                className="card"
                style={{ padding: "1rem" }}
              >
                {/* Info-rij */}
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    alignItems: "center",
                    gap: "0.75rem",
                  }}
                >
                  <span
                    style={{ fontWeight: 600, color: "rgb(var(--ink))" }}
                  >
                    {g.gebruikersnaam}
                  </span>
                  <span
                    style={{
                      fontSize: "0.875rem",
                      color: "rgb(var(--muted))",
                    }}
                  >
                    {g.email}
                  </span>
                  <span style={tagStyle}>{g.rol}</span>
                  {g.totp && <span style={tagStyle}>2FA ✓</span>}
                  {!g.actief && (
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        borderRadius: "9999px",
                        border: "1px solid rgb(213 43 30 / 0.4)",
                        background: "rgb(213 43 30 / 0.1)",
                        padding: "0.125rem 0.625rem",
                        fontSize: "0.75rem",
                        fontWeight: 500,
                        color: "rgb(var(--fout))",
                        flexShrink: 0,
                      }}
                    >
                      gedeactiveerd
                    </span>
                  )}
                </div>

                {/* Acties-rij */}
                <div
                  className="acties"
                  style={{ marginTop: "0.75rem" }}
                >
                  <button
                    type="button"
                    className="btn"
                    style={{
                      fontSize: "0.8125rem",
                      color: "rgb(var(--muted))",
                      border: "1px solid transparent",
                    }}
                    onClick={() => onRol(g.gebruikersnaam)}
                  >
                    {g.rol === "beheerder"
                      ? "Maak analist"
                      : "Maak beheerder"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.8125rem" }}
                    onClick={() => onActief(g.gebruikersnaam)}
                  >
                    {g.actief ? "Deactiveren" : "Activeren"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.8125rem" }}
                    onClick={() => onReset(g.gebruikersnaam)}
                  >
                    Wachtwoord resetten
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger"
                    style={{ fontSize: "0.8125rem" }}
                    onClick={() => onVerwijder(g.gebruikersnaam)}
                  >
                    Verwijderen
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
