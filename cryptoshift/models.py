"""Core data models for CryptoShift PQC-01 migration discovery, verification, and wave scheduling."""

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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
