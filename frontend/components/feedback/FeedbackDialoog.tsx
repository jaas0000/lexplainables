"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Dialog } from "@/components/ui/Dialog";
import {
  CATEGORIE_META,
  CATEGORIEN,
  type Categorie,
} from "@/lib/feedback-types";

/** Feedbackformulier als modaal venster, geopend vanuit het gebruikersmenu in de sidebar (story
 *  043, poort van `wetsanalyse-ai`'s `FeedbackDialoog.tsx`). Vervangt de losse zwevende knop uit
 *  `FeedbackKnop.tsx` — de formulierlogica (categorie/tekst/verzenden/succesmelding) is ongewijzigd
 *  verplaatst, alleen de schil (zwevende `div` → gedeelde `Dialog` met `variant="compact"`) en de
 *  trigger (menu-item i.p.v. eigen knop) zijn nieuw. */
export function FeedbackDialoog({ onSluit }: { onSluit: () => void }) {
  const pathname = usePathname();
  const [verzonden, setVerzonden] = useState(false);
  const [laden, setLaden] = useState(false);
  const [fout, setFout] = useState<string | null>(null);
  const [categorie, setCategorie] = useState<Categorie>("verbeteridee");
  const [tekst, setTekst] = useState("");
  const eersteVeldRef = useRef<HTMLSelectElement>(null);

  useEffect(() => {
    if (!verzonden) eersteVeldRef.current?.focus();
  }, [verzonden]);

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
    } catch {
      setFout("Verbindingsfout. Probeer het opnieuw.");
    } finally {
      setLaden(false);
    }
  }

  return (
    <Dialog label="Feedback geven" variant="compact" onSluit={onSluit}>
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-line px-5 py-3.5 pt-[max(0.875rem,env(safe-area-inset-top))]">
        <h2 className="font-display text-base font-semibold text-lint">
          Geef feedback
        </h2>
        <button
          type="button"
          onClick={onSluit}
          aria-label="Feedback sluiten"
          className="focus-ring -mr-1 rounded-kaart p-1.5 text-muted transition-colors hover:bg-surface hover:text-ink"
        >
          <svg
            viewBox="0 0 20 20"
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            aria-hidden="true"
          >
            <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      <div className="flex min-h-0 flex-col gap-3 overflow-y-auto p-4">
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
          <>
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
                ref={eersteVeldRef}
                value={categorie}
                onChange={(e) => setCategorie(e.target.value as Categorie)}
                className="field-input"
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
                className="field-input"
                style={{ resize: "vertical" }}
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
          </>
        )}
      </div>
    </Dialog>
  );
}
