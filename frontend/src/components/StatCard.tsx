import { fmtValue } from "../lib/format";
import type { ValueFormat } from "../lib/chart-select";

export default function StatCard({
  label,
  value,
}: {
  label: string;
  value: number;
  format: ValueFormat;
}) {
  return (
    <div className="flex h-full flex-col justify-center">
      <div className="text-[11px] font-medium uppercase tracking-widest text-muted">{label}</div>
      <div className="mt-2 aurora-text font-display text-5xl font-bold tabular-nums leading-none">
        {fmtValue(value, label)}
      </div>
    </div>
  );
}
