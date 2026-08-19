/** Formatteer een ISO-tijdstempel naar een mensleesbare Nederlandse weergave. */
export function formatDatum(iso: string): string {
  return new Date(iso).toLocaleString("nl-NL", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
