import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import EChart from "./EChart";
import StatCard from "./StatCard";
import { selectChart } from "../lib/chart-select";
import type { Palette } from "../lib/theme";
import type { IntentCard } from "../lib/api";

const TYPE_LABEL: Record<string, string> = {
  trend: "Trend",
  breakdown: "Breakdown",
  comparison: "Comparison",
  distribution: "Distribution",
  kpi: "KPI",
};

export default function ChartCard({ card, palette }: { card: IntentCard; palette: Palette }) {
  const [sqlOpen, setSqlOpen] = useState(false);
  const spec = useMemo(
    () => (card.ok ? selectChart(card, palette) : null),
    [card, palette],
  );

  return (
    <div className="panel panel-hover flex h-full flex-col overflow-hidden p-4">
      <div className="mb-1 flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">{card.title}</h3>
        <span className="shrink-0 rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted">
          {TYPE_LABEL[card.type] ?? card.type}
        </span>
      </div>

      {card.caption && <p className="mb-2 text-xs text-muted">{card.caption}</p>}

      <div className="min-h-0 flex-1">
        {!card.ok && (
          <div className="flex h-full items-center justify-center text-center text-sm text-muted">
            {card.error ?? "No result"}
          </div>
        )}
        {card.ok && spec?.kind === "stat" && (
          <StatCard label={spec.label} value={spec.value} format={spec.format} />
        )}
        {card.ok && spec && spec.kind !== "stat" && <EChart option={spec.option} height={220} />}
      </div>

      {card.sql && (
        <button
          onClick={() => setSqlOpen(true)}
          className="mt-2 self-start text-[11px] font-medium text-muted transition-colors hover:text-ink"
        >
          View SQL
        </button>
      )}

      <AnimatePresence>
        {sqlOpen && card.sql && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-black/50"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSqlOpen(false)}
            />
            <motion.aside
              className="panel fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col rounded-none p-6"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 320, damping: 34 }}
            >
              <div className="mb-3 flex items-center justify-between">
                <span className="font-display text-lg font-semibold text-ink">Generated SQL</span>
                <button
                  onClick={() => setSqlOpen(false)}
                  className="rounded p-1 text-muted hover:text-ink"
                  aria-label="Close"
                >
                  ✕
                </button>
              </div>
              <p className="mb-3 text-xs text-muted">{card.title}</p>
              <pre className="flex-1 overflow-auto rounded-lg bg-black/40 p-4 font-mono text-xs leading-relaxed text-ink/90">
                {card.sql}
              </pre>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
