"use client";

import React, { useEffect, useState } from "react";
import { SectieHeader } from "@/components/beheer/SectieHeader";
import { beheerFetch, BeheerFetchFout } from "@/lib/beheer-fetch";
import type { components } from "@/generated/types";

// ---- Types ---------------------------------------------------------------

type GebruikerRead = components["schemas"]["GebruikerRead"];
type Rol = "analist" | "beheerder";

// ---- Tag-stijl -----------------------------------------------------------

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

export default function GebruikersbeheerPagina() {
  const [gebruikers, setGebruikers] = useState<GebruikerRead[] | null>(null);
  const [laden, setLaden] = useState(false);

  // Nieuw-gebruiker-formulier
  const [nieuwGebruikersnaam, setNieuwGebruikersnaam] = useState("");
  const [nieuwWachtwoord, setNieuwWachtwoord] = useState("");
  const [nieuwRol, setNieuwRol] = useState<Rol>("analist");
  const [nieuwLaden, setNieuwLaden] = useState(false);

  // Tijdelijk wachtwoord (eenmalig getoond)
  const [tijdelijk, setTijdelijk] = useState<{
    gebruikersnaam: string;
    wachtwoord: string;
  } | null>(null);

  // Fout- en succesmelding
  const [fout, setFout] = useState<string | null>(null);
  // refreshKey bumpen herlaadt de gebruikerslijst (gebruikt door fout-handlers).
  const [refreshKey, setRefreshKey] = useState(0);

  // ---- Data laden ---------------------------------------------------------

  function herlaad() {
    setRefreshKey((k) => k + 1);
  }

  useEffect(() => {
    let actief = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLaden(true);
    setFout(null);
    beheerFetch("/api/admin/gebruikers")
      .then((data) => {
        if (actief) setGebruikers(data as GebruikerRead[]);
      })
      .catch((err: unknown) => {
        if (actief)
          setFout(
            err instanceof Error
              ? err.message
              : "Fout bij het ophalen van gebruikers.",
          );
      })
      .finally(() => {
        if (actief) setLaden(false);
      });
    return () => {
      actief = false;
    };
  }, [refreshKey]);

  // ---- Acties -------------------------------------------------------------

  async function onAanmaken(e: React.FormEvent) {
    e.preventDefault();
    if (!nieuwGebruikersnaam.trim() || !nieuwWachtwoord.trim()) return;
    setNieuwLaden(true);
    setFout(null);
    try {
      const nieuw = (await beheerFetch("/api/admin/gebruikers", {
        method: "POST",
        body: JSON.stringify({
          gebruikersnaam: nieuwGebruikersnaam.trim(),
          wachtwoord: nieuwWachtwoord,
          rol: nieuwRol,
        }),
      })) as GebruikerRead;
      setGebruikers((prev) => (prev ? [...prev, nieuw] : [nieuw]));
      setNieuwGebruikersnaam("");
      setNieuwWachtwoord("");
      setNieuwRol("analist");
    } catch (err) {
      setFout(
        err instanceof BeheerFetchFout && err.status === 409
          ? `Gebruikersnaam '${nieuwGebruikersnaam.trim()}' is al in gebruik.`
          : err instanceof Error
            ? err.message
            : "Fout bij aanmaken.",
      );
    } finally {
      setNieuwLaden(false);
    }
  }

  async function onPatch(
    gebruikersnaam: string,
    patch: { rol?: Rol; actief?: boolean },
  ) {
    setFout(null);
    try {
      const bijgewerkt = (await beheerFetch(
        `/api/admin/gebruikers/${gebruikersnaam}`,
        { method: "PATCH", body: JSON.stringify(patch) },
      )) as GebruikerRead;
      setGebruikers(
        (prev) =>
          prev?.map((g) =>
            g.gebruikersnaam === gebruikersnaam ? bijgewerkt : g,
          ) ?? null,
      );
    } catch (err) {
      if (err instanceof BeheerFetchFout && err.status === 409) {
        setFout(
          "Kan de laatste actieve beheerder niet deactiveren of degraderen.",
        );
      } else if (err instanceof BeheerFetchFout && err.status === 404) {
        setFout("Gebruiker niet gevonden — herlaad de pagina.");
        herlaad();
      } else {
        setFout(err instanceof Error ? err.message : "Fout bij bewerken.");
      }
    }
  }

  async function onReset(gebruikersnaam: string) {
    setFout(null);
    setTijdelijk(null);
    try {
      const result = (await beheerFetch(
        `/api/admin/gebruikers/${gebruikersnaam}/reset-wachtwoord`,
        { method: "POST" },
      )) as { gebruikersnaam: string; tijdelijk_wachtwoord: string };
      setTijdelijk({
        gebruikersnaam: result.gebruikersnaam,
        wachtwoord: result.tijdelijk_wachtwoord,
      });
    } catch (err) {
      setFout(
        err instanceof Error ? err.message : "Fout bij wachtwoord-reset.",
      );
    }
  }

  async function onVerwijder(gebruikersnaam: string) {
    if (!confirm(`Gebruiker "${gebruikersnaam}" verwijderen?`)) return;
    setFout(null);
    try {
      await beheerFetch(`/api/admin/gebruikers/${gebruikersnaam}`, {
        method: "DELETE",
      });
      setGebruikers(
        (prev) =>
          prev?.filter((g) => g.gebruikersnaam !== gebruikersnaam) ?? null,
      );
    } catch (err) {
      if (err instanceof BeheerFetchFout && err.status === 409) {
        setFout("Kan de laatste actieve beheerder niet verwijderen.");
      } else if (err instanceof BeheerFetchFout && err.status === 404) {
        setFout("Gebruiker niet gevonden — lijst wordt herladen.");
        herlaad();
      } else {
        setFout(err instanceof Error ? err.message : "Fout bij verwijderen.");
      }
    }
  }

  // ---- Render -------------------------------------------------------------

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* ---- Paginaheader ---- */}
      <div>
        <h1 style={{ fontSize: "1.875rem", fontWeight: 600 }}>
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
            <span style={{ fontWeight: 500 }}>{tijdelijk.gebruikersnaam}</span>:{" "}
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
          aantal={gebruikers?.length}
          subtitel="Toegang tot de webapp"
        />

        {/* Toevoeg-formulier */}
        <form
          onSubmit={(e) => {
            void onAanmaken(e);
          }}
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "0.75rem",
            alignItems: "flex-end",
            marginBottom: "1rem",
          }}
        >
          <div>
            <label className="field-label" htmlFor="nieuw-gebruikersnaam">
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
          <div>
            <label className="field-label" htmlFor="nieuw-wachtwoord">
              Wachtwoord
            </label>
            <input
              id="nieuw-wachtwoord"
              type="password"
              className="field-input"
              required
              minLength={8}
              placeholder="min. 8 tekens"
              value={nieuwWachtwoord}
              onChange={(e) => setNieuwWachtwoord(e.target.value)}
              style={{ width: "12rem" }}
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
          <button
            type="submit"
            className="btn btn-primary"
            disabled={nieuwLaden}
          >
            {nieuwLaden ? "Bezig…" : "Gebruiker toevoegen"}
          </button>
        </form>

        {/* Gebruikerslijst */}
        {laden && (
          <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
            Laden…
          </p>
        )}
        {!laden && gebruikers?.length === 0 && (
          <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
            Nog geen gebruikers.
          </p>
        )}
        {!laden && gebruikers && gebruikers.length > 0 && (
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
                  <span style={{ fontWeight: 600, color: "rgb(var(--ink))" }}>
                    {g.gebruikersnaam}
                  </span>
                  <span style={tagStyle}>{g.rol}</span>
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
                <div className="acties" style={{ marginTop: "0.75rem" }}>
                  <button
                    type="button"
                    className="btn"
                    style={{
                      fontSize: "0.8125rem",
                      color: "rgb(var(--muted))",
                      border: "1px solid transparent",
                    }}
                    onClick={() =>
                      void onPatch(g.gebruikersnaam, {
                        rol: g.rol === "beheerder" ? "analist" : "beheerder",
                      })
                    }
                  >
                    {g.rol === "beheerder" ? "Maak analist" : "Maak beheerder"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.8125rem" }}
                    onClick={() =>
                      void onPatch(g.gebruikersnaam, { actief: !g.actief })
                    }
                  >
                    {g.actief ? "Deactiveren" : "Activeren"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.8125rem" }}
                    onClick={() => void onReset(g.gebruikersnaam)}
                  >
                    Wachtwoord resetten
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger"
                    style={{ fontSize: "0.8125rem" }}
                    onClick={() => void onVerwijder(g.gebruikersnaam)}
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
