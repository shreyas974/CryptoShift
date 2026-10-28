# Architecture and Workflow

## 1. End-to-End Prototype Workflow

1. **Scope:** Select a bounded repository/fixture scope (`demo_bank_app/` or `data/fixtures/synthetic/`) and document supported file types.
2. **Discover (`src/cryptoshift/scanner.py`):** Analyze service descriptors, Python source files, and YAML configuration files with exact file and line evidence.
3. **Classify (`src/cryptoshift/rules.py`):** Infer `operation_purpose` (`key_establishment`, `digital_signature`, `symmetric_encryption`, `message_digest`, or `unknown`) separately from algorithm clues (`RSA-2048`, `ECDSA-P256`, `ECDHE-P256`, `DH-2048`, `3DES`, `SHA-1`). Attach confidence and rationale; place `unknown` purpose findings on `HOLD` for human review.
4. **Inventory (`src/cryptoshift/models.py`):** Emit CBOM-style `CryptoFinding` records with evidence type, operation purpose, algorithm clue, confidence, owner, protocol, and human-review status.
5. **Plan (`src/cryptoshift/scoring.py`, `src/cryptoshift/optimization/`):** Score urgency and rollout cost, validate topological dependencies (`src/cryptoshift/dependencies.py`), and schedule migration waves using:
   - Deterministic dependency-aware fallback scheduler (`src/cryptoshift/optimization/fallback_scheduler.py`)
   - Optional QpiAI Opt MILP formulation (`src/cryptoshift/optimization/qpiai_opt_adapter.py`)
   - Optional QpiAI Quantum 4-qubit Wave-0 QUBO QAOA local simulator experiment (`src/cryptoshift/optimization/qcloud_experiment.py`)
6. **Verify & Rollback (`src/cryptoshift/verification.py`, `src/cryptoshift/protocol_demo.py`, `src/cryptoshift/rollback.py`):** Run compatibility/KAT gates, record explicitly labelled mocked protocol envelope traces and wire-size overhead methodology, and generate rollback records with stop triggers and policy warnings.
7. **Report (`src/cryptoshift/reporting.py`):** Write reproducible, secret-free JSON and Markdown reports to `reports/qpiai/` and `reports/evaluation/`.

---

## 2. Canonical Package Layout

All Python source modules reside in one canonical location under `src/cryptoshift/`. No duplicate top-level `cryptoshift/` directory is maintained.

---

## 3. Trust Boundaries & Honest Limitations

- Static pattern detection is a discovery aid, not a proof of complete cryptographic inventory across a banking estate.
- The wave planner is decision-support tooling; human security architects own rollout and cryptographic policy decisions.
- QpiAI Opt and QpiAI Quantum (`QpiAI-QSV-Local`) are used for local scheduling optimization experiments, not as PQC primitives.
- Protocol traces in `src/cryptoshift/protocol_demo.py` are mocked/modelled traces combining real `hashlib` digests with analytical NIST FIPS 203/204 byte budgets.
- Secret values are never stored in code, inventory records, or committed reports.
