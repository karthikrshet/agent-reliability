/**
 * Typed API Client for Agent Reliability Lab Dashboard.
 * Connects to the FastAPI backend with runtime response validation and typed error handling.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string;
  created_at: string;
}

export interface ScenarioSummary {
  id: string;
  title: string;
  category: string;
  severity: "low" | "medium" | "high" | "critical";
  max_turns: number;
  max_tool_calls: number;
  fault_count: number;
  tags: string[];
}

export interface EvaluationRun {
  id: string;
  project_id?: string;
  agent_version_id?: string;
  state: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";
  total_trials: number;
  completed_trials: number;
  passed_trials: number;
  failed_trials: number;
  pass_rate: number;
  pass_rate_ci_lower?: number;
  pass_rate_ci_upper?: number;
  pass_at_1?: number;
  pass_at_3?: number;
  readiness_verdict?: string;
  readiness_score?: number;
  verdict_reason?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface ObservableTurn {
  turn_index: number;
  user_input?: string;
  agent_output_type: string;
  raw_text?: string;
  tool_calls?: Array<{
    id?: string;
    tool_call_id?: string;
    tool_name: string;
    arguments: Record<string, unknown>;
  }>;
  tool_results?: Array<{
    tool_call_id?: string;
    result: Record<string, unknown>;
    status?: string;
  }>;
  fault_injected?: {
    fault_type: string;
    description: string;
  };
}

export interface TrialDetail {
  id: string;
  run_id: string;
  scenario_id: string;
  trial_index: number;
  state: string;
  verdict?: "PASS" | "FAIL" | "CRITICAL_FAIL" | "NON_PRODUCTION_REFERENCE";
  score?: number;
  duration_ms?: number;
  total_cost_usd?: number;
  findings?: Array<{
    dimension: string;
    severity: string;
    summary: string;
    detail?: string;
  }>;
  observable_turns?: ObservableTurn[];
}

export interface EvidenceBlock {
  sequence_number: number;
  timestamp: string;
  event_type: string;
  payload_hash: string;
  chain_hash: string;
  trial_id?: string;
  provenance?: Record<string, unknown>;
}

export interface EvidenceChain {
  run_id: string;
  root_hash: string;
  integrity_verified: boolean;
  total_blocks: number;
  blocks: EvidenceBlock[];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function validateProject(data: unknown): Project {
  if (!data || typeof data !== "object") {
    throw new Error("Invalid Project payload: expected object");
  }
  const p = data as Record<string, unknown>;
  if (typeof p.id !== "string" || typeof p.name !== "string") {
    throw new Error("Invalid Project payload: missing id or name");
  }
  return {
    id: p.id,
    name: p.name,
    slug: typeof p.slug === "string" ? p.slug : p.id,
    description: typeof p.description === "string" ? p.description : undefined,
    created_at: typeof p.created_at === "string" ? p.created_at : new Date().toISOString(),
  };
}

function validateScenarioSummary(data: unknown): ScenarioSummary {
  if (!data || typeof data !== "object") {
    throw new Error("Invalid Scenario payload: expected object");
  }
  const s = data as Record<string, unknown>;
  if (typeof s.id !== "string") {
    throw new Error("Invalid Scenario payload: missing id");
  }
  return {
    id: s.id,
    title: typeof s.title === "string" ? s.title : s.id,
    category: typeof s.category === "string" ? s.category : "general",
    severity: (["low", "medium", "high", "critical"].includes(s.severity as string)
      ? s.severity
      : "medium") as ScenarioSummary["severity"],
    max_turns: typeof s.max_turns === "number" ? s.max_turns : 10,
    max_tool_calls: typeof s.max_tool_calls === "number" ? s.max_tool_calls : 20,
    fault_count: typeof s.fault_count === "number" ? s.fault_count : 0,
    tags: Array.isArray(s.tags) ? s.tags.map(String) : [],
  };
}

function validateEvaluationRun(data: unknown): EvaluationRun {
  if (!data || typeof data !== "object") {
    throw new Error("Invalid EvaluationRun payload: expected object");
  }
  const r = data as Record<string, unknown>;
  if (typeof r.id !== "string") {
    throw new Error("Invalid EvaluationRun payload: missing id");
  }
  return {
    id: r.id,
    project_id: typeof r.project_id === "string" ? r.project_id : undefined,
    agent_version_id: typeof r.agent_version_id === "string" ? r.agent_version_id : undefined,
    state: (["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"].includes(r.state as string)
      ? r.state
      : "PENDING") as EvaluationRun["state"],
    total_trials: typeof r.total_trials === "number" ? r.total_trials : 0,
    completed_trials: typeof r.completed_trials === "number" ? r.completed_trials : 0,
    passed_trials: typeof r.passed_trials === "number" ? r.passed_trials : 0,
    failed_trials: typeof r.failed_trials === "number" ? r.failed_trials : 0,
    pass_rate: typeof r.pass_rate === "number" ? r.pass_rate : 0.0,
    pass_rate_ci_lower: typeof r.pass_rate_ci_lower === "number" ? r.pass_rate_ci_lower : undefined,
    pass_rate_ci_upper: typeof r.pass_rate_ci_upper === "number" ? r.pass_rate_ci_upper : undefined,
    pass_at_1: typeof r.pass_at_1 === "number" ? r.pass_at_1 : undefined,
    pass_at_3: typeof r.pass_at_3 === "number" ? r.pass_at_3 : undefined,
    readiness_verdict: typeof r.readiness_verdict === "string" ? r.readiness_verdict : undefined,
    readiness_score: typeof r.readiness_score === "number" ? r.readiness_score : undefined,
    verdict_reason: typeof r.verdict_reason === "string" ? r.verdict_reason : undefined,
    created_at: typeof r.created_at === "string" ? r.created_at : new Date().toISOString(),
    started_at: typeof r.started_at === "string" ? r.started_at : undefined,
    completed_at: typeof r.completed_at === "string" ? r.completed_at : undefined,
  };
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const correlationId = `req-${Math.random().toString(36).substring(2, 9)}`;

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlationId,
        ...options.headers,
      },
    });
  } catch (err) {
    throw new ApiError(
      0,
      `Network connection failure connecting to ARL backend at ${API_BASE_URL}: ${err instanceof Error ? err.message : String(err)}`
    );
  }

  if (!res.ok) {
    let errorDetail = "";
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = await res.text();
    }
    throw new ApiError(
      res.status,
      `API error ${res.status} for ${path}: ${errorDetail || res.statusText}`,
      errorDetail
    );
  }

  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return (await res.json()) as T;
  }
  return (await res.text()) as unknown as T;
}

export async function fetchHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/healthz");
}

export async function fetchProjects(): Promise<Project[]> {
  const data = await request<unknown[]>("/api/v1/projects");
  if (!Array.isArray(data)) {
    throw new Error("Invalid response: expected array of projects");
  }
  return data.map(validateProject);
}

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const data = await request<unknown[]>("/api/v1/scenarios");
  if (!Array.isArray(data)) {
    throw new Error("Invalid response: expected array of scenarios");
  }
  return data.map(validateScenarioSummary);
}

export async function fetchRuns(projectId?: string): Promise<EvaluationRun[]> {
  const q = projectId ? `?project_id=${projectId}` : "";
  const data = await request<unknown[]>(`/api/v1/runs${q}`);
  if (!Array.isArray(data)) {
    throw new Error("Invalid response: expected array of runs");
  }
  return data.map(validateEvaluationRun);
}

export async function fetchRun(runId: string): Promise<EvaluationRun | null> {
  try {
    const data = await request<unknown>(`/api/v1/runs/${runId}`);
    return validateEvaluationRun(data);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export async function fetchRunTrials(runId: string): Promise<TrialDetail[]> {
  const data = await request<TrialDetail[]>(`/api/v1/runs/${runId}/trials`);
  if (!Array.isArray(data)) {
    throw new Error("Invalid response: expected array of trials");
  }
  return data;
}

export async function fetchRunReport(
  runId: string,
  format: "json" | "markdown" = "markdown"
): Promise<string> {
  const res = await request<string>(`/api/v1/runs/${runId}/report?format=${format}`);
  return typeof res === "string" ? res : JSON.stringify(res, null, 2);
}

export async function fetchRunEvidence(
  runId: string
): Promise<EvidenceChain | null> {
  try {
    const data = await request<EvidenceChain>(`/api/v1/runs/${runId}/evidence`);
    return data;
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export async function createRun(payload: {
  project_id: string;
  agent_version_id: string;
  scenario_ids: string[];
  trials_per_scenario?: number;
  seed?: number;
}): Promise<EvaluationRun> {
  const data = await request<unknown>("/api/v1/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return validateEvaluationRun(data);
}

export async function cancelRun(runId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/v1/runs/${runId}/cancel`, {
    method: "POST",
  });
}
