// One data model drives both the cabinet drawing and the readout: the scanner's Finding.
import type { Finding } from "../../api/types";
import type { PartStatus } from "../../anatomy/AnatomyFrame";

export type FieldId = "repository" | "evidence" | "algorithm" | "role" | "context" | "dependencies" | "exposure" | "risk" | "recommendation" | "verification";

export interface AssetField {
  id: FieldId;
  label: string;
  value: string;
  readout: string;
  basis: "known" | "inferred" | "unknown";
  status: PartStatus;
  statusLabel: string;
  cards: number;
  summary: string;
}

const basisOf = (b: string): AssetField["basis"] => (b === "declared" ? "known" : b === "inferred" ? "inferred" : "unknown");
const BASIS_TEXT = { known: "Declared or detected directly", inferred: "Inferred by the scanner", unknown: "Not established" } as const;

export function fieldsOf(f: Finding): AssetField[] {
  const make = (id: FieldId, label: string, value: string, readout: string, basis: AssetField["basis"], cards: number, summary: string, status?: PartStatus, statusLabel?: string): AssetField => ({
    id,
    label,
    value,
    readout,
    basis,
    cards: Math.max(0, Math.min(6, cards)),
    summary,
    status: status ?? basis,
    statusLabel: statusLabel ?? BASIS_TEXT[basis],
  });
  const exposureBasis: AssetField["basis"] = f.exposure.basis === "unknown" || (f.dataLifetime.basis === "unknown" && f.family !== "AES") ? (f.exposure.basis === "unknown" && f.dataLifetime.basis === "unknown" ? "unknown" : "inferred") : "known";
  const riskMissing = f.risk.factors.some((x) => x.basis === "missing");
  const v = f.verification.status;
  const vStatus: PartStatus = v === "verified_candidate" ? "passed" : v === "failed" || v === "error" ? "failed" : v === "running" || v === "incomplete" ? "pending" : v === "no_patch" ? "blocked" : "unrun";
  const lifetime = f.dataLifetime.value == null ? "lifetime unknown" : `${f.dataLifetime.value}-year data lifetime`;
  return [
    make("repository", "Repository", f.repo, f.repo, "known", 1, `Found by scanning the ${f.repo} working copy.`),
    make("evidence", "File and line evidence", `${f.file}:${f.line}`, `${f.file.split("/").pop()}:${f.line}`, "known", 1 + f.usages.length, `Line ${f.line} of ${f.file}${f.usages.length ? `, referenced on ${f.usages.length} other line${f.usages.length === 1 ? "" : "s"}` : ""}.`),
    make("algorithm", "Algorithm / API", `${f.algorithm} via ${f.api}`, f.algorithm, "known", 1, `${f.algorithm} through ${f.api}. ${f.threat.label}.`),
    make("role", "Cryptographic role", f.role.value ?? "Unknown", f.role.value ? f.role.value.split(" (")[0] : "role unknown", basisOf(f.role.basis), f.role.value ? 1 : 0, f.role.value ? `${f.role.value} (${f.role.basis}${f.role.source ? `, from ${f.role.source}` : ""}).` : "The scanner could not determine the role."),
    make("context", "Protocol / service context", f.context.value ?? "Unknown", f.service?.name ?? "context unknown", basisOf(f.context.basis), f.context.value ? 1 : 0, f.context.value ?? "No protocol or API context was established."),
    make("dependencies", "Dependency connections", `${f.dependencies.upstream.length} upstream · ${f.dependencies.downstream.length} downstream`, `${f.dependencies.downstream.length} dependents`, f.service ? "known" : "unknown", f.dependencies.upstream.length + f.dependencies.downstream.length, f.service ? `${f.service.name} depends on ${f.dependencies.upstream.length} component(s); ${f.dependencies.downstream.length} depend on it.` : "File is not mapped to a declared service."),
    make("exposure", "Exposure and data lifetime", `${f.exposure.value ?? "exposure unknown"} · ${lifetime}`, `${f.exposure.value ?? "?"} · ${f.dataLifetime.value ?? "?"}y`, exposureBasis, (f.exposure.value ? 1 : 0) + (f.dataLifetime.value != null ? 1 : 0), `Exposure ${f.exposure.value ?? "not declared"}; ${lifetime}.`),
    make("risk", "Risk assessment", `${f.risk.score}/100 (${f.risk.band})`, `risk ${f.risk.score}/100`, riskMissing ? "inferred" : "known", f.risk.factors.length, `Score ${f.risk.score} from ${f.risk.factors.length} factors${riskMissing ? ", some scored conservatively for missing evidence" : ""}.`),
    make("recommendation", "Migration recommendation", f.recommendation.target, f.recommendation.target.split(" (")[0], "inferred", 1, f.recommendation.text),
    make("verification", "Verification status", f.verification.label, f.verification.label.toLowerCase(), "known", f.patch ? 1 : 0, f.patch ? `Candidate patch ${f.patch.status}; ${f.verification.label.toLowerCase()}.` : f.verification.label, vStatus, f.verification.label),
  ];
}
