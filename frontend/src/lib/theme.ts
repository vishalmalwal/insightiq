export type ThemeMode = "dark" | "light";

export interface Palette {
  colors: string[];
  axis: string;
  split: string;
  tooltipBg: string;
  tooltipText: string;
}

const AURORA = ["#7C3AED", "#06B6D4", "#D946EF", "#22D3EE", "#A78BFA", "#F0ABFC"];

export const DARK_PALETTE: Palette = {
  colors: AURORA,
  axis: "#94A3B8",
  split: "rgba(255,255,255,0.07)",
  tooltipBg: "#111827",
  tooltipText: "#E5EDF9",
};

export const LIGHT_PALETTE: Palette = {
  colors: AURORA,
  axis: "#475569",
  split: "rgba(15,23,42,0.08)",
  tooltipBg: "#FFFFFF",
  tooltipText: "#0F172A",
};

export function paletteFor(mode: ThemeMode): Palette {
  return mode === "light" ? LIGHT_PALETTE : DARK_PALETTE;
}
