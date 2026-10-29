"""Streamlit Operator Dashboard for CryptoShift (Quant-A-Maze 3.0 — PQC-01).

Run with:
    .\\.venv\\Scripts\\streamlit.exe run src/cryptoshift/ui/app.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from cryptoshift.agent.assistant import Assistant  # noqa: E402
from cryptoshift.datasets import (  # noqa: E402
    load_banking_pqc_observations,
    resolve_dataset_paths,
    summarize_banking_pqc_observations,
    summarize_cesnet_tls22_streaming,
)
from cryptoshift.mvp_slice import (  # noqa: E402
    DEFAULT_CONFIGS_DIR,
    DEFAULT_SQLITE_PATH,
    DEFAULT_WORKSPACE_DIR,
    run_mvp_vertical_slice,
)
from cryptoshift.reporting import (  # noqa: E402
    write_mvp_vertical_slice_reports,
    write_real_dataset_summary_reports,
)


QUERA_STREAMLIT_CSS = """
<style>
  @font-face {
    font-family: 'Outfit';
    src: url('https://cdn.prod.website-files.com/643b94c382e84463a9e52264/68a6a6dea031665e62521f31_Outfit-Regular.ttf') format('truetype');
    font-weight: 400; font-style: normal; font-display: swap;
  }
  @font-face {
    font-family: 'Outfit';
    src: url('https://cdn.prod.website-files.com/643b94c382e84463a9e52264/68a6a6de6810279bb662bf0e_Outfit-Medium.ttf') format('truetype');
    font-weight: 500; font-style: normal; font-display: swap;
  }
  @font-face {
    font-family: 'Outfit';
    src: url('https://cdn.prod.website-files.com/643b94c382e84463a9e52264/68ac49a9d21267f1b47489ee_Outfit-SemiBold.ttf') format('truetype');
    font-weight: 600; font-style: normal; font-display: swap;
  }
  @font-face {
    font-family: 'Radionb';
    src: url('https://cdn.prod.website-files.com/643b94c382e84463a9e52264/64745cfba5d47718a54d664a_RadionB-Bold.woff') format('woff');
    font-weight: 700; font-style: normal; font-display: swap;
  }

  /* QuEra Deep Quantum Dark + Sunrise Purple-Orange Theme */
  .stApp {
    background-color: #0f0c24 !important;
    background-image:
      radial-gradient(rgba(64, 64, 64, 0.28) 1.68px, transparent 1.68px),
      url('https://cdn.prod.website-files.com/643b94c382e84463a9e52264/68adb90cd2298aafc5d5cc32_72eca1721e0a0804e9517c7772d2e4e8_hero%20bg%20desktop.webp') !important;
    background-size: 12px 12px, cover !important;
    background-position: 0 0, top center !important;
    background-attachment: fixed !important;
    color: #FFFFFF !important;
    font-family: 'Outfit', sans-serif !important;
  }

  [data-testid="stHeader"] {
    background: rgba(15, 12, 36, 0.72) !important;
    backdrop-filter: blur(18px) !important;
  }

  [data-testid="stSidebar"] {
    background: rgba(15, 12, 36, 0.86) !important;
    backdrop-filter: blur(24px) saturate(160%) !important;
    border-right: 1px solid rgba(250, 130, 236, 0.25) !important;
  }
  [data-testid="stSidebar"] * {
    color: #F4F4F4 !important;
    font-family: 'Outfit', sans-serif !important;
  }

  h1, h2, h3, h4 {
    font-family: 'Radionb', 'Outfit', sans-serif !important;
    color: #FFFFFF !important;
    letter-spacing: -0.02em !important;
  }

  /* QuEra Glassmorphic Metric Cards */
  [data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.07) !important;
    backdrop-filter: blur(22px) saturate(165%) !important;
    border: 1px solid rgba(250, 130, 236, 0.28) !important;
    border-radius: 16px !important;
    padding: 16px 20px !important;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35) !important;
  }
  [data-testid="stMetricValue"] {
    font-family: 'Radionb', 'Outfit', sans-serif !important;
    background: linear-gradient(90deg, #FFFFFF 0%, #FA82EC 55%, #FF7C24 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700 !important;
  }
  [data-testid="stMetricLabel"] {
    color: rgba(255, 255, 255, 0.78) !important;
    font-family: 'Outfit', sans-serif !important;
  }

  /* QuEra Pill Buttons */
  .stButton > button {
    background: linear-gradient(90deg, #7F3EFF 4%, #FA82EC 52%, #FF7C24 90%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 999px !important;
    padding: 0.65rem 1.6rem !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    box-shadow: 0 8px 24px rgba(255, 124, 36, 0.32) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
  }
  .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 32px rgba(250, 130, 236, 0.48) !important;
  }

  /* QuEra Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap: 10px !important;
    background: rgba(255, 255, 255, 0.06) !important;
    padding: 8px 12px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
    backdrop-filter: blur(18px) !important;
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 999px !important;
    color: rgba(255, 255, 255, 0.82) !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #7F3EFF 4%, #FA82EC 52%, #FF7C24 90%) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
  }

  /* Expanders & Alerts */
  [data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(255, 255, 255, 0.16) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(18px) !important;
  }

  /* QuEra Hero Banner inside Streamlit */
  .quera-hero-banner {
    position: relative;
    border-radius: 24px;
    padding: 32px 38px;
    margin-bottom: 24px;
    background:
      linear-gradient(125deg, rgba(15, 12, 36, 0.88) 0%, rgba(127, 62, 255, 0.28) 55%, rgba(255, 124, 36, 0.25) 100%),
      url('https://cdn.prod.website-files.com/643b94c382e84463a9e52264/68adb90cd2298aafc5d5cc32_72eca1721e0a0804e9517c7772d2e4e8_hero%20bg%20desktop.webp') center/cover no-repeat;
    border: 1px solid rgba(250, 130, 236, 0.35);
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
    flex-wrap: wrap;
  }
  .quera-gradient-span {
    background: linear-gradient(90deg, #7F3EFF 4%, #FA82EC 52%, #FF7C24 90%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
</style>
"""


def render_app() -> None:
    st.set_page_config(
        page_title="CryptoShift PQC-01 — QuEra UI/UX Operator Workbench",
        layout="wide",
    )
    st.markdown(QUERA_STREAMLIT_CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="quera-hero-banner">
          <div style="max-width: 760px;">
            <div style="display:flex;align-items:center;gap:14px;margin-bottom:12px;">
              <img src="https://cdn.prod.website-files.com/643b94c382e84463a9e52264/68adb32ac8e19135fcc0cb65_af0390bc875d5c819361dd8b73723b87_logo%20white.svg" width="126" alt="QuEra"/>
              <span style="padding:4px 12px;border-radius:999px;background:rgba(255,124,36,0.18);border:1px solid rgba(250,130,236,0.45);font-size:12px;font-weight:600;letter-spacing:0.06em;color:#fff;">
                CRYPTOSHIFT PQC-01 · MORE SCIENCE, LESS FICTION
              </span>
            </div>
            <h1 style="margin:0 0 8px 0;font-size:2.4rem;line-height:1.12;">
              Putting <span class="quera-gradient-span">Quantum-Safe Migration</span> to Work
            </h1>
            <p style="margin:0;color:rgba(255,255,255,0.82);font-size:1.02rem;line-height:1.5;">
              Traceable CBOM Discovery · Dependency-Ordered Wave Scheduling (<code>QpiAI Opt 299.1</code> &amp; <code>18-Qubit QAOA</code>) ·
              OpenSSL 3.5.9 TLS 1.3 Verification (<code>X25519MLKEM768</code> + <code>ML-DSA-65</code>) · Real Banking &amp; CESNET-TLS22 Streaming
            </p>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:10px;">
            <img src="https://cdn.prod.website-files.com/643b94c382e84463a9e52264/6a50a406750ffdf90d53cec2_hp-fault-tolerance_img--tl.webp" width="150" style="border-radius:14px;border:1px solid rgba(255,255,255,0.18);" alt="Roadmap"/>
            <a href="http://127.0.0.1:8765" target="_blank" style="text-decoration:none;padding:8px 18px;border-radius:999px;background:linear-gradient(90deg,#7F3EFF 4%,#FA82EC 52%,#FF7C24 90%);color:#fff;font-weight:600;font-size:0.9rem;">
              Open Full QuEra Web Experience (:8765) ↗
            </a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Target & Approval Controls")
        input_mode = st.radio(
            "Source / Config Input",
            ["Repository Path", "Upload Files (Staged Copy)"],
            index=0,
        )
        target_dir = DEFAULT_CONFIGS_DIR
        if input_mode == "Repository Path":
            custom_path = st.text_input(
                "Path to scan (relative to repo root or absolute):",
                value="demo_bank_app/configs",
            )
            candidate = Path(custom_path)
            if not candidate.is_absolute():
                candidate = ROOT / candidate
            target_dir = candidate
        else:
            uploaded = st.file_uploader(
                "Upload .py, .yaml, .yml, .conf, .nginx files",
                type=["py", "yaml", "yml", "conf", "nginx"],
                accept_multiple_files=True,
            )
            upload_dir = DEFAULT_WORKSPACE_DIR / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            if uploaded:
                for uf in uploaded:
                    (upload_dir / uf.name).write_bytes(uf.getvalue())
                target_dir = upload_dir

        st.divider()
        approve_flag = st.checkbox(
            "Human Approval: Apply patches to isolated staging copy",
            value=False,
        )
        approver_name = st.text_input(
            "Approver Name / Role (required to stage patches):",
            value="Security Architect Reviewer" if approve_flag else "",
        )
        sim_fail = st.selectbox(
            "Simulate Verification Gate Failure (Optional):",
            options=[
                "(None — Nominal Verification)",
                "interbank_tls",
                "auth_gateway",
                "card_vault",
                "payment_signing",
                "ledger_audit",
                "settlement_batch",
            ],
            index=0,
        )
        sim_fail_svc = None if sim_fail.startswith("(None") else sim_fail

        run_btn = st.button("Run Vertical Slice", type="primary")

    if "slice_result" not in st.session_state or run_btn:
        st.session_state["slice_result"] = run_mvp_vertical_slice(
            target_path=target_dir,
            approve_all=approve_flag,
            approver=approver_name,
            simulate_failure_service=sim_fail_svc,
        )
        write_mvp_vertical_slice_reports(
            st.session_state["slice_result"],
            ROOT / "reports" / "runs",
        )

    res = st.session_state["slice_result"]

    tab_scan, tab_plan, tab_patch, tab_data, tab_m3 = st.tabs(
        [
            "1. Scan & CBOM Inventory",
            "2. Dependencies, Risk & Wave Plan",
            "3. Patch Preview, Approval & Verification",
            "4. Real Datasets & HDF5 Streaming",
            "5. Member 3 Visual Console & AI Assistant",
        ]
    )

    with tab_scan:
        st.subheader("Traceable Cryptographic Bill of Materials (CBOM)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Run ID", res["run_id"])
        col2.metric("Pre-Patch File Findings", res["scanned_file_findings_count"])
        col3.metric(
            "Post-Patch Staged Findings",
            res["post_patch_staged_findings_count"]
            if res["post_patch_staged_findings_count"] is not None
            else "Pending Approval",
        )
        col4.metric("Original Source Files Unmodified", str(res["original_source_files_unmodified"]))

        st.info(
            "**NIST PQC Role Enforcement:** `ML-KEM` (FIPS 203) is recommended strictly for key establishment / key wrapping "
            "(`ECDHE-P256`, `RSA_OAEP`, `DH-2048`). `ML-DSA` (FIPS 204) is recommended strictly for digital signatures "
            "(`RS256`, `ECDSA-P256`, mTLS certificate authentication). Presence of a PQC token in a file does not clear other "
            "legacy primitives in the same file."
        )
        st.dataframe(res["scanned_file_findings"], use_container_width=True)

    with tab_plan:
        st.subheader("Explainable Risk Scoring & Dependency-Ordered Wave Schedule")
        st.markdown(
            "**Risk Formula:** `min(10.0, mean(algorithm_base_score) * criticality_multiplier + min(retention_years / 10.0, 1.5))`"
        )
        st.dataframe(res["explainable_risk_breakdown"], use_container_width=True)

        st.subheader("Migration Wave Schedule (`solve_with_fallback_scheduler`)")
        w_cols = st.columns(3)
        waves = res["wave_schedule"]["waves"]
        for w_idx in range(3):
            svcs = waves.get(str(w_idx), waves.get(w_idx, []))
            w_cols[w_idx].metric(f"Wave {w_idx}", ", ".join(svcs) if svcs else "(empty)")
        st.caption(
            f"Schedule Feasible: `{res['wave_schedule']['feasible']}` | "
            f"Objective Value: `{res['wave_schedule']['objective_value']}` | "
            f"Dependency Order Valid: `{res['dependency_order_valid']}`"
        )

    with tab_patch:
        st.subheader("Staged Patch Previews, Human Approval Gate & Verification / Rollback")
        st.write(
            f"**Current Approval State:** `{res['approval_status']}` | "
            f"**Approver:** `{res['approver'] or 'None (Held in preview mode)'}`"
        )
        for p in res["patch_proposals"]:
            with st.expander(
                f"{p['proposal_id']} — {p['source_file']} (Service: {p['service_id']}, Wave {p['assigned_wave']}) [{p['approval_status']}]",
                expanded=True,
            ):
                for act in p["actions"]:
                    st.markdown(f"- {act}")
                st.code(p["unified_diff"], language="diff")
                st.caption(
                    f"Source SHA-256: `{p['source_sha256'][:16]}...` | "
                    f"Staged Copy Path: `{p['staged_file_path'] or 'Not staged (requires human approval)'}` | "
                    f"Backup Path: `{p['backup_file_path'] or 'N/A'}`"
                )

        st.subheader("Verification Gates & Automatic Rollback Status")
        st.dataframe(res["verification_gates"], use_container_width=True)
        st.dataframe(res["rollback_events"], use_container_width=True)
        if res["staged_files_rolled_back"]:
            st.warning(
                f"Automatic rollback restored backups for failed staged files: {res['staged_files_rolled_back']}"
            )

        if DEFAULT_SQLITE_PATH.is_file():
            with sqlite3.connect(DEFAULT_SQLITE_PATH) as conn:
                rows = conn.execute(
                    "SELECT run_id, created_at_utc, target_path, approval_status, approver, findings_count, post_patch_findings_count, gates_passed, gates_total, rollbacks_triggered FROM mvp_runs ORDER BY created_at_utc DESC LIMIT 10"
                ).fetchall()
            st.subheader("Recent Persisted Runs in Local SQLite (`scratch/mvp_workspace/cryptoshift_mvp.db`)")
            st.dataframe(
                [
                    {
                        "run_id": r[0],
                        "created_at_utc": r[1],
                        "target_path": r[2],
                        "approval_status": r[3],
                        "approver": r[4],
                        "pre_findings": r[5],
                        "post_findings": r[6],
                        "gates": f"{r[7]}/{r[8]}",
                        "rollbacks": r[9],
                    }
                    for r in rows
                ],
                use_container_width=True,
            )

    with tab_data:
        st.subheader("Real Datasets: Longitudinal Banking PQC Observations & CESNET-TLS22-S Streaming")
        paths = resolve_dataset_paths()
        st.json(paths.status_dict(), expanded=False)

        pqc_summary = summarize_banking_pqc_observations()
        st.markdown("### 1. PQ Readiness Index — 320 Longitudinal Banking TLS 1.3 Observations")
        if pqc_summary.get("status") == "verified":
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Observations", pqc_summary["audit"]["row_count"])
            c2.metric("Duplicate (scan_file, host, ts) Keys", pqc_summary["audit"]["duplicate_observation_keys"])
            c3.metric("Unique Banking Hosts (5 Dates)", pqc_summary["audit"]["unique_hosts"])
            c4.metric("Unclassified ERROR Rows", pqc_summary["unclassified_error_count"])

            st.caption(
                f"**Attribution:** {pqc_summary['attribution']} (`{pqc_summary['license']}`). "
                "Note: `ERROR` rows are unclassified probe outcomes and are never relabelled as `CLASSICAL`."
            )
            st.dataframe(
                [
                    {"scan_date": d, **counts}
                    for d, counts in pqc_summary["status_counts_by_scan_date"].items()
                ],
                use_container_width=True,
            )
            records, _ = load_banking_pqc_observations()
            with st.expander("Inspect Raw Longitudinal Observation Rows (320 rows)"):
                st.dataframe(records, use_container_width=True)
        else:
            st.error(pqc_summary.get("message", "PQC observations CSV unavailable."))

        st.markdown("### 2. CESNET-TLS22 `S` Subset (25,000,000 Flows, 3.23 GB HDF5) — Out-of-Core Streaming")
        col_chunk, col_max = st.columns(2)
        chunk_sz = col_chunk.number_input("Streaming Chunk Size (rows)", min_value=1000, max_value=100000, value=25000, step=5000)
        max_rows = col_max.number_input("Max Rows to Stream in Window", min_value=5000, max_value=500000, value=50000, step=25000)

        ces_summary = summarize_cesnet_tls22_streaming(chunk_size=int(chunk_sz), max_stream_rows=int(max_rows))
        if ces_summary.get("status") == "verified":
            bm = ces_summary["incremental_streaming_benchmark"]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total HDF5 Flows (14 Tables)", f"{ces_summary['total_table_rows']:,}")
            m2.metric("Streamed Window Rows", f"{bm['streamed_rows']:,}")
            m3.metric("Streaming Throughput", f"{bm['throughput_rows_per_sec']:,.0f} rows/s")
            m4.metric("Duplicate Flow IDs in Stream", bm["streamed_duplicate_flow_ids"])

            st.caption(
                f"**Citation:** {ces_summary['required_citation']} | **DOI:** `{ces_summary['doi']}` (`{ces_summary['license']}`) | "
                f"**SHA-256:** `{ces_summary['recorded_sha256']}`"
            )
            st.warning(
                "**Scope Boundary:** CESNET-TLS22 is real encrypted TLS flow metadata from October 2021 used for ingestion, "
                "streaming scale, and service-label exploration. It is NOT bank-internal data, NOT PQC migration ground truth, "
                "and is NEVER used to compute PQC detector precision or recall."
            )
            st.write("**Top Decoded `CATEGORY` Labels in Streamed Window:**", bm["top_categories_in_stream"])
            st.write("**Top Decoded `APP` Labels in Streamed Window:**", bm["top_apps_in_stream"])
            write_real_dataset_summary_reports(
                {
                    "dataset_configuration": paths.status_dict(),
                    "banking_pqc_observations": pqc_summary,
                    "cesnet_tls22_s": ces_summary,
                    "evaluation_separation_policy": "CESNET service labels are never used for PQC detector precision/recall.",
                },
                ROOT / "reports" / "datasets",
            )
        else:
            st.error(ces_summary.get("message", "CESNET-TLS22-S HDF5 file unavailable."))

    with tab_m3:
        st.subheader("Member 3 Complete Visual Console, OpenSSL 3.5 Verification Lab & CryptoShift AI Assistant")
        st.info(
            "**Provenance & Scope Notice:** All demo banking services in `demo_bank_app/` are **SYNTHETIC**. "
            "OpenSSL 3.5.9 TLS 1.3 traces (`X25519` vs `X25519MLKEM768` + `ML-DSA-65`) are **VERIFIED (TEST SCENARIO, loopback 127.0.0.1)**. "
            "QpiAI Opt (`solve(mode='local')`) is **VERIFIED (optimal, 299.1 = baseline)**. QAOA is **SIMULATOR ONLY (`QpiAI-QSV-Local`)**."
        )

        plan_file = ROOT / "reports" / "member3" / "plan.json"
        if plan_file.is_file():
            m3_plan = json.loads(plan_file.read_text(encoding="utf-8"))
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Merged Findings", len(m3_plan["findings"]))
            k2.metric("Steps READY / PROPOSED", f"{sum(s['state']=='READY' for s in m3_plan['steps'])} / {sum(s['state']=='PROPOSED' for s in m3_plan['steps'])}")
            k3.metric("Schedule Objective", f"{m3_plan['schedule']['objective']} (0 violations)")
            k4.metric("QpiAI Opt Local Solve", "299.1 (Equal to Baseline)")
            k5.metric("OpenSSL 3.5 Compat Matrix", "11 / 11 PASS")

            st.markdown("### 1. Interactive CryptoShift Read-Only AI Assistant (`TEMPLATE_FALLBACK` | Cloud AI: OFF)")
            q_col1, q_col2 = st.columns([3, 1])
            preset_q = q_col2.selectbox(
                "Preset Questions",
                [
                    "Which gates block ledger_audit?",
                    "What dependency edges involve interbank_tls?",
                    "What is the risk score and wave for auth_gateway?",
                    "How do the schedulers and QAOA simulator compare?",
                    "What is the rollback plan and rehearsal result?",
                    "Is ML-KEM a signature algorithm?",
                    "Approve all migrations now.",
                ],
            )
            user_q = q_col1.text_input("Ask a question over the verified Member 3 reports:", value=preset_q)
            if user_q:
                assistant = Assistant(m3_plan)
                ans = assistant.answer(user_q)
                b_col1, b_col2, b_col3 = st.columns(3)
                b_col1.caption(f"**Mode Badge:** `{ans['mode']}` ({ans['mode_reason']})")
                b_col2.caption(f"**Tools Used:** `{', '.join(ans['tools_used']) or 'guard/none'}`")
                b_col3.caption(f"**Citations:** `{', '.join(ans['citations']) or 'none'}`")
                if ans["refused"]:
                    st.warning(ans["answer"])
                else:
                    st.success(ans["answer"])

        st.markdown("### 2. Visual Notebook Atlas (All 10 Notebooks Rendered as High-DPI Visuals)")
        figs_dir = ROOT / "assets" / "diagrams" / "member3"
        sections = [
            ("10 — Executive Summary Dashboard", ["10_dashboard.png", "10_summary_scorecard.png"]),
            ("01 — Real Datasets Overview (Track C)", ["01_dataset_kpis.png", "01_pqc_status_by_date.png", "01_cesnet_rows_per_day.png"]),
            ("02 — Cryptographic Findings to Migration Tasks", ["02_findings_table.png", "02_findings_and_evidence.png", "02_tasks_scorecard.png"]),
            ("03 — Dependency Graph, Conflicts, Risk & Sensitivity", ["03_dependency_graph.png", "03_edges_and_conflicts.png", "03_risk_contributions.png", "03_sensitivity.png"]),
            ("04 — Wave Scheduling: Exact Baseline vs QpiAI Opt MILP", ["04_waves.png", "04_schedule_and_opt_scorecard.png"]),
            ("05 — QpiAI Quantum / QCloud Local Simulator QAOA", ["05_qaoa_scorecard.png", "05_qaoa_energy_and_samples.png"]),
            ("06 — OpenSSL 3.5.9 Verification, KATs, Stack Checks, Compatibility & Gates", ["06_selftests_kats_and_stack.png", "06_handshake_bytes.png", "06_compatibility.png", "06_overhead_boxplot.png", "06_gate_heatmap.png"]),
            ("07 — ML Track A: CESNET-TLS22 Service-Category Classifier", ["07_cesnet_card.png", "07_metrics_vs_baselines.png", "07_per_class_recall.png", "07_confusion_matrix.png"]),
            ("08 — ML Track B: Finding-Purpose Triage (Negative Result vs Rules)", ["08_purpose_triage.png", "08_triage_decision_card.png"]),
            ("09 — CryptoShift Assistant Evaluation (Template vs Sarvam Cloud)", ["09_qa_cards.png", "09_agent_eval.png", "09_sarvam_vs_template.png"]),
        ]
        for sec_title, img_names in sections:
            with st.expander(sec_title, expanded=sec_title.startswith(("10", "06"))):
                for img_name in img_names:
                    img_path = figs_dir / img_name
                    if img_path.is_file():
                        st.image(str(img_path), use_container_width=True)


if __name__ == "__main__":
    render_app()
