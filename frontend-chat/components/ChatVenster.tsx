"use client";

import { useRef, useState } from "react";
import { signOut } from "next-auth/react";

type Bericht = {
  rol: "gebruiker" | "lex";
  tekst: string;
  niveau?: "gegrond" | "onbepaald" | "ongegrond";
  fout?: boolean;
};

// `crypto.randomUUID()` bestaat alleen in een secure context (HTTPS of localhost) — via
// Tailscale over plain HTTP ontbreekt hij. Geen beveiligingsgevoelig gebruik hier (puur een
// client-side correlatie-id), dus een simpele fallback volstaat.
function maakGespreksId(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Eerste, minimale chat-UI voor Lex (graph-qa) — story 056. Geen gesprekgeschiedenis/
 * persistentie: `conversationId` leeft alleen in React-state, dus een herlaad begint een nieuw
 * gesprek (zie de story-doc §Buiten scope). Praat met `POST /api/chat`, de streaming BFF-route
 * die naar `api`'s chat-proxy (story 055) forwardt.
 */
export function ChatVenster({ gebruikersnaam }: { gebruikersnaam: string }) {
  const [berichten, setBerichten] = useState<Bericht[]>([]);
  const [vraag, setVraag] = useState("");
  const [bezig, setBezig] = useState(false);
  const conversationId = useRef(maakGespreksId());

  async function verstuur(e: React.FormEvent) {
    e.preventDefault();
    const tekst = vraag.trim();
    if (!tekst || bezig) return;

    setBerichten((b) => [
      ...b,
      { rol: "gebruiker", tekst },
      { rol: "lex", tekst: "" },
    ]);
    setVraag("");
    setBezig(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: tekst,
          conversation_id: conversationId.current,
        }),
      });
      if (!res.ok || !res.body) {
        werkLaatsteLexBericht((laatste) => ({
          ...laatste,
          tekst: "Er ging iets mis bij het versturen van de vraag.",
          fout: true,
        }));
        return;
      }
      await verwerkStream(res.body, werkLaatsteLexBericht);
    } catch {
      werkLaatsteLexBericht((laatste) => ({
        ...laatste,
        tekst: "Er ging iets mis. Probeer het opnieuw.",
        fout: true,
      }));
    } finally {
      setBezig(false);
    }
  }

  function werkLaatsteLexBericht(fn: (laatste: Bericht) => Bericht) {
    setBerichten((b) => {
      const kopie = [...b];
      const laatste = kopie[kopie.length - 1];
      if (laatste?.rol === "lex") kopie[kopie.length - 1] = fn(laatste);
      return kopie;
    });
  }

  async function verwerkStream(
    body: ReadableStream<Uint8Array>,
    update: (fn: (laatste: Bericht) => Bericht) => void,
  ) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      // sse-starlette scheidt events met \r\n\r\n (niet kaal \n\n) — normaliseer eerst, anders
      // splitst niets ooit en groeit de buffer stil door zonder ooit een event te verwerken.
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

      const blokken = buffer.split("\n\n");
      buffer = blokken.pop() ?? "";
      for (const blok of blokken) {
        for (const regel of blok.split("\n")) {
          if (!regel.startsWith("data:")) continue;
          const payload = regel.slice("data:".length).trim();
          if (!payload) continue;
          verwerkEvent(JSON.parse(payload), update);
        }
      }
    }
  }

  function verwerkEvent(
    event: Record<string, unknown>,
    update: (fn: (laatste: Bericht) => Bericht) => void,
  ) {
    switch (event.type) {
      case "token":
        update((laatste) => ({
          ...laatste,
          tekst: laatste.tekst + String(event.content ?? ""),
        }));
        break;
      case "grounding":
        update((laatste) => ({
          ...laatste,
          niveau: event.niveau as Bericht["niveau"],
        }));
        break;
      case "error":
        update((laatste) => ({
          ...laatste,
          tekst: String(event.message ?? "Er ging iets mis."),
          fout: true,
        }));
        break;
    }
  }

  return (
    <div className="mx-auto flex h-screen max-w-2xl flex-col px-4 py-6">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-lint">Lex</h1>
        <button
          type="button"
          className="btn btn-secondary text-xs"
          onClick={() => signOut({ callbackUrl: "/login" })}
        >
          Uitloggen ({gebruikersnaam})
        </button>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto">
        {berichten.length === 0 && (
          <p className="text-sm text-muted">
            Stel een vraag over de Invorderingswet 1990 — bijvoorbeeld
            &ldquo;Wat is een belastingschuldige?&rdquo;
          </p>
        )}
        {berichten.map((b, i) => (
          <div
            key={i}
            className={`card ${b.rol === "gebruiker" ? "bg-surface" : ""} ${b.fout ? "border-fout" : ""}`}
          >
            <p className="whitespace-pre-wrap text-sm">{b.tekst || "…"}</p>
            {b.niveau && (
              <p className="mt-2 text-xs text-faint">
                {b.niveau === "gegrond" && "✓ gegrond in de kennisgraaf"}
                {b.niveau === "onbepaald" &&
                  "geen vindplaats/citaat om te controleren"}
                {b.niveau === "ongegrond" &&
                  "⚠ niet gegrond — controleer dit antwoord"}
              </p>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={verstuur} className="mt-4 flex gap-2">
        <input
          type="text"
          className="field-input"
          placeholder="Stel een vraag…"
          value={vraag}
          onChange={(e) => setVraag(e.target.value)}
          disabled={bezig}
        />
        <button
          type="submit"
          className="btn btn-primary"
          disabled={bezig || !vraag.trim()}
        >
          {bezig ? "…" : "Versturen"}
        </button>
      </form>
    </div>
  );
}
