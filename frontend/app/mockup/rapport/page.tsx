"use client";

import { useState } from "react";

type Variant = "rapport-gevuld" | "rapport-leeg-secties" | "niet-beschikbaar";

const VARIANTEN: { id: Variant; label: string }[] = [
  { id: "rapport-gevuld",       label: "Rapport — volledig gevuld" },
  { id: "rapport-leeg-secties", label: "Rapport — lege secties" },
  { id: "niet-beschikbaar",     label: "Rapport niet beschikbaar" },
];

const NEP_WERKGEBIED = {
  naam: "Participatieplicht Wwb 2026",
  hoofdvraag: "Welke verplichtingen en rechten vloeien voort uit de participatieplicht in de Wet werk en bijstand?",
  omschrijving:
    "Dit werkgebied analyseert de bepalingen rondom de participatieplicht voor bijstandsgerechtigden, inclusief uitzonderingen, sancties en de rol van de gemeente.",
  analysefocus: "Nadruk op de verhouding tussen participatieplicht en mantelzorgverlening.",
  scoping:
    "In scope: art. 1, 9, 9a, 17, 18 Wwb. Buiten scope: kinderopvang-gerelateerde verplichtingen.",
};

const NEP_BRONNEN = [
  {
    bron_id: "b1",
    label: "Wwb art. 9",
    wet: "Wet werk en bijstand",
    bwbId: "BWBR0011823",
    artikel: "9",
    lid: null,
    samenvatting:
      "Bijstandsgerechtigden zijn verplicht naar vermogen algemeen geaccepteerde arbeid te verkrijgen. De gemeente kan ontheffing verlenen voor mantelzorgers en alleenstaande ouders met kinderen tot 5 jaar.",
  },
  {
    bron_id: "b2",
    label: "Wwb art. 18",
    wet: "Wet werk en bijstand",
    bwbId: "BWBR0011823",
    artikel: "18",
    lid: null,
    samenvatting:
      "Bij niet-nakoming van de participatieplicht kan de gemeente de uitkering verlagen. De verlaging dient proportioneel te zijn en mag slechts éénmalig voor hetzelfde vergrijp worden opgelegd.",
  },
];

const NEP_BEGRIPPEN = [
  {
    id: "bg1",
    naam: "Participatieplicht",
    klasse: "Verplichting",
    definitie:
      "De uit art. 9 Wwb voortvloeiende plicht van de bijstandsgerechtigde om naar vermogen bij te dragen aan zijn eigen participatie door het verrichten van arbeid of maatschappelijk nuttige activiteiten.",
    synoniemen: ["arbeidsplicht", "re-integratieplicht"],
    voorbeeld: "Een bijstandsgerechtigde die weigert een aangeboden traject te volgen, schendt de participatieplicht.",
  },
  {
    id: "bg2",
    naam: "Ontheffing",
    klasse: "Besluit",
    definitie:
      "Een door het college van B&W verleende tijdelijke of permanente vrijstelling van de participatieplicht, op grond van dringende redenen (art. 9 lid 2 Wwb).",
    synoniemen: ["vrijstelling"],
    voorbeeld: "Mantelzorgers kunnen een ontheffing aanvragen als de zorg de re-integratie structureel belemmert.",
  },
  {
    id: "bg3",
    naam: "Verlaging uitkering",
    klasse: "Sanctie",
    definitie:
      "Een tijdelijke vermindering van de bijstandsuitkering die het college oplegt bij niet-nakoming van de participatieplicht (art. 18 Wwb).",
    synoniemen: ["maatregel", "sanctie"],
    voorbeeld: "Bij eerste weigering wordt de uitkering met 20% verlaagd gedurende één maand.",
  },
];

const NEP_REGELS = [
  {
    id: "r1",
    naam: "Participatieplicht geldt voor bijstandsgerechtigden",
    omschrijving:
      "Als een persoon bijstand ontvangt op grond van de Wwb, dan is die persoon verplicht naar vermogen algemeen geaccepteerde arbeid te verwerven en te aanvaarden (art. 9 lid 1 sub a Wwb).",
  },
  {
    id: "r2",
    naam: "Ontheffing mogelijk bij dringende redenen",
    omschrijving:
      "Als het college van B&W van oordeel is dat er sprake is van een dringende reden (art. 9 lid 2 Wwb), dan kan het college de participatieplicht tijdelijk of permanent opheffen.",
  },
  {
    id: "r3",
    naam: "Verlaging bij niet-nakoming",
    omschrijving:
      "Als een bijstandsgerechtigde de participatieplicht niet naleeft zonder dringende reden, dan verlaagt het college de uitkering overeenkomstig de verordening (art. 18 lid 2 Wwb).",
  },
];

