export type BerichtType = "info" | "update" | "waarschuwing" | "kritiek";

export const TYPE_META: Record<BerichtType, { label: string; kleurVar: string }> = {
  info:         { label: "Info",         kleurVar: "--info" },
  update:       { label: "Update",       kleurVar: "--succes" },
  waarschuwing: { label: "Waarschuwing", kleurVar: "--waarschuwing" },
  kritiek:      { label: "Kritiek",      kleurVar: "--fout" },
};

export const BERICHT_TYPES: readonly BerichtType[] = Object.keys(
  TYPE_META,
) as BerichtType[];
