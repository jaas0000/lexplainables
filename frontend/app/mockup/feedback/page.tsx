"use client";

import { useState } from "react";
import type { components } from "@/generated/types";
import { SectieHeader, LeegePlaceholder } from "@/components/beheer/SectieHeader";
import { CATEGORIE_META, CATEGORIEN, type Categorie } from "@/lib/feedback-types";
import { CategorieBadge } from "@/components/feedback/CategorieBadge";
import { FeedbackItem } from "@/components/feedback/FeedbackItem";

type FeedbackRead = components["schemas"]["FeedbackRead"];

const NEP_FEEDBACK: FeedbackRead[] = [
  {
    id: 3,
    client_id: "abc123",
    userid: "m.dejong",
    categorie: "probleemmelding",
    tekst:
      "De zoekbalk reageert niet na het filteren op datum — bij een lege resultatenset crasht de pagina.",
    pagina: "/analyse/123",
    created: "2026-08-14T09:12:00Z",
  },
  {
    id: 2,
    client_id: "def456",
    userid: "p.smits",
    categorie: "verbeteridee",
    tekst:
      "Zou handig zijn als je de exportknop ook bovenaan de pagina hebt staan, niet alleen onderaan.",
    pagina: "/analyse/87",
    created: "2026-08-13T14:55:00Z",
  },
  {
    id: 1,
    client_id: "ghi789",
    userid: "a.visser",
    categorie: "compliment",
    tekst: "Geweldige tool! Bespaart ons uren handmatig werk.",
    pagina: null,
    created: "2026-08-12T11:03:00Z",
  },
];

type Variant =
  | "knop-gesloten"
  | "knop-open"
  | "knop-verzonden"
  | "beheer-navigatieknop"
  | "feedbackpagina-gevuld"
  | "feedbackpagina-leeg";

const VARIANTEN: { id: Variant; label: string }[] = [
  { id: "knop-gesloten",        label: "Knop — gesloten" },
  { id: "knop-open",            label: "Knop — formulier open" },
  { id: "knop-verzonden",       label: "Knop — verzonden" },
  { id: "beheer-navigatieknop", label: "Beheer — navigatieknop" },
  { id: "feedbackpagina-gevuld", label: "Feedbackpagina — met items" },
  { id: "feedbackpagina-leeg",   label: "Feedbackpagina — leeg" },
];

function IcoonChat() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
    </svg>
  );
}

