import { describe, expect, it } from "vitest";
import { selectChart, type EChartSpec, type StatSpec } from "./chart-select";

const seriesType = (spec: EChartSpec) =>
  (spec.option.series as { type: string }[])[0].type;
const seriesCount = (spec: EChartSpec) => (spec.option.series as unknown[]).length;

describe("deterministic chart selection", () => {
  it("kpi → stat card with value + format", () => {
    const spec = selectChart({ type: "kpi", columns: ["mrr"], rows: [[222773.7]] }) as StatSpec;
    expect(spec.kind).toBe("stat");
    expect(spec.value).toBeCloseTo(222773.7);
    expect(spec.format).toBe("currency");
  });

  it("trend → line", () => {
    const spec = selectChart({
      type: "trend",
      columns: ["period", "amount"],
      rows: [["2025-01-01", 10], ["2025-02-01", 12]],
    }) as EChartSpec;
    expect(spec.kind).toBe("line");
    expect(seriesType(spec)).toBe("line");
  });

  it("breakdown → bar", () => {
    const spec = selectChart({
      type: "breakdown",
      columns: ["category", "amount"],
      rows: [["Beauty", 100], ["Home", 80]],
    }) as EChartSpec;
    expect(spec.kind).toBe("bar");
    expect(seriesType(spec)).toBe("bar");
  });

  it("comparison with many periods → multi-series line", () => {
    const rows: unknown[][] = [];
    for (let m = 1; m <= 8; m++) {
      rows.push([`2025-0${m}-01`, "North", m * 10]);
      rows.push([`2025-0${m}-01`, "South", m * 8]);
    }
    const spec = selectChart({ type: "comparison", columns: ["period", "region", "amount"], rows }) as EChartSpec;
    expect(spec.kind).toBe("line");
    expect(seriesCount(spec)).toBe(2); // one line per region
  });

  it("comparison with few periods → grouped bar", () => {
    const spec = selectChart({
      type: "comparison",
      columns: ["period", "region", "amount"],
      rows: [
        ["2024-01-01", "North", 5], ["2024-01-01", "South", 4],
        ["2025-01-01", "North", 7], ["2025-01-01", "South", 6],
      ],
    }) as EChartSpec;
    expect(spec.kind).toBe("groupedBar");
    expect(seriesType(spec)).toBe("bar");
    expect(seriesCount(spec)).toBe(2);
  });

  it("distribution with ≤6 categories → donut", () => {
    const spec = selectChart({
      type: "distribution",
      columns: ["region", "amount"],
      rows: [["North", 4], ["South", 3], ["East", 2], ["West", 1]],
    }) as EChartSpec;
    expect(spec.kind).toBe("donut");
    expect(seriesType(spec)).toBe("pie");
  });

  it("distribution with >6 categories → bar", () => {
    const rows = Array.from({ length: 9 }, (_, i) => [`c${i}`, i + 1]);
    const spec = selectChart({ type: "distribution", columns: ["category", "amount"], rows }) as EChartSpec;
    expect(spec.kind).toBe("bar");
  });
});
