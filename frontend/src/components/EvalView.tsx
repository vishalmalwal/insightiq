import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getEvalRun, listEvalRuns, runEval, type EvalRun } from "../lib/api";

const pct = (v: number | null) => (v == null ? "—" : `${Math.round(v * 100)}%`);

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel p-4">
      <div className="text-[11px] font-medium uppercase tracking-widest text-muted">{label}</div>
      <div className="mt-1 aurora-text font-display text-3xl font-bold tabular-nums">{value}</div>
    </div>
  );
}

export default function EvalView() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);

  const runs = useQuery({ queryKey: ["eval-runs"], queryFn: listEvalRuns });
  const run = useMutation({
    mutationFn: runEval,
    onSuccess: (r) => {
      setSelected(r.id);
      qc.invalidateQueries({ queryKey: ["eval-runs"] });
    },
  });

  const activeId = selected ?? runs.data?.[0]?.id ?? null;
  const detail = useQuery({
    queryKey: ["eval-run", activeId],
    queryFn: () => getEvalRun(activeId as string),
    enabled: !!activeId,
  });
  const active: EvalRun | undefined = detail.data ?? runs.data?.find((r) => r.id === activeId);

  return (
    <section className="mx-auto max-w-[1200px] px-5 pb-24 pt-4">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold text-ink">SQL-accuracy evals</h2>
          <p className="mt-1 text-sm text-muted">
            Each case runs the full pipeline and compares its result set to a hand-written gold
            query (denotation match).
          </p>
        </div>
        <button
          onClick={() => run.mutate()}
          disabled={run.isPending}
          className="aurora rounded-xl px-5 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
        >
          {run.isPending ? "Running…" : "Run suite"}
        </button>
      </div>

      {!runs.isLoading && (runs.data?.length ?? 0) === 0 && !run.isPending && (
        <div className="panel p-8 text-center text-sm text-muted">
          No runs yet — click <span className="text-ink">Run suite</span> to score the pipeline.
        </div>
      )}

      {active && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="Execution accuracy" value={pct(active.exec_accuracy)} />
            <Metric label="Valid-SQL rate" value={pct(active.valid_sql_rate)} />
            <Metric label="Intent accuracy" value={pct(active.intent_accuracy)} />
            <Metric
              label="Avg latency"
              value={active.avg_latency_ms == null ? "—" : `${Math.round(active.avg_latency_ms)} ms`}
            />
          </div>
          <div className="mt-2 text-xs text-muted">
            suite {active.suite_version}
            {` · ${active.provider}`}
            {active.git_sha && ` · ${active.git_sha}`}
            {active.finished_at && ` · ${new Date(active.finished_at).toLocaleString()}`}
          </div>
        </>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_260px]">
        {/* Per-case results */}
        <div className="panel overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/[0.03] text-xs text-muted">
              <tr>
                <th className="px-4 py-2">Case</th>
                <th className="px-4 py-2">Result</th>
                <th className="px-4 py-2 text-right">Latency</th>
              </tr>
            </thead>
            <tbody>
              {detail.data?.cases.map((c) => (
                <tr key={c.case_id} className="border-t border-white/[0.06]">
                  <td className="px-4 py-2 font-mono text-xs text-ink">{c.case_id}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        c.passed
                          ? "bg-emerald-500/15 text-emerald-400"
                          : "bg-red-500/15 text-red-400"
                      }`}
                    >
                      {c.passed ? "pass" : "fail"}
                    </span>
                    {!c.passed && c.error && (
                      <span className="ml-2 text-xs text-muted">{c.error}</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs text-muted">
                    {c.latency_ms == null ? "—" : `${Math.round(c.latency_ms)} ms`}
                  </td>
                </tr>
              ))}
              {!detail.data && (
                <tr>
                  <td className="px-4 py-6 text-center text-sm text-muted" colSpan={3}>
                    {activeId ? "Loading…" : "Run the suite to see per-case results."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Run history */}
        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-widest text-muted">
            History
          </div>
          <ul className="space-y-1">
            {runs.data?.map((r) => (
              <li key={r.id}>
                <button
                  onClick={() => setSelected(r.id)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-xs ${
                    r.id === activeId ? "panel" : "text-muted hover:text-ink"
                  }`}
                >
                  <span className="font-medium text-ink">{pct(r.exec_accuracy)}</span>
                  <span className="ml-2">{r.provider}</span>
                  <span className="ml-2 text-muted">{r.suite_version}</span>
                  <span className="block text-[10px] text-muted">
                    {r.finished_at ? new Date(r.finished_at).toLocaleString() : "running…"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
