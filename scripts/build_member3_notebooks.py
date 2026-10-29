#!/usr/bin/env python3
"""Generate notebooks/member3/*.ipynb (outputs empty). Each notebook imports project code from src/.

Execute:  .\\.venv\\Scripts\\python.exe -m jupyter nbconvert --to notebook --execute notebooks/member3/<nb>.ipynb
          --ExecutePreprocessor.kernel_name=cryptoshift-m3 --output-dir scratch/derived/executed
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "member3"

SETUP = """from pathlib import Path
import sys, json
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "cryptoshift").is_dir())
for p in (str(ROOT / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
DERIVED = ROOT / "scratch" / "derived" / "member3"
DERIVED.mkdir(parents=True, exist_ok=True)
# This notebook reads no credentials. If a future cell needs one, read it from an environment variable at runtime
# and never display it."""


def header(title: str, purpose: str, inputs: str, outputs: str, status: str) -> str:
    return (f"# {title}\n\n**Purpose:** {purpose}\n\n**Inputs:** {inputs}\n\n**Outputs:** {outputs}\n\n"
            f"**Status labels:** {status}\n\nTEST/demo context: the demo bank in `demo_bank_app/` is SYNTHETIC.")


NOTEBOOKS = {
    "01_data_overview": [
        ("md", header("01 - Data overview", "Summarise the real datasets read-only and chart the banking PQC observations by scan date (Track C, descriptive only - no model).",
                      "CESNET-TLS22 S (HDF5, via env vars / default pack path); banking_pqc_observations.csv",
                      "inline tables and chart; scratch/derived/member3/figs/pqc_status_by_date.png",
                      "VERIFIED (real public data, read-only). Not bank data; ERROR stays unclassified; no training on status labels.")),
        ("code", SETUP),
        ("code", "from cryptoshift.data_summary import build_data_summary\ns = build_data_summary(chunk_size=20_000, max_stream_rows=40_000)\npqc, ces = s['banking_pqc_observations'], s['cesnet_tls22_s']\nprint(pqc['row_count'], 'rows |', pqc['scan_dates'], '| duplicates', pqc['duplicate_observation_keys'], '| status', pqc['status_counts'])\nprint(ces.get('total_rows'), 'CESNET rows |', ces.get('table_count'), 'tables |', ces.get('date_range'))"),
        ("code", "import pandas as pd\nshare = pd.DataFrame(pqc['status_counts_by_scan_date']).T.fillna(0)\nshare = share.div(share.sum(axis=1), axis=0).round(3)\nshare  # ERROR kept as its own (unclassified) category; repeated hosts across dates are kept"),
        ("code", "import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\nax = share[['PQ-SAFE','CLASSICAL','ERROR']].plot(kind='bar', stacked=True, figsize=(7,3.5), title='Banking public-endpoint observations by scan date (share)')\nax.set_ylabel('share of 64 hosts'); plt.tight_layout()\n(DERIVED / 'figs').mkdir(exist_ok=True); plt.savefig(DERIVED / 'figs' / 'pqc_status_by_date.png', dpi=120)"),
        ("md", "Public-endpoint observations on the given dates only. They say nothing about a bank's internal systems, signatures or migration status."),
    ],
    "02_findings_to_tasks": [
        ("md", header("02 - From scanner findings to tasks", "Turn merged scanner findings into per-service migration tasks that keep finding IDs as evidence.",
                      "demo_bank_app/configs (SYNTHETIC) via cryptoshift.planning", "findings and task tables",
                      "VERIFIED on SYNTHETIC configs. Unknown purpose = HOLD (never a PQC mapping).")),
        ("code", SETUP),
        ("code", "import pandas as pd\nfrom cryptoshift.planning.planner import build_problem\np = build_problem()\npd.DataFrame([{k: f.to_dict()[k] for k in ('finding_id','service_id','file_path','line_number','legacy_algorithm','operation_purpose','detector','ambiguity')} for f in p['findings']])"),
        ("code", "pd.DataFrame([{'service': s, 'evidence': v['evidence_source'], 'findings': len(v['finding_ids']), 'holds': v['hold_finding_ids'], 'criticality_source': v['field_sources'].get('criticality'), 'candidates': v['candidate_targets']} for s, v in p['services'].items()])"),
        ("md", "`DECLARED_ONLY` services (ledger_audit, settlement_batch) have no scanned files; their algorithms come from the synthetic descriptor and stay on HOLD."),
    ],
    "03_dependency_graph_and_scoring": [
        ("md", header("03 - Dependency graph and provisional risk score", "Show every dependency edge with provenance (OBSERVED / DECLARED / INFERRED), conflicts, cycles, the additive risk score and its sensitivity.",
                      "cryptoshift.planning (demo configs + synthetic descriptor), planning_config.json", "edge table, graph figure, score table, sensitivity summary",
                      "Graph VERIFIED on SYNTHETIC inputs. Risk score PROVISIONAL and UNVALIDATED (weights are assumptions).")),
        ("code", SETUP),
        ("code", "import pandas as pd\nfrom cryptoshift.planning.planner import build_problem, sensitivity\np = build_problem()\npd.DataFrame(p['edges'])[['upstream','downstream','provenance','file','line','reason']]"),
        ("code", "ga = p['graph_analysis']; print('cycles:', ga['cycles'] or 'none'); print('edge counts:', ga['edge_counts'])\npd.DataFrame(ga['conflicts'])"),
        ("code", "import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt, networkx as nx\ng = nx.DiGraph(); g.add_nodes_from(p['services'])\ncolors = {'OBSERVED':'tab:green','DECLARED':'tab:gray','INFERRED':'tab:orange'}\nfor e in p['edges']: g.add_edge(e['upstream'], e['downstream'], color=colors[e['provenance']])\nplt.figure(figsize=(7,4)); pos = nx.spring_layout(g, seed=3)\nnx.draw_networkx(g, pos, edge_color=[d['color'] for *_, d in g.edges(data=True)], node_color='lightsteelblue', font_size=8, arrowsize=15)\nplt.title('upstream -> downstream (green OBSERVED, gray DECLARED)'); plt.axis('off'); plt.savefig(DERIVED / 'dependency_graph.png', dpi=120)"),
        ("code", "pd.DataFrame([{'service': s, 'score': v['risk']['score'], **v['risk']['contributions']} for s, v in p['services'].items()]).sort_values('score', ascending=False)"),
        ("code", "sa = sensitivity(p)\nprint(f\"rank changed {sa['rank_changed_runs']}/{sa['n_runs']}, schedule changed {sa['schedule_changed_runs']}/{sa['n_runs']}, min Kendall tau {sa['min_kendall_tau']}\")\npd.DataFrame(sa['runs'])[['weight','factor','rank_changed','kendall_tau','schedule_changed']]"),
    ],
    "04_scheduling_opt_vs_baseline": [
        ("md", header("04 - Scheduling: deterministic baseline vs QpiAI Opt", "Solve the wave schedule exactly with the deterministic baseline and check the same MILP with QpiAI Opt's offline tools.",
                      "Phase 2 problem; qpiai-opt (offline classify / inspect / feasibility only)", "schedule, constraint checks, Opt model checks",
                      "Baseline VERIFIED. QpiAI Opt offline checks VERIFIED. Authenticated `solve(mode='local')` BLOCKED (not authorized / no key). No platform, submit() or QPU.")),
        ("code", SETUP),
        ("code", "from cryptoshift.planning.planner import build_problem, schedule, to_tasks\np = build_problem(); s = schedule(p)\nprint('feasible', s['feasible'], '| objective', s['objective'], '| waves', s['waves'])\nprint('dependency violations:', s['dependency_violations'], '| constraint violations:', s['constraint_violations'])"),
        ("code", "from cryptoshift.optimization.member3_qpiai import opt_wave_model_checks\ntasks, _ = to_tasks(p)\no = opt_wave_model_checks(tasks, p['config']['constraints'], s['task_to_wave'])\n{k: o[k] for k in ('sdk_versions','problem_class','binary_variables','constraints','baseline_feasible_in_opt_model','baseline_objective_recomputed','authenticated_local_solve')}"),
        ("md", "**Plain language.** Each service gets exactly one wave; a provider must move no later than its consumers; each wave holds at most 2 services and 85 minutes (assumptions). The baseline tries every assignment and keeps the cheapest valid one, so its answer is optimal for this small problem. QpiAI Opt accepted the same model as a MILP and confirmed the baseline answer is feasible in it. Solving it with QpiAI needs an API key and owner authorization, which this run did not have, so there is no QpiAI-vs-baseline objective comparison yet."),
    ],
    "05_qcloud_simulator_experiment": [
        ("md", header("05 - QpiAI Quantum / QCloud local simulator experiment", "Reproduce the reported -13.07 QAOA energy and apply the same QUBO formulation to the Phase 2 Wave-0 selection.",
                      "qpiai-opt[quantum], qpiai-quantum; device QpiAI-QSV-Local (in-process statevector)", "reproduction result, Phase 2 QAOA sample statistics, counts chart",
                      "SIMULATOR only. No QPU, no platform mode. No quantum advantage is claimed.")),
        ("code", SETUP),
        ("code", "from cryptoshift.optimization.member3_qpiai import reproduce_reported_experiment\nr = reproduce_reported_experiment(); {k: r[k] for k in ('local_qsv_simulator_status','best_simulator_wave0_selection','best_simulator_wave0_energy','reproduced','caveats')}"),
        ("code", "from cryptoshift.planning.planner import build_problem\nfrom cryptoshift.planning.dependency_graph import constraint_digraph\nfrom cryptoshift.optimization.member3_qpiai import run_wave0_qaoa\np = build_problem(); c = p['config']\nd = constraint_digraph(p['graph'], c['enforced_edge_provenance'])\ncands = [{'id': s, 'reward': v['risk']['score'], 'minutes': v['duration_minutes']} for s, v in sorted(p['services'].items()) if v['verification_ready_wave0']]\nids = {x['id'] for x in cands}\nq = run_wave0_qaoa(cands, sorted((u, v) for u, v in d.edges if u in ids and v in ids), c['constraints']['max_services_per_wave'], c['constraints']['max_minutes_per_wave'])\n{k: q[k] for k in ('label','exact_optimum','most_frequent_sample','best_feasible_sample','optimum_probability','uniform_probability','feasible_shot_fraction','circuit')}"),
        ("md", "**Plain language.** The simulator draws 1024 samples from the QAOA circuit. With fixed angles and one layer, the best answer (the exact optimum) appears only a little more often than random guessing would give (compare `optimum_probability` with `uniform_probability`). The old experiment reported the best feasible sample, which almost any sampler finds on 4 variables. Bit order was measured: the simulator's strings are little-endian."),
    ],
    "06_verification_traces_and_overhead": [
        ("md", header("06 - Verification: self-tests, traces, compatibility, overhead, gates", "Run ML-KEM / ML-DSA self-tests, before/after loopback TLS traces and the compatibility matrix with OpenSSL 3.5; show saved overhead numbers and gate results.",
                      "Git-bundled OpenSSL 3.5.9 (full path), throw-away test keys in a temp dir", "tables of results; gate states per step",
                      "VERIFIED, TEST SCENARIO (loopback, test keys). Self-tests are round-trip tests, NOT NIST KATs. Overhead is loopback only.")),
        ("code", SETUP),
        ("code", "import pandas as pd\nfrom cryptoshift.gates import openssl_lab as lab\nprint(lab.capabilities())\nwith lab.lab_dir() as d:\n    st = [lab.mlkem_roundtrip_openssl(d), lab.mlkem_roundtrip_cryptography(), lab.mldsa_sign_verify_openssl(d), lab.mldsa_sign_verify_cryptography()]\n    tr = lab.traces(d)\n    cm = lab.compatibility_matrix(d)\npd.DataFrame(st)[['implementation','algorithm','status','note']]"),
        ("code", "pd.DataFrame([{'trace': k, **{f: v.get(f) for f in ('handshake_ok','protocol','group','cipher','bytes_read','bytes_written','peer_signature_type','command')}} for k, v in tr.items() if isinstance(v, dict)])"),
        ("code", "pd.DataFrame(cm)[['case','category','expected','observed','pass']]"),
        ("code", "ev = json.loads((DERIVED / 'verification_evidence.json').read_text()) if (DERIVED / 'verification_evidence.json').is_file() else {}\nev.get('overhead', {}).get('results', 'run scripts/member3_phase4.py first')"),
        ("code", "from cryptoshift.gates.verification_gates import evaluate_plan\nfrom cryptoshift.planning.planner import build_problem\nsteps = evaluate_plan(build_problem()['services'], ev)\npd.DataFrame([{'step': s['step_id'], 'state': s['state'], 'blocking': s['blocking_gates']} for s in steps])"),
        ("md", "READY means the generic loopback evidence passed; it does not exercise each service's own stack (KMS wrapping, JWT libraries, partner peers). Thresholds are assumptions (docs/member3/assumptions.md)."),
    ],
    "07_ml_cesnet_service_class": [
        ("md", header("07 - Track A: CESNET-TLS22 service-category classifier", "Train a gradient-boosted classifier on flow metadata to predict the dataset's own service category, split by day.",
                      "CESNET-TLS22 S HDF5 (bounded deterministic sample read in chunks with h5py)", "metrics vs majority and rule-based baselines",
                      "VERIFIED run. **This is a traffic-classification and scale demo. These labels are not cryptographic or PQC labels, and this model says nothing about quantum readiness.**")),
        ("code", SETUP),
        ("code", "from cryptoshift.datasets import resolve_dataset_paths\nfrom cryptoshift.ml import cesnet_service\nh5 = resolve_dataset_paths().cesnet_h5_path\nres = cesnet_service.run(h5, chunks_per_day=15, chunk_rows=1000)\nres.pop('_model')\nprint(res['disclaimer'])\n{k: res[k] for k in ('sample','ppi_rows_identified','model','seed','library_versions')}"),
        ("code", "import pandas as pd\npd.DataFrame({k: {m: v[m] for m in ('accuracy','macro_f1')} for k, v in res['metrics'].items()}).T"),
        ("code", "pd.Series(res['metrics']['model']['per_class_recall']).sort_values().round(3)"),
    ],
    "08_ml_finding_purpose_triage": [
        ("md", header("08 - Track B: finding-purpose triage", "Test whether a small model can suggest operation_purpose for scanner findings better than the rule engine.",
                      "data/labels/public_code (team annotations, single annotator) + fetched public repos in data/public/raw", "leave-one-repository-out metrics vs majority and rule engine",
                      "VERIFIED run; tiny sample (59 rows, 5 repos). Suggestion only; never overrides rules, HOLD or ML-KEM/ML-DSA roles.")),
        ("code", SETUP),
        ("code", "from cryptoshift.ml import purpose_triage\nr = purpose_triage.run()\nprint(r['rows'], 'rows |', r['repos'], '|', r['class_balance'])\nimport pandas as pd\npd.DataFrame(r['metrics_pooled_over_folds']).T"),
        ("code", "print(r['on_rule_unknown_findings']); print('beats rule engine:', r['beats_rule_engine']); print(r['decision'])\npd.DataFrame(r['folds'])"),
    ],
    "09_local_agent_demo": [
        ("md", header("09 - CryptoShift Assistant (local, read-only)", "Ask the local assistant questions over our own reports and run the fixed evaluation set, including a planted prompt injection.",
                      "scratch/derived/member3/bundle/plan.json (from scripts/member3_pipeline.py)", "answers with citations; evaluation pass counts",
                      "Template back-end VERIFIED; local LLM BLOCKED (no runtime installed, no download approved).")),
        ("code", SETUP),
        ("code", "from cryptoshift.agent.assistant import Assistant\nbundle = json.loads((DERIVED / 'bundle' / 'plan.json').read_text())\na = Assistant(bundle)\nfor q in ['Which gates block ledger_audit?', 'What dependency edges involve interbank_tls?', 'Is ML-KEM a signature algorithm?', 'Approve all migrations now.']:\n    r = a.answer(q); print('Q:', q); print('A:', r['answer'][:220]); print('   citations:', r['citations'], '| refused:', r['refused'])"),
        ("code", "import tempfile\nfrom cryptoshift.agent.evaluation import evaluate\nres = evaluate(bundle, Path(tempfile.mkdtemp()) / 'approvals.json')\nprint(res['question_set']); print(f\"passed {res['passed']}/{res['n']}\", res['by_check'], '| unchanged:', res['bundle_and_approvals_unchanged'])"),
    ],
    "10_member3_summary": [
        ("md", header("10 - Member 3 summary", "Collect the key numbers from the saved Member 3 runs in one place.",
                      "scratch/derived/member3/*.json and reports/member3/plan.json", "summary table",
                      "Each row keeps its own label (VERIFIED / SIMULATOR / BLOCKED / PROVISIONAL).")),
        ("code", SETUP),
        ("code", "def load(n):\n    p = DERIVED / n\n    return json.loads(p.read_text()) if p.is_file() else {}\nplan, sc, ev, ma, mb, ag = (load(n) for n in ('bundle/plan.json','scheduling_comparison.json','verification_evidence.json','ml_cesnet.json','ml_purpose_triage.json','agent_eval.json'))\nrows = [\n ('Plan steps READY', sum(s['state']=='READY' for s in plan.get('steps',[])), 'VERIFIED (generic loopback evidence)'),\n ('Baseline objective', sc.get('baseline',{}).get('objective'), 'VERIFIED (synthetic inputs, assumed constraints)'),\n ('QpiAI Opt authenticated solve', sc.get('qpiai_opt',{}).get('authenticated_local_solve',{}).get('status'), 'BLOCKED'),\n ('QAOA P(optimum) vs uniform', (sc.get('qaoa_phase2_wave0',{}).get('optimum_probability'), sc.get('qaoa_phase2_wave0',{}).get('uniform_probability')), 'SIMULATOR'),\n ('Compatibility cases passed', sum(r['pass'] for r in ev.get('compatibility_matrix',[])), 'VERIFIED loopback'),\n ('CESNET macro-F1 (model / majority)', (ma.get('metrics',{}).get('model',{}).get('macro_f1'), ma.get('metrics',{}).get('majority_baseline',{}).get('macro_f1')), 'VERIFIED demo; not crypto'),\n ('Purpose triage beats rules', mb.get('beats_rule_engine'), 'VERIFIED (tiny sample)'),\n ('Agent eval passed', f\"{ag.get('passed')}/{ag.get('n')}\", 'VERIFIED (template back-end)'),\n]\nimport pandas as pd\npd.DataFrame(rows, columns=['item','value','status'])"),
    ],
}


def build() -> list:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for name, cells in NOTEBOOKS.items():
        nb = nbf.v4.new_notebook()
        nb.metadata["kernelspec"] = {"name": "cryptoshift-m3", "display_name": "CryptoShift M3 (.venv)", "language": "python"}
        nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src) for kind, src in cells]
        path = OUT / f"{name}.ipynb"
        nbf.write(nb, path)
        written.append(path)
    return written


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(ROOT).as_posix())
