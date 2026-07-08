import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  askQuestion,
  getDashboard,
  getProjects,
  getSampleQuestions,
  patchDashboardLayout,
  type AskResponse,
} from "./lib/api";
import DashboardGrid, { DashboardSkeleton } from "./components/DashboardGrid";
import DateFilter, { type DateRange } from "./components/DateFilter";
import ThemeToggle from "./components/ThemeToggle";
import SemanticLayerEditor from "./components/SemanticLayerEditor";
import EvalView from "./components/EvalView";
import { useTheme } from "./hooks/useTheme";
import { useReducedMotion } from "./hooks/useReducedMotion";
import { useLenis } from "./hooks/useLenis";
import { paletteFor } from "./lib/theme";

export default function App() {
  const { mode, toggle } = useTheme();
  const reduced = useReducedMotion();
  useLenis(!reduced);
  const palette = useMemo(() => paletteFor(mode), [mode]);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const projects = useQuery({ queryKey: ["projects"], queryFn: getProjects });
  const [projectId, setProjectId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [draft, setDraft] = useState("");
  const [range, setRange] = useState<DateRange | null>(null);
  const [shared, setShared] = useState<AskResponse | null>(null);
  const [sharedLayout, setSharedLayout] = useState<unknown[] | undefined>(undefined);
  const [showModel, setShowModel] = useState(false);
  const [view, setView] = useState<"ask" | "evals">("ask");

  // Zero-setup: default to the first sample project.
  useEffect(() => {
    if (!projectId && projects.data?.length) {
      const sample = projects.data.find((p) => p.data_source === "sample") ?? projects.data[0];
      setProjectId(sample.id);
    }
  }, [projects.data, projectId]);

  const samples = useQuery({
    queryKey: ["sample-questions", projectId],
    queryFn: () => getSampleQuestions(projectId as string),
    enabled: !!projectId,
  });

  const ask = useMutation({
    mutationFn: (vars: { q: string; r: DateRange | null }) =>
      askQuestion(
        projectId as string,
        vars.q,
        vars.r ? { dateFrom: vars.r.from, dateTo: vars.r.to } : {},
      ),
    onMutate: () => {
      setShared(null);
      setSharedLayout(undefined);
    },
    onSuccess: (data) => {
      if (data.dashboard_id) {
        const url = new URL(window.location.href);
        url.searchParams.set("d", data.dashboard_id);
        window.history.replaceState({}, "", url.toString());
      }
    },
  });

  const run = (q: string, r: DateRange | null = range) => {
    const query = q.trim();
    if (!query || !projectId) return;
    setQuestion(query);
    setDraft(query);
    ask.mutate({ q: query, r });
  };

  const onRange = (r: DateRange | null) => {
    setRange(r);
    if (question) run(question, r); // re-run the pipeline with the time filter
  };

  // Restore a shared dashboard from ?d=<id>.
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("d");
    if (!id) return;
    getDashboard(id)
      .then((d) => {
        if (d.project_id) setProjectId(d.project_id);
        setQuestion(d.response.question);
        setDraft(d.response.question);
        setShared(d.response);
        setSharedLayout(d.layout as unknown[]);
      })
      .catch(() => undefined);
  }, []);

  const result: AskResponse | null = ask.data ?? shared;
  const hasResult = ask.isPending || !!result;

  const selectProject = (id: string) => {
    setProjectId(id);
    setQuestion("");
    setDraft("");
    setShared(null);
    setSharedLayout(undefined);
    ask.reset();
  };

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-[1200px] items-center justify-between px-5 py-5">
        <div className="flex items-center gap-3">
          <span className="font-display text-xl font-bold tracking-tight text-ink">
            Insight<span className="aurora-text">IQ</span>
          </span>
          {projects.data && projects.data.length > 0 && (
            <div className="ml-2 hidden gap-1 sm:flex">
              {projects.data.map((p) => (
                <button
                  key={p.id}
                  onClick={() => selectProject(p.id)}
                  className={`rounded-full px-3 py-1 text-xs transition-colors ${
                    projectId === p.id
                      ? "bg-white/[0.08] text-ink"
                      : "text-muted hover:text-ink"
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <nav className="panel flex rounded-full p-0.5 text-xs">
            {(["ask", "evals"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`rounded-full px-3 py-1 capitalize transition-colors ${
                  view === v ? "aurora text-white" : "text-muted hover:text-ink"
                }`}
              >
                {v}
              </button>
            ))}
          </nav>
          <ThemeToggle mode={mode} onToggle={toggle} />
        </div>
      </header>

      {view === "evals" && <EvalView />}

      {view === "ask" && (
        <>
      {/* Hero / Ask bar — the signature moment. Tall until a result resolves. */}
      <section
        className={`relative mx-auto max-w-[1200px] px-5 ${
          hasResult ? "pb-4 pt-2" : "flex min-h-[62vh] flex-col justify-center pb-10"
        }`}
      >
        <div className="aurora-hero pointer-events-none absolute inset-0 -z-10 opacity-90" />

        {!hasResult && (
          <motion.div
            initial={reduced ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-6 text-center"
          >
            <h1 className="font-display text-4xl font-bold leading-tight text-ink sm:text-6xl">
              Ask your data <span className="aurora-text">anything.</span>
            </h1>
            <p className="mx-auto mt-3 max-w-xl text-sm text-muted sm:text-base">
              Type a question in plain English and InsightIQ plans the queries, writes safe SQL,
              and assembles a whole dashboard.
            </p>
          </motion.div>
        )}

        <div className={`mx-auto w-full ${hasResult ? "" : "max-w-2xl"}`}>
          <div className="aurora-ring panel flex items-center gap-2 rounded-2xl p-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run(draft)}
              placeholder="e.g. compare monthly revenue by region this year vs last year"
              className="flex-1 bg-transparent px-3 py-2 text-ink placeholder:text-muted focus:outline-none"
            />
            <button
              onClick={() => run(draft)}
              disabled={ask.isPending || !draft.trim()}
              className="aurora rounded-xl px-5 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {ask.isPending ? "Thinking…" : "Ask"}
            </button>
          </div>

          {/* Sample-question chips — one click, zero typing. */}
          {samples.data && samples.data.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {samples.data.map((q) => (
                <button
                  key={q}
                  onClick={() => run(q)}
                  className="panel panel-hover rounded-full px-3 py-1.5 text-xs text-muted hover:text-ink"
                >
                  {q}
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Dashboard */}
      {hasResult && (
        <section className="mx-auto max-w-[1200px] px-5 pb-24">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate font-display text-lg font-semibold text-ink">
                {question}
              </div>
              {result && (
                <div className="mt-0.5 text-xs text-muted">
                  {result.plan.intents.length} chart
                  {result.plan.intents.length === 1 ? "" : "s"}
                  {result.cache_hit && " · cached"}
                  {result.cost_usd > 0 && ` · $${result.cost_usd.toFixed(4)}`}
                  {result.dashboard_id && (
                    <>
                      {" · "}
                      <button
                        onClick={() =>
                          navigator.clipboard?.writeText(window.location.href).catch(() => undefined)
                        }
                        className="underline decoration-dotted hover:text-ink"
                      >
                        copy link
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
            <DateFilter value={range} onChange={onRange} />
          </div>

          {ask.isPending && <DashboardSkeleton />}
          {ask.isError && (
            <div className="panel p-6 text-sm text-muted">
              {(ask.error as Error).message}
            </div>
          )}
          {result?.degraded && (
            <div className="panel p-6 text-sm text-amber-400">{result.message}</div>
          )}
          {result && !result.degraded && !ask.isPending && (
            <DashboardGrid
              cards={result.cards}
              palette={palette}
              animate={!reduced}
              initialLayout={sharedLayout as never}
              onLayoutChange={(l) => {
                const id = result.dashboard_id;
                if (!id) return;
                if (saveTimer.current) clearTimeout(saveTimer.current);
                saveTimer.current = setTimeout(() => {
                  patchDashboardLayout(id, l).catch(() => undefined);
                }, 800);
              }}
            />
          )}
        </section>
      )}

      {/* Optional: inspect / edit the semantic layer (Phase 2 feature). */}
      {projectId && (
        <section className="mx-auto max-w-[1200px] px-5 pb-16">
          <button
            onClick={() => setShowModel((s) => !s)}
            className="text-xs font-medium text-muted hover:text-ink"
          >
            {showModel ? "Hide data model" : "Edit data model"}
          </button>
          {showModel && <SemanticLayerEditor projectId={projectId} />}
        </section>
      )}
        </>
      )}
    </div>
  );
}
