"""Core data models for CryptoShift PQC-01 discovery, CBOM inventory, verification, evaluation, and wave scheduling."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CryptoFinding:
    finding_id: str
    service_id: str
    file_path: str
    line_number: int
    legacy_algorithm: str
    quantum_threat: str  # "Shor-CRQC" or "Grover-Weakened"
    target_pqc_algorithm: str
    nist_standard: str
    severity: str
    evidence_type: str = "service_descriptor"  # "source_code" | "config_file" | "dependency_manifest" | "service_descriptor"
    operation_purpose: str = "unknown"  # "key_establishment" | "digital_signature" | "symmetric_encryption" | "message_digest" | "unknown"
    confidence: str = "high"  # "high" | "medium" | "low"
    rationale: str = ""
    owner: str = "unknown"
    library_or_protocol: str = "unknown"
    human_review_status: str = "requires_human_review"
    # Stage 1 inventory fields (backward compatible: all optional with defaults)
    detector: str = "legacy"  # "legacy" | "python_ast" | "tls_config" | "dependency_manifest" | "certificate"
    algorithm_family: str = ""  # e.g. "RSA", "ECDSA", "ECDH", "DH", "3DES", "SHA-1", "TLS-protocol"
    detected_value: str = ""  # API name, directive value or dependency spec that triggered the finding
    location: str = ""  # "line 12" or "directive ssl_ciphers (line 12)"
    snippet_redacted: str = ""  # redacted, truncated source line (never secrets, keys or certificate bodies)
    ambiguity: str = "none"  # "none" | "ambiguous" (several purposes possible) | "unknown" (purpose not determinable)
    in_test_file: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MigrationTask:
    service_id: str
    name: str
    legacy_algorithms: List[str]
    target_algorithms: List[str]
    dependencies: List[str]
    duration_minutes: int
    rollout_cost: float
    risk_score: float
    verification_ready_wave0: bool
    criticality: str
    owner: str = "Banking Platform Engineering"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WaveScheduleConfig:
    num_waves: int = 3
    max_services_per_wave: int = 2
    max_minutes_per_wave: int = 85
    risk_delay_weight: float = 3.5
    enforce_verification_gate: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WaveScheduleResult:
    solver_name: str
    status: str  # "implemented" | "run successfully" | "fallback" | "blocked" | "not attempted"
    execution_mode: str  # "deterministic_local" | "qpiai_opt_local" | "qpiai_qcloud_local_sim"
    feasible: bool
    objective_value: Optional[float]
    task_to_wave: Dict[str, int]
    waves: Dict[int, List[str]]
    runtime_seconds: float
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationGateResult:
    service_id: str
    wave_index: int
    kat_passed: bool
    hybrid_handshake_passed: bool
    latency_within_slo: bool
    overall_passed: bool
    details: str
    input_revision: str = "HEAD-synthetic-fixture-v1"
    finding_ids: List[str] = field(default_factory=list)
    dependency_prerequisites: List[str] = field(default_factory=list)
    peer_combinations_tested: List[str] = field(
        default_factory=lambda: [
            "legacy_peer -> hybrid_service (classical fallback compatible)",
            "hybrid_peer -> hybrid_service (PQC + classical dual-mode)",
        ]
    )
    trace_reference: str = "MOCKED_SYNTHETIC_TRACE:protocol_demo.py"
    overhead_methodology: str = (
        "Modelled NIST FIPS 203/204 wire-size delta + local hashlib/HMAC timing check (not a production network benchmark)"
    )
    approver: str = "pending_human_security_architect_review"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RollbackEvent:
    service_id: str
    wave_index: int
    triggered: bool
    reason: str
    restored_algorithm: str
    snapshot_id: str
    known_good_config_version: str = "v1.4.2-pre-pqc-baseline"
    feature_flag: str = "CRYPTOSHIFT_ENABLE_HYBRID_PQC=false"
    owner: str = "Banking Platform SRE & Crypto Governance"
    measurable_stop_trigger: str = "p99 handshake latency > 15ms OR TLS/signature verification error rate > 0.1%"
    downstream_compatibility: str = "Dual-mode peers accept classical envelope during rollback window"
    re_verification_steps: str = "Re-run KAT vectors, check MTU fragmentation on middleboxes, and obtain human sign-off"
    policy_note: str = "Warning: reverting to legacy SHA-1 or 3DES violates NIST SP 800-131A baseline policy and requires compensating controls."

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

