"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { TypeBadge } from "@/components/berichten/TypeBadge";
import { TYPE_META, type BerichtType } from "@/lib/bericht-types";

interface Bericht {
  id: number;
  titel: string;
  type: BerichtType;
  versie: string | null;
  gepubliceerd_op: string | null;
  gelezen: boolean;
  created: string;
}

function BerichtItem({ bericht }: { bericht: Bericht }) {
  const { kleurVar } = TYPE_META[bericht.type];
  const datum = new Date(bericht.gepubliceerd_op ?? bericht.created).toLocaleDateString(
    "nl-NL",
    { day: "numeric", month: "long", year: "numeric" },
  );

  return (
    <div
      style={{
        position: "relative",
        padding: "0.75rem 1rem 0.75rem 1.25rem",
        borderBottom: "1px solid rgb(var(--line))",
        background: bericht.gelezen ? "rgb(var(--paper))" : "rgb(var(--surface))",
      }}
    >
      {!bericht.gelezen && (
        <span
          aria-hidden
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: "3px",
            background: `rgb(var(${kleurVar}))`,
            borderRadius: "3px 0 0 3px",
          }}
        />
      )}
      <div style={{ display: "flex", alignItems: "center", gap: "0.375rem", flexWrap: "wrap" }}>
        <TypeBadge type={bericht.type} />
        {bericht.versie && (
          <span
            style={{
              fontSize: "0.6875rem",
              fontFamily: "monospace",
              padding: "0.125rem 0.4rem",
              borderRadius: "3px",
              color: "rgb(var(--faint))",
              border: "1px solid rgb(var(--line))",
              background: "rgb(var(--surface))",
            }}
          >
            {bericht.versie}
          </span>
        )}
      </div>
      <p
        style={{
          marginTop: "0.25rem",
          fontSize: "0.875rem",
          fontWeight: 600,
          color: "rgb(var(--ink))",
        }}
      >
        {bericht.titel}
      </p>
      <p style={{ marginTop: "0.2rem", fontSize: "0.75rem", color: "rgb(var(--faint))" }}>
        {datum}
      </p>
    </div>
  );
}

export function BerichtenPopover() {
  const [open, setOpen] = useState(false);
  const [ongelezen, setOngelezen] = useState(0);
  const [berichten, setBerichten] = useState<Bericht[] | null>(null);
  const [laden, setLaden] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function laadAantal() {
      try {
        const res = await fetch("/api/berichten/ongelezen-aantal");
        if (res.ok) {
          const data = (await res.json()) as { aantal: number };
          setOngelezen(data.aantal);
        }
      } catch {
        // Stil negeren bij netwerk-hapering.
      }
    }
    void laadAantal();
    const id = setInterval(() => void laadAantal(), 60_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e: MouseEvent) {
      if (
        panelRef.current?.contains(e.target as Node) ||
        triggerRef.current?.contains(e.target as Node)
      )
        return;
      setOpen(false);
    }
    function onEscape(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEscape);
    };
  }, [open]);

  async function onOpen() {
    setLaden(true);
    try {
      const res = await fetch("/api/berichten?ongelezen=true");
      if (!res.ok) return;
      const data = (await res.json()) as { items: Bericht[] };
      setBerichten(data.items);
      if (data.items.length > 0) {
        fetch("/api/berichten/lees-alles", { method: "POST" }).catch(() => {});
        setOngelezen(0);
      }
    } catch {
      // Panel toont wat er al staat.
    } finally {
      setLaden(false);
    }
  }

  function toggle() {
    const wordt = !open;
    setOpen(wordt);
    if (wordt) void onOpen();
  }

  const badgeLabel = ongelezen > 99 ? "99+" : String(ongelezen);

  return (
    <div style={{ position: "relative" }}>
      <button
        ref={triggerRef}
        type="button"
        aria-label="Berichten"
        aria-expanded={open}
        onClick={toggle}
        className={`nav-link${open ? " nav-link--active" : ""}`}
        style={{ position: "relative" }}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {ongelezen > 0 && (
          <span
            aria-hidden
            style={{
              position: "absolute",
              top: "0.5rem",
              right: "0.375rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minWidth: "1rem",
              height: "1rem",
              borderRadius: "9999px",
              background: "rgb(var(--fout))",
              color: "rgb(var(--paper))",
              fontSize: "0.6rem",
              fontWeight: 700,
              lineHeight: 1,
              padding: "0 0.2rem",
            }}
          >
            {badgeLabel}
          </span>
        )}
      </button>

      {open && (
        <div
          ref={panelRef}
          role="dialog"
          aria-label="Berichten"
          style={{
            position: "absolute",
            right: 0,
            top: "calc(100% + 0.375rem)",
            zIndex: 50,
            width: "20rem",
            maxHeight: "30rem",
            overflowY: "auto",
            background: "rgb(var(--paper))",
            border: "1px solid rgb(var(--line))",
            borderRadius: "6px",
            boxShadow: "0 4px 16px rgb(0 0 0 / 0.12)",
          }}
        >
          <div
            style={{
              padding: "0.625rem 1rem",
              borderBottom: "1px solid rgb(var(--line))",
            }}
          >
            <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "rgb(var(--ink))" }}>
              Berichten
            </p>
          </div>

          {laden && (
            <p
              style={{
                padding: "1rem",
                fontSize: "0.875rem",
                color: "rgb(var(--muted))",
              }}
            >
              Laden…
            </p>
          )}

          {!laden && berichten !== null && berichten.length === 0 && (
            <p
              style={{
                padding: "1rem",
                fontSize: "0.875rem",
                color: "rgb(var(--muted))",
              }}
            >
              Geen nieuwe berichten.
            </p>
          )}

          {!laden && berichten !== null && berichten.length > 0 && (
            <div>
              {berichten.map((b) => (
                <BerichtItem key={b.id} bericht={b} />
              ))}
            </div>
          )}

          {!laden && (
            <div
              style={{
                padding: "0.5rem 1rem",
                borderTop: "1px solid rgb(var(--line))",
              }}
            >
              <Link
                href="/berichten"
                onClick={() => setOpen(false)}
                style={{
                  fontSize: "0.75rem",
                  color: "rgb(var(--link))",
                }}
              >
                Alle berichten bekijken →
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
