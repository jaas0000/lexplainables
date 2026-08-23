"use client";

import { useEffect, useRef, type ReactNode } from "react";

/** Selector voor de elementen die de Tab-trap als focusbaar telt. */
const FOCUSBAAR =
  'a[href],button:not([disabled]),textarea,input:not([disabled]),select,[tabindex]:not([tabindex="-1"])';

interface Props {
  /** Voorleesnaam van het venster (aria-label). */
  label: string;
  onSluit: () => void;
  /** Wat Escape doet, als dat niet simpelweg sluiten is. */
  onEscape?: () => void;
  children: ReactNode;
}

/** Gecentreerd modaal venster met vaste hoogte — bedoeld voor het instellingenvenster, dat anders
 *  bij elke tabwissel van formaat zou springen. Op mobiel een bijna-volledig-scherm sheet.
 *
 *  Poort van `wetsanalyse-ai/frontend/components/ui/Dialog.tsx`, beperkt tot de `center`-variant:
 *  de andere vormen (`compact`/`side`/`kolom`/`drawer`) horen bij de chat-werkplek, die hier nog
 *  niet bestaat — zie werkwijze-story 042 §lexplainables-specifieke afwijkingen. */
export function Dialog({ label, onSluit, onEscape, children }: Props) {
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
      <div
        ref={paneelRef}
        tabIndex={-1}
        className="absolute inset-x-0 bottom-0 top-[6%] flex flex-col rounded-t-vorm bg-paper shadow-kaart outline-none animate-rise sm:inset-0 sm:m-auto sm:h-[min(42rem,85vh)] sm:w-[min(56rem,92vw)] sm:rounded-vorm"
      >
        {children}
      </div>
    </div>
  );
}