function WerkgebiedSectie({ werkgebied }: { werkgebied: typeof NEP_WERKGEBIED }) {
  return (
    <section style={{ marginBottom: "2rem" }}>
      <h2
        style={{
          fontSize: "1.125rem",
          fontWeight: 700,
          marginBottom: "1rem",
          paddingBottom: "0.5rem",
          borderBottom: "2px solid rgb(var(--lijn, var(--line)))",
        }}
      >
        Werkgebied
      </h2>
      <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "0.5rem 1.5rem" }}>
        {[
          ["Naam", werkgebied.naam],
          ["Hoofdvraag", werkgebied.hoofdvraag],
          ["Analysefocus", werkgebied.analysefocus],
          ["Omschrijving", werkgebied.omschrijving],
          ["Scoping", werkgebied.scoping],
        ].map(([label, val]) => (
          val ? (
            <>
              <dt
                key={`dt-${label}`}
                style={{ fontSize: "0.8125rem", fontWeight: 600, color: "rgb(var(--muted))", whiteSpace: "nowrap" }}
              >
                {label}
              </dt>
              <dd key={`dd-${label}`} style={{ fontSize: "0.9rem", margin: 0 }}>{val}</dd>
            </>
          ) : null
        ))}
      </dl>
    </section>
  );
}

