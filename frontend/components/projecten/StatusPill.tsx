import type { components } from "@/generated/types";

type AnalyseStatus = components["schemas"]["AnalyseOverzicht"]["status"];

export const STATUS_META: Record<
  AnalyseStatus,
  { label: string; kleurVar: string }
> = {
  nieuw: { label: "Nieuw", kleurVar: "--info" },
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
