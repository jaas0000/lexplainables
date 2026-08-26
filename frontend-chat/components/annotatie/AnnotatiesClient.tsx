"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { signOut } from "next-auth/react";
import { ArtefactPaneel } from "./ArtefactPaneel";
import type { DocumentSamenvatting } from "@/lib/annotatie-types";

/**
 * Annotaties staan los van de gesprekken (zelfde principe als wetsanalyse-ai's `/annotaties`):
 * een eersteklas overzicht, niet alleen bereikbaar via het gesprek waarin een document ontstond.
 * Versmald t.o.v. de referentie: één lijst i.p.v. de "te doen"/"alles"-tweeling, geen
 * JAS-kleurstrip-thumbnail.
 */
export function AnnotatiesClient({
  gebruikersnaam,
}: {
  gebruikersnaam: string;
}) {
  const [documenten, setDocumenten] = useState<DocumentSamenvatting[] | null>(
    null,
  );
  const [artefactSlug, setArtefactSlug] = useState<string | null>(null);

  async function laad() {
    const res = await fetch("/api/annotatie/documenten");
    if (!res.ok) return;
    const data = await res.json();
    setDocumenten(data.items ?? []);
  }

  // React Strict Mode draait het mount-effect twee keer in dev — zelfde guard-patroon als
  // `ChatVenster.tsx`.
  const geinitialiseerd = useRef(false);
  useEffect(() => {
    if (geinitialiseerd.current) return;
    geinitialiseerd.current = true;
    laad();
  }, []);

  return (
    <div className="mx-auto flex h-screen max-w-5xl">
      <div className="flex h-screen flex-1 flex-col px-4 py-6">
        <header className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="btn btn-secondary text-xs">
              ← Chat
            </Link>
            <h1 className="text-xl font-semibold text-lint">Annotaties</h1>
          </div>
          <button
            type="button"
            className="btn btn-secondary text-xs"
            onClick={() => signOut({ callbackUrl: "/login" })}
          >
            Uitloggen ({gebruikersnaam})
          </button>
        </header>

        <div className="flex-1 space-y-2 overflow-y-auto">
          {documenten === null && <p className="text-sm text-faint">Laden…</p>}
          {documenten !== null && documenten.length === 0 && (
            <p className="text-sm text-muted">
              Nog geen annotaties — start er een via de chat (modus
              &ldquo;Annoteren&rdquo;).
            </p>
          )}
          {documenten?.map((doc) => (
            <button
              key={doc.slug}
              type="button"
              className="card flex w-full items-center justify-between text-left hover:bg-surface"
              onClick={() => setArtefactSlug(doc.slug)}
            >
              <div>
                <p className="text-sm font-medium">
                  {doc.bwb_id} — art. {doc.artikel}
                  {doc.lid ? ` lid ${doc.lid}` : ""}
                </p>
                <p className="text-xs text-faint">
                  {doc.werkgebied} · {doc.aantal_elementen} elementen
                </p>
              </div>
              <span className="text-xs text-faint">{doc.status}</span>
            </button>
          ))}
        </div>
      </div>

      {artefactSlug && (
        <ArtefactPaneel
          slug={artefactSlug}
          onSluiten={() => setArtefactSlug(null)}
        />
      )}
    </div>
  );
}
