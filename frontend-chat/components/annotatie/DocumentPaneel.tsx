"use client";

import { useRef, useState } from "react";
import { JAS_KLASSEN, jasStyle } from "@/lib/jas";
import type { AnnotatieElement, Wetsartikel } from "@/lib/annotatie-types";

type Selectie = { tekst: string; lid: string; x: number; y: number };

/**
 * De wetsartikeltekst, per lid. Toont hoogstens ÉÉN markering tegelijk (de geselecteerde
 * reviewkaart) — alles tegelijk kleuren is onleesbaar en twee markeringen kunnen toch niet op
 * dezelfde tekst liggen. Zelfde principe als wetsanalyse-ai's `DocumentPaneel`, versmald: geen
 * offset-anker-tracking (client zoekt een letterlijke substring op, net als de brongetrouw-check
 * server-side al doet), wél zelf-markeren via tekstselectie.
 */
export function DocumentPaneel({
  wetsartikel,
  actiefElement,
  vergrendeld,
  onMarkeer,
}: {
  wetsartikel: Wetsartikel | null;
  actiefElement: AnnotatieElement | null;
  vergrendeld: boolean;
  onMarkeer: (tekst: string, lid: string, klasse: string) => void;
}) {
  const [selectie, setSelectie] = useState<Selectie | null>(null);
  const [klasse, setKlasse] = useState<string>(JAS_KLASSEN[0]);
  const containerRef = useRef<HTMLDivElement>(null);

  function verwerkSelectie() {
    if (vergrendeld) return;
    const sel = window.getSelection();
    const tekst = sel?.toString().trim() ?? "";
    if (!sel || !tekst || sel.rangeCount === 0) {
      setSelectie(null);
      return;
    }
    const range = sel.getRangeAt(0);
    const container = containerRef.current;
    if (!container || !container.contains(range.commonAncestorContainer)) {
      setSelectie(null);
      return;
    }
    const lidEl = (
      range.commonAncestorContainer instanceof Element
        ? range.commonAncestorContainer
        : range.commonAncestorContainer.parentElement
    )?.closest("[data-lid]");
    const lid = lidEl?.getAttribute("data-lid") ?? "";
    const rect = range.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    setSelectie({
      tekst,
      lid,
      x: rect.left - containerRect.left,
      y: rect.bottom - containerRect.top + 4,
    });
  }

  function bevestigMarkering() {
    if (!selectie) return;
    onMarkeer(selectie.tekst, selectie.lid, klasse);
    setSelectie(null);
    window.getSelection()?.removeAllRanges();
  }

  const leden = wetsartikel?.leden ?? [];

  return (
    <div
      className="relative border-b border-line p-4"
      ref={containerRef}
      onMouseUp={verwerkSelectie}
    >
      {wetsartikel?.opschrift && (
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-faint">
          {wetsartikel.opschrift}
        </p>
      )}
      {leden.length === 0 && wetsartikel && (
        <p className="whitespace-pre-wrap text-sm">{wetsartikel.tekst}</p>
      )}
      {leden.map((lid, i) => (
        <p
          key={i}
          data-lid={lid.nummer ?? ""}
          className="mb-2 whitespace-pre-wrap text-sm"
        >
          {lid.nummer && (
            <span className="mr-1 font-medium text-faint">{lid.nummer}.</span>
          )}
          <Gemarkeerd
            tekst={lid.tekst}
            element={actiefElement}
            lidNummer={lid.nummer ?? ""}
          />
        </p>
      ))}
      {!wetsartikel && (
        <p className="text-sm text-faint">Wetstekst wordt geladen…</p>
      )}

      {selectie && (
        <div
          className="card absolute z-10 flex items-center gap-2 p-2 shadow-lg"
          style={{ left: selectie.x, top: selectie.y }}
        >
          <select
            className="field-input text-xs"
            value={klasse}
            onChange={(e) => setKlasse(e.target.value)}
          >
            {JAS_KLASSEN.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-primary text-xs"
            onClick={bevestigMarkering}
          >
            Markeren
          </button>
          <button
            type="button"
            className="btn btn-secondary text-xs"
            onClick={() => setSelectie(null)}
          >
            Annuleren
          </button>
        </div>
      )}
    </div>
  );
}

function Gemarkeerd({
  tekst,
  element,
  lidNummer,
}: {
  tekst: string;
  element: AnnotatieElement | null;
  lidNummer: string;
}) {
  if (!element || element.lid !== lidNummer) return <>{tekst}</>;
  const idx = tekst.indexOf(element.tekst);
  if (idx === -1) return <>{tekst}</>;
  return (
    <>
      {tekst.slice(0, idx)}
      <mark className={`rounded border px-0.5 ${jasStyle(element.klasse)}`}>
        {tekst.slice(idx, idx + element.tekst.length)}
      </mark>
      {tekst.slice(idx + element.tekst.length)}
    </>
  );
}
