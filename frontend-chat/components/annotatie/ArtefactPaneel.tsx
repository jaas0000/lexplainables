"use client";

import { useEffect, useRef, useState } from "react";
import { DocumentPaneel } from "./DocumentPaneel";
import { ReviewQueue } from "./ReviewQueue";
import type {
  AnnotatieDocument,
  AnnotatieElement,
  BeoordelingsReden,
  Wetsartikel,
} from "@/lib/annotatie-types";

/**
 * Het annotatie-artefact: wetsartikel + reviewqueue voor één document. Vanaf `xl:` (1280px) een
 * eigen kolom naast de chat (`kolom`-variant, geen backdrop); daaronder een van-rechts-inschuivend
 * paneel met backdrop — zelfde principe als wetsanalyse-ai's `ArtefactPaneel`/`Dialog`-varianten,
 * hier met Tailwind-responsive-klassen i.p.v. een los `useBreedScherm`-hook.
 */
export function ArtefactPaneel({
  slug,
  onSluiten,
}: {
  slug: string;
  onSluiten: () => void;
}) {
  const [doc, setDoc] = useState<AnnotatieDocument | null>(null);
  const [wetsartikel, setWetsartikel] = useState<Wetsartikel | null>(null);
  const [actiefId, setActiefId] = useState<string | null>(null);
  const [fout, setFout] = useState<string | null>(null);
  const [bezig, setBezig] = useState(false);

  async function laadDocument() {
    setFout(null);
    try {
      const [docRes, artikelRes] = await Promise.all([
        fetch(`/api/annotatie/documenten/${slug}`),
        fetch(`/api/annotatie/documenten/${slug}/wetsartikel`),
      ]);
      if (!docRes.ok) {
        setFout(
          docRes.status === 404
            ? "Deze annotatie is verwijderd."
            : "Kon het document niet laden.",
        );
        return;
      }
      setDoc(await docRes.json());
      if (artikelRes.ok) setWetsartikel(await artikelRes.json());
    } catch {
      setFout("Kon het document niet laden.");
    }
  }

  // React Strict Mode draait het effect twee keer in dev bij hetzelfde `slug`; alleen een
  // écht gewijzigde slug (openen van een ander document) hoort een herlaad te triggeren —
  // zelfde guard-gedachte als `ChatVenster.tsx`, hier per-slug i.p.v. eenmalig.
  const geladenSlugRef = useRef<string | null>(null);
  useEffect(() => {
    if (geladenSlugRef.current === slug) return;
    geladenSlugRef.current = slug;
    laadDocument();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  async function beslissing(
    elementId: string,
    body: {
      type: "goedkeuren" | "bewerken" | "afwijzen" | "opmerking";
      reden?: BeoordelingsReden;
      opmerking?: string;
      wijziging?: {
        klasse?: string;
        tekst?: string;
        toelichting?: string;
        lid?: string;
      };
    },
  ) {
    setBezig(true);
    try {
      const res = await fetch(
        `/api/annotatie/documenten/${slug}/elementen/${elementId}/beslissing`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      if (!res.ok) {
        setFout(
          res.status === 409
            ? "Deze annotatie is afgerond. Heropen hem om te wijzigen."
            : "De beslissing kon niet worden opgeslagen.",
        );
        return;
      }
      setDoc(await res.json());
    } finally {
      setBezig(false);
    }
  }

  async function verwijderElement(elementId: string) {
    setBezig(true);
    try {
      const res = await fetch(
        `/api/annotatie/documenten/${slug}/elementen/${elementId}`,
        {
          method: "DELETE",
        },
      );
      if (!res.ok) {
        setFout(
          res.status === 409
            ? "Alleen je eigen markeringen kun je verwijderen; verwerp een agent-voorstel."
            : "De markering kon niet worden verwijderd.",
        );
        return;
      }
      await laadDocument();
    } finally {
      setBezig(false);
    }
  }

  async function markeer(tekst: string, lid: string, klasse: string) {
    setBezig(true);
    try {
      const res = await fetch(`/api/annotatie/documenten/${slug}/elementen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ klasse, tekst, lid }),
      });
      if (!res.ok) {
        setFout("De markering kon niet worden aangemaakt.");
        return;
      }
      setDoc(await res.json());
    } finally {
      setBezig(false);
    }
  }

  async function zetStatus(geaccordeerd: boolean) {
    setBezig(true);
    try {
      const res = await fetch(`/api/annotatie/documenten/${slug}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ geaccordeerd }),
      });
      if (res.ok) setDoc(await res.json());
    } finally {
      setBezig(false);
    }
  }

  async function exporteer(formaat: "pdf" | "csv" | "json") {
    const res = await fetch(
      `/api/annotatie/documenten/${slug}/export?formaat=${formaat}`,
      {
        method: "POST",
      },
    );
    if (!res.ok) {
      setFout("Exporteren is niet gelukt.");
      return;
    }
    const blob = await res.blob();
    const dispositie = res.headers.get("Content-Disposition") ?? "";
    const match = /filename="([^"]+)"/.exec(dispositie);
    const bestandsnaam = match?.[1] ?? `annotatie.${formaat}`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = bestandsnaam;
    a.click();
    URL.revokeObjectURL(url);
  }

  const vergrendeld = doc?.status === "geaccordeerd";
  const actiefElement: AnnotatieElement | null =
    doc?.elementen?.find((e) => e.id === actiefId) ?? null;
  const lid = doc?.lid ? ` lid ${doc.lid}` : "";
  const titel = doc ? `${doc.bwb_id} — art. ${doc.artikel}${lid}` : "Annotatie";

  return (
    <>
      <div
        className="fixed inset-0 z-20 bg-ink/20 xl:hidden"
        onClick={onSluiten}
        aria-hidden
      />
      <div className="fixed inset-y-0 right-0 z-30 flex w-full max-w-md flex-col border-l border-line bg-paper xl:static xl:z-auto xl:max-w-none xl:w-[28rem] xl:shrink-0">
        <header className="flex items-center justify-between gap-2 border-b border-line p-3">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-lint">
              {titel}
            </h2>
            {doc && <p className="text-xs text-faint">Status: {doc.status}</p>}
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {doc && (
              <button
                type="button"
                className="btn btn-secondary text-xs"
                disabled={bezig}
                onClick={() => zetStatus(!vergrendeld)}
              >
                {vergrendeld ? "Heropenen" : "Afronden"}
              </button>
            )}
            <ExportMenu onExporteer={exporteer} />
            <button
              type="button"
              className="btn btn-secondary text-xs"
              onClick={onSluiten}
              aria-label="Sluiten"
            >
              ✕
            </button>
          </div>
        </header>

        {fout && (
          <div className="melding melding-fout m-3" role="alert">
            {fout}
          </div>
        )}
        {vergrendeld && (
          <p className="mx-3 mt-3 text-xs text-faint">
            Deze annotatie is afgerond. Heropen hem om markeringen te wijzigen.
          </p>
        )}

        <div className="flex-1 overflow-y-auto">
          <DocumentPaneel
            wetsartikel={wetsartikel}
            actiefElement={actiefElement}
            vergrendeld={vergrendeld}
            onMarkeer={markeer}
          />
          {doc && (
            <ReviewQueue
              elementen={doc.elementen ?? []}
              actiefId={actiefId}
              vergrendeld={vergrendeld}
              onSelecteer={(el) =>
                setActiefId(el.id === actiefId ? null : el.id)
              }
              onBeslissing={beslissing}
              onVerwijder={verwijderElement}
            />
          )}
        </div>
      </div>
    </>
  );
}

function ExportMenu({
  onExporteer,
}: {
  onExporteer: (formaat: "pdf" | "csv" | "json") => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        type="button"
        className="btn btn-secondary text-xs"
        onClick={() => setOpen((v) => !v)}
      >
        Exporteren
      </button>
      {open && (
        <div className="card absolute right-0 top-full z-10 mt-1 flex flex-col gap-1 p-2">
          {(["pdf", "csv", "json"] as const).map((f) => (
            <button
              key={f}
              type="button"
              className="btn btn-secondary text-xs"
              onClick={() => {
                onExporteer(f);
                setOpen(false);
              }}
            >
              {f.toUpperCase()}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