function BronnenSectie({ bronnen }: { bronnen: typeof NEP_BRONNEN }) {
  if (bronnen.length === 0) {
    return (
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "0.75rem" }}>Bronnen</h2>
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))", fontStyle: "italic" }}>
          Geen bronnen in dit rapport.
        </p>
      </section>
    );
  }
  return (
    <section style={{ marginBottom: "2rem" }}>
      <h2 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "1rem", paddingBottom: "0.5rem", borderBottom: "2px solid rgb(var(--line))" }}>
        Bronnen ({bronnen.length})
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {bronnen.map((b) => (
          <div
            key={b.bron_id}
            style={{
              padding: "1rem",
              background: "rgb(var(--surface))",
              border: "1px solid rgb(var(--line))",
              borderRadius: "6px",
            }}
          >
            <p style={{ fontWeight: 600, fontSize: "0.9rem", marginBottom: "0.375rem" }}>
              {b.label}{" "}
              <span style={{ fontWeight: 400, color: "rgb(var(--muted))", fontSize: "0.8125rem" }}>
                — {b.wet}
              </span>
            </p>
            <p style={{ fontSize: "0.875rem", lineHeight: 1.6 }}>{b.samenvatting}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function BegrippenSectie({ begrippen }: { begrippen: typeof NEP_BEGRIPPEN }) {
  if (begrippen.length === 0) {
    return (
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "0.75rem" }}>Begrippen</h2>
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))", fontStyle: "italic" }}>
          Geen begrippen gedefinieerd in dit rapport.
        </p>
      </section>
    );
  }
  return (
    <section style={{ marginBottom: "2rem" }}>
      <h2 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "1rem", paddingBottom: "0.5rem", borderBottom: "2px solid rgb(var(--line))" }}>
        Begrippen ({begrippen.length})
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
        {begrippen.map((b) => (
          <div
            key={b.id}
            style={{
              padding: "0.875rem 1rem",
              background: "rgb(var(--surface))",
              border: "1px solid rgb(var(--line))",
              borderRadius: "6px",
            }}
          >
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.625rem", marginBottom: "0.375rem" }}>
              <span style={{ fontWeight: 700, fontSize: "0.9375rem" }}>{b.naam}</span>
              <span
                style={{
                  fontSize: "0.6875rem",
                  fontWeight: 600,
                  padding: "0.1rem 0.4rem",
                  borderRadius: "4px",
                  background: "rgb(var(--info) / 0.15)",
                  color: "rgb(var(--info))",
                }}
              >
                {b.klasse}
              </span>
            </div>
            <p style={{ fontSize: "0.875rem", lineHeight: 1.6, marginBottom: "0.375rem" }}>
              {b.definitie}
            </p>
            {b.synoniemen.length > 0 && (
              <p style={{ fontSize: "0.8125rem", color: "rgb(var(--muted))" }}>
                Synoniemen: {b.synoniemen.join(", ")}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function RegelsSectie({ regels }: { regels: typeof NEP_REGELS }) {
  if (regels.length === 0) {
    return (
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "0.75rem" }}>Afleidingsregels</h2>
        <p style={{ fontSize: "0.875rem", color: "rgb(var(--faint))", fontStyle: "italic" }}>
          Geen afleidingsregels geformuleerd in dit rapport.
        </p>
      </section>
    );
  }
  return (
    <section style={{ marginBottom: "2rem" }}>
      <h2 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "1rem", paddingBottom: "0.5rem", borderBottom: "2px solid rgb(var(--line))" }}>
        Afleidingsregels ({regels.length})
      </h2>
      <ol style={{ paddingLeft: "1.5rem", display: "flex", flexDirection: "column", gap: "0.875rem" }}>
        {regels.map((r) => (
          <li key={r.id}>
            <p style={{ fontWeight: 600, fontSize: "0.9rem", marginBottom: "0.25rem" }}>{r.naam}</p>
            <p style={{ fontSize: "0.875rem", lineHeight: 1.6, color: "rgb(var(--ink))" }}>{r.omschrijving}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function RapportViewer({ bronnen = NEP_BRONNEN, begrippen = NEP_BEGRIPPEN, regels = NEP_REGELS }: {
  bronnen?: typeof NEP_BRONNEN;
  begrippen?: typeof NEP_BEGRIPPEN;
  regels?: typeof NEP_REGELS;
}) {
  return (
    <div style={{ maxWidth: "52rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem" }}>
        <div>
          <button className="btn btn-secondary" style={{ fontSize: "0.8125rem", marginBottom: "0.75rem" }}>
            ← Terug naar analyse
          </button>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }}>
            Rapport: {NEP_WERKGEBIED.naam}
          </h2>
        </div>
        <a
          href="#"
          className="btn btn-secondary"
          style={{ fontSize: "0.8125rem", textDecoration: "none" }}
          onClick={(e) => e.preventDefault()}
        >
          ↓ Download Markdown
        </a>
      </div>

      <div
        style={{
          background: "rgb(var(--paper))",
          border: "1px solid rgb(var(--line))",
          borderRadius: "8px",
          padding: "1.5rem 2rem",
        }}
      >
        <WerkgebiedSectie werkgebied={NEP_WERKGEBIED} />
        <BronnenSectie bronnen={bronnen} />
        <BegrippenSectie begrippen={begrippen} />
        <RegelsSectie regels={regels} />
      </div>
    </div>
  );
}

function NietBeschikbaar() {
  return (
    <div style={{ maxWidth: "36rem" }}>
      <button className="btn btn-secondary" style={{ fontSize: "0.8125rem", marginBottom: "1rem" }}>
        ← Terug naar analyse
      </button>
      <div className="melding melding-fout">
        Het rapport is nog niet beschikbaar — de analyse is nog niet klaar. Bekijk de voortgang
        op de statuspagina.
      </div>
      <div style={{ marginTop: "1rem" }}>
        <button className="btn btn-primary" style={{ fontSize: "0.8125rem" }}>
          Naar statuspagina →
        </button>
      </div>
    </div>
  );
}

export default function RapportMockup() {
  const [variant, setVariant] = useState<Variant>("rapport-gevuld");

  return (
    <div className="main">
      <div
        style={{
          display: "inline-flex",
          background: "rgb(var(--lint))",
          color: "white",
          borderRadius: "4px",
          padding: "0.2rem 0.625rem",
          fontSize: "0.6875rem",
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: "1.25rem",
        }}
      >
        Mockup — Rapport bekijken (story 013)
      </div>

      <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" }}>Rapport</h1>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "2rem" }}>
        {VARIANTEN.map((v) => (
          <button
            key={v.id}
            className={variant === v.id ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => setVariant(v.id)}
          >
            {v.label}
          </button>
        ))}
      </div>

      {variant === "rapport-gevuld"       && <RapportViewer />}
      {variant === "rapport-leeg-secties" && <RapportViewer bronnen={[]} begrippen={[]} regels={[]} />}
      {variant === "niet-beschikbaar"     && <NietBeschikbaar />}
    </div>
  );
}
