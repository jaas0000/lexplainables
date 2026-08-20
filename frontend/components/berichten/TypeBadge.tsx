import { TYPE_META, type BerichtType } from "@/lib/bericht-types";

export function TypeBadge({ type }: { type: BerichtType }) {
  const { label, kleurVar } = TYPE_META[type];
  return (
    <span
      style={{
        fontSize: "0.6875rem",
        fontWeight: 600,
        padding: "0.125rem 0.4rem",
        borderRadius: "3px",
        color: `rgb(var(${kleurVar}))`,
        border: `1px solid rgb(var(${kleurVar}) / 0.4)`,
        background: `rgb(var(${kleurVar}) / 0.08)`,
      }}
    >
      {label}
    </span>
  );
}
