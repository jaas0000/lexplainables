"use client";

import { useState, useEffect } from "react";
import type { components } from "@/generated/types";

type WetKeuze = components["schemas"]["WetKeuze"];
type ArtikelKeuze = components["schemas"]["ArtikelKeuze"];

export interface WetSelectorWaarde {
  bwb_id: string;
  artikelen: string[];
}

interface WetSelectorProps {
  /** Wordt aangeroepen zodra de gebruiker een wet en/of artikelen (de-)selecteert. */
  onChange?: (waarde: WetSelectorWaarde | null) => void;
}

interface WettenState {
  data: WetKeuze[];
  laden: boolean;
  fout: string | null;
}

interface ArtikelenState {
  data: ArtikelKeuze[];
  laden: boolean;
  fout: string | null;
}

export function WetSelector({ onChange }: WetSelectorProps) {
  const [wetten, setWetten] = useState<WettenState>({
    data: [],
    laden: true,
    fout: null,
  });
  const [gekozenWet, setGekozenWet] = useState("");
  const [artikelen, setArtikelen] = useState<ArtikelenState>({
    data: [],
    laden: false,
    fout: null,
  });
  const [gekozenArtikelen, setGekozenArtikelen] = useState<string[]>([]);

  // Laad wettenlijst eenmalig bij mount.
  useEffect(() => {
    let actief = true;

    fetch("/api/wetten")
      .then((r) => {
        if (!r.ok) throw new Error(`Fout bij ophalen wetten (${r.status})`);
        return r.json() as Promise<WetKeuze[]>;
      })
      .then((data) => {
        if (actief) setWetten({ data, laden: false, fout: null });
      })
      .catch((e: unknown) => {
        if (actief)
          setWetten({
            data: [],
            laden: false,
            fout: e instanceof Error ? e.message : "Onbekende fout.",
          });
      });

    return () => {
      actief = false;
    };
  }, []);

  // Laad artikelstructuur voor het gegeven bwb_id. Roept setArtikelen aan via closure;
  // geen useCallback nodig omdat de functie alleen vanuit een event handler wordt gebruikt.
  function laadArtikelen(bwb_id: string) {
    setArtikelen({ data: [], laden: true, fout: null });

    fetch(`/api/wetten/${bwb_id}/structuur`)
      .then((r) => {
        if (r.status === 404) throw new Error("Wet niet gevonden.");
        if (!r.ok) throw new Error(`Fout bij ophalen artikelen (${r.status})`);
        return r.json() as Promise<{
          bwb_id: string;
          artikelen: ArtikelKeuze[];
        }>;
      })
      .then((data) => {
        setArtikelen({ data: data.artikelen, laden: false, fout: null });
      })
      .catch((e: unknown) => {
        setArtikelen({
          data: [],
          laden: false,
          fout: e instanceof Error ? e.message : "Onbekende fout.",
        });
      });
  }

  function kiesWet(bwb_id: string) {
    setGekozenWet(bwb_id);
    setGekozenArtikelen([]);
    if (bwb_id) {
      laadArtikelen(bwb_id);
      onChange?.({ bwb_id, artikelen: [] });
    } else {
      setArtikelen({ data: [], laden: false, fout: null });
      onChange?.(null);
    }
  }

  function toggleArtikel(artikel: string) {
    setGekozenArtikelen((prev) => {
      const nieuw = prev.includes(artikel)
        ? prev.filter((a) => a !== artikel)
        : [...prev, artikel];
      onChange?.(gekozenWet ? { bwb_id: gekozenWet, artikelen: nieuw } : null);
      return nieuw;
    });
  }

  if (wetten.laden) {
    return (
      <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))" }}>
        Wetten laden…
      </p>
    );
  }

  if (wetten.fout) {
    return (
      <p
        role="alert"
        style={{ fontSize: "0.875rem", color: "rgb(var(--danger, 220 38 38))" }}
      >
        {wetten.fout}
      </p>
    );
  }

  if (wetten.data.length === 0) {
    return (
      <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))" }}>
        Geen wetten beschikbaar.
      </p>
    );
  }

  return (
    <div style={{ maxWidth: "36rem" }}>
      <div style={{ marginBottom: "1rem" }}>
        <label
          style={{
            display: "block",
            fontSize: "0.8125rem",
            fontWeight: 600,
            marginBottom: "0.375rem",
          }}
        >
          Wet
        </label>
        <select
          className="field-input"
          value={gekozenWet}
          onChange={(e) => kiesWet(e.target.value)}
          style={{ width: "100%" }}
        >
          <option value="">— Kies een wet —</option>
          {wetten.data.map((w) => (
            <option key={w.bwb_id} value={w.bwb_id}>
              {w.naam}
            </option>
          ))}
        </select>
      </div>

      {gekozenWet && (
        <div>
          <label
            style={{
              display: "block",
              fontSize: "0.8125rem",
              fontWeight: 600,
              marginBottom: "0.375rem",
            }}
          >
            Artikelen
            <span
              style={{
                fontWeight: 400,
                color: "rgb(var(--faint))",
                marginLeft: "0.375rem",
              }}
            >
              (één of meer kiezen)
            </span>
          </label>

          {artikelen.laden && (
            <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))" }}>
              Artikelen laden…
            </p>
          )}

          {artikelen.fout && (
            <p
              role="alert"
              style={{
                fontSize: "0.875rem",
                color: "rgb(var(--danger, 220 38 38))",
              }}
            >
              {artikelen.fout}
            </p>
          )}

          {!artikelen.laden &&
            !artikelen.fout &&
            artikelen.data.length === 0 && (
              <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))" }}>
                Geen artikelen beschikbaar voor deze wet.
              </p>
            )}

          {!artikelen.laden && !artikelen.fout && artikelen.data.length > 0 && (
            <div
              style={{
                border: "1px solid rgb(var(--line))",
                borderRadius: "6px",
                overflow: "hidden",
              }}
            >
              {artikelen.data.map((a, i) => (
                <label
                  key={a.artikel}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    padding: "0.5rem 0.75rem",
                    cursor: "pointer",
                    background: gekozenArtikelen.includes(a.artikel)
                      ? "rgb(var(--surface))"
                      : "rgb(var(--paper))",
                    borderTop: i > 0 ? "1px solid rgb(var(--line))" : "none",
                    fontSize: "0.875rem",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={gekozenArtikelen.includes(a.artikel)}
                    onChange={() => toggleArtikel(a.artikel)}
                  />
                  <span style={{ fontWeight: 500, minWidth: "3rem" }}>
                    art. {a.artikel}
                  </span>
                  <span
                    style={{
                      color: "rgb(var(--muted))",
                      fontSize: "0.8125rem",
                    }}
                  >
                    {a.pad}
                  </span>
                </label>
              ))}
            </div>
          )}

          {gekozenArtikelen.length > 0 && (
            <p
              style={{
                marginTop: "0.5rem",
                fontSize: "0.8125rem",
                color: "rgb(var(--muted))",
              }}
            >
              {gekozenArtikelen.length}{" "}
              {gekozenArtikelen.length === 1 ? "artikel" : "artikelen"}{" "}
              geselecteerd
            </p>
          )}
        </div>
      )}

      {!gekozenWet && (
        <p
          style={{
            fontSize: "0.875rem",
            color: "rgb(var(--faint))",
            fontStyle: "italic",
          }}
        >
          Kies een wet om de artikelstructuur te tonen.
        </p>
      )}
    </div>
  );
}
