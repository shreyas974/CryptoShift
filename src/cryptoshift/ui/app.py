"""Streamlit Operator Dashboard for CryptoShift (Quant-A-Maze 3.0 — PQC-01).

Run with:
    .\\.venv\\Scripts\\streamlit.exe run src/cryptoshift/ui/app.py
"""

from __future__ import annotations

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


def render_app() -> None:
    st.set_page_config(
        page_title="CryptoShift PQC-01 Operator Workbench",
        layout="wide",
    )
    st.title("CryptoShift (PQC-01): Verification-Gated Cryptographic Migration")
    st.caption(
        "Context-aware CBOM discovery (NIST FIPS 203 ML-KEM vs. FIPS 204 ML-DSA), dependency-ordered wave scheduling, "
        "human-approved staged patching, verification gates, and real-dataset TLS telemetry."
    )

    tab_scan, tab_plan, tab_patch, tab_data = st.tabs(
        [
            "1. Scan & CBOM Inventory",
            "2. Dependencies, Risk & Wave Plan",
            "3. Patch Preview, Approval & Verification",
            "4. Real Datasets & HDF5 Streaming",
        ]
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


if __name__ == "__main__":
    render_app()
