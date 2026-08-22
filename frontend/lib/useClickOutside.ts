import { useEffect, useLayoutEffect, useRef, type RefObject } from "react";

/** Sluit een open paneel bij een klik buiten `ref` of bij Escape. `onSluit` mag een nieuwe
 *  functie zijn bij elke render (via een ref intern, bijgewerkt in een eigen effect — refs
 *  mogen niet tijdens render zelf gemuteerd worden) — het listener-effect draait alleen
 *  opnieuw als `open` wisselt, niet bij elke render van de aanroeper. */
export function useClickOutside(
  ref: RefObject<HTMLElement | null>,
  open: boolean,
  onSluit: () => void,
) {
  const onSluitRef = useRef(onSluit);
  useLayoutEffect(() => {
    onSluitRef.current = onSluit;
  });

  useEffect(() => {
    if (!open) return;
    const opBuiten = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onSluitRef.current();
      }
    };
    const opEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onSluitRef.current();
    };
    document.addEventListener("mousedown", opBuiten);
    window.addEventListener("keydown", opEsc);
    return () => {
      document.removeEventListener("mousedown", opBuiten);
      window.removeEventListener("keydown", opEsc);
    };
  }, [open, ref]);
}
