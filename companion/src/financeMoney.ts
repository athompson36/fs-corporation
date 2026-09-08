/** Display-only. API bodies remain integer USD cents. */
export function formatUsd(cents: number): string {
  const n = Number(cents);
  if (!Number.isFinite(n)) return "$—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(n / 100);
}
