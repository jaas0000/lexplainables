import type { components } from "@/generated/types";

type AnalyseStatus = components["schemas"]["AnalyseOverzicht"]["status"];

export const STATUS_META: Record<
  AnalyseStatus,
  { label: string; kleurVar: string }
> = {
  wachtrij: { label: "In wachtrij", kleurVar: "--muted" },
  actief: { label: "Actief", kleurVar: "--info" },
  review: { label: "Wacht op review", kleurVar: "--gold" },
  klaar: { label: "Klaar", kleurVar: "--succes" },
  fout: { label: "Fout", kleurVar: "--fout" },
};

export function StatusDot({ status }: { status: AnalyseStatus }) {
  const { label, kleurVar } = STATUS_META[status];
  return (
    <span
      style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
    >
      <span
        style={{
          width: "8px",
          height: "8px",
          borderRadius: "50%",
          background: `rgb(var(${kleurVar}))`,
          flexShrink: 0,
        }}
      />
      <span style={{ fontSize: "0.875rem", color: "rgb(var(--ink))" }}>
        {label}
      </span>
    </span>
  );
}
