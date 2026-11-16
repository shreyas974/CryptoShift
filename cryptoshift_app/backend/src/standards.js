// Standards mapping for findings:
// - transition deadlines from NIST IR 8547 (quantum-vulnerable public-key algorithms are
//   deprecated after 2030 and disallowed after 2035) and NIST's SHA-1 retirement (end of 2030);
// - export as a CycloneDX 1.6 Cryptography Bill of Materials (CBOM).
import crypto from "node:crypto";

const DEADLINES = {
  RSA: { deprecatedAfter: 2030, disallowedAfter: 2035, source: "NIST IR 8547 (quantum-vulnerable public-key algorithms)" },
  ECC: { deprecatedAfter: 2030, disallowedAfter: 2035, source: "NIST IR 8547 (quantum-vulnerable public-key algorithms)" },
  SHA1: { deprecatedAfter: null, disallowedAfter: 2030, source: "NIST SHA-1 retirement (phase-out by 31 Dec 2030)" },
  AES: null,
};

export function deadlineFor(finding, now = new Date()) {
  const d = DEADLINES[finding.family];
  if (!d) return { status: "none", label: "No transition deadline (algorithm remains approved)", deprecatedAfter: null, disallowedAfter: null, yearsLeft: null, source: null };
  const year = now.getUTCFullYear();
  const yearsLeft = d.disallowedAfter - year;
  return {
    status: yearsLeft <= 0 ? "disallowed" : d.deprecatedAfter && year > d.deprecatedAfter ? "deprecated" : "scheduled",
    label: d.deprecatedAfter ? `Deprecated after ${d.deprecatedAfter}, disallowed after ${d.disallowedAfter}` : `Disallowed after ${d.disallowedAfter}`,
    deprecatedAfter: d.deprecatedAfter,
    disallowedAfter: d.disallowedAfter,
    yearsLeft,
    source: d.source,
  };
}

// Algorithm facts for the CBOM. OIDs: rsaEncryption, id-ecPublicKey, id-sha1, id-aes256-GCM.
function algorithmProps(f) {
  const role = f.role?.value ?? "";
  if (f.family === "RSA") {
    const signing = /sign|certificate/i.test(role);
    return { oid: "1.2.840.113549.1.1.1", primitive: signing ? "signature" : "pke", functions: signing ? ["keygen", "sign", "verify"] : ["keygen", "encrypt", "decrypt"], classical: f.keyBits >= 3072 ? 128 : f.keyBits >= 2048 ? 112 : 80, param: String(f.keyBits ?? "") };
  }
  if (f.family === "ECC") {
    const agree = /agreement|ECDH|ECDHE/i.test(role + f.algorithm);
    return { oid: "1.2.840.10045.2.1", primitive: agree ? "key-agree" : "signature", functions: agree ? ["keygen", "keyderive"] : ["keygen", "sign", "verify"], classical: 128, param: "P-256", curve: "secp256r1" };
  }
  if (f.family === "SHA1") return { oid: "1.3.14.3.2.26", primitive: "hash", functions: ["digest"], classical: 0, param: "160" };
  if (f.family === "AES") return { oid: "2.16.840.1.101.3.4.1.46", primitive: "ae", functions: ["encrypt", "decrypt", "tag"], classical: 256, param: "256", mode: "gcm", quantum: 5 };
  return { primitive: "unknown", functions: ["unknown"], classical: 0 };
}

export function toCycloneDxCbom(repo, scan, toolVersion) {
  const groups = new Map();
  for (const f of scan.findings) {
    const key = f.algorithm;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(f);
  }
  const components = [...groups.entries()].map(([algorithm, findings]) => {
    const f = findings[0];
    const p = algorithmProps(f);
    const algorithmProperties = {
      primitive: p.primitive,
      ...(p.param ? { parameterSetIdentifier: p.param } : {}),
      ...(p.curve ? { curve: p.curve } : {}),
      ...(p.mode ? { mode: p.mode } : {}),
      executionEnvironment: "software-plain-ram",
      implementationPlatform: "generic",
      cryptoFunctions: p.functions,
      classicalSecurityLevel: p.classical,
      nistQuantumSecurityLevel: p.quantum ?? 0,
    };
    const deadline = deadlineFor(f);
    return {
      type: "cryptographic-asset",
      "bom-ref": `crypto/algorithm/${algorithm.replace(/[^A-Za-z0-9.-]+/g, "-")}`,
      name: algorithm,
      cryptoProperties: { assetType: "algorithm", algorithmProperties, ...(p.oid ? { oid: p.oid } : {}) },
      evidence: { occurrences: findings.map((x) => ({ location: x.file, line: x.line, symbol: x.api, additionalContext: x.snippet })) },
      properties: [
        { name: "cryptoshift:quantumThreat", value: f.threat?.level ?? "unknown" },
        { name: "cryptoshift:recommendation", value: f.recommendation?.target ?? "" },
        { name: "cryptoshift:maxRiskScore", value: String(Math.max(...findings.map((x) => x.risk?.score ?? 0))) },
        ...(deadline.disallowedAfter ? [{ name: "cryptoshift:disallowedAfter", value: String(deadline.disallowedAfter) }, { name: "cryptoshift:deadlineSource", value: deadline.source }] : []),
      ],
    };
  });
  return {
    $schema: "http://cyclonedx.org/schema/bom-1.6.schema.json",
    bomFormat: "CycloneDX",
    specVersion: "1.6",
    serialNumber: `urn:uuid:${crypto.randomUUID()}`,
    version: 1,
    metadata: {
      timestamp: new Date().toISOString(),
      tools: { components: [{ type: "application", name: "CryptoShift", version: toolVersion }] },
      component: { type: "application", "bom-ref": `repo/${repo.id}`, name: repo.name },
      properties: [{ name: "cryptoshift:scanId", value: scan.id }, { name: "cryptoshift:scannedAt", value: scan.at }, { name: "cryptoshift:filesScanned", value: String(scan.filesScanned) }],
    },
    components,
    dependencies: [{ ref: `repo/${repo.id}`, dependsOn: components.map((c) => c["bom-ref"]) }],
  };
}
