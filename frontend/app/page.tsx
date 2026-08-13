"use client";

import { useCallback, useEffect, useState } from "react";
import type { components } from "@/generated/types";

type BerichtAdminRead = components["schemas"]["BerichtAdminRead"];
type BerichtCreate = components["schemas"]["BerichtCreate"];
type BerichtType = BerichtCreate["type"];

const BERICHT_TYPES: BerichtType[] = [
  "info",
  "update",
  "waarschuwing",
  "kritiek",
];

// Fase 2 (frontend-bouwen regel 4): de API-basis-URL komt uit een environment-variabele, niet
// hardcoded — zie .env.example.
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const ADMIN_ID_OPSLAGSLEUTEL = "wetsanalyse.beheerder-id";

const LEEG_FORMULIER: Pick<
  BerichtAdminRead,
  "titel" | "inhoud" | "type" | "versie"
> = {
  titel: "",
  inhoud: "",
  type: "info",
  versie: null,
};

/** Roept de API aan met de beheerder-id-stand-in als `X-Admin-Id`-header (zie
 * api/app/shared/auth.py) en gooit een leesbare fout bij een niet-2xx-status, zodat de
 * aanroeper die als zichtbare foutmelding kan tonen in plaats van stil te falen. */
async function beheerFetch(
  pad: string,
  adminId: string,
  init: RequestInit = {},
) {
  const response = await fetch(`${API_BASE_URL}${pad}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Id": adminId,
      ...init.headers,
    },
  });
  if (!response.ok) {
    const detail = await response
      .json()
      .then((data) => data.detail)
      .catch(() => null);
    throw new Error(detail ?? `${response.status} ${response.statusText}`);
  }
  if (response.status === 204) return undefined;
  return response.json();
}

/** Foutmelding uit een `catch`-blok, met een fallback voor het geval het geen `Error` is
 * (bv. een non-Error throw). Was 4× letterlijk gekopieerd op elke foutafhandelingsplek. */
function foutmelding(err: unknown, fallback: string) {
  return err instanceof Error ? err.message : fallback;
}

/** Vaste stijl voor de vier volledige-breedte-formuliervelden (titel, inhoud, type, versie) —
 * was 6× als los inline-object herhaald; de beheerder-id-input heeft een eigen, afwijkende
 * breedte en blijft dus buiten deze constante. */
const veldStijl = { display: "block", width: "100%" } as const;

export default function BerichtenAdminPagina() {
  // Auth-stand-in (geen echt inlogscherm): een tekstveld voor de beheerder-id, bewaard in
  // localStorage, dat bij elke aanroep als X-Admin-Id-header meegaat.
  const [adminId, setAdminId] = useState("");
  const [berichten, setBerichten] = useState<BerichtAdminRead[] | null>(null);
  const [laden, setLaden] = useState(false);
  const [fout, setFout] = useState<string | null>(null);
  const [formulier, setFormulier] = useState(LEEG_FORMULIER);
  const [bewerktId, setBewerktId] = useState<number | null>(null);

  useEffect(() => {
    // Synchronisatie met een extern systeem (localStorage) bij het laden van de pagina — de
    // waarde kan pas ná mount bekend zijn (server-side rendering heeft geen `window`), dus een
    // effect is hier het juiste, geen work-around zonder hydration-mismatch beschikbaar.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAdminId(window.localStorage.getItem(ADMIN_ID_OPSLAGSLEUTEL) ?? "");
  }, []);

  function adminIdWijzigen(waarde: string) {
    setAdminId(waarde);
    window.localStorage.setItem(ADMIN_ID_OPSLAGSLEUTEL, waarde);
  }

  const berichtenOphalen = useCallback(async () => {
    if (!adminId) return;
    setLaden(true);
    setFout(null);
    try {
      const pagina = await beheerFetch("/v1/admin/berichten", adminId);
      setBerichten(pagina.items);
    } catch (err) {
      setFout(
        foutmelding(err, "Onbekende fout bij het ophalen van berichten."),
      );
    } finally {
      setLaden(false);
    }
  }, [adminId]);

  useEffect(() => {
    // Synchronisatie met een extern systeem (de API): berichten ophalen bij mount en bij elke
    // wijziging van de beheerder-id.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    berichtenOphalen();
  }, [berichtenOphalen]);

  async function formulierVerzenden() {
    setFout(null);
    const body: BerichtCreate = {
      titel: formulier.titel,
      inhoud: formulier.inhoud,
      type: formulier.type,
      versie: formulier.versie || null,
    };
    try {
      if (bewerktId === null) {
        // De API geeft het aangemaakte bericht terug — direct aan de lokale lijst toevoegen
        // i.p.v. de hele lijst opnieuw op te halen (was voorheen een volledige refetch).
        const nieuw: BerichtAdminRead = await beheerFetch(
          "/v1/admin/berichten",
          adminId,
          { method: "POST", body: JSON.stringify(body) },
        );
        setBerichten((huidig) => [nieuw, ...(huidig ?? [])]);
      } else {
        const bijgewerkt: BerichtAdminRead = await beheerFetch(
          `/v1/admin/berichten/${bewerktId}`,
          adminId,
          { method: "PUT", body: JSON.stringify(body) },
        );
        setBerichten((huidig) =>
          (huidig ?? []).map((b) => (b.id === bijgewerkt.id ? bijgewerkt : b)),
        );
        setBewerktId(null);
      }
      setFormulier(LEEG_FORMULIER);
    } catch (err) {
      setFout(
        foutmelding(err, "Onbekende fout bij het opslaan van het bericht."),
      );
    }
  }

  function bewerkenStarten(b: BerichtAdminRead) {
    setBewerktId(b.id);
    setFormulier({
      titel: b.titel,
      inhoud: b.inhoud,
      type: b.type,
      versie: b.versie,
    });
  }

  function bewerkenAnnuleren() {
    setBewerktId(null);
    setFormulier(LEEG_FORMULIER);
  }

  async function publicatieWisselen(b: BerichtAdminRead) {
    setFout(null);
    try {
      const bijgewerkt: BerichtAdminRead = await beheerFetch(
        `/v1/admin/berichten/${b.id}/publicatie`,
        adminId,
        {
          method: "PATCH",
          body: JSON.stringify({ gepubliceerd: !b.gepubliceerd }),
        },
      );
      setBerichten((huidig) =>
        (huidig ?? []).map((r) => (r.id === bijgewerkt.id ? bijgewerkt : r)),
      );
    } catch (err) {
      setFout(
        foutmelding(
          err,
          "Onbekende fout bij het wijzigen van de publicatiestatus.",
        ),
      );
    }
  }

  async function berichtVerwijderen(id: number) {
    setFout(null);
    try {
      await beheerFetch(`/v1/admin/berichten/${id}`, adminId, {
        method: "DELETE",
      });
      setBerichten((huidig) => (huidig ?? []).filter((b) => b.id !== id));
    } catch (err) {
      setFout(
        foutmelding(err, "Onbekende fout bij het verwijderen van het bericht."),
      );
    }
  }

  return (
    <main
      style={{
        maxWidth: 900,
        margin: "2rem auto",
        padding: "0 1rem",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <h1>Berichten beheren</h1>

      <label style={{ display: "block", marginTop: "1rem" }}>
        Beheerder-id
        <input
          value={adminId}
          onChange={(e) => adminIdWijzigen(e.target.value)}
          placeholder="bv. beheerder-a"
          style={{ display: "block", width: 260 }}
        />
      </label>

      {fout && (
        <p role="alert" style={{ color: "#b00020", marginTop: "1rem" }}>
          {fout}
        </p>
      )}

      {!adminId && (
        <p style={{ marginTop: "1rem" }}>
          Vul een beheerder-id in om berichten te beheren.
        </p>
      )}

      {adminId && (
        <>
          <section style={{ marginTop: "2rem" }}>
            <h2>
              {bewerktId === null
                ? "Nieuw bericht"
                : `Bericht #${bewerktId} bewerken`}
            </h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                formulierVerzenden();
              }}
              style={{ display: "grid", gap: "0.5rem", maxWidth: 500 }}
            >
              <label>
                Titel
                <input
                  value={formulier.titel}
                  onChange={(e) =>
                    setFormulier((f) => ({ ...f, titel: e.target.value }))
                  }
                  required
                  style={veldStijl}
                />
              </label>
              <label>
                Inhoud
                <textarea
                  value={formulier.inhoud}
                  onChange={(e) =>
                    setFormulier((f) => ({ ...f, inhoud: e.target.value }))
                  }
                  required
                  rows={3}
                  style={veldStijl}
                />
              </label>
              <label>
                Type
                <select
                  value={formulier.type}
                  onChange={(e) =>
                    setFormulier((f) => ({
                      ...f,
                      type: e.target.value as BerichtType,
                    }))
                  }
                  style={veldStijl}
                >
                  {BERICHT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Versie (optioneel)
                <input
                  value={formulier.versie ?? ""}
                  onChange={(e) =>
                    setFormulier((f) => ({
                      ...f,
                      versie: e.target.value || null,
                    }))
                  }
                  style={veldStijl}
                />
              </label>
              <button type="submit">
                {bewerktId === null ? "Aanmaken" : "Opslaan"}
              </button>{" "}
              {bewerktId !== null && (
                <button type="button" onClick={bewerkenAnnuleren}>
                  Annuleren
                </button>
              )}
            </form>
          </section>

          <section style={{ marginTop: "2rem" }}>
            <h2>Alle berichten</h2>
            {laden && <p>Laden…</p>}
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr
                  style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}
                >
                  <th>Titel</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Aangemaakt door</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {(berichten ?? []).map((b) => (
                  <tr key={b.id} style={{ borderBottom: "1px solid #eee" }}>
                    <td>{b.titel}</td>
                    <td>{b.type}</td>
                    <td>{b.gepubliceerd ? "gepubliceerd" : "concept"}</td>
                    <td>{b.aangemaakt_door}</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      <button onClick={() => bewerkenStarten(b)}>
                        Bewerken
                      </button>{" "}
                      <button onClick={() => publicatieWisselen(b)}>
                        {b.gepubliceerd ? "Depubliceren" : "Publiceren"}
                      </button>{" "}
                      <button onClick={() => berichtVerwijderen(b.id)}>
                        Verwijderen
                      </button>
                    </td>
                  </tr>
                ))}
                {berichten?.length === 0 && (
                  <tr>
                    <td colSpan={5}>Geen berichten.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>
        </>
      )}
    </main>
  );
}
