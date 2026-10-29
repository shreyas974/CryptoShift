"""CryptoShift demo console (Streamlit). Run: scripts\\run_ui.ps1 (binds 127.0.0.1).

Every number and chart comes from `data.load()`. Scanned text is shown only as escaped plain text.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
for p in (ROOT / "src", ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from cryptoshift.ui.console import components as C  # noqa: E402
from cryptoshift.ui.console import data as D  # noqa: E402

PAGES = ["1 Overview", "2 Data & evidence", "3 Inventory", "4 Dependencies", "5 Migration plan", "6 Verification",
         "7 Approval & rollback", "8 Detection evaluation", "9 ML & AI", "10 Claims & limits"]
BANNER = ("Hackathon prototype (PQC-01). Synthetic demo bank; TLS results are a loopback TEST SCENARIO with throw-away "
          "keys. Not production ready, not certified, not compliant, no quantum-safety guarantee. "
          "Migration candidates are for human review; unknown purpose = HOLD.")


def L(key: str) -> D.Loaded:
    return D.load(key, st.session_state["base"])


# ------------------------------------------------------------------ pages
def page_overview() -> None:
    plan, sched, ag, ags = L("plan"), L("scheduling"), L("agent_eval"), L("agent_eval_sarvam")
    if not C.need(st, plan):
        return
    p = plan.value
    steps = p["steps"]
    ready = sum(s["state"] == "READY" for s in steps)
    opt = (sched.value or {}).get("qpiai_opt", {}).get("authenticated_local_solve", {}) if sched.ok else {}
    stages = [
        ("Inventory", "VERIFIED", f"{len(p['findings'])} findings"),
        ("Graph", "VERIFIED", f"{sum(e['provenance'] == 'OBSERVED' for e in p['edges'])} OBSERVED edges"),
        ("Risk score", "PARTIAL", "provisional, not validated"),
        ("Schedule", "VERIFIED", f"objective {p['schedule']['objective']}"),
        ("QpiAI Opt", opt.get("status", "UNKNOWN"), "equal to baseline" if opt.get("status") == "RUN" else "offline checks only"),
        ("Gates", "PARTIAL" if ready < len(steps) else "VERIFIED", f"{ready}/{len(steps)} READY"),
        ("Approval", "PLANNED" if not p["approval"]["approved_steps"] else "APPROVED", f"{len(p['approval']['approved_steps'])} approved (human only)"),
        ("Rollback", "VERIFIED" if p["rollback"].get("rehearsal_result", {}).get("recovered") else "UNKNOWN", "rehearsed on a copy"),
    ]
    st.subheader("Pipeline")
    for row in (stages[:4], stages[4:]):
        cols = st.columns(4)
        for col, (name, status, note) in zip(cols, row):
            col.markdown(f"**{name}**  \n{C.badge_md(status)}")
            col.caption(note)
    st.subheader("Key numbers")
    k = st.columns(4)
    k[0].metric("Findings", len(p["findings"]))
    k[1].metric("Services", len(p["services"]))
    k[2].metric("Steps READY", f"{ready} / {len(steps)}")
    k[3].metric("Plan hash", p["plan_hash"][:12])
    st.info("READY means the generic loopback evidence passed and the purpose is resolved. It is not verification of "
            "the service's own production stack.")
    if ag.ok:
        st.caption(f"Assistant evaluation: template {ag.value['passed']}/{ag.value['n']}"
                   + (f"; Sarvam cloud run {ags.value.get('v3_passed')}/24 (stricter v3 check)" if ags.ok else ""))
    with st.expander("Run actions (operator; fixed allow-list, no shell, outputs to scratch/derived)"):
        if st.session_state["mode"] == "DEMO":
            st.write("Disabled in DEMO mode (frozen snapshot).")
        else:
            choice = st.selectbox("Command", list(C.ALLOWED_COMMANDS))
            if st.button("Run selected command"):
                with st.spinner(f"running: {choice}"):
                    rc, out = C.run_allowed(choice)
                (st.success if rc == 0 else st.error)(f"exit code {rc}")
                st.code(out, language="text")
    C.footer(st, plan, sched)


def page_data() -> None:
    reg = L("registry")
    st.write("Datasets are read-only; they are never relabelled, augmented or duplicated.")
    if C.need(st, reg):
        items = reg.value.get("datasets", reg.value) if isinstance(reg.value, dict) else reg.value
        rows = []
        for d in (items if isinstance(items, list) else [dict(v, id=k) for k, v in items.items()]):
            rows.append({k: (", ".join(map(str, v)) if isinstance(v, list) else v) for k, v in d.items()
                         if not isinstance(v, dict)})
        C.data_table(st, rows, "data/registry.json")
    st.warning("CESNET-TLS22 is REAL flow metadata used only as a traffic-classification and scale demo. Its labels are "
               "not cryptographic or PQC labels.")
    src = ROOT / "data" / "labels" / "public_code" / "sources.json"
    if src.is_file():
        import json

        s = json.loads(src.read_text(encoding="utf-8"))["sources"]
        C.data_table(st, [{"id": x["id"], "split": x["split"], "licence": x["license"], "commit": x["commit"][:12],
                           "files": len(x["files"]), "url": x["url"]} for x in s],
                     "Public code used for labels (pinned commits; third-party code is not committed)")
    C.footer(st, reg)


def page_inventory() -> None:
    plan, inv = L("plan"), L("inventory")
    if not C.need(st, plan):
        return
    fs = plan.value["findings"]
    st.write("Each candidate is **for human review**. Unknown purpose means HOLD. Format: CBOM-like "
             "(a CycloneDX 1.6 subset validated separately).")
    c = st.columns(4)
    svc = c[0].selectbox("Service", ["(all)"] + sorted({f["service_id"] for f in fs}))
    pur = c[1].selectbox("Purpose", ["(all)"] + sorted({f["operation_purpose"] for f in fs}))
    det = c[2].selectbox("Detector", ["(all)"] + sorted({f.get("detector", "legacy") for f in fs}))
    hold = c[3].checkbox("Only HOLD (unknown purpose)")
    sel = [f for f in fs if (svc == "(all)" or f["service_id"] == svc) and (pur == "(all)" or f["operation_purpose"] == pur)
           and (det == "(all)" or f.get("detector", "legacy") == det) and (not hold or f["operation_purpose"] == "unknown")]
    if not sel:
        st.info("No findings for this filter.")
    else:
        C.data_table(st, [{"id": f["finding_id"], "location": f"{f['file_path']}:{f['line_number']}", "service": f["service_id"],
                           "attribution": f.get("service_id_confidence") or "n/a", "family": f.get("algorithm_family") or f["legacy_algorithm"],
                           "purpose": f["operation_purpose"], "confidence": f["confidence"], "ambiguity": f.get("ambiguity", "none"),
                           "candidate (human review)": f["target_pqc_algorithm"]} for f in sel])
        fid = st.selectbox("Show evidence for finding", [f["finding_id"] for f in sel])
        f = next(x for x in sel if x["finding_id"] == fid)
        st.text("Snippet (redacted, shown as plain text):")
        st.code(C.escaped_text(f.get("snippet_redacted") or "(no snippet)"), language="text")
        st.text(C.escaped_text(f"Rationale: {f.get('rationale', '')}", 300))
        st.text(C.escaped_text(f"Service basis: {f.get('service_id_basis', '')}", 300))
        by = pd.Series([f["operation_purpose"] for f in sel]).value_counts()
        st.bar_chart(by)
        with st.expander("Data behind this chart"):
            st.dataframe(by.rename("findings"))
    C.footer(st, plan, inv)


def _graph_figure(nodes, edges):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    g = nx.MultiDiGraph()
    g.add_nodes_from(nodes)
    for e in edges:
        g.add_edge(e["upstream"], e["downstream"], prov=e["provenance"])
    pos = nx.circular_layout(g)
    fig, ax = plt.subplots(figsize=(8, 5))
    nx.draw_networkx_nodes(g, pos, node_color="#dbe7fb", node_size=2600, ax=ax, edgecolors="#1f6feb")
    nx.draw_networkx_labels(g, pos, font_size=8, ax=ax)
    styles = {"OBSERVED": ("solid", "#1a7f37"), "DECLARED": ("dashed", "#57606a"), "INFERRED": ("dotted", "#bf8700")}
    for prov, (ls, colour) in styles.items():
        el = [(u, v) for u, v, d in g.edges(data=True) if d["prov"] == prov]
        nx.draw_networkx_edges(g, pos, edgelist=el, style=ls, edge_color=colour, arrows=True, arrowsize=15, ax=ax,
                               node_size=2600, connectionstyle="arc3,rad=0.08")
    ax.set_axis_off()
    return fig


def page_dependencies() -> None:
    plan, fx = L("plan"), L("relationships_fixture")
    if not C.need(st, plan):
        return
    p = plan.value
    st.markdown("Legend: " + C.badge_md("OBSERVED") + " solid green = evidence in a file with a line · "
                + C.badge_md("DECLARED") + " dashed grey = synthetic descriptor only · "
                + C.badge_md("INFERRED") + " dotted amber = assumption with a reason. Arrow = provider → consumer.")
    st.pyplot(_graph_figure(sorted(p["services"]), p["edges"]))
    C.data_table(st, [{"edge": f"{e['upstream']} → {e['downstream']}", "provenance": e["provenance"], "kind": e.get("kind") or "",
                       "file:line": f"{e['file']}:{e['line']}" if e.get("line") else (e.get("file") or ""), "reason": e.get("reason", "")}
                      for e in p["edges"]], "Text edge list (same data as the graph)")
    ga = p["graph_analysis"]
    st.markdown(f"**Cycles:** {len(ga['cycles'])} · **Unknown endpoints:** {len(p['unknown_endpoints'])} · **Conflicts:** {len(ga['conflicts'])}")
    if ga["conflicts"]:
        C.data_table(st, ga["conflicts"], "Observed vs declared conflicts (never hidden)")
    if p["unknown_endpoints"]:
        C.data_table(st, p["unknown_endpoints"], "UNKNOWN references (not turned into edges)")
    if fx.ok:
        with st.expander("Second example: SYNTHETIC multi-service fixture (Member 2 relationships)"):
            C.data_table(st, [{"edge": f"{e['source']} → {e['target']}", "kind": e["kind"], "file:line": f"{e['file']}:{e['line']}",
                               "confidence": e["confidence"]} for e in fx.value["edges"]])
            C.data_table(st, fx.value["unknown_references"], "UNKNOWN references")
    C.footer(st, plan, fx)


def page_plan() -> None:
    plan, sc = L("plan"), L("scheduling")
    if not C.need(st, plan):
        return
    p = plan.value
    st.warning("Risk score: **provisional, not validated**. Scheduling numbers are ASSUMPTIONS (docs/member3/assumptions.md).")
    rows = [{"service": s, "wave": p["schedule"]["task_to_wave"].get(s), "risk": v["risk"]["score"],
             "risk reason": v["risk"]["reason"], "evidence": v["evidence_source"], "findings": ", ".join(v["finding_ids"])}
            for s, v in sorted(p["services"].items(), key=lambda kv: (p["schedule"]["task_to_wave"].get(kv[0], 99), kv[0]))]
    C.data_table(st, rows, f"Waves (objective {p['schedule']['objective']}, dependency violations {len(p['schedule']['dependency_violations'])})")
    st.bar_chart(pd.Series({f"Wave {k}": len(v) for k, v in p["schedule"]["waves"].items()}, name="services"))
    if C.need(st, sc):
        s = sc.value
        o, q = s["qpiai_opt"]["authenticated_local_solve"], s["qaoa_phase2_wave0"]
        c = st.columns(3)
        c[0].markdown(f"**Deterministic baseline**  \n{C.badge_md('VERIFIED')}")
        c[0].metric("Objective (lower is better)", s["baseline"]["objective"])
        c[0].caption(f"runtime {s['baseline']['runtime_seconds']} s; exact search")
        c[1].markdown(f"**QpiAI Opt local solve**  \n{C.badge_md(o.get('status'))}")
        c[1].metric("Objective", o.get("objective", "n/a"),
                    delta=None if o.get("status") != "RUN" else f"{o['same_input_comparison']['difference']} vs baseline", delta_color="off")
        c[1].caption(f"{o.get('solver_status', o.get('reason', ''))}; same assignment: {o.get('same_input_comparison', {}).get('same_assignment')}. **Equal, not better.**")
        c[2].markdown(f"**QCloud QAOA (Wave 0)**  \n{C.badge_md('SIMULATOR')}")
        c[2].metric("P(optimum)", q["optimum_probability"], delta=f"uniform {q['uniform_probability']}", delta_color="off")
        c[2].caption("QpiAI-QSV-Local statevector simulator, 1024 shots. No quantum advantage is claimed.")
    C.footer(st, plan, sc)


def page_verification() -> None:
    plan, ev = L("plan"), L("verification")
    st.info("TEST SCENARIO, loopback 127.0.0.1, throw-away test keys. Loopback timing is not network timing. "
            "ML-KEM / ML-DSA checks are self-tests, not NIST KATs.")
    if C.need(st, plan):
        steps = plan.value["steps"]
        gates = sorted({g["gate"] for s in steps for g in s["gates"]})
        C.data_table(st, [{"step": s["step_id"], "state": C.badge_text(s["state"]),
                           **{g: C.badge_text(next((x["status"] for x in s["gates"] if x["gate"] == g), "UNKNOWN")) for g in gates}}
                          for s in steps], "Gate results (text + icon)")
    if C.need(st, ev):
        v = ev.value
        C.data_table(st, [{"case": r["case"], "type": r["category"], "expected": r["expected"], "observed": r["observed"],
                           "result": C.badge_text("PASS" if r["pass"] else "FAIL")} for r in v["compatibility_matrix"]],
                     "Compatibility matrix incl. NEGATIVE cases (must be rejected)")
        t = v["traces"]
        C.data_table(st, [{"trace": k, "protocol": x.get("protocol"), "group": x.get("group"), "cipher": x.get("cipher"),
                           "bytes read": x.get("bytes_read"), "bytes written": x.get("bytes_written"),
                           "peer signature": x.get("peer_signature_type")} for k, x in t.items() if isinstance(x, dict)],
                     "BEFORE (X25519) vs AFTER (X25519MLKEM768) handshake traces")
        tb = pd.DataFrame({k: {"read": x.get("bytes_read"), "written": x.get("bytes_written")} for k, x in t.items() if isinstance(x, dict)}).T
        st.bar_chart(tb)
        with st.expander("Data behind this chart"):
            st.dataframe(tb)
        o = v["overhead"]
        st.caption(C.escaped_text(f"Overhead method: {o['method']}", 400))
        C.data_table(st, [{"config": k, **{kk: vv for kk, vv in r.items() if not isinstance(vv, (list, dict))}} for k, r in o["results"].items()],
                     "Overhead (median / p95; process start-up dominates; do not quote as network overhead)")
        st.caption(C.escaped_text("Environment: " + ", ".join(f"{k}={o['environment'][k]}" for k in o["environment"]), 400))
    C.footer(st, plan, ev)


def page_approval() -> None:
    plan = L("plan")
    if not C.need(st, plan):
        return
    p = plan.value
    st.write("Only a human approves. The button works only when every required gate passes and you type your name "
             "and the plan hash. There is no 'approve all'.")
    sid = st.selectbox("Step", [s["step_id"] for s in p["steps"]])
    step = next(s for s in p["steps"] if s["step_id"] == sid)
    st.markdown(f"State: {C.badge_md(step['state'])}" + (f" · blocked by: {', '.join(step['blocking_gates'])}" if step["blocking_gates"] else ""))
    name = st.text_input("Approver name")
    typed = st.text_input("Plan hash (first 12+ characters)", help=f"current plan hash starts with {p['plan_hash'][:12]}")
    ok, why = C.can_approve(step, name, typed, p["plan_hash"])
    demo = st.session_state["mode"] == "DEMO"
    if st.button("Approve this step", disabled=not ok or demo):
        from cryptoshift import member3_pipeline as pipe
        from cryptoshift.gates.approval import ApprovalError, approve

        try:
            rec = approve(p, [sid], name, pipe.APPROVALS)
            st.success(f"Recorded approval by {C.escaped_text(rec['approver'], 60)} at {rec['approved_at_utc']} for plan hash {rec['plan_hash'][:12]}.")
        except ApprovalError as exc:
            st.error(C.escaped_text(str(exc), 300))
    st.caption("Disabled in DEMO mode." if demo else ("Ready to approve." if ok else f"Approve disabled: {why}"))
    st.subheader("Rollback plan")
    rb = p["rollback"]
    res = rb.get("rehearsal_result", {})
    C.data_table(st, [{"item": "restore", "value": rb.get("restore")}, {"item": "snapshot sha256", "value": rb.get("snapshot_sha256")},
                      {"item": "trigger", "value": rb.get("trigger")}, {"item": "recovery check", "value": rb.get("recovery_check")},
                      {"item": "rehearsal: forced failure detected", "value": str(res.get("forced_failure_detected"))},
                      {"item": "rehearsal: restored hash matches", "value": str(res.get("restored_hash_matches_snapshot"))},
                      {"item": "rehearsal: classical recovery", "value": str(res.get("recovered"))}])
    for w in rb.get("warnings", []):
        st.warning(C.escaped_text(w, 300))
    st.error("Never restore SHA-1 or 3DES as a 'fix'. A rollback brings back the old risk; plan a forward fix.")
    C.footer(st, plan)


def page_detection() -> None:
    st.write("Labels are **AI-assisted drafts; human review pending**. Each set is shown separately, never as one merged number.")
    rows, used = [], []
    for key, name in (("eval_calibration", "Calibration (development data)"), ("eval_calibration2", "Calibration-2 (seen data, formerly held-out)"),
                      ("eval_held_out", "Held-out round 2 (labelled before the run, frozen detector, run once)")):
        l = L(key)
        used.append(l)
        if l.ok:
            r = l.value
            rows.append({"set": name, "repos": len(r["repositories"]), "positives": r["labels"].get("positive", 0),
                         "TP": r["counts"]["TP"], "FP": r["counts"]["FP"], "FN": r["counts"]["FN"],
                         "precision": r["precision"], "recall": r["recall"], "status": r["status"][:60]})
        else:
            rows.append({"set": name, "status": f"file missing ({l.command})"})
    C.data_table(st, rows)
    h = L("eval_held_out")
    if h.ok:
        st.markdown(f"Held-out recall is **{h.value['recall']}** with 0 false positives: the misses are coverage gaps "
                    "(nginx `.tmpl` templates, cipher lists in Python tuples, JWS names in constructors, Java enums/KeyFactory, "
                    "pyproject dependencies). Not tuned after the run.")
        st.bar_chart(pd.DataFrame(h.value["per_source"]).T.fillna(0))
        with st.expander("Data behind this chart"):
            st.dataframe(pd.DataFrame(h.value["per_source"]).T.fillna(0))
    st.text("Synthetic smoke test (data/fixtures/synthetic): 10 findings, decoy ignored. SYNTHETIC, not a metric.")
    cb = L("eval_cryptoapi")
    used.append(cb)
    st.subheader("CryptoAPI-Bench (Java, mapped subset)")
    if C.need(st, cb):
        st.info(cb.value["sentence"])
        C.data_table(st, [{"group": g, **m} for g, m in cb.value["per_group"].items()] + [{"group": "OVERALL", **cb.value["overall"]}],
                     f"{cb.value['cases_scored']} cases scored; RSA is partial (key size not checked)")
    C.footer(st, *used)


def page_ml_ai() -> None:
    a, b, ag, ags = L("ml_cesnet"), L("ml_triage"), L("agent_eval"), L("agent_eval_sarvam")
    st.subheader("Track A: CESNET service category")
    st.warning("Traffic-classification and scale demo. **Not a PQC model**; these labels are not cryptographic labels.")
    if C.need(st, a):
        m = a.value["metrics"]
        df = pd.DataFrame({k: {"accuracy": v["accuracy"], "macro F1": v["macro_f1"]} for k, v in m.items()}).T
        st.bar_chart(df)
        st.dataframe(df)
    st.subheader("Track B: finding-purpose triage")
    if C.need(st, b):
        df = pd.DataFrame(b.value["metrics_pooled_over_folds"]).T[["accuracy", "macro_f1"]]
        st.dataframe(df)
        st.write(C.escaped_text(b.value["decision"], 300))
    st.subheader("CryptoShift Assistant: cloud LLM (Sarvam) with local read-only tools")
    st.markdown("Cloud AI in this console: " + C.badge_md("BLOCKED") + " **OFF**. Questions here run TEMPLATE_FALLBACK, "
                "so nothing leaves the machine and no credits are used.")
    plan = L("plan")
    if plan.ok:
        from cryptoshift.agent.assistant import Assistant

        q = st.text_input("Ask about the reports", value="Which gates block ledger_audit?")
        if st.button("Ask"):
            r = Assistant(plan.value).answer(q)
            st.markdown(f"Mode: {C.badge_md('VERIFIED')} `{r.get('mode', 'TEMPLATE_FALLBACK')}`" + (" · refused" if r["refused"] else ""))
            st.text(C.escaped_text(r["answer"], 1200))
            st.caption("Citations: " + C.escaped_text(", ".join(r["citations"]), 400))
    if ag.ok:
        rows = [{"run": "TEMPLATE_FALLBACK", "passed (v2)": ag.value["passed"], "passed (v3 stricter)": ag.value["passed"], "cost": "Rs 0"}]
        if ags.ok:
            u = ags.value.get("usage_this_run", {})
            rows.append({"run": f"SARVAM_CLOUD live run ({ags.value['modes']})", "passed (v2)": ags.value["passed"],
                         "passed (v3 stricter)": ags.value.get("v3_passed"),
                         "cost": f"Rs {u.get('estimated_cost_inr')} ({u.get('requests')} requests)"})
        C.data_table(st, rows, "Assistant evaluation, 24 fixed questions")
        if ags.ok:
            st.caption(C.escaped_text(ags.value.get("v3_check_note", ""), 400))
    C.footer(st, a, b, ag, ags)


def page_claims() -> None:
    cl = L("claims")
    st.subheader("Claims we must not make")
    for c in ("production ready", "compliant / certified", "formally verified", "quantum-safe guaranteed",
              "QpiAI or QAOA beats the baseline (they are equal / simulator only)", "the risk score is validated",
              "the detector is validated or the inventory complete (held-out recall 0.116; labels are AI drafts)",
              "the assistant is a local LLM (it is Sarvam cloud with local tools, or a template fallback)",
              "CESNET results say anything about PQC"):
        st.markdown(f"- {C.badge_md('BLOCKED')} {c}")
    st.subheader("Not tested")
    st.write("Real bank systems or networks; per-service integration (KMS, JWT stacks); NIST KAT vectors; network-level "
             "overhead; human label review; screenshots (PLANNED).")
    if C.need(st, cl):
        with st.expander("Claims register (docs/stage0/claims-register.md, read-only)"):
            st.markdown(cl.value)
    C.footer(st, cl)


RENDER = dict(zip(PAGES, [page_overview, page_data, page_inventory, page_dependencies, page_plan, page_verification,
                          page_approval, page_detection, page_ml_ai, page_claims]))


def main() -> None:
    st.set_page_config(page_title="CryptoShift console", page_icon="🔐", layout="wide")
    with st.sidebar:
        st.title("CryptoShift")
        page = st.radio("Page", PAGES, key="page")
        st.divider()
        snap = D.latest_snapshot()
        mode = st.radio("Data", ["LIVE", "DEMO"], key="mode", horizontal=True,
                        help="DEMO reads a frozen snapshot of real outputs (offline).")
        st.markdown("Cloud AI: " + C.badge_md("BLOCKED") + " **OFF**")
        st.caption("Theme: Settings menu (⋮) → light / dark.")
    st.session_state["base"] = D.base_dir(mode)
    if mode == "DEMO":
        st.info(f"Offline demo snapshot: {snap.name if snap else 'none found (showing LIVE data)'}")
    st.warning(BANNER)
    st.header(page)
    RENDER[page]()


if __name__ == "__main__":  # Streamlit runs the script as __main__; importing the module renders nothing
    main()
