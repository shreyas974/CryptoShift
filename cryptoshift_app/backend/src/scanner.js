// Static scanner: finds cryptographic API usage in a repository working copy, line by line.
// Every finding carries the exact file, line and source text it was derived from.
// Fields the scanner cannot establish are returned as { value: null, basis: "unknown" }.
import { walk, readFile, manifestOf, serviceOf, repoDir } from "./repos.js";
import { shortId, db, save, audit } from "./store.js";
import { buildGraph } from "./graph.js";

const SKIP = [/^tests\//, /^tools\//, /^shared\/bankcrypto\/primitives\.py$/];

const THREATS = {
  RSA: { level: "shor", label: "Broken by Shor's algorithm on a cryptographically relevant quantum computer" },
  ECC: { level: "shor", label: "Broken by Shor's algorithm on a cryptographically relevant quantum computer" },
  SHA1: { level: "classical", label: "Collision resistance already broken classically; not a primary quantum concern" },
  AES: { level: "grover", label: "Grover's algorithm halves effective strength; AES-256 retains a ~128-bit margin" },
};

// Each rule: regex over one source line, plus how to describe a match.
const RULES = [
  {
    id: "keypair-rsa",
    re: /generate_keypair\("RSA",\s*(\d+)\)/,
    api: "primitives.generate_keypair",
    describe: (m) => ({ algorithm: `RSA-${m[1]}`, family: "RSA", keyBits: Number(m[1]) }),
  },
  {
    id: "keypair-ec",
    re: /generate_keypair\("(ECDSA-P256|ECDH-P256)"\)/,
    api: "primitives.generate_keypair",
    describe: (m) => ({ algorithm: m[1], family: "ECC", keyBits: 256 }),
  },
  {
    id: "tls-groups",
    re: /KEY_EXCHANGE_GROUPS\s*=\s*\[([^\]]*)\]/,
    api: "tls_config.KEY_EXCHANGE_GROUPS",
    describe: (m) => {
      const groups = [...m[1].matchAll(/"([^"]+)"/g)].map((g) => g[1]);
      const classical = groups.filter((g) => !/MLKEM/i.test(g));
      if (!classical.length || groups.some((g) => /MLKEM/i.test(g))) return null; // already hybrid
      return { algorithm: `ECDHE (${groups.join(", ")})`, family: "ECC", keyBits: 256, role: { value: "Key agreement (TLS handshake)", basis: "declared", source: "TLS group list" }, context: "TLS 1.2 / 1.3 handshakes for every service using shared tls_config" };
    },
  },
  {
    id: "tls-cert",
    re: /CERT_SIGNATURE\s*=\s*"(RSA-(\d+))"/,
    api: "tls_config.CERT_SIGNATURE",
    describe: (m) => ({ algorithm: m[1], family: "RSA", keyBits: Number(m[2]), role: { value: "Certificate signature (server authentication)", basis: "declared", source: "CERT_SIGNATURE setting" }, context: "TLS server certificates issued by the internal CA" }),
  },
  {
    id: "hash-sha1",
    re: /checksum\("SHA1"/,
    api: "primitives.checksum",
    describe: () => ({ algorithm: "SHA-1", family: "SHA1", keyBits: null, role: { value: "Integrity checksum", basis: "inferred", source: "call to checksum()" } }),
  },
  {
    id: "cipher-aes",
    re: /seal\("AES-256-GCM"/,
    api: "primitives.seal",
    describe: () => ({ algorithm: "AES-256-GCM", family: "AES", keyBits: 256, role: { value: "Data encryption at rest", basis: "inferred", source: "call to seal()" } }),
  },
];

const ROLE_BY_NAME = [
  [/CA_KEY/, "Certificate signing (issuing CA)"],
  [/transport/i, "Key transport (wrapping exported keys)"],
  [/AGREEMENT|kex/i, "Key agreement (session keys)"],
  [/SIGN|INSTRUCTION/i, "Digital signature"],
];

function assignedName(line) {
  const match = line.match(/^\s*(?:self\.)?([A-Za-z_][A-Za-z0-9_]*)\s*=/);
  return match ? match[1] : null;
}

function enclosingFunction(lines, index) {
  for (let i = index; i >= 0; i--) {
    const match = lines[i].match(/^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)/);
    if (match) return match[1];
  }
  return null;
}

function usagesOf(lines, name, definedAt) {
  if (!name) return [];
  const re = new RegExp(`\\b(?:self\\.)?${name}\\b`);
  const out = [];
  lines.forEach((line, index) => {
    if (index === definedAt || !re.test(line)) return;
    out.push({ line: index + 1, fn: enclosingFunction(lines, index) });
  });
  return out;
}

function recommendationFor(finding) {
  const role = finding.role.value ?? "";
  const vendor = finding.service?.kind === "third-party";
  if (finding.family === "AES") return { action: "retain", target: "AES-256-GCM", standard: null, text: "Retain. AES-256 is considered adequate against known quantum attacks; review key management only.", blockedBy: null };
  if (finding.family === "SHA1") return { action: "replace", target: "SHA-256", standard: "FIPS 180-4", text: "Replace SHA-1 with SHA-256. This is a classical weakness fix, not a post-quantum migration.", blockedBy: null };
  let target = "ML-DSA-65";
  let standard = "FIPS 204";
  if (/agreement|transport/i.test(role)) {
    target = /TLS/.test(role) ? "X25519MLKEM768 (hybrid)" : "ML-KEM-768";
    standard = "FIPS 203";
  }
  if (/Certificate/i.test(role)) target = "ML-DSA-65 or ML-DSA-87 (hybrid certificate chain)";
  return {
    action: "migrate",
    target,
    standard,
    text: vendor ? `Vendored third-party code: request a ${target}-capable release from the vendor rather than patching in place.` : `Migrate to ${target} (${standard}).`,
    blockedBy: vendor ? "Vendor release required" : null,
  };
}

export function scoreRisk(finding, graph) {
  const factors = [];
  const add = (points, label, basis) => factors.push({ points, label, basis });
  const threat = THREATS[finding.family];
  if (threat.level === "shor") add(40, "Public-key algorithm vulnerable to Shor's algorithm", "algorithm");
  else if (threat.level === "classical") add(15, "Classically weak hash (SHA-1)", "algorithm");
  else add(0, "Symmetric 256-bit cipher: adequate post-quantum margin", "algorithm");
  if (finding.family === "RSA" && finding.keyBits && finding.keyBits < 2048) add(10, `RSA-${finding.keyBits} is below current classical minimums`, "algorithm");
  const role = finding.role.value ?? "";
  if (threat.level === "shor" && /agreement|transport/i.test(role)) add(10, "Confidentiality role: recorded traffic is exposed to harvest-now-decrypt-later", "role");
  else if (threat.level === "shor" && /signature|sign/i.test(role)) add(5, "Authenticity role: forgery possible once a CRQC exists", "role");
  else if (!finding.role.value) add(5, "Role unknown (scored conservatively)", "missing");
  const exposure = finding.exposure.value;
  if (exposure === "internet") add(15, "Internet-facing service", "declared");
  else if (exposure === "partner") add(12, "Partner-facing (external network)", "declared");
  else if (exposure === "internal") add(5, "Internal-only service", "declared");
  else add(8, "Exposure not declared (scored conservatively)", "missing");
  if (threat.level !== "grover") {
    const life = finding.dataLifetime.value;
    if (life == null) add(8, "Data lifetime not declared (scored conservatively)", "missing");
    else if (life >= 10) add(15, `Protected data must stay confidential/authentic for ${life} years`, "declared");
    else if (life >= 3) add(8, `Data lifetime ${life} years`, "declared");
    else add(3, `Short data lifetime (${life} year${life === 1 ? "" : "s"})`, "declared");
  }
  const dependents = finding.service ? graph.dependentsOf(finding.service.id).length : 0;
  if (threat.level !== "grover" && dependents) add(Math.min(10, dependents * 2), `${dependents} service${dependents === 1 ? "" : "s"} depend on this component`, "graph");
  const score = Math.min(100, factors.reduce((sum, f) => sum + f.points, 0));
  const band = score >= 70 ? "critical" : score >= 50 ? "high" : score >= 30 ? "medium" : "low";
  return { score, band, factors };
}

function missingEvidence(finding) {
  const out = [];
  if (finding.role.basis !== "declared") out.push("Confirm the cryptographic role with the owning team (currently " + (finding.role.basis === "inferred" ? "inferred from identifiers" : "unknown") + ").");
  if (finding.exposure.basis === "unknown") out.push("Declare the service's network exposure in cryptoshift.services.json.");
  if (finding.dataLifetime.basis === "unknown" && finding.family !== "AES") out.push("Declare how long the protected data must stay confidential or authentic.");
  if (!finding.context.value) out.push("Link this usage to a protocol or API so its runtime context is known.");
  out.push("Runtime telemetry (handshake or key-usage logs) would confirm the algorithm is actually negotiated in production.");
  return out;
}

export function scanRepository(repoId) {
  const manifest = manifestOf(repoId);
  const all = walk(repoDir(repoId)).filter((rel) => rel.endsWith(".py") && !SKIP.some((re) => re.test(rel)));
  const raw = [];
  const imports = [];
  for (const rel of all) {
    const text = readFile(repoId, rel);
    const lines = text.split(/\r?\n/);
    lines.forEach((line, index) => {
      const imp = line.match(/^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+([\w, ]+)/);
      if (imp) imports.push({ file: rel, line: index + 1, module: imp[1], names: imp[2].split(",").map((s) => s.trim()) });
      for (const rule of RULES) {
        const match = line.match(rule.re);
        if (!match) continue;
        const described = rule.describe(match);
        if (!described) continue;
        const name = assignedName(line);
        const usages = usagesOf(lines, name, index);
        let role = described.role;
        if (!role) {
          const hit = ROLE_BY_NAME.find(([re]) => name && re.test(name));
          role = hit ? { value: hit[1], basis: "inferred", source: `identifier ${name}` } : { value: null, basis: "unknown", source: null };
        }
        const service = serviceOf(manifest, rel);
        const fnNames = [...new Set(usages.map((u) => u.fn).filter(Boolean))];
        raw.push({
          id: shortId(`${repoId}:${rel}:${index + 1}:${rule.id}`),
          repo: repoId,
          rule: rule.id,
          file: rel,
          line: index + 1,
          column: (match.index ?? 0) + 1,
          snippet: line.trim(),
          excerpt: lines.slice(Math.max(0, index - 3), index + 4).map((text, i) => ({ line: Math.max(0, index - 3) + i + 1, text })),
          api: rule.api,
          algorithm: described.algorithm,
          family: described.family,
          keyBits: described.keyBits,
          identifier: name,
          usages,
          role,
          context: described.context
            ? { value: described.context, basis: "declared", source: rule.api }
            : fnNames.length
              ? { value: `Used by ${fnNames.map((f) => f + "()").join(", ")} in ${rel.split("/").pop()}`, basis: "inferred", source: "references in the same file" }
              : { value: null, basis: "unknown", source: null },
          service: service ? { id: service.id, name: service.name, kind: service.kind, basis: "declared" } : null,
          exposure: service?.exposure ? { value: service.exposure, basis: "declared", source: "cryptoshift.services.json" } : { value: null, basis: "unknown", source: null },
          dataLifetime: service?.dataLifetimeYears != null ? { value: service.dataLifetimeYears, basis: "declared", source: "cryptoshift.services.json" } : { value: null, basis: "unknown", source: null },
          threat: THREATS[described.family],
        });
      }
    });
  }
  const graph = buildGraph(manifest, imports);
  for (const finding of raw) {
    finding.risk = scoreRisk(finding, graph);
    finding.recommendation = recommendationFor(finding);
    finding.missingEvidence = missingEvidence(finding);
    finding.dependencies = finding.service
      ? { upstream: graph.dependenciesOf(finding.service.id), downstream: graph.dependentsOf(finding.service.id) }
      : { upstream: [], downstream: [] };
  }
  raw.sort((a, b) => b.risk.score - a.risk.score || a.file.localeCompare(b.file) || a.line - b.line);
  const scan = {
    id: shortId(`${repoId}:${Date.now()}`),
    repo: repoId,
    at: new Date().toISOString(),
    filesScanned: all.length,
    rules: RULES.map((r) => r.id),
    findings: raw,
    imports,
  };
  db().scans[repoId] = scan;
  save();
  audit("scan.completed", `${repoId}: ${raw.length} findings in ${all.length} files`);
  return scan;
}

