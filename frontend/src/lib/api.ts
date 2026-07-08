/**
 * Typed API client. All calls go through the Vite dev proxy (/api → backend).
 * Response types mirror the backend Pydantic schemas.
 */

// In dev, unset → "/api/v1" (Vite proxies to the API). In prod set
// VITE_API_BASE to the deployed API origin (e.g. https://insightiq-api.onrender.com).
const BASE = `${import.meta.env.VITE_API_BASE ?? ""}/api/v1`;

export interface SystemInfo {
  app_name: string;
  version: string;
  environment: string;
  llm_provider: string;
  planner_model: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function getSystemInfo(): Promise<SystemInfo> {
  return request<SystemInfo>("/system/info");
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  data_source: string;
  created_at: string;
}

export function getProjects(): Promise<Project[]> {
  return request<Project[]>("/projects");
}

export interface SemanticLayerOut {
  id: string;
  project_id: string;
  version: number;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  spec: unknown;
  yaml: string;
}

export interface VersionMeta {
  version: number;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
}

export function getSemanticLayer(projectId: string, version?: number): Promise<SemanticLayerOut> {
  const q = version ? `?version=${version}` : "";
  return request<SemanticLayerOut>(`/projects/${projectId}/semantic-layer${q}`);
}

export function generateSemanticLayer(projectId: string): Promise<SemanticLayerOut> {
  return request<SemanticLayerOut>(`/projects/${projectId}/semantic-layer/generate`, {
    method: "POST",
  });
}

export function updateSemanticLayer(projectId: string, yaml: string): Promise<SemanticLayerOut> {
  return request<SemanticLayerOut>(`/projects/${projectId}/semantic-layer`, {
    method: "PUT",
    body: JSON.stringify({ yaml }),
  });
}

export function listSemanticVersions(projectId: string): Promise<VersionMeta[]> {
  return request<VersionMeta[]>(`/projects/${projectId}/semantic-layer/versions`);
}

export interface IntentCard {
  intent_id: string;
  type: string;
  title: string;
  ok: boolean;
  sql: string | null;
  columns: string[];
  rows: unknown[][];
  row_count: number;
  caption: string | null;
  error: string | null;
}

export interface AskResponse {
  ask_request_id: string | null;
  dashboard_id: string | null;
  question: string;
  degraded: boolean;
  message: string | null;
  cache_hit: boolean;
  cost_usd: number;
  plan: { question: string; intents: { id: string; type: string; title: string }[] };
  cards: IntentCard[];
}

export interface AskParams {
  dateFrom?: string;
  dateTo?: string;
}

export function askQuestion(
  projectId: string,
  question: string,
  params: AskParams = {},
): Promise<AskResponse> {
  return request<AskResponse>(`/projects/${projectId}/ask`, {
    method: "POST",
    body: JSON.stringify({
      question,
      date_from: params.dateFrom ?? null,
      date_to: params.dateTo ?? null,
    }),
  });
}

export function getSampleQuestions(projectId: string): Promise<string[]> {
  return request<string[]>(`/projects/${projectId}/sample-questions`);
}

export interface DashboardOut {
  id: string;
  project_id: string | null;
  created_at: string;
  layout: unknown[];
  response: AskResponse;
}

export function getDashboard(dashboardId: string): Promise<DashboardOut> {
  return request<DashboardOut>(`/dashboards/${dashboardId}`);
}

export interface EvalRun {
  id: string;
  suite_version: string;
  provider: string;
  git_sha: string | null;
  exec_accuracy: number | null;
  valid_sql_rate: number | null;
  intent_accuracy: number | null;
  avg_latency_ms: number | null;
  total_cost_usd: number | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface EvalCaseResult {
  case_id: string;
  passed: boolean;
  generated_sql: string | null;
  error: string | null;
  latency_ms: number | null;
  cost_usd: number | null;
}

export interface EvalRunDetail extends EvalRun {
  cases: EvalCaseResult[];
}

export function runEval(): Promise<EvalRun> {
  return request<EvalRun>("/eval/run", { method: "POST" });
}

export function listEvalRuns(): Promise<EvalRun[]> {
  return request<EvalRun[]>("/eval/runs");
}

export function getEvalRun(runId: string): Promise<EvalRunDetail> {
  return request<EvalRunDetail>(`/eval/runs/${runId}`);
}

export function patchDashboardLayout(
  dashboardId: string,
  layout: unknown[],
): Promise<DashboardOut> {
  return request<DashboardOut>(`/dashboards/${dashboardId}`, {
    method: "PATCH",
    body: JSON.stringify({ layout }),
  });
}
