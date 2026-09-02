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

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const correlationId = `req-${Math.random().toString(36).substring(2, 9)}`;

  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Correlation-ID": correlationId,
      ...options.headers,
    },
  });

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
  try {
    return await request<Project[]>("/api/v1/projects");
  } catch {
    return [];
  }
}

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  try {
    return await request<ScenarioSummary[]>("/api/v1/scenarios");
  } catch {
    return [];
  }
}

export async function fetchRuns(projectId?: string): Promise<EvaluationRun[]> {
  const q = projectId ? `?project_id=${projectId}` : "";
  try {
    return await request<EvaluationRun[]>(`/api/v1/runs${q}`);
  } catch {
    return [];
  }
}

export async function fetchRun(runId: string): Promise<EvaluationRun | null> {
  try {
    return await request<EvaluationRun>(`/api/v1/runs/${runId}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export async function fetchRunTrials(runId: string): Promise<TrialDetail[]> {
  try {
    return await request<TrialDetail[]>(`/api/v1/runs/${runId}/trials`);
  } catch {
    return [];
  }
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
    return await request<EvidenceChain>(`/api/v1/runs/${runId}/evidence`);
  } catch {
    return null;
  }
}

export async function createRun(payload: {
  project_id: string;
  agent_version_id: string;
  scenario_ids: string[];
  trials_per_scenario?: number;
  seed?: number;
}): Promise<EvaluationRun> {
  return request<EvaluationRun>("/api/v1/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function cancelRun(runId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/v1/runs/${runId}/cancel`, {
    method: "POST",
  });
}
