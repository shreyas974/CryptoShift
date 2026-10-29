# CryptoShift

**Quant-A-Maze 3.0 | Track: Post-Quantum Cryptography (PQC-01)**  
*Verification-Gated Cryptographic Migration Across Banking Applications*

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![QpiAI SDKs](https://img.shields.io/badge/QpiAI-Opt%20%7C%20Quantum-8A2BE2)](https://qpiai.tech/)
[![NIST Standards](https://img.shields.io/badge/NIST-FIPS%20203%20%7C%20204-blue)](https://csrc.nist.gov/pqc)
[![React 18 + Vite](https://img.shields.io/badge/React-18%20%7C%20Vite%20SPA-61DAFB?logo=react&logoColor=black)](https://vitejs.dev/)
[![Sarvam AI](https://img.shields.io/badge/Sarvam%20AI-105B%20Reasoning-FF6F00)](https://sarvam.ai/)
[![Vercel Ready](https://img.shields.io/badge/Vercel-Serverless%20Ready-000000?logo=vercel&logoColor=white)](docs/VERCEL_DEPLOYMENT_GUIDE.md)
[![License Status](https://img.shields.io/badge/Status-Evaluation%20Ready-success)](#)

---

## Executive Overview

**CryptoShift** is an enterprise-grade platform engineered for evidence-backed discovery, dependency-aware wave scheduling, multi-stage verification gating, and human-in-the-loop governance for post-quantum cryptographic (PQC) migration across mission-critical banking architectures.

### The Banking Challenge (PQC-01)
Legacy financial systems rely heavily on public-key algorithms (**RSA-1024/2048**, **ECDH**, **ECDSA**) across payment gateways, interbank clearance protocols, core ledgers, and hardware security modules (HSMs). These systems face an existential threat from Shor’s algorithm and **Harvest-Now-Decrypt-Later (HNDL)** adversarial interception. However, migrating banking microservices cannot be done with naive search-and-replace:
1. **Dependency Deadlocks:** Circular or undeclared inter-service dependencies cause service outages if migrated in the wrong order.
2. **Wire & Overhead Explosion:** Post-quantum public keys and signatures (e.g. ML-KEM-768: 1,184 B; ML-DSA-65: 3,309 B) inflate TLS packets and introduce packet fragmentation and latency spikes.
3. **Protocol Fallback Risks:** Dual-mode clients negotiating with classical-only servers risk silent downgrade attacks.

### Tripartite Security Governance
CryptoShift enforces an uncompromising architectural principle:
$$\mathbf{AI\ Proposes} \quad \longrightarrow \quad \mathbf{Verification\ Validates} \quad \longrightarrow \quad \mathbf{Humans\ Approve}$$
- **AI Proposes:** Deterministic rule engines and **Sarvam AI (105B Reasoning Model)** propose candidate FIPS 203 (ML-KEM) and FIPS 204 (ML-DSA) replacements.
- **Verification Validates:** Throwaway execution sandboxes execute empirical seed KAT vectors, dual-mode peer compatibility matrices, and protocol handshake checks before any patch can advance.
- **Humans Approve:** An authenticated named reviewer must explicitly sign off on a verified candidate before staged release with byte-for-byte SHA-256 rollback checkpoints.

---

## Full-Stack Web Platform (`cryptoshift_app/`)

CryptoShift features a complete, standalone company-grade web application built with a warm sunlit glass enterprise interface, zero-dependency SVG charts, and interactive physical anatomy figures:

```
cryptoshift_app/
├── frontend/               # React 18 + Vite + TypeScript (Sunlit Glass UI)
│   ├── src/anatomy/        # Isometric drawing kit and living SVG frames
│   ├── src/components/     # Zero-dependency SVG Donut, Bar & Wave visualizers
│   ├── src/figures/        # 4 Living Isometric Physical Anatomy models
│   └── src/pages/          # Overview, Inventory, Risk, Planner, Patches, Verification
├── backend/                # Zero-dependency Node.js REST API + SQLite/JSON Store
│   ├── src/scanner.js      # Monorepo AST & API scanner
│   ├── src/graph.js        # Interbank DAG sequencer & cycle detector
│   ├── src/verify.js       # Real-time Python test execution runner
│   ├── src/patches.js      # Candidate patch synthesizers & Sarvam AI client
│   └── src/server.js       # Unified production server (API + Static bundle)
├── sample-repos/           # Bundled retail-banking monorepo (northbank-core)
├── api/index.js            # Vercel Serverless Function adapter
└── vercel.json             # Vercel Edge build & rewrite configuration
```

### The 4 Living Anatomy Experiences ([`/anatomy`](http://localhost:8787/anatomy))
1. **Fig 01 — Quantum Computer Cutaway:** Educational physical cutaway of a dilution refrigerator (300 K to 10 mK stages), microwave RF lines, and superconducting chip. Connects the physics of quantum noise to Shor's algorithm without claiming present-day NISQ machines break RSA.
2. **Fig 02 — Cryptographic Evidence Cabinet:** Physical 10-drawer specimen cabinet that pulls live evidence drawers (File/Line, Algorithm, Role, Exposure, Risk, Target PQC) for any scanned finding.
3. **Fig 03 — Banking Dependencies Bench:** Multi-tier isometric DAG bench highlighting upstream prerequisites in amber and downstream blast-radii in blue, with toggleable import-inferred conduits.
4. **Fig 04 — Verified Migration Line:** Physical inspection carriage that travels along the test track, halting at the first failing station with live pass/fail status lamps.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Discovery ["1. Context-Aware Discovery"]
        Repo["Banking Monorepos / Source"] --> Scanner["AST & Config Scanner"]
        Scanner --> CBOM["10-Field Evidence Cabinet"]
    end

    subgraph Intelligence ["2. Multi-Model Intelligence"]
        CBOM --> ML_Triage["Purpose Triage ML (HistGradientBoosting)"]
        CBOM --> Sarvam["Sarvam AI 105B Reasoning Proposer"]
        CBOM --> RiskScoring["Explainable Shor/HNDL Risk Scoring"]
    end

    subgraph Scheduling ["3. Combinatorial & Quantum Optimization"]
        RiskScoring --> DAG["Interbank Dependency Graph"]
        DAG --> QpiAI_MILP["QpiAI Opt 0.0.9 (Binary MILP)"]
        DAG --> QpiAI_QAOA["QpiAI Quantum SDK (QAOA on QpiAI-QSV-Local)"]
        QpiAI_MILP --> Waves["Cycle-Free Migration Waves (W0, W1, W2)"]
        QpiAI_QAOA --> Waves
    end

    subgraph Verification ["4. Multi-Stage Verification Rail"]
        Waves --> CandidatePatch["Candidate FIPS 203/204 Patch"]
        CandidatePatch --> ThrowawayEnv["Ephemeral Baseline vs Candidate Sandbox"]
        ThrowawayEnv --> KAT["Seed Known Answer Tests (KAT)"]
        ThrowawayEnv --> Compat["11-Case Dual-Mode Handshake Matrix"]
        ThrowawayEnv --> Latency["Wire Overhead & Latency Benchmarks"]
    end

    subgraph Governance ["5. Human Review & Safe Release"]
        KAT & Compat & Latency --> Gate{"Human Review Gate"}
        Gate -->|Named Attestation| Release["Staged Release (SHA-256 Checkpoint)"]
        Gate -->|Unverified / Rejected| Rollback["Byte-for-Byte Rollback Recovery"]
    end
```

---

## Detailed Results & Visual Evidence

All figures below are generated directly from real executions on this machine (`Python 3.12.14`, `OpenSSL 3.5.9`, `QpiAI Opt 0.0.9`, `QpiAI Quantum 0.3.0`, and `sarvam-105b-conversations`).

---

### Section 1: Real-World Ingestion & Telemetry Datasets

To ensure our migration planning reflects real-world banking traffic rather than pure theory, we ingested and analyzed **44,600+ real-world TLS handshakes** from the **CESNET TLS Telemetry Dataset**, alongside longitudinal PQC algorithm observations.

| Dataset / Telemetry KPI Overview | Daily Flow Volume Analysis | Longitudinal PQC Cipher Status |
|:---:|:---:|:---:|
| ![Dataset KPIs](assets/diagrams/member3/01_dataset_kpis.png) | ![CESNET Rows per Day](assets/diagrams/member3/01_cesnet_rows_per_day.png) | ![PQC Status by Date](assets/diagrams/member3/01_pqc_status_by_date.png) |

- **`01_dataset_kpis.png`:** Highlights the 44.6k+ real TLS flows, 10 distinct service classes, and 14 cryptographic findings mapped across banking microservices.
- **`01_cesnet_rows_per_day.png`:** Temporal flow distribution across the 14-day observation window (training partition: Oct 4–10; testing partition: Oct 11–17, 2021).
- **`01_pqc_status_by_date.png`:** Demonstrates that less than 0.2% of legacy traffic employs hybrid key exchange, underscoring the urgent need for structured, dependency-aware migration.

---

### Section 2: Context-Aware CBOM Discovery & Evidence Cabinet

The AST and configuration scanner parses Python, Java, shell scripts, and TLS configuration files to build a 10-field Cryptographic Bill of Materials (CBOM).

| Findings & Evidence Distribution | 10-Field Evidence Cabinet Table | Task Assignment Scorecard |
|:---:|:---:|:---:|
| ![Findings and Evidence](assets/diagrams/member3/02_findings_and_evidence.png) | ![Findings Table](assets/diagrams/member3/02_findings_table.png) | ![Tasks Scorecard](assets/diagrams/member3/02_tasks_scorecard.png) |

- **`02_findings_and_evidence.png`:** Discovered usages categorized by algorithm family: Shor-critical asymmetric keys (`ECDHE`, `RSA-1024`, `ECDSA-P256`), legacy collision-vulnerable hashes (`SHA-1`), and symmetric ciphers (`AES-256`).
- **`02_findings_table.png`:** Full evidence cabinet displaying exact file and line locations (`shared/bankcrypto/tls_config.py:6`, `vendor/legacy_hsm_client/client.py:11`), cryptographic purpose, and conservative risk points.
- **`02_tasks_scorecard.png`:** Scorecard tracking migration candidate synthesis and verification readiness across all detected usages.

---

### Section 3: Inter-Service Dependency DAG & Risk Scoring

Banking services cannot be migrated in isolation. Upstream identity providers and gateways must be sequenced before settlement or ledger databases.

| Banking Dependency Graph (DAG) | Observed vs Declared Edge Conflicts | Factor Risk Scoring Contributions | Monte Carlo Sensitivity Analysis |
|:---:|:---:|:---:|:---:|
| ![Dependency Graph](assets/diagrams/member3/03_dependency_graph.png) | ![Edges and Conflicts](assets/diagrams/member3/03_edges_and_conflicts.png) | ![Risk Contributions](assets/diagrams/member3/03_risk_contributions.png) | ![Sensitivity](assets/diagrams/member3/03_sensitivity.png) |

- **`03_dependency_graph.png`:** Multi-tier dependency topology across 6 core banking services: `interbank_tls`, `auth_gateway`, `card_vault`, `ledger_audit`, `payment_signing`, and `settlement_batch`.
- **`03_edges_and_conflicts.png`:** Identifies discrepancies between declared architecture manifests and actual code imports/reverse-proxy conduits (e.g. nginx proxying `interbank_tls` to `ledger_audit`).
- **`03_risk_contributions.png`:** Explainable risk scoring breakdown: +40 Shor-vulnerable, +15 internet exposure, +15 data retention $\ge 10\text{ y}$, +10 sub-2048-bit RSA. Missing evidence receives conservative penalty points.
- **`03_sensitivity.png`:** 10-run Monte Carlo weight perturbation analysis proving that priority scheduling remains robust against minor parameter variances.

---

### Section 4: Combinatorial Wave Scheduling (MILP vs Baseline)

The migration sequence groups services into concurrent waves subject to:
1. **Maintenance Window Budget:** Maximum $\le 85\text{ minutes}$ downtime per wave.
2. **Concurrency Capacity:** At most 2 services migrated concurrently per wave.
3. **Precedence Invariance:** No downstream service can migrate until its upstream dependencies are complete.

| Concurrent Wave Scheduling | Baseline vs QpiAI Opt Scorecard |
|:---:|:---:|
| ![Wave Schedule](assets/diagrams/member3/04_waves.png) | ![Schedule and Opt Scorecard](assets/diagrams/member3/04_schedule_and_opt_scorecard.png) |

- **`04_waves.png`:** The 3 scheduled migration waves:
  - **Wave 0:** `interbank_tls` (Root TLS ingress) + `ledger_audit` (Core storage)
  - **Wave 1:** `auth_gateway` (Identity token issuance) + `payment_signing` (Transaction authorization)
  - **Wave 2:** `card_vault` (DEK wrapping) + `settlement_batch` (Clearinghouse batching)
- **`04_schedule_and_opt_scorecard.png`:** The exact deterministic combinatorial baseline achieves an objective value of **`248.105`** in **4.8 ms**. The **QpiAI Opt 0.0.9** binary MILP model (`Model("cryptoshift_wave_schedule")`, 18 binary variables, 19 constraints) confirms feasibility and matches the exact optimal schedule (`diff = 0.0`).

---

### Section 5: QpiAI Quantum Optimization (QAOA on `QpiAI-QSV-Local`)

To explore quantum algorithmic readiness, Wave-0 priority selection was formulated as a 4-qubit Quadratic Unconstrained Binary Optimization (QUBO) problem:
$$\min_{q \in \{0, 1\}^4} \quad H(q) = \sum_{i} c_i q_i + 8.0 \left(\sum_i q_i - 2\right)^2 + 10.0 \sum_{(i, j) \in \text{Conflicts}} q_j (1 - q_i)$$

The problem was compiled using `QUBOProblem.from_model` and solved using a 1-layer Variational Quantum Approximate Optimization Algorithm (**QAOA**) circuit on the local statevector simulator **`QpiAI-QSV-Local`**.

| QAOA Statevector Energy & Sample Distribution | QpiAI Quantum Experiment Scorecard |
|:---:|:---:|
| ![QAOA Energy and Samples](assets/diagrams/member3/05_qaoa_energy_and_samples.png) | ![QAOA Scorecard](assets/diagrams/member3/05_qaoa_scorecard.png) |

- **`05_qaoa_energy_and_samples.png`:** Probability distribution across 1024 simulator shots. The ground-state optimum bitstring $|1100\rangle$ corresponds to `['interbank_tls', 'ledger_audit']` with ground energy **`-13.07`**.
- **`05_qaoa_scorecard.png`:** Verification scorecard proving the quantum simulation matches the exact classical optimum. Circuit parameters: 4 qubits, depth 8, size 18. *(All quantum experiments executed classically on `QpiAI-QSV-Local`; no quantum speedup is claimed).*

---

### Section 6: Multi-Stage Verification Rail & OpenSSL Benchmarks

Candidate patches must survive a multi-station inspection line before human sign-off.

| KAT Vector & Primitive Timing | Dual-Mode Handshake Matrix | Wire Size Packet Expansion | Handshake Latency Distributions | Verification Gate Heatmap |
|:---:|:---:|:---:|:---:|:---:|
| ![KATs and Stack](assets/diagrams/member3/06_selftests_kats_and_stack.png) | ![Compatibility](assets/diagrams/member3/06_compatibility.png) | ![Handshake Bytes](assets/diagrams/member3/06_handshake_bytes.png) | ![Overhead Boxplot](assets/diagrams/member3/06_overhead_boxplot.png) | ![Gate Heatmap](assets/diagrams/member3/06_gate_heatmap.png) |

- **`06_selftests_kats_and_stack.png`:** FIPS 203 deterministic seed KATs (`ML-KEM-768`: 1,184 B public key; SHA-256 `0b7934c8...`) and FIPS 204 seed KATs (`ML-DSA-65`: 1,952 B public key; SHA-256 `d666806e...`). In-process primitive execution measured in microseconds.
- **`06_compatibility.png`:** **11/11 dual-mode test cases passed**: verified classical client fallback, hybrid client negotiation, and strict rejection of expired certs, untrusted CAs, and mismatched cipher groups.
- **`06_handshake_bytes.png`:** Exact wire size differential:
  - Classical TLS 1.3 (`X25519`): **757 B** read / **388 B** written.
  - Hybrid TLS 1.3 (`X25519MLKEM768`): **1,846 B** read / **1,564 B** written.
  - Hybrid TLS 1.3 with `ML-DSA-65` Certificate: **10,207 B** read / **1,564 B** written.
- **`06_overhead_boxplot.png`:** Latency distribution over 30 test runs (median 44.8 ms classical vs 45.3 ms hybrid; process start-up dominates in loopback; wire bytes remain stable).
- **`06_gate_heatmap.png`:** Real-time gate status across all banking services confirming pre-promotion readiness.

---

### Section 7: Machine Learning Track A — CESNET Service Classifier

To detect banking traffic patterns and automate service classification without manual tagging, an ML model was trained on the **CESNET TLS Telemetry Dataset**.

- **Model Trained:** `HistGradientBoostingClassifier` with categorical feature binning.
- **Dataset Partition:** Split strictly by calendar day (Train: Oct 4–10, 2021 [105,000 rows]; Test: Oct 11–17, 2021 [105,000 rows]).
- **Results:** Achieved **81.3% Accuracy** and **0.748 Macro-F1** (substantially outperforming the majority-class baseline of 11.8% accuracy / 0.010 F1).

| Classifier Decision Card | Confusion Matrix (105k Test Rows) | Metric Comparison vs Baselines | Per-Class Precision & Recall |
|:---:|:---:|:---:|:---:|
| ![CESNET Card](assets/diagrams/member3/07_cesnet_card.png) | ![Confusion Matrix](assets/diagrams/member3/07_confusion_matrix.png) | ![Metrics vs Baselines](assets/diagrams/member3/07_metrics_vs_baselines.png) | ![Per-Class Recall](assets/diagrams/member3/07_per_class_recall.png) |

- **`07_confusion_matrix.png`:** Detailed confusion matrix showing high recall for Gateway, Clearing, and Internal Ledger services.
- **`07_metrics_vs_baselines.png`:** Side-by-side comparison proving statistical significance over byte-heuristic and majority baselines.
- **`07_per_class_recall.png`:** Breakdown of classification precision across banking service classes.

---

### Section 8: Machine Learning Track B — Finding Purpose Triage

Dual-use asymmetric algorithms present a major migration hazard: **RSA** can serve as an encryption mechanism (needing ML-KEM) or a digital signature (needing ML-DSA). A machine learning triage model was evaluated against rule-based heuristic engines.

| Purpose Triage Decision Flow | Leave-One-Repo-Out Cross-Validation Card |
|:---:|:---:|
| ![Purpose Triage](assets/diagrams/member3/08_purpose_triage.png) | ![Triage Decision Card](assets/diagrams/member3/08_triage_decision_card.png) |

- **`08_purpose_triage.png`:** Flow diagram showing disambiguation between Key Transport, Digital Signature, and Token Issuance.
- **`08_triage_decision_card.png`:** Evaluated on 79 labelled findings across 8 repositories using Leave-One-Repository-Out (LORO) cross-validation.
- **Scientific Honesty Rule:** Because the rule-based engine achieved a higher macro-F1 (0.783 vs 0.273) on edge cases, **the deterministic rule engine is kept in production**, while the ML model is retained strictly as an auxiliary advisor.

---

### Section 9: LLM Reasoning Agent Evaluation (Sarvam AI Integration)

CryptoShift connects to **Sarvam AI (`sarvam-105b-conversations`)** to provide deep post-quantum cryptographic architectural reasoning.

| Sarvam AI vs Template Baseline | 24-Question Benchmark Cards | Security & Prompt Injection Evaluation |
|:---:|:---:|:---:|
| ![Sarvam vs Template](assets/diagrams/member3/09_sarvam_vs_template.png) | ![QA Cards](assets/diagrams/member3/09_qa_cards.png) | ![Agent Eval](assets/diagrams/member3/09_agent_eval.png) |

- **`09_sarvam_vs_template.png`:** Evaluates Sarvam AI cloud responses against deterministic templates across 24 fixed benchmark questions covering FIPS 203/204 compliance and HNDL mitigations.
- **`09_qa_cards.png`:** Demonstrates structured architectural reasoning: explaining why RSA key transport requires ML-KEM-768 encapsulation, while JWT signing requires ML-DSA-65.
- **`09_agent_eval.png`:** Validates zero prompt-injection susceptibility and strict refusal policies when presented with malicious repository overrides.

---

### Section 10: Executive Summary & Dashboard

| Multi-Panel Vertical Slice Dashboard | Complete Project Evaluation Scorecard |
|:---:|:---:|
| ![Dashboard](assets/diagrams/member3/10_dashboard.png) | ![Summary Scorecard](assets/diagrams/member3/10_summary_scorecard.png) |

- **`10_dashboard.png`:** Unified multi-panel dashboard reflecting telemetry, CBOM evidence, schedule optimization, and verification status.
- **`10_summary_scorecard.png`:** Final project verification scorecard summarizing 10/10 green milestones across discovery, scheduling, quantum simulation, verification, and human governance.

---

## Quickstart & Launch Instructions

### 1. Prerequisites
- **Python:** 3.11 or 3.12 (virtual environment at `.venv`)
- **Node.js:** v20.x or higher
- **Credentials:** Copy `.env.example` to `.env` and set `SARVAM_API_KEY` (optional: `QPIAI_OPT_API_KEY`, `QPIAI_QCLOUD_API_KEY`).

### 2. Start Web Application (Recommended)
Launch the unified production server on port **8787**:
```powershell
# Navigate to web application directory
cd cryptoshift_app

# Set python path and start unified production server
$env:CRYPTOSHIFT_PYTHON = "$((Get-Location).Path)\..\.venv\Scripts\python.exe"
node backend/src/server.js
```
Open in browser: **[http://localhost:8787](http://localhost:8787)**  
*(Vite Dev Server available at [http://127.0.0.1:5173](http://127.0.0.1:5173) via `npm --prefix cryptoshift_app/frontend run dev`)*.

### 3. Run QpiAI CLI & Optimization Demo
```powershell
# 1. Run safe offline QpiAI capability & credential check
.\.venv\Scripts\python.exe cryptoshift_cli.py check-auth

# 2. Run with authenticated QpiAI local solve
.\.venv\Scripts\python.exe cryptoshift_cli.py check-auth --online-auth

# 3. Run complete discovery, MILP wave scheduling, and QAOA simulator demo
.\.venv\Scripts\python.exe cryptoshift_cli.py demo --online-auth
```

### 4. Run Test Suites
```powershell
# Run backend API and verification suite (10/10 PASS)
cd cryptoshift_app
npm.cmd test

# Run frontend TypeScript typecheck (0 errors)
cd cryptoshift_app/frontend
npm.cmd run typecheck

# Run Python regression tests
cd ..
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 5. Deploy to Vercel
See the complete step-by-step instructions in [`docs/VERCEL_DEPLOYMENT_GUIDE.md`](docs/VERCEL_DEPLOYMENT_GUIDE.md):
```powershell
cd cryptoshift_app
npx vercel
```

---

## Deliverables & Documentation Index

- **[Full Website User-Audit, Bug-Fix & Quality Report](docs/USER_AUDIT_AND_FIX_REPORT.md)** — Exhaustive 10-category audit and technical validation report.
- **[Vercel Deployment Guide](docs/VERCEL_DEPLOYMENT_GUIDE.md)** — Step-by-step instructions for all-in-one and hybrid Vercel deployment.
- **[QpiAI Execution Log](reports/qpiai/QPIAI_EXECUTION_LOG.log)** — Official execution trace of QpiAI Opt, MILP formulation, and QAOA simulation on `QpiAI-QSV-Local`.
- **[QpiAI Integration & Verification Report](reports/qpiai/qpiai_evidence_report.md)** — Hardware and mathematical details of the quantum scheduling experiment.
- **[Architecture & Trust Boundaries](docs/architecture.md)** — Threat model, key boundaries, and cryptographic lifecycle.
- **[Dataset & Evaluation Guide](docs/dataset-and-evaluation.md)** — Evaluation protocols for CESNET telemetry and synthetic fixtures.
- **[Migration Verification & Rollback Guide](docs/migration-and-verification.md)** — Dual-mode protocol matrices and rollback safety.

---

## Scientific Rigor & Honesty Disclosure

- **Synthetic Banking Monorepos:** Services in `demo_bank_app/` and `cryptoshift_app/sample-repos/northbank-core` are synthetic banking fixtures modelled after retail microservice architectures.
- **Classical Statevector Simulation:** All quantum circuit executions (`QAOA(reps=1)`, depth 8, size 18, 1024 shots) executed on the classical statevector simulator **`QpiAI-QSV-Local`**. No quantum supremacy or speedup over exact classical combinatorial solvers is claimed.
- **Deterministic Baseline Parity:** The exact deterministic combinatorial baseline achieves an identical objective value of **`248.105`** and Wave-0 assignment (`interbank_tls`, `ledger_audit`) as the QpiAI Opt MILP solver and QAOA minimum energy state (`-13.07`).
- **Telemetry Origin:** Traffic analysis utilizes genuine data from the public **CESNET TLS Telemetry Dataset** (44.6k+ flows), with synthetic fixture labels explicitly distinguished in all evaluation metrics.
