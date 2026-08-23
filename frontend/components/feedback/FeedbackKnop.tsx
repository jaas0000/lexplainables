"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import {
  CATEGORIE_META,
  CATEGORIEN,
  type Categorie,
} from "@/lib/feedback-types";
import { useClickOutside } from "@/lib/useClickOutside";

export function FeedbackKnop() {
  const pathname = usePathname();
  const [panelOpen, setPanelOpen] = useState(false);
  const [verzonden, setVerzonden] = useState(false);
  const [laden, setLaden] = useState(false);
  const [fout, setFout] = useState<string | null>(null);
  const [categorie, setCategorie] = useState<Categorie>("verbeteridee");
  const [tekst, setTekst] = useState("");
  const panelRef = useRef<HTMLDivElement>(null);
  const verzondenTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useClickOutside(panelRef, panelOpen, () => setPanelOpen(false));

  useEffect(() => {
    return () => {
      if (verzondenTimeout.current) clearTimeout(verzondenTimeout.current);
    };
  }, []);

  async function handleVerzenden() {
    if (!tekst.trim()) {
      setFout("Vul uw opmerking in.");
      return;
    }
    setLaden(true);
    setFout(null);
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ categorie, tekst, pagina: pathname }),
      });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        const detail = await res
          .json()
          .then((d: { detail?: string }) => d.detail)
          .catch(() => null);
        setFout(detail ?? `${res.status} ${res.statusText}`);
        return;
      }
      setVerzonden(true);
      verzondenTimeout.current = setTimeout(() => {
        setVerzonden(false);
        setPanelOpen(false);
        setTekst("");
        setCategorie("verbeteridee");
      }, 2000);
    } catch {
      setFout("Verbindingsfout. Probeer het opnieuw.");
    } finally {
      setLaden(false);
    }
  }

  return (
    <>
      {panelOpen && (
        <div
          ref={panelRef}
          style={{
            position: "fixed",
            bottom: "5rem",
            right: "1.5rem",
            width: "22rem",
            maxWidth: "calc(100vw - 3rem)",
            background: "rgb(var(--paper))",
            border: "1px solid rgb(var(--line))",
            borderRadius: "8px",
            boxShadow: "0 8px 24px rgb(0 0 0 / 0.12)",
            overflow: "hidden",
            zIndex: 1000,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0.75rem 1rem",
              borderBottom: "1px solid rgb(var(--line))",
              background: "rgb(var(--surface))",
            }}
          >
            <span style={{ fontSize: "0.875rem", fontWeight: 600 }}>
              Geef feedback
            </span>
            <button
              onClick={() => setPanelOpen(false)}
              aria-label="Sluiten"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "rgb(var(--muted))",
                fontSize: "1rem",
                lineHeight: 1,
                padding: "0.125rem 0.25rem",
              }}
            >
              ✕
            </button>
          </div>

          {verzonden ? (
            <div
              style={{
                padding: "2rem 1rem",
                textAlign: "center",
                color: "rgb(var(--succes))",
                fontSize: "0.875rem",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden
              >
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.59L5.41 12l1.42-1.42L10 13.17l7.17-7.17 1.42 1.42L10 16.59z" />
              </svg>
              Bedankt voor uw feedback!
            </div>
          ) : (
            <div
              style={{
                padding: "1rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.75rem",
              }}
            >
              {fout && (
                <p
                  role="alert"
                  style={{
                    fontSize: "0.8125rem",
                    color: "rgb(var(--fout))",
                    margin: 0,
                  }}
                >
                  {fout}
                </p>
              )}
              <div>
                <label
                  htmlFor="feedback-categorie"
                  style={{
                    display: "block",
                    fontSize: "0.8125rem",
                    fontWeight: 500,
                    marginBottom: "0.25rem",
                    color: "rgb(var(--ink))",
                  }}
                >
                  Categorie
                </label>
                <select
                  id="feedback-categorie"
                  value={categorie}
                  onChange={(e) => setCategorie(e.target.value as Categorie)}
                  style={{
                    width: "100%",
                    padding: "0.375rem 0.5rem",
                    fontSize: "0.8125rem",
                    border: "1px solid rgb(var(--line))",
                    borderRadius: "4px",
                    background: "rgb(var(--paper))",
                    color: "rgb(var(--ink))",
                  }}
                >
                  {CATEGORIEN.map((c) => (
                    <option key={c} value={c}>
                      {CATEGORIE_META[c].label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label
                  htmlFor="feedback-tekst"
                  style={{
                    display: "block",
                    fontSize: "0.8125rem",
                    fontWeight: 500,
                    marginBottom: "0.25rem",
                    color: "rgb(var(--ink))",
                  }}
                >
                  Uw opmerking{" "}
                  <span style={{ fontWeight: 400, color: "rgb(var(--faint))" }}>
                    (verplicht, max 4000 tekens)
                  </span>
                </label>
                <textarea
                  id="feedback-tekst"
                  rows={4}
                  maxLength={4000}
                  value={tekst}
                  onChange={(e) => setTekst(e.target.value)}
                  placeholder="Beschrijf uw feedback..."
                  style={{
                    width: "100%",
                    padding: "0.375rem 0.5rem",
                    fontSize: "0.8125rem",
                    border: "1px solid rgb(var(--line))",
                    borderRadius: "4px",
                    background: "rgb(var(--paper))",
                    color: "rgb(var(--ink))",
                    resize: "vertical",
                    fontFamily: "inherit",
                    boxSizing: "border-box",
                  }}
                />
              </div>
              <button
                className="btn btn-primary"
                style={{ width: "100%" }}
                disabled={laden}
                onClick={() => void handleVerzenden()}
              >
                {laden ? "Verzenden…" : "Verzenden"}
              </button>
            </div>
          )}
        </div>
      )}

      <button
        className="btn btn-primary"
        onClick={() => setPanelOpen((v) => !v)}
        aria-label="Feedback geven"
        aria-expanded={panelOpen}
        style={{
          position: "fixed",
          bottom: "1.5rem",
          right: "1.5rem",
          display: "flex",
          alignItems: "center",
          gap: "0.375rem",
          fontSize: "0.8125rem",
          padding: "0.5rem 0.875rem",
          boxShadow: "0 4px 12px rgb(0 0 0 / 0.15)",
          zIndex: 1000,
        }}
      >
        <svg
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden
        >
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
        </svg>
        Feedback
      </button>
    </>
  );
}
