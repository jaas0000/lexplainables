"use client";

import { useEffect, useState } from "react";
import type { components } from "@/generated/types";
import { SectieHeader } from "@/components/beheer/SectieHeader";
import { beheerFetch } from "@/lib/beheer-fetch";

type AppInstellingen = components["schemas"]["AppInstellingen"];

/** App-instellingen-tab van het instellingenvenster. Verplaatst uit
 *  `app/beheer/instellingen/page.tsx` (werkwijze-story 042), inhoud ongewijzigd. */
export function AppInstellingenPanel() {
  const [instellingen, setInstellingen] = useState<AppInstellingen | null>(
    null,
  );
  const [laden, setLaden] = useState(true);
  const [bezig, setBezig] = useState(false);
  const [fout, setFout] = useState<string | null>(null);

  useEffect(() => {
    beheerFetch("/api/admin/instellingen")
      .then((data) => setInstellingen(data as AppInstellingen))
      .catch((err) =>
        setFout(
          err instanceof Error ? err.message : "Kon instellingen niet ophalen.",
        ),
      )
      .finally(() => setLaden(false));
  }, []);

  async function wisselCapture() {
    if (!instellingen || bezig) return;
    setBezig(true);
    setFout(null);
    try {
      const bijgewerkt = (await beheerFetch("/api/admin/instellingen", {
        method: "PUT",
        body: JSON.stringify({
          capture_llm_calls: !instellingen.capture_llm_calls,
        }),
      })) as AppInstellingen;
      setInstellingen(bijgewerkt);
    } catch (err) {
      setFout(
        err instanceof Error ? err.message : "Kon instelling niet opslaan.",
      );
    } finally {
      setBezig(false);
    }
  }

  const capture = instellingen?.capture_llm_calls ?? false;

  return (
    <div style={{ maxWidth: "56rem", margin: "0 auto", width: "100%" }}>
      {laden && (
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--muted))" }}>
          Laden…
        </p>
      )}

      {!laden && (
        <section style={{ marginBottom: "2rem" }}>
          <SectieHeader
            titel="LLM-invoer vastleggen"
            subtitel="prompts + respons, voor analyse"
          />

          <div className="card" style={{ marginBottom: "1rem" }}>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: "0.75rem",
              }}
            >
              {/* Tekst links */}
              <div style={{ flex: 1, minWidth: "16rem" }}>
                <p
                  style={{
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    color: "rgb(var(--ink))",
                  }}
                >
                  Vastleggen van LLM-calls
                </p>
                <p
                  style={{
                    marginTop: "0.125rem",
                    fontSize: "0.75rem",
                    color: "rgb(var(--muted))",
                  }}
                >
                  Legt per call de letterlijke system/user-prompt en de ruwe
                  respons vast (incl. auto-correctie en gefaalde calls).
                  Standaard uit; aanzetten kost extra opslag per analyse.
                </p>
              </div>

              {/* Tag + knop rechts */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                }}
              >
                <span
                  className={`badge ${capture ? "badge-gepubliceerd" : "badge-concept"}`}
                >
                  {capture ? "aan" : "uit"}
                </span>
                <button
                  type="button"
                  className={capture ? "btn btn-secondary" : "btn btn-primary"}
                  disabled={bezig || instellingen === null}
                  onClick={() => void wisselCapture()}
                  style={{ opacity: bezig ? 0.6 : 1 }}
                >
                  {bezig ? "Bezig…" : capture ? "Uitzetten" : "Aanzetten"}
                </button>
              </div>
            </div>

            {fout && (
              <div
                role="alert"
                className="melding melding-fout"
                style={{ marginTop: "0.75rem" }}
              >
                {fout}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
