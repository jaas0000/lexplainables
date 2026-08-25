"use client";

import { useEffect, useRef, useState } from "react";
import { signOut } from "next-auth/react";

type AnnotatieElement = { klasse: string; tekst: string };

type Bericht = {
  rol: "gebruiker" | "lex";
  tekst: string;
  niveau?: "gegrond" | "onbepaald" | "ongegrond";
  fout?: boolean;
  elementen?: AnnotatieElement[];
  opgeslagen?: { slug: string; aanvaard: number; verworpen: number };
  waarschuwing?: string;
};

type GesprekSamenvatting = {
  id: string;
  titel: string;
  aantal_berichten: number;
  bijgewerkt: string;
};

type ApiBericht = {
  rol: "user" | "assistant";
  tekst: string;
  annotatie_slug: string;
  annotatie_titel: string;
};

/**
 * Chat-UI voor Lex (graph-qa) — story 056 + de gespreksgeschiedenis-uitbreiding erna. Elk
 * gesprek is een echte, server-side rij (`POST /api/gesprekken`, die naar `api`'s
 * `/v1/gesprekken` proxyt): de gebruiker se eigen vraag persisteert deze component zelf, het
 * antwoord van Lex persisteert graph-qa zelf ná afloop van de stream
 * (`tools/graph-qa/agent/beurt.py::voer_beurt_uit`) — een herlaad of gesloten tabblad kost dus
 * geen werk meer. De sidebar laat eerdere gesprekken heropenen; alleen de tekstinhoud van een
 * annotatiebeurt wordt niet opnieuw getoond (die leeft in het annotatiedocument zelf, niet in
 * het bericht — zie `api/app/features/gesprekken/__init__.py`).
 */
