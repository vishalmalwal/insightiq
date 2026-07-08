export interface DateRange {
  from: string;
  to: string;
}

// Anchored to the sample-data window (2024-01 … 2026-06).
const PRESETS: { label: string; range: DateRange | null }[] = [
  { label: "All time", range: null },
  { label: "Last 12 mo", range: { from: "2025-07-01", to: "2026-06-30" } },
  { label: "2026", range: { from: "2026-01-01", to: "2026-12-31" } },
  { label: "2025", range: { from: "2025-01-01", to: "2025-12-31" } },
  { label: "2024", range: { from: "2024-01-01", to: "2024-12-31" } },
];

export default function DateFilter({
  value,
  onChange,
}: {
  value: DateRange | null;
  onChange: (r: DateRange | null) => void;
}) {
  const activeLabel = value ? `${value.from}:${value.to}` : "all";
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {PRESETS.map((p) => {
        const key = p.range ? `${p.range.from}:${p.range.to}` : "all";
        const active = key === activeLabel;
        return (
          <button
            key={p.label}
            onClick={() => onChange(p.range)}
            className={`rounded-full px-3 py-1 text-xs transition-colors ${
              active
                ? "aurora text-white"
                : "border border-white/10 text-muted hover:text-ink"
            }`}
          >
            {p.label}
          </button>
        );
      })}
    </div>
  );
}
