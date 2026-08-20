"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { components } from "@/generated/types";
import { SectieHeader, LeegePlaceholder } from "@/components/beheer/SectieHeader";
import { FeedbackItem } from "@/components/feedback/FeedbackItem";
import { beheerFetch, BeheerFetchFout } from "@/lib/beheer-fetch";

type FeedbackRead = components["schemas"]["FeedbackRead"];

export default function FeedbackPagina() {
  const [items, setItems] = useState<FeedbackRead[] | null>(null);
  const [laden, setLaden] = useState(false);
  const [fout, setFout] = useState<string | null>(null);
  const [verwijderFout, setVerwijderFout] = useState<string | null>(null);

  useEffect(() => {
    async function laad() {
      setLaden(true);
      setFout(null);
      try {
        const data = (await beheerFetch("/api/admin/feedback")) as {
          items: FeedbackRead[];
        };
        setItems(data.items);
      } catch (err) {
        setFout(
          err instanceof Error ? err.message : "Fout bij het ophalen van feedback.",
        );
      } finally {
        setLaden(false);
      }
    }
    void laad();
    beheerFetch("/api/admin/feedback/markeer-gezien", { method: "POST" }).catch(
      console.error,
    );
  }, []);

  async function verwijderen(id: number) {
    setVerwijderFout(null);
    try {
      await beheerFetch(`/api/admin/feedback/${id}`, { method: "DELETE" });
      setItems((prev) => prev?.filter((item) => item.id !== id) ?? null);
    } catch (err) {
      setVerwijderFout(err instanceof Error ? err.message : "Fout bij verwijderen.");
      if (err instanceof BeheerFetchFout && err.status === 404) {
        // Item bestaat server-side al niet meer; ruim de lokale kopie op.
        setItems((prev) => prev?.filter((item) => item.id !== id) ?? null);
      }
    }
  }

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <Link href="/beheer" style={{ fontSize: "0.8125rem", color: "rgb(var(--lint))" }}>
          ← Terug naar beheer
        </Link>
      </div>

      <SectieHeader titel="Gebruikersfeedback" aantal={items?.length} />

      {fout && (
        <div className="melding melding-fout" style={{ marginBottom: "1rem" }}>
          <p role="alert">{fout}</p>
        </div>
      )}

      {verwijderFout && (
        <div className="melding melding-fout" style={{ marginBottom: "1rem" }}>
          <p role="alert">{verwijderFout}</p>
        </div>
      )}

      {laden && (
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>Laden…</p>
      )}

      {!laden && items !== null && items.length === 0 && (
        <LeegePlaceholder tekst="Nog geen feedback ontvangen." />
      )}

      {!laden && items !== null && items.length > 0 && (
        <div>
          {items.map((item) => (
            <FeedbackItem key={item.id} item={item} onVerwijderen={(id) => void verwijderen(id)} />
          ))}
        </div>
      )}
    </div>
  );
}
