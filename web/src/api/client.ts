import { z } from "zod";
import type { paths } from "./schema";

/** Every API path the client may call must exist in the generated OpenAPI types (compile-time check). */
export type ApiPath = keyof paths;

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

let csrfToken = "";
export const setCsrf = (t: string) => {
  csrfToken = t;
};

function readCookie(name: string): string {
  return (
    document.cookie
      .split("; ")
      .find((c) => c.startsWith(`${name}=`))
      ?.split("=")[1] ?? ""
  );
}

async function call<T>(path: ApiPath | string, schema: z.ZodType<T> | null, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (method !== "GET") {
    headers.set("X-CSRF-Token", csrfToken || readCookie("cs_csrf"));
    if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...init, method, headers, credentials: "same-origin" });
  const body: unknown = res.headers.get("content-type")?.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    const err = (body as { error?: { code?: string; message?: string } })?.error;
    throw new ApiError(err?.code ?? "http_error", err?.message ?? `HTTP ${res.status}`, res.status);
  }
  if (!schema) return body as T;
  const parsed = schema.safeParse(body);
  if (!parsed.success)
    throw new ApiError("contract_mismatch", `response for ${path} does not match the expected shape`, 502);
  return parsed.data;
}

// ---------------------------------------------------------------- runtime shapes (Zod) for key responses
export const Source = z.object({
  key: z.string().optional(),
  file: z.string(),
  producer: z.string(),
  label: z.string(),
  modified: z.string().nullable().optional(),
  sha256: z.string().nullable().optional(),
  command: z.string(),
  mode: z.string().optional(),
  status: z.string().optional(),
});
export type Source = z.infer<typeof Source>;

export const Me = z.object({ username: z.string(), role: z.enum(["viewer", "analyst", "approver"]), csrf: z.string() });
export type Me = z.infer<typeof Me>;

export const Stage = z.object({ name: z.string(), status: z.string(), note: z.string(), source: z.string() });
export const Overview = z.object({
  data_mode: z.string(),
  sources: z.record(z.string(), Source),
  stages: z.array(Stage).default([]),
  counts: z
    .object({
      findings: z.number().optional(),
      services: z.number().optional(),
      steps_ready: z.number().optional(),
      steps_total: z.number().optional(),
      held_out_recall: z.number().nullable().optional(),
      assistant_template_passed: z.number().nullable().optional(),
      assistant_cloud_v3_passed: z.number().nullable().optional(),
    })
    .default({}),
  plan_hash: z.string().nullable().default(null),
});
export type Overview = z.infer<typeof Overview>;

export const FindingRow = z.object({
  id: z.string(),
  file: z.string(),
  line: z.number(),
  service: z.string(),
  service_basis: z.string(),
  service_confidence: z.string(),
  family: z.string(),
  purpose: z.string(),
  confidence: z.string(),
  ambiguity: z.string(),
  detector: z.string(),
  candidate: z.string(),
  snippet: z.string(),
  rationale: z.string(),
  hold: z.boolean(),
  detected_value: z.string().default(""),
  where: z.string().default(""),
  threat: z.string().default(""),
  severity: z.string().default(""),
  review: z.string().default(""),
  in_test_file: z.boolean().default(false),
  role_certainty: z.string().default("UNKNOWN / MANUAL REVIEW"),
});
export type FindingRow = z.infer<typeof FindingRow>;
export const Findings = z.object({ status: z.string(), source: Source, rows: z.array(FindingRow), notice: z.string() });

export const ApprovalStep = z.object({
  step_id: z.string(),
  service: z.string(),
  state: z.string(),
  blocking: z.array(z.string()),
  all_required_gates_pass: z.boolean(),
  approved: z.boolean(),
});
export type ApprovalStep = z.infer<typeof ApprovalStep>;
export const Approvals = z.object({
  status: z.string(),
  source: Source,
  plan_hash: z.string().nullable(),
  steps: z.array(ApprovalStep),
  approved_steps: z.array(z.string()).default([]),
  invalidated: z.array(z.record(z.string(), z.unknown())).default([]),
  records: z.number().default(0),
});
export type Approvals = z.infer<typeof Approvals>;

export const AskResult = z.object({
  answer: z.string(),
  citations: z.array(z.string()),
  mode: z.string(),
  mode_reason: z.string(),
  refused: z.boolean(),
  usage: z.record(z.string(), z.unknown()),
  via: z.string(),
});
export type AskResult = z.infer<typeof AskResult>;

