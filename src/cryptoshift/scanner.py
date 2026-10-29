"""Context-aware cryptographic inventory scanner across source, configuration, and synthetic banking services."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptoshift.models import CryptoFinding
from cryptoshift.rules import resolve_contextual_pqc_rule
from demo_bank_app.services import SYNTHETIC_BANK_SERVICES

# Service-level context map for the synthetic banking fixture
SERVICE_PURPOSE_CONTEXT: Dict[Tuple[str, str], Dict[str, str]] = {
    ("auth_gateway", "RSA-2048"): {
        "purpose": "digital_signature",
        "protocol": "OAuth2 / OIDC JWT RS256 Token Signing",
        "owner": "Identity & Access Team",
        "confidence": "high",
        "rationale": "Service issues signed JWT bearer tokens using RS256.",
    },
    ("auth_gateway", "SHA-1"): {
        "purpose": "message_digest",
        "protocol": "Legacy Token Thumbprint Digest",
        "owner": "Identity & Access Team",
        "confidence": "high",
        "rationale": "Certificate thumbprint calculation uses SHA-1.",
    },
    ("ledger_audit", "ECDSA-P256"): {
        "purpose": "digital_signature",
        "protocol": "Core Ledger Merkle-Root Notarization",
        "owner": "Core Ledger Team",
        "confidence": "high",
        "rationale": "Signs immutable audit batches with ECDSA secp256r1.",
    },
    ("ledger_audit", "SHA-1"): {
        "purpose": "message_digest",
        "protocol": "Legacy Audit Record Digest",
        "owner": "Core Ledger Team",
        "confidence": "high",
        "rationale": "Secondary legacy digest computed with SHA-1.",
    },
    ("interbank_tls", "ECDHE-P256"): {
        "purpose": "key_establishment",
        "protocol": "Interbank ISO-20022 mTLS Ephemeral Key Exchange",
        "owner": "Network & Interbank Connectivity Team",
        "confidence": "high",
        "rationale": "TLS session key establishment uses ECDHE over P-256.",
    },
    ("interbank_tls", "RSA-2048"): {
        "purpose": "digital_signature",
        "protocol": "Interbank mTLS Peer Certificate Authentication",
        "owner": "Network & Interbank Connectivity Team",
        "confidence": "high",
        "rationale": "mTLS leaf and intermediate certificates use RSA-2048 signatures.",
    },
    ("card_vault", "RSA-2048"): {
        "purpose": "key_establishment",
        "protocol": "PKCS#11 Vault DEK Key Wrapping (RSA-OAEP)",
        "owner": "Card Security & PCI Vault Team",
        "confidence": "high",
        "rationale": "RSA-2048 wraps symmetric data encryption keys (key establishment/encapsulation role).",
    },
    ("card_vault", "3DES"): {
        "purpose": "symmetric_encryption",
        "protocol": "Legacy Card PIN Block / Track Envelope Encryption",
        "owner": "Card Security & PCI Vault Team",
        "confidence": "high",
        "rationale": "Legacy payment HSM slot configured for Triple-DES.",
    },
    ("payment_signing", "ECDSA-P256"): {
        "purpose": "digital_signature",
        "protocol": "RTGS / UPI Payment Instruction Signature",
        "owner": "Real-Time Payments Team",
        "confidence": "high",
        "rationale": "Signs outbound payment instructions with ECDSA-P256.",
    },
    ("payment_signing", "RSA-2048"): {
        "purpose": "digital_signature",
        "protocol": "ISO-20022 XMLDSig Detached Signature",
        "owner": "Real-Time Payments Team",
        "confidence": "high",
        "rationale": "Fallback XMLDSig envelope signing uses RSA-2048.",
    },
    ("settlement_batch", "DH-2048"): {
        "purpose": "key_establishment",
        "protocol": "Clearinghouse SFTP/SSH Group14 Key Exchange",
        "owner": "Settlement & Treasury Operations",
        "confidence": "high",
        "rationale": "Batch transfer channel negotiates finite-field DH-2048 key exchange.",
    },
    ("settlement_batch", "RSA-2048"): {
        "purpose": "digital_signature",
        "protocol": "End-of-Day Settlement Manifest Signature",
        "owner": "Settlement & Treasury Operations",
        "confidence": "high",
        "rationale": "Batch settlement manifest is signed with RSA-2048.",
    },
    ("settlement_batch", "3DES"): {
        "purpose": "symmetric_encryption",
        "protocol": "Legacy Clearinghouse Batch Archive Cipher",
        "owner": "Settlement & Treasury Operations",
        "confidence": "high",
        "rationale": "Archive payload encrypted with 3DES-CBC for legacy partner.",
    },
}

# Patterns for source/config file scanning (used in dataset evaluation and file scanner)
LINE_DETECTION_PATTERNS: List[Tuple[re.Pattern[str], str, str, str]] = [
    (
        re.compile(r"\b(rsa\.generate_private_key|RS256|PKCS1v15|RSA_SIGN)\b", re.IGNORECASE),
        "RSA-2048",
        "digital_signature",
        "high",
    ),
    (
        re.compile(r"\b(RSA_OAEP|padding\.OAEP|RSA_KEY_WRAP|RSA_KEM)\b", re.IGNORECASE),
        "RSA-2048",
        "key_establishment",
        "high",
    ),
    (
        re.compile(r"\b(ec\.SECP256R1|ECDSA_P256|ES256|ec\.ECDSA)\b", re.IGNORECASE),
        "ECDSA-P256",
        "digital_signature",
        "high",
    ),
    (
        re.compile(r"\b(ECDHE[_-]RSA|ECDHE[_-]ECDSA|ECDHE[_-]P256|TLS_ECDHE|prime256v1)\b", re.IGNORECASE),
        "ECDHE-P256",
        "key_establishment",
        "high",
    ),
    (
        re.compile(r"\b(diffie-hellman-group14|DH_2048|dh\.generate_parameters)\b", re.IGNORECASE),
        "DH-2048",
        "key_establishment",
        "high",
    ),
    (
        re.compile(r"\b(TripleDES|3DES|DES3\.new|DES-CBC3-SHA)\b", re.IGNORECASE),
        "3DES",
        "symmetric_encryption",
        "high",
    ),
    (
        re.compile(r"\b(hashlib\.sha1|hashes\.SHA1)\b", re.IGNORECASE),
        "SHA-1",
        "message_digest",
        "high",
    ),
    # Generic RSA clue without clear operation context -> flagged with medium/low confidence
    (
        re.compile(r"\b(LEGACY_RSA_2048_CONFIG)\b"),
        "RSA-2048",
        "unknown",
        "medium",
    ),
]

PQC_TOKEN_RE = re.compile(r"\b(X25519MLKEM768|ML-KEM-768|ML-DSA-65|SLH-DSA)\b", re.IGNORECASE)


def _file_sha256_short(file_path: Path) -> str:
    try:
        return hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
    except OSError:
        return "unknown"


def scan_banking_services() -> List[CryptoFinding]:
    """Scan the synthetic banking services and emit context-aware CBOM findings."""
    findings: List[CryptoFinding] = []
    idx = 1
    for line_idx, (service_id, meta) in enumerate(SYNTHETIC_BANK_SERVICES.items(), start=10):
        for alg in meta["legacy_algorithms"]:
            ctx = SERVICE_PURPOSE_CONTEXT.get(
                (service_id, alg),
                {
                    "purpose": "unknown",
                    "protocol": "Unspecified Banking Protocol",
                    "owner": "unknown",
                    "confidence": "medium",
                    "rationale": "Algorithm listed in service descriptor without explicit operation role.",
                },
            )
            rule = resolve_contextual_pqc_rule(alg, ctx["purpose"])
            findings.append(
                CryptoFinding(
                    finding_id=f"CS-F{idx:03d}",
                    service_id=service_id,
                    file_path="demo_bank_app/services.py",
                    line_number=line_idx * 4,
                    legacy_algorithm=alg,
                    quantum_threat=rule["quantum_threat"],
                    target_pqc_algorithm=rule["target_pqc"],
                    nist_standard=rule["nist_standard"],
                    severity=rule["severity"],
                    evidence_type="service_descriptor",
                    operation_purpose=ctx["purpose"],
                    confidence=ctx["confidence"],
                    rationale=ctx["rationale"],
                    owner=ctx["owner"],
                    library_or_protocol=ctx["protocol"],
                    human_review_status="requires_human_review",
                )
            )
            idx += 1
    return findings


def scan_source_file(file_path: Path, service_id: str = "scanned_repo") -> List[CryptoFinding]:
    """Scan a single source or config file for cryptographic clues with line-level evidence."""
    findings: List[CryptoFinding] = []
    if not file_path.is_file():
        return findings
    ext = file_path.suffix.lower()
    ev_type = "config_file" if ext in (".yaml", ".yml", ".json", ".ini", ".conf", ".toml") else "source_code"

    try:
        raw_text = file_path.read_text(encoding="utf-8")
        lines = raw_text.splitlines()
    except OSError:
        return findings

    has_pqc_token = bool(PQC_TOKEN_RE.search(raw_text))
    file_hash = _file_sha256_short(file_path)

    idx = 1
    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # If a line already configures hybrid X25519MLKEM768, do not flag prime256v1 fallback on that same line
        if "X25519MLKEM768" in stripped and ("prime256v1" in stripped or "ECDHE-P256" in stripped):
            continue
        for regex, alg_clue, purpose, confidence in LINE_DETECTION_PATTERNS:
            match = regex.search(raw_line)
            if match:
                rule = resolve_contextual_pqc_rule(alg_clue, purpose)
                matched_token = match.group(0)
                mixed_note = (
                    " [Mixed-posture warning: PQC identifier appears elsewhere in this file, "
                    "but this legacy primitive remains active and requires migration.]"
                    if has_pqc_token
                    else ""
                )
                findings.append(
                    CryptoFinding(
                        finding_id=f"SCAN-{file_path.stem}-{idx:02d}",
                        service_id=service_id,
                        file_path=str(file_path.as_posix()),
                        line_number=line_no,
                        legacy_algorithm=alg_clue,
                        quantum_threat=rule["quantum_threat"],
                        target_pqc_algorithm=rule["target_pqc"],
                        nist_standard=rule["nist_standard"],
                        severity=rule["severity"],
                        evidence_type=ev_type,
                        operation_purpose=purpose,
                        confidence=confidence,
                        rationale=(
                            f"Detected '{matched_token}' on line {line_no} "
                            f"(sha256:{file_hash}).{mixed_note}"
                        ),
                        owner="unknown",
                        library_or_protocol="static_file_scan",
                        human_review_status="requires_human_review",
                    )
                )
                idx += 1
                break
    return findings


def scan_nginx_config_file(
    file_path: Path,
    default_service_id: str = "nginx_tls_service",
) -> Tuple[List[CryptoFinding], Dict[str, Any]]:
    """Parse an Nginx TLS configuration file with directive- and line-level provenance."""
    findings: List[CryptoFinding] = []
    meta: Dict[str, Any] = {
        "service_id": default_service_id,
        "owner": "Network & Interbank Connectivity Team",
        "dependencies": [],
        "file_sha256_short": _file_sha256_short(file_path),
        "pqc_identifiers_present": [],
    }
    if not file_path.is_file():
        return findings, meta

    raw_text = file_path.read_text(encoding="utf-8")
    lines = raw_text.splitlines()
    file_hash = meta["file_sha256_short"]

    for line in lines:
        m_svc = re.search(r"#\s*Service ID:\s*([A-Za-z0-9_\-]+)", line, re.IGNORECASE)
        if m_svc:
            meta["service_id"] = m_svc.group(1).strip()
        m_own = re.search(r"#\s*Owner:\s*(.+)$", line, re.IGNORECASE)
        if m_own:
            meta["owner"] = m_own.group(1).strip()

    service_id = meta["service_id"]
    owner = meta["owner"]
    pqc_matches = PQC_TOKEN_RE.findall(raw_text)
    meta["pqc_identifiers_present"] = sorted(set(pqc_matches))
    has_pqc = bool(meta["pqc_identifiers_present"])

    idx = 1
    directive_re = re.compile(r"^\s*([a-zA-Z0-9_]+)\s+([^;#]+);")

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m_dir = directive_re.match(raw_line)
        if not m_dir:
            continue

        directive = m_dir.group(1).strip()
        val = m_dir.group(2).strip()

        if directive == "proxy_pass":
            m_host = re.search(r"https?://([a-zA-Z0-9_\-]+)", val)
            if m_host:
                dep_svc = m_host.group(1).split(".")[0]
                if dep_svc and dep_svc != service_id and dep_svc not in meta["dependencies"]:
                    meta["dependencies"].append(dep_svc)

        # 1. Key establishment curve / group check (ML-KEM role)
        if directive in ("ssl_ecdh_curve", "proxy_ssl_ecdh_curve", "ssl_conf_command"):
            if "X25519MLKEM768" in val or "ML-KEM" in val:
                continue
            if any(tok in val for tok in ("prime256v1", "secp256r1", "X25519", "secp384r1")):
                rule = resolve_contextual_pqc_rule("ECDHE-P256", "key_establishment")
                findings.append(
                    CryptoFinding(
                        finding_id=f"NGX-{file_path.stem}-{idx:02d}",
                        service_id=service_id,
                        file_path=str(file_path.as_posix()),
                        line_number=line_no,
                        legacy_algorithm="ECDHE-P256",
                        quantum_threat=rule["quantum_threat"],
                        target_pqc_algorithm=rule["target_pqc"],
                        nist_standard=rule["nist_standard"],
                        severity=rule["severity"],
                        evidence_type="config_file",
                        operation_purpose="key_establishment",
                        confidence="high",
                        rationale=(
                            f"Nginx directive '{directive} {val};' at line {line_no} (sha256:{file_hash}) "
                            "negotiates classical ECDHE key exchange without hybrid ML-KEM (FIPS 203)."
                        ),
                        owner=owner,
                        library_or_protocol=f"nginx:{directive}={val}",
                        human_review_status="requires_human_review",
                    )
                )
                idx += 1

        # 2. Cipher suite check (ECDHE key exchange + 3DES symmetric cipher)
        if directive in ("ssl_ciphers", "proxy_ssl_ciphers"):
            if "DES-CBC3" in val or "3DES" in val:
                rule_3des = resolve_contextual_pqc_rule("3DES", "symmetric_encryption")
                findings.append(
                    CryptoFinding(
                        finding_id=f"NGX-{file_path.stem}-{idx:02d}",
                        service_id=service_id,
                        file_path=str(file_path.as_posix()),
                        line_number=line_no,
                        legacy_algorithm="3DES",
                        quantum_threat=rule_3des["quantum_threat"],
                        target_pqc_algorithm=rule_3des["target_pqc"],
                        nist_standard=rule_3des["nist_standard"],
                        severity=rule_3des["severity"],
                        evidence_type="config_file",
                        operation_purpose="symmetric_encryption",
                        confidence="high",
                        rationale=(
                            f"Nginx directive '{directive} {val};' at line {line_no} (sha256:{file_hash}) "
                            "enables legacy 3DES cipher suite (Sweet32 / Grover-weakened)."
                            + (
                                " [Mixed-posture warning: PQC group configured elsewhere does not mitigate 3DES.]"
                                if has_pqc
                                else ""
                            )
                        ),
                        owner=owner,
                        library_or_protocol=f"nginx:{directive}={val}",
                        human_review_status="requires_human_review",
                    )
                )
                idx += 1

        # 3. Certificate signature authentication check (ML-DSA role)
        if directive in ("ssl_certificate", "proxy_ssl_certificate") and "rsa" in val.lower():
            if "mldsa" not in val.lower():
                rule_sig = resolve_contextual_pqc_rule("RSA-2048", "digital_signature")
                findings.append(
                    CryptoFinding(
                        finding_id=f"NGX-{file_path.stem}-{idx:02d}",
                        service_id=service_id,
                        file_path=str(file_path.as_posix()),
                        line_number=line_no,
                        legacy_algorithm="RSA-2048",
                        quantum_threat=rule_sig["quantum_threat"],
                        target_pqc_algorithm=rule_sig["target_pqc"],
                        nist_standard=rule_sig["nist_standard"],
                        severity=rule_sig["severity"],
                        evidence_type="config_file",
                        operation_purpose="digital_signature",
                        confidence="high",
                        rationale=(
                            f"Nginx directive '{directive} {val};' at line {line_no} (sha256:{file_hash}) "
                            "uses classical RSA-2048 X.509 certificate authentication (requires FIPS 204 ML-DSA migration)."
                        ),
                        owner=owner,
                        library_or_protocol=f"nginx:{directive}={val}",
                        human_review_status="requires_human_review",
                    )
                )
                idx += 1

    return findings, meta


def scan_yaml_config_file(
    file_path: Path,
    default_service_id: str = "yaml_service",
) -> Tuple[List[CryptoFinding], Dict[str, Any]]:
    """Parse a YAML configuration file using PyYAML AST nodes to preserve exact key paths and line numbers."""
    import yaml

    findings: List[CryptoFinding] = []
    file_hash = _file_sha256_short(file_path)
    meta: Dict[str, Any] = {
        "service_id": default_service_id,
        "service_name": default_service_id,
        "owner": "Banking Platform Engineering",
        "criticality": "HIGH",
        "data_retention_years": 10,
        "verification_ready_wave0": True,
        "dependencies": [],
        "file_sha256_short": file_hash,
        "pqc_identifiers_present": [],
    }
    if not file_path.is_file():
        return findings, meta

    raw_text = file_path.read_text(encoding="utf-8")
    meta["pqc_identifiers_present"] = sorted(set(PQC_TOKEN_RE.findall(raw_text)))
    has_pqc = bool(meta["pqc_identifiers_present"])

    try:
        parsed_dict = yaml.safe_load(raw_text) or {}
        root_node = yaml.compose(raw_text)
    except Exception:
        return scan_source_file(file_path, service_id=default_service_id), meta

    if isinstance(parsed_dict, dict):
        meta["service_id"] = str(parsed_dict.get("service_id", default_service_id))
        meta["service_name"] = str(parsed_dict.get("service_name", meta["service_id"]))
        meta["owner"] = str(parsed_dict.get("owner", meta["owner"]))
        meta["criticality"] = str(parsed_dict.get("criticality", meta["criticality"]))
        meta["data_retention_years"] = int(parsed_dict.get("data_retention_years", 10))
        meta["verification_ready_wave0"] = bool(parsed_dict.get("verification_ready_wave0", True))
        deps = parsed_dict.get("depends_on", [])
        if isinstance(deps, list):
            meta["dependencies"] = [str(d) for d in deps]

    service_id = meta["service_id"]
    owner = meta["owner"]
    idx = 1

    def _walk(node: Any, path_prefix: str) -> None:
        nonlocal idx
        if isinstance(node, yaml.MappingNode):
            for k_node, v_node in node.value:
                k_str = str(k_node.value)
                full_key = f"{path_prefix}.{k_str}" if path_prefix else k_str
                if isinstance(v_node, yaml.ScalarNode):
                    val_str = str(v_node.value).strip()
                    line_no = int(k_node.start_mark.line) + 1
                    _evaluate_yaml_scalar(full_key, k_str, val_str, line_no)
                else:
                    _walk(v_node, full_key)
        elif isinstance(node, yaml.SequenceNode):
            for item_idx, item_node in enumerate(node.value):
                _walk(item_node, f"{path_prefix}[{item_idx}]")

    def _evaluate_yaml_scalar(full_key: str, key_name: str, val_str: str, line_no: int) -> None:
        nonlocal idx
        combined = f"{key_name}: {val_str}"
        if "X25519MLKEM768" in val_str or "ML-KEM" in val_str or "ML-DSA" in val_str or "SHA3-256" in val_str:
            return
        for regex, alg_clue, purpose, confidence in LINE_DETECTION_PATTERNS:
            if regex.search(combined):
                rule = resolve_contextual_pqc_rule(alg_clue, purpose)
                mixed_warn = (
                    f" [Mixed-posture warning: file also contains PQC token {meta['pqc_identifiers_present']}, "
                    f"but '{full_key}={val_str}' remains quantum-vulnerable.]"
                    if has_pqc
                    else ""
                )
                findings.append(
                    CryptoFinding(
                        finding_id=f"YML-{file_path.stem}-{idx:02d}",
                        service_id=service_id,
                        file_path=str(file_path.as_posix()),
                        line_number=line_no,
                        legacy_algorithm=alg_clue,
                        quantum_threat=rule["quantum_threat"],
                        target_pqc_algorithm=rule["target_pqc"],
                        nist_standard=rule["nist_standard"],
                        severity=rule["severity"],
                        evidence_type="config_file",
                        operation_purpose=purpose,
                        confidence=confidence,
                        rationale=(
                            f"YAML directive '{full_key}: {val_str}' at line {line_no} "
                            f"(sha256:{file_hash}).{mixed_warn}"
                        ),
                        owner=owner,
                        library_or_protocol=f"yaml:{full_key}={val_str}",
                        human_review_status="requires_human_review",
                    )
                )
                idx += 1
                break

    if root_node is not None:
        _walk(root_node, "")
    return findings, meta


def scan_python_service_file(
    file_path: Path,
    default_service_id: str = "python_service",
) -> Tuple[List[CryptoFinding], Dict[str, Any]]:
    """Scan a Python source file, extracting module-level SERVICE_ID/OWNER/DEPENDS_ON metadata and line evidence."""
    meta: Dict[str, Any] = {
        "service_id": default_service_id,
        "owner": "Banking Platform Engineering",
        "dependencies": [],
        "file_sha256_short": _file_sha256_short(file_path),
    }
    if not file_path.is_file():
        return [], meta

    try:
        raw_text = file_path.read_text(encoding="utf-8")
        tree = ast.parse(raw_text, filename=str(file_path))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "SERVICE_ID" and isinstance(node.value, ast.Constant):
                            meta["service_id"] = str(node.value.value)
                        elif target.id == "OWNER" and isinstance(node.value, ast.Constant):
                            meta["owner"] = str(node.value.value)
                        elif target.id == "DEPENDS_ON" and isinstance(node.value, (ast.List, ast.Tuple)):
                            meta["dependencies"] = [
                                str(elt.value) for elt in node.value.elts if isinstance(elt, ast.Constant)
                            ]
    except Exception:
        pass

    findings = scan_source_file(file_path, service_id=meta["service_id"])
    for f in findings:
        f.owner = meta["owner"]
    return findings, meta


def scan_repository_path(
    target_path: Path,
    default_service_id: Optional[str] = None,
) -> Tuple[List[CryptoFinding], Dict[str, Dict[str, Any]]]:
    """Scan a file or directory of source code and TLS configs, returning findings and per-service metadata."""
    all_findings: List[CryptoFinding] = []
    service_metadata: Dict[str, Dict[str, Any]] = {}

    if target_path.is_file():
        files = [target_path]
    elif target_path.is_dir():
        files = sorted(
            p
            for p in target_path.rglob("*")
            if p.is_file() and p.suffix.lower() in (".py", ".yaml", ".yml", ".conf", ".nginx", ".json", ".toml", ".ini")
        )
    else:
        return all_findings, service_metadata

    for fpath in files:
        ext = fpath.suffix.lower()
        fallback_svc = default_service_id or fpath.stem
        if ext in (".yaml", ".yml"):
            f_list, meta = scan_yaml_config_file(fpath, default_service_id=fallback_svc)
        elif ext in (".conf", ".nginx"):
            f_list, meta = scan_nginx_config_file(fpath, default_service_id=fallback_svc)
        elif ext == ".py":
            f_list, meta = scan_python_service_file(fpath, default_service_id=fallback_svc)
        else:
            f_list = scan_source_file(fpath, service_id=fallback_svc)
            meta = {
                "service_id": fallback_svc,
                "owner": "unknown",
                "dependencies": [],
                "file_sha256_short": _file_sha256_short(fpath),
            }

        svc_id = meta.get("service_id", fallback_svc)
        if svc_id not in service_metadata:
            service_metadata[svc_id] = {
                "service_id": svc_id,
                "owner": meta.get("owner", "unknown"),
                "dependencies": list(meta.get("dependencies", [])),
                "files": [str(fpath.as_posix())],
                "pqc_identifiers_present": list(meta.get("pqc_identifiers_present", [])),
            }
        else:
            service_metadata[svc_id]["files"].append(str(fpath.as_posix()))
            for dep in meta.get("dependencies", []):
                if dep not in service_metadata[svc_id]["dependencies"]:
                    service_metadata[svc_id]["dependencies"].append(dep)

        all_findings.extend(f_list)

    return all_findings, service_metadata
