"use client";

import { useEffect, useRef, type ReactNode } from "react";

/** Selector voor de elementen die de Tab-trap als focusbaar telt. */
const FOCUSBAAR =
  'a[href],button:not([disabled]),textarea,input:not([disabled]),select,[tabindex]:not([tabindex="-1"])';

export type DialogVariant =
  /** Gecentreerd venster met vaste hoogte (instellingen) — anders zou het bij elke tabwissel van
   *  formaat springen. */
  | "center"
  /** Gecentreerd venster dat met de inhoud meegroeit tot een plafond (feedback) — een formulier
   *  van een paar velden hoort niet in een venster van 42rem met een halve pagina wit eronder. */
  | "compact";

const PANEEL_CLASS: Record<DialogVariant, string> = {
  center:
    "absolute inset-x-0 bottom-0 top-[6%] flex flex-col rounded-t-vorm bg-paper shadow-kaart outline-none animate-rise sm:inset-0 sm:m-auto sm:h-[min(42rem,85vh)] sm:w-[min(56rem,92vw)] sm:rounded-vorm",
  compact:
    "absolute inset-x-0 bottom-0 max-h-[85dvh] flex flex-col rounded-t-vorm bg-paper shadow-kaart outline-none animate-rise sm:inset-0 sm:bottom-auto sm:m-auto sm:h-auto sm:max-h-[85vh] sm:w-[min(34rem,92vw)] sm:rounded-vorm",
};

interface Props {
  /** Voorleesnaam van het venster (aria-label). */
  label: string;
  variant?: DialogVariant;
  onSluit: () => void;
  /** Wat Escape doet, als dat niet simpelweg sluiten is. */
  onEscape?: () => void;
  children: ReactNode;
}

/** Modaal venster in twee vormen: `center` (vaste hoogte, instellingenvenster) en `compact`
 *  (inhoud-hoogte met een plafond, feedback). Op mobiel een sheet.
 *
 *  Poort van `wetsanalyse-ai/frontend/components/ui/Dialog.tsx`, beperkt tot deze twee varianten:
 *  de overige vormen (`side`/`kolom`/`drawer`) horen bij de chat-werkplek, die hier nog niet
 *  bestaat — zie werkwijze-story 042 §lexplainables-specifieke afwijkingen. `compact` kwam erbij in
 *  story 043 (`FeedbackDialoog`), de eerste echte tweede consument. */
export function Dialog({
  label,
  variant = "center",
  onSluit,
  onEscape,
  children,
}: Props) {
  const paneelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const opKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        (onEscape ?? onSluit)();
        return;
      }
      if (e.key === "Tab" && paneelRef.current) {
        const f = paneelRef.current.querySelectorAll<HTMLElement>(FOCUSBAAR);
        if (f.length === 0) return;
        const first = f[0];
        const last = f[f.length - 1];
        const actief = document.activeElement;
        if (e.shiftKey && (actief === first || actief === paneelRef.current)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && actief === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", opKey);
    return () => window.removeEventListener("keydown", opKey);
  }, [onSluit, onEscape]);

  // De focus verplaatsen hoort bij het ópenen, niet bij het (her)registreren van de luisteraar —
  // anders trekt elke wisseling van een callback de cursor terug naar het paneel.
  useEffect(() => {
    paneelRef.current?.focus();
  }, []);

  return (
    <div
      className="fixed inset-0 z-40"
      role="dialog"
      aria-modal="true"
      aria-label={label}
    >
      <div className="absolute inset-0 bg-ink/30" onClick={onSluit} />
      <div ref={paneelRef} tabIndex={-1} className={PANEEL_CLASS[variant]}>
        {children}
      </div>
    </div>
  );
}
