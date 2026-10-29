"""Transparent additive risk score (PROVISIONAL and UNVALIDATED).

score = w_crypto * crypto_exposure + w_net * network_exposure + w_crit * criticality
        + w_dep * dependents_norm + w_ready * verification_readiness

- crypto_exposure: sum of class points over distinct (family group, purpose) pairs of the service's findings,
  capped at `crypto_exposure_cap` (class points in planning_config.json).
- network_exposure: 1.0 if a TLS listener/server block was observed in the service's files, else 0.0;
  0.5 if the service has no scanned files (unknown).
- criticality: points by criticality label (OBSERVED in config or DECLARED in descriptor).
- dependents_norm: number of transitive downstream services / max over services.
- verification_readiness: 1.0 if ready for Wave 0 (raises priority of services that can be verified early).
Weights and points are assumptions, not fitted to data.
"""

from __future__ import annotations

from typing import Any, Dict, List

SHOR_GROUPS = {"RSA", "EC", "DH", "DSA"}


def algorithm_class(group: str, purpose: str) -> str:
    if group in SHOR_GROUPS:
        if purpose == "key_establishment":
            return "shor_key_establishment"
        if purpose == "digital_signature":
            return "shor_signature"
        return "asymmetric_unknown_purpose"
    if group == "LEGACY_SYM":
        return "legacy_symmetric"
    if group == "WEAK_HASH":
        return "weak_hash"
    if group == "TLS_PROTOCOL":
        return "legacy_protocol"
    return "other"


def score_service(features: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    w = cfg["risk_weights"]
    pts = cfg["algorithm_class_points"]
    pairs = sorted(set(features["group_purpose_pairs"]))
    crypto_raw = sum(pts[algorithm_class(g, p)] for g, p in pairs)
    crypto = min(crypto_raw, cfg["crypto_exposure_cap"])
    parts = {
        "crypto_exposure": (w["crypto_exposure"], crypto),
        "network_exposure": (w["network_exposure"], cfg["network_exposure_points"][features["network_exposure"]]),
        "criticality": (w["criticality"], cfg["criticality_points"].get(features["criticality"], cfg["criticality_points"]["unknown"])),
        "dependents": (w["dependents"], features["dependents_norm"]),
        "verification_readiness": (w["verification_readiness"], 1.0 if features["verification_ready_wave0"] else 0.0),
    }
    contributions = {k: round(wt * val, 4) for k, (wt, val) in parts.items()}
    score = round(sum(contributions.values()), 4)
    reason = "; ".join(
        f"{k}={parts[k][1]:.2f}x{parts[k][0]:g}={contributions[k]:.2f}" for k in parts
    ) + f" | pairs={[f'{g}/{p}' for g, p in pairs]} | criticality={features['criticality']} | exposure={features['network_exposure']}"
    return {"score": score, "contributions": contributions, "inputs": {k: v[1] for k, v in parts.items()},
            "reason": reason, "label": "PROVISIONAL, UNVALIDATED"}


def rank(scores: Dict[str, float]) -> List[str]:
    return [s for s, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]