function FeedbackPanel({ verzonden }: { verzonden: boolean }) {
  return (
    <div
      style={{
        position: "absolute",
        bottom: "4.5rem",
        right: "1.5rem",
        width: "22rem",
        maxWidth: "calc(100% - 3rem)",
        background: "rgb(var(--paper))",
        border: "1px solid rgb(var(--line))",
        borderRadius: "8px",
        boxShadow: "0 8px 24px rgb(0 0 0 / 0.12)",
        overflow: "hidden",
        zIndex: 10,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0.75rem 1rem",
          borderBottom: "1px solid rgb(var(--line))",
          background: "rgb(var(--surface))",
        }}
      >
        <span style={{ fontSize: "0.875rem", fontWeight: 600 }}>Geef feedback</span>
        <button
          aria-label="Sluiten"
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "rgb(var(--muted))",
            fontSize: "1rem",
            lineHeight: 1,
            padding: "0.125rem 0.25rem",
          }}
        >
          ✕
        </button>
      </div>

      {verzonden ? (
        <div
          style={{
            padding: "2rem 1rem",
            textAlign: "center",
            color: "rgb(var(--succes))",
            fontSize: "0.875rem",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.59L5.41 12l1.42-1.42L10 13.17l7.17-7.17 1.42 1.42L10 16.59z" />
          </svg>
          Bedankt voor uw feedback!
        </div>
      ) : (
        <div style={{ padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <div>
            <label
              style={{
                display: "block",
                fontSize: "0.8125rem",
                fontWeight: 500,
                marginBottom: "0.25rem",
                color: "rgb(var(--ink))",
              }}
            >
              Categorie
            </label>
            <select
              defaultValue="verbeteridee"
              style={{
                width: "100%",
                padding: "0.375rem 0.5rem",
                fontSize: "0.8125rem",
                border: "1px solid rgb(var(--line))",
                borderRadius: "4px",
                background: "rgb(var(--paper))",
                color: "rgb(var(--ink))",
              }}
            >
              {CATEGORIEN.map((c) => (
                <option key={c} value={c}>
                  {CATEGORIE_META[c].label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label
              style={{
                display: "block",
                fontSize: "0.8125rem",
                fontWeight: 500,
                marginBottom: "0.25rem",
                color: "rgb(var(--ink))",
              }}
            >
              Uw opmerking{" "}
              <span style={{ fontWeight: 400, color: "rgb(var(--faint))" }}>
                (verplicht, max 4000 tekens)
              </span>
            </label>
            <textarea
              rows={4}
              placeholder="Beschrijf uw feedback..."
              style={{
                width: "100%",
                padding: "0.375rem 0.5rem",
                fontSize: "0.8125rem",
                border: "1px solid rgb(var(--line))",
                borderRadius: "4px",
                background: "rgb(var(--paper))",
                color: "rgb(var(--ink))",
                resize: "vertical",
                fontFamily: "inherit",
                boxSizing: "border-box",
              }}
            />
          </div>
          <button className="btn btn-primary" style={{ width: "100%" }}>
            Verzenden
          </button>
        </div>
      )}
    </div>
  );
}

function KnopDemo({ variant }: { variant: "gesloten" | "open" | "verzonden" }) {
  return (
    <div
      style={{
        position: "relative",
        height: "26rem",
        background: "rgb(var(--surface))",
        borderRadius: "8px",
        border: "1px solid rgb(var(--line))",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "2rem",
          color: "rgb(var(--faint))",
          fontSize: "0.875rem",
          fontStyle: "italic",
          lineHeight: 1.6,
        }}
      >
        ← Simulatie van de applicatiepagina →
        <br />
        De feedbackknop zweeft rechtsonder op het scherm, ongeacht welke pagina
        de gebruiker bezoekt.
      </div>

      {variant !== "gesloten" && <FeedbackPanel verzonden={variant === "verzonden"} />}

      <button
        className="btn btn-primary"
        style={{
          position: "absolute",
          bottom: "1.5rem",
          right: "1.5rem",
          display: "flex",
          alignItems: "center",
          gap: "0.375rem",
          fontSize: "0.8125rem",
          padding: "0.5rem 0.875rem",
          boxShadow: "0 4px 12px rgb(0 0 0 / 0.15)",
        }}
      >
        <IcoonChat />
        Feedback
      </button>
    </div>
  );
}

function BeheerNavigatieKnop() {
  return (
    <div>
      <SectieHeader titel="Gebruikersfeedback" />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "1rem",
          background: "rgb(var(--surface))",
          border: "1px solid rgb(var(--line))",
          borderRadius: "6px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
          <span style={{ fontSize: "0.875rem", color: "rgb(var(--ink))" }}>
            Ingezonden feedbackitems
          </span>
          <span
            style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              padding: "0.125rem 0.4rem",
              borderRadius: "99px",
              background: "rgb(var(--fout))",
              color: "white",
            }}
          >
            3 ongelezen
          </span>
        </div>
        <button className="btn btn-secondary" style={{ fontSize: "0.8125rem" }}>
          Bekijk feedback →
        </button>
      </div>
    </div>
  );
}

function FeedbackPaginaDemo({ items }: { items: FeedbackRead[] }) {
  return (
    <div>
      <SectieHeader
        titel="Gebruikersfeedback"
        aantal={items.length}
        subtitel={items.length > 0 ? "3 ongelezen" : undefined}
      />
      {items.length === 0 ? (
        <LeegePlaceholder tekst="Nog geen feedback ontvangen." />
      ) : (
        <div>
          {items.map((item) => (
            <FeedbackItem key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FeedbackMockup() {
  const [variant, setVariant] = useState<Variant>("knop-gesloten");

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
        Mockup — Feedback (story 009)
      </div>

      <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" }}>Feedback</h1>

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

      {variant === "knop-gesloten"        && <KnopDemo variant="gesloten" />}
      {variant === "knop-open"            && <KnopDemo variant="open" />}
      {variant === "knop-verzonden"       && <KnopDemo variant="verzonden" />}
      {variant === "beheer-navigatieknop" && <BeheerNavigatieKnop />}
      {variant === "feedbackpagina-gevuld" && <FeedbackPaginaDemo items={NEP_FEEDBACK} />}
      {variant === "feedbackpagina-leeg"   && <FeedbackPaginaDemo items={[]} />}
    </div>
  );
}
