"use client";

import React, { useState } from "react";
import { SectieHeader } from "@/components/beheer/SectieHeader";

// ---- Types ---------------------------------------------------------------

type Rol = "analist" | "beheerder";

interface Gebruiker {
  gebruikersnaam: string;
  rol: Rol;
  actief: boolean;
  bijgewerkt: string;
}

// ---- Nepdata -------------------------------------------------------------

const NEPPE_GEBRUIKERS: Gebruiker[] = [
  {
    gebruikersnaam: "beheerder",
    rol: "beheerder",
    actief: true,
    bijgewerkt: "2026-08-15T10:00:00Z",
  },
  {
    gebruikersnaam: "j.smeets",
    rol: "analist",
    actief: true,
    bijgewerkt: "2026-08-14T08:30:00Z",
  },
  {
    gebruikersnaam: "l.vandijk",
    rol: "analist",
    actief: true,
    bijgewerkt: "2026-08-10T14:15:00Z",
  },
  {
    gebruikersnaam: "m.bakker",
    rol: "analist",
    actief: false,
    bijgewerkt: "2026-08-01T09:00:00Z",
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

function datumLabel(iso: string): string {
  return new Date(iso).toLocaleDateString("nl-NL", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// ---- Component -----------------------------------------------------------

export default function GebruikersbeheerMockup() {
  const [gebruikers, setGebruikers] =
    useState<Gebruiker[]>(NEPPE_GEBRUIKERS);

  // Inline rol-bewerking
  const [bewerkRolVan, setBewerkRolVan] = useState<string | null>(null);
  const [bewerkRolWaarde, setBewerkRolWaarde] = useState<Rol>("analist");

  // Verwijder-bevestiging
  const [verwijderVan, setVerwijderVan] = useState<string | null>(null);

  // Wachtwoord-reset resultaat (eenmalig getoond)
  const [resetResultaat, setResetResultaat] = useState<{
    gebruikersnaam: string;
    wachtwoord: string;
  } | null>(null);

  // Gekopieerd-feedback voor het clipboard
  const [gekopieerd, setGekopieerd] = useState(false);

  // Foutmelding (bijv. laatste beheerder)
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

  function rolBewerkStarten(g: Gebruiker) {
    setBewerkRolVan(g.gebruikersnaam);
    setBewerkRolWaarde(g.rol);
    setFout(null);
    setResetResultaat(null);
  }

  function rolOpslaan(gebruikersnaam: string) {
    const gebruiker = gebruikers.find(
      (g) => g.gebruikersnaam === gebruikersnaam,
    );
    if (
      gebruiker?.rol === "beheerder" &&
      bewerkRolWaarde === "analist" &&
      isLaatsteActieveBeheerder(gebruikersnaam)
    ) {
      setFout(
        "Kan de laatste actieve beheerder niet degraderen tot analist.",
      );
      return;
    }
    setGebruikers((prev) =>
      prev.map((g) =>
        g.gebruikersnaam === gebruikersnaam
          ? { ...g, rol: bewerkRolWaarde, bijgewerkt: new Date().toISOString() }
          : g,
      ),
    );
    setBewerkRolVan(null);
    setFout(null);
  }

  function toggleActief(gebruikersnaam: string) {
    const gebruiker = gebruikers.find(
      (g) => g.gebruikersnaam === gebruikersnaam,
    );
    if (!gebruiker) return;
    if (gebruiker.actief && isLaatsteActieveBeheerder(gebruikersnaam)) {
      setFout("Kan de laatste actieve beheerder niet deactiveren.");
      return;
    }
    setFout(null);
    setGebruikers((prev) =>
      prev.map((g) =>
        g.gebruikersnaam === gebruikersnaam
          ? { ...g, actief: !g.actief, bijgewerkt: new Date().toISOString() }
          : g,
      ),
    );
  }

  function wachtwoordResetten(gebruikersnaam: string) {
    setFout(null);
    setGekopieerd(false);
    setResetResultaat({
      gebruikersnaam,
      wachtwoord: genereerTijdelijkWachtwoord(),
    });
  }

  function kopieerWachtwoord(wachtwoord: string) {
    void navigator.clipboard.writeText(wachtwoord);
    setGekopieerd(true);
    setTimeout(() => setGekopieerd(false), 2000);
  }

  function verwijderenStarten(gebruikersnaam: string) {
    if (isLaatsteActieveBeheerder(gebruikersnaam)) {
      setFout("Kan de laatste actieve beheerder niet verwijderen.");
      return;
    }
    setFout(null);
    setBewerkRolVan(null);
    setVerwijderVan(gebruikersnaam);
  }

  function verwijderenBevestigen() {
    if (!verwijderVan) return;
    setGebruikers((prev) =>
      prev.filter((g) => g.gebruikersnaam !== verwijderVan),
    );
    setVerwijderVan(null);
    setFout(null);
  }

  // ---- Render ------------------------------------------------------------

  const aantalActief = gebruikers.filter((g) => g.actief).length;

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
          <h1 style={{ fontSize: "1.75rem" }}>Gebruikersbeheer</h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgb(var(--muted))",
            }}
          >
            Beheer accounts: rollen, actief-status en wachtwoorden.
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

      {/* ---- Wachtwoord-reset-resultaat ---- */}
      {resetResultaat && (
        <div
          className="melding melding-waarschuwing"
          style={{ flexDirection: "column", gap: "0.75rem" }}
        >
          <div>
            <strong style={{ fontSize: "0.9375rem" }}>
              Tijdelijk wachtwoord — noteer dit nu
            </strong>
            <p
              style={{
                marginTop: "0.25rem",
                fontSize: "0.875rem",
                color: "rgb(var(--ink))",
              }}
            >
              Voor{" "}
              <span
                style={{ fontFamily: "monospace", fontWeight: 600 }}
              >
                {resetResultaat.gebruikersnaam}
              </span>
              :
            </p>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              flexWrap: "wrap",
            }}
          >
            <code
              style={{
                padding: "0.375rem 0.75rem",
                background: "rgb(var(--paper))",
                border: "1px solid rgb(var(--line))",
                borderRadius: "4px",
                fontFamily: "monospace",
                fontSize: "1rem",
                letterSpacing: "0.05em",
                color: "rgb(var(--ink))",
              }}
            >
              {resetResultaat.wachtwoord}
            </code>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: "0.8125rem" }}
              onClick={() => kopieerWachtwoord(resetResultaat.wachtwoord)}
            >
              {gekopieerd ? "Gekopieerd!" : "Kopieer"}
            </button>
          </div>
          <p
            style={{
              fontSize: "0.8125rem",
              color: "rgb(var(--muted))",
              fontStyle: "italic",
            }}
          >
            Dit wachtwoord wordt niet opnieuw getoond. Deel het veilig
            met de gebruiker.
          </p>
          <div>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: "0.8125rem" }}
              onClick={() => setResetResultaat(null)}
            >
              Sluiten
            </button>
          </div>
        </div>
      )}

      {/* ---- Gebruikerstabel ---- */}
      <section>
        <SectieHeader
          titel="Gebruikers"
          aantal={gebruikers.length}
          subtitel={`${aantalActief} actief`}
        />

        {gebruikers.length === 0 ? (
          <p
            style={{
              fontSize: "0.875rem",
              color: "rgb(var(--faint))",
              fontStyle: "italic",
              padding: "1.5rem 0",
            }}
          >
            Geen gebruikers gevonden.
          </p>
        ) : (
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table className="tabel">
              <thead>
                <tr>
                  <th>Gebruikersnaam</th>
                  <th>Rol</th>
                  <th>Actief</th>
                  <th>Bijgewerkt</th>
                  <th>Acties</th>
                </tr>
              </thead>
              <tbody>
                {gebruikers.map((g) => (
                  <tr key={g.gebruikersnaam}>
                    {/* Naam */}
                    <td>
                      <span
                        style={{
                          fontFamily: "monospace",
                          fontWeight: 500,
                          fontSize: "0.875rem",
                        }}
                      >
                        {g.gebruikersnaam}
                      </span>
                    </td>

                    {/* Rol — normaal of inline bewerken */}
                    <td>
                      {bewerkRolVan === g.gebruikersnaam ? (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "0.375rem",
                          }}
                        >
                          <select
                            className="field-input"
                            value={bewerkRolWaarde}
                            onChange={(e) =>
                              setBewerkRolWaarde(e.target.value as Rol)
                            }
                            autoFocus
                            style={{
                              minHeight: "1.875rem",
                              height: "1.875rem",
                              padding: "0.125rem 0.5rem",
                              fontSize: "0.8125rem",
                              width: "auto",
                            }}
                          >
                            <option value="analist">analist</option>
                            <option value="beheerder">beheerder</option>
                          </select>
                          <button
                            type="button"
                            className="btn btn-primary"
                            style={{
                              fontSize: "0.75rem",
                              padding: "0.25rem 0.625rem",
                              minHeight: "1.875rem",
                            }}
                            onClick={() => rolOpslaan(g.gebruikersnaam)}
                          >
                            OK
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{
                              fontSize: "0.75rem",
                              padding: "0.25rem 0.5rem",
                              minHeight: "1.875rem",
                            }}
                            onClick={() => setBewerkRolVan(null)}
                            aria-label="Annuleren"
                          >
                            ×
                          </button>
                        </div>
                      ) : (
                        <span
                          style={{
                            fontSize: "0.875rem",
                            color: "rgb(var(--ink))",
                          }}
                        >
                          {g.rol}
                        </span>
                      )}
                    </td>

                    {/* Actief */}
                    <td>
                      <span
                        className={`badge ${g.actief ? "badge-gepubliceerd" : "badge-concept"}`}
                      >
                        {g.actief ? "ja" : "nee"}
                      </span>
                    </td>

                    {/* Bijgewerkt */}
                    <td
                      style={{
                        fontSize: "0.8125rem",
                        color: "rgb(var(--faint))",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {datumLabel(g.bijgewerkt)}
                    </td>

                    {/* Acties */}
                    <td>
                      <div className="acties">
                        {bewerkRolVan !== g.gebruikersnaam && (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ fontSize: "0.8125rem" }}
                            onClick={() => rolBewerkStarten(g)}
                          >
                            Rol wijzigen
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ fontSize: "0.8125rem" }}
                          onClick={() => toggleActief(g.gebruikersnaam)}
                        >
                          {g.actief ? "Deactiveren" : "Activeren"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ fontSize: "0.8125rem" }}
                          onClick={() =>
                            wachtwoordResetten(g.gebruikersnaam)
                          }
                        >
                          Wachtwoord resetten
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger"
                          style={{ fontSize: "0.8125rem" }}
                          onClick={() =>
                            verwijderenStarten(g.gebruikersnaam)
                          }
                        >
                          Verwijderen
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ---- Verwijder-dialoog (modal overlay) ---- */}
      {verwijderVan && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.35)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
          onClick={() => setVerwijderVan(null)}
        >
          <div
            className="card"
            style={{ maxWidth: 420, width: "90%", boxShadow: "0 8px 32px rgba(0,0,0,0.18)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2
              style={{
                fontSize: "1.0625rem",
                fontWeight: 600,
                marginBottom: "0.75rem",
                color: "rgb(var(--ink))",
              }}
            >
              Account verwijderen
            </h2>
            <p
              style={{
                fontSize: "0.9375rem",
                color: "rgb(var(--ink))",
                marginBottom: "0.25rem",
              }}
            >
              Weet je zeker dat je{" "}
              <span style={{ fontFamily: "monospace", fontWeight: 600 }}>
                {verwijderVan}
              </span>{" "}
              wilt verwijderen?
            </p>
            <p
              style={{
                fontSize: "0.8125rem",
                color: "rgb(var(--muted))",
                marginBottom: "1.25rem",
              }}
            >
              Deze actie kan niet ongedaan worden gemaakt.
            </p>
            <div
              style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}
            >
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setVerwijderVan(null)}
              >
                Annuleren
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={verwijderenBevestigen}
              >
                Ja, verwijderen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
