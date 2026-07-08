/**
 * Deterministic chart selection: (intent type + result shape) → ECharts spec.
 * No LLM. Rules: trend→line, breakdown→bar, comparison→grouped bar/line,
 * kpi→stat, distribution→bar/pie (≤6 categories → donut).
 */
import type { EChartsOption } from "echarts";
import { isCurrencyName, isPercentName } from "./format";
import { DARK_PALETTE, type Palette } from "./theme";

export interface CardLike {
  type: string;
  columns: string[];
  rows: unknown[][];
}

export type ChartKind = "stat" | "line" | "bar" | "groupedBar" | "donut";
export type ValueFormat = "currency" | "number" | "percent";

export interface StatSpec {
  kind: "stat";
  label: string;
  value: number;
  format: ValueFormat;
}
export interface EChartSpec {
  kind: Exclude<ChartKind, "stat">;
  option: EChartsOption;
}
export type ChartSpec = StatSpec | EChartSpec;

const DONUT_MAX = 6;

function isNumericColumn(rows: unknown[][], ci: number): boolean {
  return rows.length > 0 && rows.every((r) => r[ci] === null || typeof r[ci] === "number");
}

function classify(card: CardLike) {
  const numeric = card.columns.map((_, ci) => isNumericColumn(card.rows, ci));
  const periodIdx = card.columns.indexOf("period");
  let measureIdx = -1;
  for (let i = numeric.length - 1; i >= 0; i--) {
    if (numeric[i]) {
      measureIdx = i;
      break;
    }
  }
  const catIdxs = card.columns
    .map((_, i) => i)
    .filter((i) => !numeric[i] && i !== periodIdx);
  return { numeric, periodIdx, measureIdx: measureIdx < 0 ? card.columns.length - 1 : measureIdx, catIdxs };
}

function formatOf(name: string): ValueFormat {
  if (isCurrencyName(name)) return "currency";
  if (isPercentName(name)) return "percent";
  return "number";
}

function base(palette: Palette): EChartsOption {
  return {
    color: palette.colors,
    grid: { left: 8, right: 16, top: 28, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      backgroundColor: palette.tooltipBg,
      borderWidth: 0,
      textStyle: { color: palette.tooltipText, fontSize: 12 },
    },
    legend: { type: "scroll", top: 0, textStyle: { color: palette.axis, fontSize: 11 } },
    xAxis: {
      type: "category",
      axisLabel: { color: palette.axis, fontSize: 11, hideOverlap: true },
      axisLine: { lineStyle: { color: palette.split } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: palette.axis, fontSize: 11 },
      splitLine: { lineStyle: { color: palette.split } },
    },
  };
}

function pivot(card: CardLike, periodIdx: number, catIdx: number, measureIdx: number) {
  const periods = Array.from(new Set(card.rows.map((r) => String(r[periodIdx])))).sort();
  const cats = Array.from(new Set(card.rows.map((r) => String(r[catIdx]))));
  const lookup = new Map<string, number>();
  for (const r of card.rows) {
    lookup.set(`${r[periodIdx]}|${r[catIdx]}`, r[measureIdx] as number);
  }
  const series = cats.map((c) => ({
    name: c,
    data: periods.map((p) => lookup.get(`${p}|${c}`) ?? null),
  }));
  return { periods, cats, series };
}

function shortLabel(p: string): string {
  return p.length >= 7 ? p.slice(0, 7) : p; // YYYY-MM from an ISO date
}

export function selectChart(card: CardLike, palette: Palette = DARK_PALETTE): ChartSpec {
  const { periodIdx, measureIdx, catIdxs } = classify(card);
  const measureName = card.columns[measureIdx] ?? "value";

  if (card.type === "kpi") {
    const value = (card.rows[0]?.[measureIdx] as number) ?? 0;
    return { kind: "stat", label: measureName, value, format: formatOf(measureName) };
  }

  if (card.type === "trend") {
    const opt = base(palette);
    if (periodIdx >= 0 && catIdxs.length > 0) {
      const { periods, series } = pivot(card, periodIdx, catIdxs[0], measureIdx);
      opt.xAxis = { ...(opt.xAxis as object), data: periods.map(shortLabel) };
      opt.series = series.map((s) => ({ ...s, type: "line", smooth: true, showSymbol: false }));
    } else {
      const xi = periodIdx >= 0 ? periodIdx : 0;
      opt.xAxis = { ...(opt.xAxis as object), data: card.rows.map((r) => shortLabel(String(r[xi]))) };
      opt.legend = { show: false };
      opt.series = [
        { name: measureName, type: "line", smooth: true, showSymbol: false, areaStyle: { opacity: 0.08 }, data: card.rows.map((r) => r[measureIdx] as number) },
      ];
    }
    return { kind: "line", option: opt };
  }

  if (card.type === "comparison") {
    if (periodIdx >= 0 && catIdxs.length > 0) {
      const { periods, series } = pivot(card, periodIdx, catIdxs[0], measureIdx);
      const opt = base(palette);
      opt.xAxis = { ...(opt.xAxis as object), data: periods.map(shortLabel) };
      if (periods.length > 6) {
        opt.series = series.map((s) => ({ ...s, type: "line", smooth: true, showSymbol: false }));
        return { kind: "line", option: opt };
      }
      opt.series = series.map((s) => ({ ...s, type: "bar" }));
      return { kind: "groupedBar", option: opt };
    }
    // no breakdown → treat as a line over the period
    return selectChart({ ...card, type: "trend" }, palette);
  }

  if (card.type === "distribution") {
    const catIdx = catIdxs[0] ?? 0;
    const labels = card.rows.map((r) => String(r[catIdx]));
    const values = card.rows.map((r) => r[measureIdx] as number);
    if (labels.length <= DONUT_MAX) {
      return {
        kind: "donut",
        option: {
          color: palette.colors,
          tooltip: { trigger: "item", backgroundColor: palette.tooltipBg, borderWidth: 0, textStyle: { color: palette.tooltipText } },
          legend: { type: "scroll", bottom: 0, textStyle: { color: palette.axis, fontSize: 11 } },
          series: [
            {
              type: "pie",
              radius: ["45%", "72%"],
              center: ["50%", "45%"],
              itemStyle: { borderColor: palette.tooltipBg, borderWidth: 2 },
              label: { color: palette.axis, fontSize: 11 },
              data: labels.map((name, i) => ({ name, value: values[i] })),
            },
          ],
        },
      };
    }
    return selectChart({ ...card, type: "breakdown" }, palette);
  }

  // breakdown (default): horizontal-friendly vertical bar
  const catIdx = catIdxs[0] ?? 0;
  const opt = base(palette);
  opt.legend = { show: false };
  opt.xAxis = { ...(opt.xAxis as object), data: card.rows.map((r) => String(r[catIdx])) };
  opt.series = [{ name: measureName, type: "bar", barMaxWidth: 42, itemStyle: { borderRadius: [4, 4, 0, 0] }, data: card.rows.map((r) => r[measureIdx] as number) }];
  return { kind: "bar", option: opt };
}
