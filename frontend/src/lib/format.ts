export function isCurrencyName(name: string): boolean {
  return /amount|revenue|mrr|price|sales|cost|spend|total/i.test(name);
}
export function isPercentName(name: string): boolean {
  return /pct|percent|rate|ratio|share/i.test(name);
}

export function fmtNumber(v: number): string {
  if (Math.abs(v) >= 1_000_000) return (v / 1_000_000).toFixed(1) + "M";
  if (Math.abs(v) >= 1_000) return (v / 1_000).toFixed(1) + "k";
  return Number.isInteger(v) ? String(v) : v.toFixed(2);
}
export function fmtCurrency(v: number): string {
  return "$" + fmtNumber(v);
}
export function fmtValue(v: number, name: string): string {
  if (isCurrencyName(name)) return fmtCurrency(v);
  if (isPercentName(name)) return v.toFixed(1) + "%";
  return fmtNumber(v);
}