// ---------------------------------------------------------------- endpoints
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Loose = any;
export const api = {
  me: () => call("/api/v1/auth/me", Me),
  login: (username: string, password: string) =>
    call("/api/v1/auth/login", Me, { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => call("/api/v1/auth/logout", null, { method: "POST" }),
  overview: () => call("/api/v1/overview", Overview),
  findings: () => call("/api/v1/findings", Findings),
  graph: () => call<Loose>("/api/v1/graph", null),
  plan: () => call<Loose>("/api/v1/plan", null),
  verification: () => call<Loose>("/api/v1/verification", null),
  approvals: () => call("/api/v1/approvals", Approvals),
  approve: (step_id: string, approver_name: string, plan_hash_prefix: string) =>
    call<Loose>("/api/v1/approvals", null, {
      method: "POST",
      body: JSON.stringify({ step_id, approver_name, plan_hash_prefix, acknowledged: true }),
    }),
  rollback: () => call<Loose>("/api/v1/rollback", null),
  evaluation: () => call<Loose>("/api/v1/evaluation", null),
  ml: () => call<Loose>("/api/v1/ml", null),
  sources: () => call<Loose>("/api/v1/sources", null),
  claims: () => call<Loose>("/api/v1/claims", null),
  assistantStatus: () => call<Loose>("/api/v1/assistant/status", null),
  ask: (question: string) =>
    call("/api/v1/assistant/ask", AskResult, { method: "POST", body: JSON.stringify({ question }) }),
  commands: () => call<{ id: string; label: string; timeout_s: number }[]>("/api/v1/jobs/commands", null),
  startJob: (command_id: string) =>
    call<{ job_id: number }>("/api/v1/jobs", null, { method: "POST", body: JSON.stringify({ command_id }) }),
  job: (id: number) => call<Loose>(`/api/v1/jobs/${id}`, null),
  audit: () => call<Loose>("/api/v1/audit?limit_=100", null),
  verifyAudit: () =>
    call<{ valid: boolean; entries: number; first_bad_id: number | null }>("/api/v1/audit/verify", null),
  settings: () => call<Loose>("/api/v1/settings", null),
  putSettings: (s: Record<string, unknown>) =>
    call<Loose>("/api/v1/settings", null, { method: "PUT", body: JSON.stringify(s) }),
  report: (key: string) => call<Loose>(`/api/v1/reports/${encodeURIComponent(key)}`, null),
  fullReport: () => call<Loose>("/api/v1/report", null),
  // dataset runs: upload -> pipeline -> outputs
  pipelines: () => call<Pipeline[]>("/api/v1/pipelines", null),
  runs: () => call<Run[]>("/api/v1/runs", null),
  run: (id: number) => call<Run>(`/api/v1/runs/${id}`, null),
  runResult: (id: number) => call<Loose>(`/api/v1/runs/${id}/result`, null),
  createRun: (form: FormData) =>
    call<{ run_id: number; job_id: number; files: number; skipped: string[]; sha256: string }>("/api/v1/runs", null, {
      method: "POST",
      body: form,
    }),
  demoRepos: () =>
    call<{ id: string; label: string; path: string; note: string; files: number; available: boolean }[]>(
      "/api/v1/demo-repos",
      null,
    ),
  createDemoRun: (repo_id: string, pipeline: string) =>
    call<{ run_id: number; job_id: number; files: number; skipped: string[]; sha256: string }>(
      "/api/v1/runs/demo",
      null,
      {
        method: "POST",
        body: JSON.stringify({ repo_id, pipeline, authorized: true }),
      },
    ),
  deleteRun: (id: number) => call<Loose>(`/api/v1/runs/${id}`, null, { method: "DELETE" }),
  // users (approver)
  users: () => call<UserRow[]>("/api/v1/users", null),
  addUser: (username: string, role: string, password: string) =>
    call<Loose>("/api/v1/users", null, { method: "POST", body: JSON.stringify({ username, role, password }) }),
  updateUser: (id: number, patch: { role?: string; disabled?: boolean; password?: string }) =>
    call<Loose>(`/api/v1/users/${id}`, null, { method: "PUT", body: JSON.stringify(patch) }),
  activity: (n = 30) => call<Activity>(`/api/v1/activity?limit_=${n}`, null),
};

export type Pipeline = { id: string; label: string; stages: string[]; timeout: number; note: string };
export type RunStage = { status: string; seconds?: number; error?: string; label?: string } & Record<string, unknown>;
export type Run = {
  id: number;
  job_id: number | null;
  pipeline: string;
  pipeline_label: string;
  dataset_name: string;
  dataset_sha256: string;
  file_count: number;
  skipped_count: number;
  total_bytes: number;
  created_by: string;
  created_at: string;
  status: string;
  summary: { status: string; stages: Record<string, RunStage>; started_utc: string; finished_utc?: string } | null;
  outputs?: { path: string; bytes: number }[];
  log_tail?: string | null;
  stages?: string[];
};
export type UserRow = { id: number; username: string; role: string; disabled: boolean; created_at: string | null };
export type ActivityItem = {
  id: number;
  ts: string;
  actor: string;
  action: string;
  result: string;
  target: string;
  title: string;
};
export type Activity = { latest_id: number; items: ActivityItem[] };
