# Member 2 → Member 3 / Member 4 handoff

## Output contract

| Artifact | Producer | Schema | Example (real run) |
|---|---|---|---|
| CBOM-like inventory v1.1 | `scan_inventory()` + `build_cbom_like()`; CLI `cryptoshift_cli.py inventory --path X`; `scripts/inventory_v11.py --path X` | `schemas/inventory-cbom-like-1.1.schema.json` | `schemas/examples/inventory-cbom-like-1.1.example.json` |
| Relationships | `inventory.relationships.extract_relationships(target, catalog=stats["_catalog"])` | `schemas/relationships.schema.json` | `schemas/examples/relationships.example.json` |
| CycloneDX 1.6 subset (optional) | `inventory.cyclonedx.to_cyclonedx(cbom)` + `validate()` | official CycloneDX 1.6.1 (fetched, checksummed) | written by `scripts/inventory_v11.py --cyclonedx` |

## Python API (stable for Member 3)

```python
from cryptoshift.inventory import scan_inventory, build_cbom_like
from cryptoshift.inventory.relationships import extract_relationships

findings, stats = scan_inventory(path, extra_known_services=["ledger_audit"])  # optional extra ids from a descriptor
rels = extract_relationships(path, catalog=stats["_catalog"])                    # reuse the same service catalogue
```

- **Fields on each `CryptoFinding`:**
  - `service_id`, `service_id_basis`, `service_id_confidence`. When no rule matches, `service_id` is `"unknown"` and confidence is `"none"`.
  - `operation_purpose` (unknown → the plan must HOLD), `ambiguity`, `confidence`, `detector`, `file_path` (relative), `line_number`, `snippet_redacted` (≤160 characters).
- **Relationship edges:** every edge is `OBSERVED` with `file` and `line`. Map them to the graph as OBSERVED. `unknown_references` must stay visible to the user as UNKNOWN; never turn them into edges.
- **`stats["_catalog"]`:** an in-memory object. Do not serialise it; use `stats["service_catalog"]` (a dict) for JSON.

## Known limits (do not hide in the UI)

- **Held-out round-2 recall:** 0.116 (precision 1.0, 0 FP) on 155 AI-assisted draft positives. The gaps are listed in `README.md`.
- **CryptoAPI-Bench mapped subset (Java only):** P 0.71, R 0.43.
- **Labels:** all are `pending-human`. Show them as "AI-assisted draft labels", never as ground truth.
- **CycloneDX:** "validated against CycloneDX 1.6 schema, subset" holds only for the two outputs that were validated. The default output name stays "CBOM-like".

## Shared files touched by Member 2 (please review)

| File | Change |
|---|---|
| `src/cryptoshift/models.py` | 2 optional `CryptoFinding` fields (`service_id_basis`, `service_id_confidence`), with defaults (backward compatible) |
| `src/cryptoshift/cli.py` | `scan` prints relative paths; `inventory` adds relationships, scan time and the by-service line |
| `data/labels/public_code/sources.json`, `labels_held_out.json` (Member 1 area) | Stage 1 held-out → `calibration-2` (labels unchanged); 4 round-2 sources added |
| `data/labels/public_code/README.md` (Member 1 area) | additive "Round 2" section |
| `scripts/evaluate_public_labels.py`, `scripts/fetch_public_label_sources.py` | new splits, freeze check, raw-file fetch mode |
