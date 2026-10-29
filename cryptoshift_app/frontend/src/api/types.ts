export type Basis = "declared" | "inferred" | "unknown";
export interface Field<T> {
  value: T | null;
  basis: Basis;
  source: string | null;
}

export interface Health {
  ok: boolean;
  startedAt: string;
  python: string | null;
  proposer: string;
  sarvamAvailable?: boolean;
  node: string;
}

export interface Repository {
  id: string;
  name: string;
  description: string;
  language: string;
  source: string;
  services: number;
  lastScan: { id: string; at: string; filesScanned: number; findings: number } | null;
}

export interface RiskFactor {
  points: number;
  label: string;
  basis: string;
}

export type CheckStatus = "queued" | "running" | "passed" | "failed" | "blocked" | "unavailable" | "not_applicable" | "not_run";
export type Verdict = "verified_candidate" | "failed" | "incomplete" | "error" | null;

export interface Finding {
  id: string;
  repo: string;
  rule: string;
  file: string;
  line: number;
  column: number;
  snippet: string;
  excerpt: { line: number; text: string }[];
  api: string;
  algorithm: string;
  family: "RSA" | "ECC" | "SHA1" | "AES";
  keyBits: number | null;
  identifier: string | null;
  usages: { line: number; fn: string | null }[];
  role: Field<string>;
  context: Field<string>;
  service: { id: string; name: string; kind: string; basis: Basis } | null;
  exposure: Field<string>;
  dataLifetime: Field<number>;
  threat: { level: "shor" | "grover" | "classical"; label: string };
  risk: { score: number; band: "critical" | "high" | "medium" | "low"; factors: RiskFactor[] };
  recommendation: { action: string; target: string; standard: string | null; text: string; blockedBy: string | null };
  missingEvidence: string[];
  dependencies: { upstream: string[]; downstream: string[] };
  patch: { id: string; status: PatchStatus; after: string } | null;
  proposalBlocked: string | null;
  verification: { status: "no_patch" | "not_run" | "running" | "verified_candidate" | "failed" | "incomplete" | "error"; label: string };
}

export interface FindingsResponse {
  scan: { id: string; at: string; filesScanned: number; rules: string[] };
  findings: Finding[];
}

export interface GraphNode {
  id: string;
  name: string;
  kind: string;
  path: string;
  exposure: string | null;
  owner: string | null;
  findings: number;
  maxRisk: number;
  findingIds: string[];
  dependencies: string[];
  dependents: string[];
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  basis: "known" | "inferred";
  confirmedByImport?: boolean;
  evidence: { source?: string; file?: string; line?: number; text?: string }[];
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  note: string;
}

export interface PlanStep {
  node: string;
  wave: number | null;
  status: "schedulable" | "blocked-cycle" | "blocked-upstream";
  prerequisites: string[];
  blockedBy: string[];
}

export interface Plan {
  includeInferred: boolean;
  valid: boolean;
  waves: string[][];
  steps: PlanStep[];
  cycles: { members: string[]; edges: GraphEdge[] }[];
  edgeCount: { known: number; inferred: number };
  compatibility: { node: string | null; patchId: string; file: string; line: number; check: string; detail: string }[];
}

export type PatchStatus = "proposed" | "approved" | "rejected" | "released" | "rolled_back";

export interface Check {
  id: "diff" | "build" | "tests" | "vectors" | "protocol";
  name: string;
  required: boolean;
  status: CheckStatus;
  detail: string;
  output?: string;
  startedAt: string | null;
  finishedAt: string | null;
  baseline?: { ran: number; failing: string[] };
  candidate?: { ran: number; failing: string[]; reasons: string[] };
  regressions?: string[];
  results?: { algorithm: string; status: string; detail: string }[];
  note?: string;
}

export interface RunSummary {
  id: string;
  status: "running" | "complete";
  verdict: Verdict;
  startedAt: string;
  finishedAt: string | null;
  patchHash: string;
  checks: Check[];
}

export interface TracePeer {
  peer: string;
  regression: boolean;
  changed: boolean;
  baseline: { peer: string; ok: boolean; group?: string; events: { step: string; detail: string }[] };
  candidate: { peer: string; ok: boolean; group?: string; events: { step: string; detail: string }[] };
}

export interface Run extends RunSummary {
  patchId: string;
  repo: string;
  python: string | null;
  traces: { model: string; baselinePolicy: Record<string, unknown>; candidatePolicy: Record<string, unknown>; peers: TracePeer[] } | null;
}

export interface Patch {
  id: string;
  findingId: string;
  repo: string;
  service: Finding["service"];
  file: string;
  line: number;
  before: string;
  after: string;
  diff: string;
  algorithms: string[];
  fromAlgorithm: string;
  touchesProtocol: boolean;
  rationale: string;
  proposer: string;
  baseHash: string;
  hash: string;
  status: PatchStatus;
  createdAt: string;
  decisions: { decision: string; reviewer: string; note: string; at: string; runId: string | null }[];
  release: { at: string; by: string; checkpointId: string } | null;
  latestRun: RunSummary | null;
}

export interface PatchDetail extends Patch {
  finding: Finding | null;
  runs: RunSummary[];
}

export interface Checkpoint {
  id: string;
  patchId: string;
  repo: string;
  file: string;
  createdAt: string;
  originalHash: string;
  releasedHash: string;
  status: "active" | "restored";
  restoredAt: string | null;
}

export interface TraceRecord {
  runId: string;
  patchId: string;
  file: string;
  line: number;
  at: string;
  verdict: Verdict;
  traces: NonNullable<Run["traces"]>;
}

export interface AuditEntry {
  id: string;
  at: string;
  actor: string;
  action: string;
  detail: string;
}