export function ChatVenster({ gebruikersnaam }: { gebruikersnaam: string }) {
  const [berichten, setBerichten] = useState<Bericht[]>([]);
  const [vraag, setVraag] = useState("");
  const [bezig, setBezig] = useState(false);
  const [modus, setModus] = useState<"vraag" | "annoteren">("vraag");
  const [bwbId, setBwbId] = useState("");
  const [artikel, setArtikel] = useState("");
  const [lid, setLid] = useState("");
  const [werkgebied, setWerkgebied] = useState("");
  const [gesprekId, setGesprekId] = useState<string | null>(null);
  const [gesprekken, setGesprekken] = useState<GesprekSamenvatting[]>([]);

  // React Strict Mode draait een mount-effect twee keer in dev — zonder deze guard maakt de
  // tweede invocatie een tweede gesprek aan en veegt die de net verstuurde eerste beurt weer
  // leeg zodra hij ná de eerste `verstuur()` alsnog resolvet.
  const geinitialiseerd = useRef(false);
  useEffect(() => {
    if (geinitialiseerd.current) return;
    geinitialiseerd.current = true;
    nieuwGesprek();
    laadGesprekken();
  }, []);

  async function laadGesprekken() {
    const res = await fetch("/api/gesprekken");
    if (!res.ok) return;
    setGesprekken(await res.json());
  }

  async function nieuwGesprek() {
    const res = await fetch("/api/gesprekken", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ titel: "" }),
    });
    if (!res.ok) return;
    const gesprek = await res.json();
    setGesprekId(gesprek.id);
    setBerichten([]);
  }

  async function openGesprek(id: string) {
    if (bezig) return;
    const res = await fetch(`/api/gesprekken/${id}`);
    if (!res.ok) return;
    const gesprek: { id: string; berichten: ApiBericht[] } = await res.json();
    setGesprekId(gesprek.id);
    setBerichten(
      gesprek.berichten.map((b) => ({
        rol: b.rol === "user" ? "gebruiker" : "lex",
        tekst: b.annotatie_slug
          ? `Annotatie opgeslagen: ${b.annotatie_titel} (${b.annotatie_slug})`
          : b.tekst,
      })),
    );
  }

  async function persisteerGebruikersbericht(
    gid: string,
    tekst: string,
    eersteBeurt: boolean,
  ) {
    try {
      await fetch(`/api/gesprekken/${gid}/berichten`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rol: "user", tekst }),
      });
      // Eerste beurt van een gesprek: geef het een titel op basis van de vraag zelf, zodat de
      // sidebar iets zinnigers toont dan "Nieuw gesprek" voor elk gesprek.
      if (eersteBeurt) {
        await fetch(`/api/gesprekken/${gid}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ titel: tekst.slice(0, 80) }),
        });
      }
    } catch {
      // Best-effort: de vraag staat al zichtbaar in de UI: het antwoord van Lex persisteert
      // hoe dan ook (graph-qa schrijft dat zelf weg) — alleen deze regel zou dan ontbreken bij
      // een latere heropening van dit gesprek.
    }
  }

  async function stuurVerzoek(
    body: Record<string, unknown>,
    gebruikerstekst: string,
  ) {
    const gid = gesprekId;
    const eersteBeurt = berichten.length === 0;
    setBerichten((b) => [
      ...b,
      { rol: "gebruiker", tekst: gebruikerstekst },
      {
        rol: "lex",
        tekst: "",
        elementen: modus === "annoteren" ? [] : undefined,
      },
    ]);
    setBezig(true);

    try {
      if (gid)
        await persisteerGebruikersbericht(gid, gebruikerstekst, eersteBeurt);

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...body, conversation_id: gid }),
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
      laadGesprekken();
    }
  }

  async function verstuur(e: React.FormEvent) {
    e.preventDefault();
    const tekst = vraag.trim();
    if (!tekst || bezig) return;
    setVraag("");
    await stuurVerzoek({ question: tekst }, tekst);
  }

  async function startAnnoteren(e: React.FormEvent) {
    e.preventDefault();
    if (bezig || !bwbId.trim() || !artikel.trim() || !werkgebied.trim()) return;
    const doel = {
      bwbId: bwbId.trim(),
      artikel: artikel.trim(),
      lid: lid.trim(),
    };
    await stuurVerzoek(
      { doel, werkgebied: werkgebied.trim() },
      `Annoteren: ${doel.bwbId} art. ${doel.artikel}${doel.lid ? ` lid ${doel.lid}` : ""} (${werkgebied.trim()})`,
    );
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
      case "doel":
        update((laatste) => ({ ...laatste, tekst: "Bezig met annoteren…" }));
        break;
      case "element":
        update((laatste) => ({
          ...laatste,
          tekst: "",
          elementen: [
            ...(laatste.elementen ?? []),
            {
              klasse: String(event.klasse ?? ""),
              tekst: String(event.tekst ?? ""),
            },
          ],
        }));
        break;
      case "opgeslagen":
        update((laatste) => ({
          ...laatste,
          opgeslagen: {
            slug: String(event.slug ?? ""),
            aanvaard: Number(event.aanvaard ?? 0),
            verworpen: Number(event.verworpen ?? 0),
          },
        }));
        break;
      case "waarschuwing":
        update((laatste) => ({
          ...laatste,
          waarschuwing: String(event.message ?? "Wegschrijven is niet gelukt."),
        }));
        break;
    }
  }

  return (
    <div className="mx-auto flex h-screen max-w-5xl">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-line px-3 py-6 sm:flex">
        <button
          type="button"
          className="btn btn-secondary mb-4 w-full text-xs"
          onClick={nieuwGesprek}
          disabled={bezig}
        >
          + Nieuw gesprek
        </button>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {gesprekken.length === 0 && (
            <p className="px-1 text-xs text-faint">Nog geen gesprekken.</p>
          )}
          {gesprekken.map((g) => (
            <button
              key={g.id}
              type="button"
              onClick={() => openGesprek(g.id)}
              className={`block w-full truncate rounded px-2 py-1.5 text-left text-xs ${
                g.id === gesprekId
                  ? "bg-surface font-medium text-lint"
                  : "text-muted"
              }`}
            >
              {g.titel || "Nieuw gesprek"}
            </button>
          ))}
        </div>
      </aside>

      <div className="flex h-screen flex-1 flex-col px-4 py-6">
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

        <div className="mb-4 flex gap-2 text-sm">
          <button
            type="button"
            className={`btn ${modus === "vraag" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setModus("vraag")}
          >
            Vraag stellen
          </button>
          <button
            type="button"
            className={`btn ${modus === "annoteren" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setModus("annoteren")}
          >
            Annoteren
          </button>
        </div>

        <div
          className="flex-1 space-y-3 overflow-y-auto"
          data-testid="berichten"
        >
          {berichten.length === 0 && modus === "vraag" && (
            <p className="text-sm text-muted">
              Stel een vraag over de Invorderingswet 1990 — bijvoorbeeld
              &ldquo;Wat is een belastingschuldige?&rdquo;
            </p>
          )}
          {berichten.length === 0 && modus === "annoteren" && (
            <p className="text-sm text-muted">
              Vul een BWB-id, artikel en werkgebied in om Lex een artikel te
              laten annoteren.
            </p>
          )}
          {berichten.map((b, i) => (
            <div
              key={i}
              className={`card ${b.rol === "gebruiker" ? "bg-surface" : ""} ${b.fout ? "border-fout" : ""}`}
            >
              {(b.tekst || b.elementen === undefined) && (
                <p className="whitespace-pre-wrap text-sm">{b.tekst || "…"}</p>
              )}
              {b.niveau && (
                <p className="mt-2 text-xs text-faint">
                  {b.niveau === "gegrond" && "✓ gegrond in de kennisgraaf"}
                  {b.niveau === "onbepaald" &&
                    "geen vindplaats/citaat om te controleren"}
                  {b.niveau === "ongegrond" &&
                    "⚠ niet gegrond — controleer dit antwoord"}
                </p>
              )}
              {b.elementen && b.elementen.length > 0 && (
                <ul className="space-y-1 text-sm">
                  {b.elementen.map((el, j) => (
                    <li key={j}>
                      <span className="rounded bg-surface px-1.5 py-0.5 text-xs font-medium text-lint">
                        {el.klasse}
                      </span>{" "}
                      <span className="whitespace-pre-wrap">{el.tekst}</span>
                    </li>
                  ))}
                </ul>
              )}
              {b.opgeslagen && (
                <p className="mt-2 text-xs text-faint">
                  Opgeslagen ({b.opgeslagen.slug}): {b.opgeslagen.aanvaard}{" "}
                  aanvaard, {b.opgeslagen.verworpen} verworpen.
                </p>
              )}
              {b.waarschuwing && (
                <p className="mt-2 text-xs text-fout">⚠ {b.waarschuwing}</p>
              )}
            </div>
          ))}
        </div>

        {modus === "vraag" ? (
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
        ) : (
          <form onSubmit={startAnnoteren} className="mt-4 flex flex-wrap gap-2">
            <input
              type="text"
              className="field-input flex-1"
              placeholder="BWB-id (bv. BWBR0004770)"
              value={bwbId}
              onChange={(e) => setBwbId(e.target.value)}
              disabled={bezig}
            />
            <input
              type="text"
              className="field-input w-24"
              placeholder="Artikel"
              value={artikel}
              onChange={(e) => setArtikel(e.target.value)}
              disabled={bezig}
            />
            <input
              type="text"
              className="field-input w-20"
              placeholder="Lid"
              value={lid}
              onChange={(e) => setLid(e.target.value)}
              disabled={bezig}
            />
            <input
              type="text"
              className="field-input flex-1"
              placeholder="Werkgebied"
              value={werkgebied}
              onChange={(e) => setWerkgebied(e.target.value)}
              disabled={bezig}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={
                bezig || !bwbId.trim() || !artikel.trim() || !werkgebied.trim()
              }
            >
              {bezig ? "…" : "Start annotatie"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
