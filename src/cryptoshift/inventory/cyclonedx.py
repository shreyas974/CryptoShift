"""Optional CycloneDX 1.6 CBOM SUBSET export of the CBOM-like inventory, plus validation against the official schema.

Subset only: one `cryptographic-asset` component per (algorithm family, purpose) with `evidence.occurrences` (file,
line), one `application` component per attributed service, and `dependencies` from OBSERVED relationships. Fields
we cannot know statically (key sizes, certification level, execution environment) are omitted, not guessed. Even a
schema-valid document is NOT a complete inventory.

The schema is NOT bundled: `scripts/fetch_cyclonedx_schema.py` downloads bom-1.6 + spdx + jsf from the CycloneDX
specification repository at a pinned tag into scratch/derived/cyclonedx-schema/ and records SHA-256 checksums.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

VERSION = "cyclonedx-subset/1.0"

PRIMITIVE = {
    ("key_establishment", "RSA"): ("pke", ["encapsulate", "decapsulate"]),
    ("key_establishment", "*"): ("key-agree", ["keyderive"]),
    ("digital_signature", "*"): ("signature", ["sign", "verify"]),
    ("message_digest", "*"): ("hash", ["digest"]),
    ("symmetric_encryption", "RC4"): ("stream-cipher", ["encrypt", "decrypt"]),
    ("symmetric_encryption", "*"): ("block-cipher", ["encrypt", "decrypt"]),
}


def _primitive(purpose: str, family: str) -> Tuple[str, List[str]]:
    if family in ("Hybrid-ML-KEM",):
        return "kem", ["encapsulate", "decapsulate"]
    return PRIMITIVE.get((purpose, family)) or PRIMITIVE.get((purpose, "*")) or ("unknown", ["unknown"])


def to_cyclonedx(cbom: Dict[str, Any]) -> Dict[str, Any]:
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for f in cbom["findings"]:
        groups[(f["algorithm_family"], f["operation_purpose"])].append(f)
    components: List[Dict[str, Any]] = []
    svc_assets: Dict[str, set] = defaultdict(set)
    for (family, purpose), fs in sorted(groups.items()):
        ref = f"crypto:{family}:{purpose}".replace(" ", "_")
        if family == "TLS-protocol":
            crypto = {"assetType": "protocol", "protocolProperties": {"type": "tls"}}
        else:
            prim, funcs = _primitive(purpose, family)
            crypto = {"assetType": "algorithm", "algorithmProperties": {"primitive": prim, "cryptoFunctions": funcs}}
        components.append({
            "type": "cryptographic-asset", "bom-ref": ref, "name": family,
            "description": f"purpose={purpose}; candidate (human review): {fs[0]['target_pqc_algorithm']}"[:500],
            "cryptoProperties": crypto,
            "evidence": {"occurrences": [{"location": f["file_path"], "line": max(int(f["line_number"]), 1),
                                          "additionalContext": f"{f['finding_id']} {f['detector']}"} for f in fs]},
        })
        for f in fs:
            svc_assets[f["service_id"]].add(ref)
    for svc in sorted(svc_assets):
        components.append({"type": "application", "bom-ref": f"service:{svc}", "name": svc})
    deps: Dict[str, set] = {f"service:{s}": set(refs) for s, refs in svc_assets.items()}
    for e in cbom.get("relationships", {}).get("edges", []):
        deps.setdefault(f"service:{e['source']}", set()).add(f"service:{e['target']}")
        if not any(c["bom-ref"] == f"service:{e['target']}" for c in components):
            components.append({"type": "application", "bom-ref": f"service:{e['target']}", "name": e["target"]})
        if not any(c["bom-ref"] == f"service:{e['source']}" for c in components):
            components.append({"type": "application", "bom-ref": f"service:{e['source']}", "name": e["source"]})
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, cbom['scan']['input_set_sha256'])}",
        "metadata": {"timestamp": cbom["generated_at_utc"],
                     "tools": {"components": [{"type": "application", "name": "cryptoshift-inventory", "version": "1.1"}]},
                     "properties": [{"name": "cryptoshift:note", "value": "CBOM subset; static analysis; not complete"},
                                    {"name": "cryptoshift:input_set_sha256", "value": cbom["scan"]["input_set_sha256"]}]},
        "components": components,
        "dependencies": [{"ref": k, "dependsOn": sorted(v)} for k, v in sorted(deps.items())],
    }


def validate(doc: Dict[str, Any], schema_dir: Path) -> List[str]:
    """Return a list of validation error messages (empty = valid). Requires the fetched schema files."""
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7

    def load(name: str) -> Dict[str, Any]:
        return json.loads((schema_dir / name).read_text(encoding="utf-8"))

    bom = load("bom-1.6.schema.json")
    reg = Registry()
    for name in ("spdx.schema.json", "jsf-0.82.schema.json"):
        s = load(name)
        res = Resource.from_contents(s, default_specification=DRAFT7)
        reg = reg.with_resource(name, res).with_resource(s.get("$id", name), res)
    validator = Draft7Validator(bom, registry=reg)
    return [f"{'/'.join(map(str, e.absolute_path))}: {e.message[:200]}" for e in validator.iter_errors(doc)]
