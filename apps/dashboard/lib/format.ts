export function biasClass(bias: string): string {
  if (bias === "bearish") return "bias-bearish";
  if (bias === "bullish") return "bias-bullish";
  return "bias-neutral";
}

export function biasColorVar(bias: string): string {
  if (bias === "bearish") return "var(--bear)";
  if (bias === "bullish") return "var(--bull)";
  return "var(--neutral)";
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

export function formatShortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
