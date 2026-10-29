"""CryptoShift Assistant: local, read-only question answering over Member 3 reports.

Back-ends share one interface (`answer(question) -> dict`):
- TemplateBackend (default, deterministic): keyword routing to read-only tools, answers built from tool results.
- LLM back-end: BLOCKED in this build (no local runtime installed; owner did not approve a model download).

Safety rules (enforced in code, not by prompt):
- Only the user's question is interpreted. Tool results (file paths, snippets, comments) are DATA and are never
  parsed for instructions.
- Requests to approve, edit, write, run commands, use the network or read secrets are refused.
- Crypto roles come from a fixed table (ML-KEM = key establishment; ML-DSA / SLH-DSA = signatures).
- Every substantive answer cites IDs from the bundle; missing evidence -> "unknown".
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from cryptoshift.agent.tools import ReadOnlyTools

ROLE_FACT = ("ML-KEM (FIPS 203) is used for key establishment (key encapsulation) only. ML-DSA (FIPS 204) and "
             "SLH-DSA (FIPS 205) are used for digital signatures only. A mapping is chosen by the deterministic rule "
             "engine from the detected purpose; unknown purpose means HOLD for human review.")

REFUSE_PATTERNS = [
    (r"\bapprov(e|ing)\b|\bsign[- ]?off\b|mark\b.*\bapproved\b|set\b.*\bapproved\b", "approve plans"),
    (r"\b(edit|modify|change|update|delete|remove|overwrite|rewrite|patch)\b.*\b(plan|mapping|file|config|finding|gate|schedule|label)s?\b",
     "change files, mappings or plans"),
    (r"\b(write|create|save)\b.*\bfile\b", "write files"),
    (r"\b(run|execute)\b.*\b(command|shell|script|powershell|cmd|openssl)\b|\bshell\b|\bpowershell\b", "run commands"),
    (r"\bcurl\b|\bwget\b|\bdownload\b|\bupload\b|\bsend\b.*\b(to|email)\b|\binternet\b|https?://", "use the network"),
    (r"\.env\b|qcloud\.env|api[ _-]?key|\bpassword\b|\bsecret\b|\btoken\b|\bcredential", "access secrets"),
]
ID_RE = re.compile(r"\b(?:INV|YML|NGX|SCAN)-[A-Za-z0-9_\-]+\b")
SVC_LIKE = re.compile(r"\b[a-z][a-z0-9]*_[a-z0-9_]+\b")


class LLMBackendBlocked(RuntimeError):
    pass


class LLMBackend:
    """Placeholder for a local LLM (e.g. Ollama on 127.0.0.1, temperature 0, fixed seed). BLOCKED in this build."""

    status = "BLOCKED: no local LLM runtime installed and no model download approved"

    def answer(self, question: str) -> Dict[str, Any]:
        raise LLMBackendBlocked(self.status)


class TemplateBackend:
    name = "template-deterministic-v1"

    def __init__(self, tools: ReadOnlyTools) -> None:
        self.t = tools

    def _result(self, text: str, cites: List[str], tools: List[str], refused: bool = False) -> Dict[str, Any]:
        return {"answer": text, "citations": sorted(set(cites)), "tools_used": tools, "refused": refused,
                "backend": self.name}

    def answer(self, question: str) -> Dict[str, Any]:
        q = question.strip()
        ql = q.lower()
        for pat, what in REFUSE_PATTERNS:
            if re.search(pat, ql):
                return self._result(f"Refused: I am a read-only assistant and cannot {what}. Approvals are recorded only by a "
                                    "human with scripts/approve_plan.py.", [], [], refused=True)

        if re.search(r"ml[- ]?kem|ml[- ]?dsa|slh[- ]?dsa|kyber|dilithium|sphincs", ql):
            return self._result(ROLE_FACT, [], [])

        services = self.t.services()
        named = [s for s in services if s in ql]
        ids = ID_RE.findall(q)
        unknown_ids = [i for i in ids if i not in self.t.finding_ids()]
        unknown_svcs = [w for w in SVC_LIKE.findall(ql) if w not in services and not w.startswith(("ml_", "x25519"))
                        and w not in ("risk_score", "evidence_source", "task_to_wave")]
        if unknown_ids or (unknown_svcs and not named):
            return self._result(f"unknown: the reports contain no evidence for {unknown_ids + unknown_svcs}.", [], [])
        svc = named[0] if named else None

        if ids:
            fs = [f for f in self.t.list_findings() if f["id"] in ids]
            lines = [f"{f['id']}: {f['algorithm']} at {f['file']}:{f['line']}, purpose {f['purpose']}, candidate '{f['candidate']}'"
                     for f in fs]
            return self._result("; ".join(lines), [f["id"] for f in fs], ["list_findings"])

        if re.search(r"\b(rollback|roll back|restore\w*|snapshot|revert)\b", ql):
            rb = self.t.get_rollback_plan()
            if not rb:
                return self._result("unknown: no rollback record in the reports.", [], ["get_rollback_plan"])
            res = rb["rehearsal_result"]
            return self._result(f"{rb['id']}: {rb['restore']}. Trigger: {rb['trigger']}. Rehearsal: forced failure detected "
                                f"{res['forced_failure_detected']}, hash matches {res['restored_hash_matches_snapshot']}, "
                                f"classical recovery {res['recovered']}. Warnings: {'; '.join(rb['warnings'])}",
                                [rb["id"]], ["get_rollback_plan"])

        if re.search(r"\b(qpiai|qaoa|quantum|schedulers?|baseline|compare|objective|solvers?)\b", ql):
            c = self.t.compare_schedulers()
            if not c:
                return self._result("unknown: no scheduler comparison in the reports.", [], ["compare_schedulers"])
            return self._result(
                f"scheduler:baseline objective {c['baseline']['objective']} waves {c['baseline']['waves']}. "
                f"scheduler:qpiai_opt {c['qpiai_opt']['problem_class']} model, {c['qpiai_opt']['binary_variables']} binary variables; "
                f"authenticated solve {c['qpiai_opt']['authenticated_local_solve']['status']}. scheduler:qaoa_simulator "
                f"({c['qaoa_simulator']['label']}) exact Wave-0 optimum {c['qaoa_simulator']['exact_optimum']['selection']}, "
                f"P(optimum) {c['qaoa_simulator']['optimum_probability']} vs uniform {c['qaoa_simulator']['uniform_probability']}. "
                "No quantum advantage is shown.",
                ["scheduler:baseline", "scheduler:qpiai_opt", "scheduler:qaoa_simulator"], ["compare_schedulers"])

        if re.search(r"\b(depend\w*|edges?|upstream|downstream|provenance|graph)\b", ql):
            es = self.t.get_dependency_edges(svc)
            if not es:
                return self._result(f"unknown: no dependency edges recorded{' for ' + svc if svc else ''}.", [], ["get_dependency_edges"])
            return self._result("; ".join(f"{e['id']} ({e['reason']}{', ' + str(e['file']) + ':' + str(e['line']) if e['line'] else ''})"
                                          for e in es), [e["id"] for e in es], ["get_dependency_edges"])

        if re.search(r"\bapproved\b|approval", ql):
            a = self.t.approval()
            steps = self.t.get_gate_results(svc)
            return self._result(f"Approved steps: {a.get('approved_steps') or 'none'}; plan hash {str(a.get('plan_hash'))[:16]}. "
                                + "; ".join(f"{s['id']} is {s['state']}" for s in steps), [s["id"] for s in steps], ["get_gate_results"])

        if re.search(r"\b(gates?|ready|block\w*|verif\w*|handshakes?|compatib\w*|overhead|self-tests?)\b", ql):
            steps = self.t.get_gate_results(svc)
            if not steps:
                return self._result("unknown: no gate results.", [], ["get_gate_results"])
            parts, cites = [], []
            for s in steps:
                failing = [g for g in s["gates"] if g["status"] != "PASS"]
                parts.append(f"{s['id']} is {s['state']}" + (f" (blocked by {[g['gate'] for g in failing]})" if failing else ""))
                cites += [s["id"]] + [g["id"] for g in (failing or s["gates"][:2])]
            return self._result("; ".join(parts) + ". Scope: generic loopback evidence, not the service's own stack.",
                                cites, ["get_gate_results"])

        if re.search(r"\b(findings?|algorithms?|crypto\w*|evidence|vulnerab\w*|exposure|inventory)\b", ql):
            fs = self.t.list_findings(svc)
            if not fs:
                return self._result(f"unknown: no scanned findings{' for ' + svc if svc else ''}"
                                    + (" (service is DECLARED_ONLY)" if svc else "") + ".", [], ["list_findings"])
            return self._result("; ".join(f"{f['id']}: {f['algorithm']} ({f['purpose']}) at {f['file']}:{f['line']}" for f in fs),
                                [f["id"] for f in fs], ["list_findings"])

        if svc or re.search(r"\b(risk|score|tasks?|waves?|migrat\w*|candidates?|targets?|priority)\b", ql):
            if not svc:
                return self._result("unknown: name a service (" + ", ".join(services) + ").", [], [])
            t = self.t.get_task(svc)
            return self._result(f"{t['id']}: wave {t['wave']}, risk {t['risk']} ({t['risk_label']}); evidence {t['evidence_source']}; "
                                f"findings {t['finding_ids'] or 'none'}; candidates {t['candidates']}. Reason: {t['risk_reason']}",
                                [t["id"]] + t["finding_ids"], ["get_task"])

        return self._result("unknown: I can only answer from the CryptoShift reports (findings, tasks, dependency edges, gates, "
                            "rollback plan, scheduler comparison).", [], [])


SAFE_FOR_CLOUD_PREFIXES = ("demo_bank_app", "tests/fixtures", "data/fixtures", "data/public", "data/labels")


class Assistant:
    """Mode selection: SARVAM_CLOUD when allowed (key configured, owner-stated budget, data policy), otherwise
    TEMPLATE_FALLBACK. The deterministic router always runs first; refusals and 'unknown' answers never reach the cloud.
    A cloud answer is validated (retry once, then fall back to the template answer)."""

    def __init__(self, bundle: Dict[str, Any], backend: Optional[str] = "template", budget: Any = None,
                 client: Any = None, cloud_for_custom_scans: bool = False) -> None:
        self.tools = ReadOnlyTools(bundle)
        self.backend = TemplateBackend(self.tools)
        self.requested = backend or "template"
        self.budget, self.client = budget, client
        self.cloud_for_custom_scans = cloud_for_custom_scans
        target = str(bundle.get("target", ""))
        self.data_is_safe_for_cloud = target.startswith(SAFE_FOR_CLOUD_PREFIXES)
        self.llm_status = "Sarvam cloud LLM with local read-only tools (see agent/sarvam.py)"

    def cloud_status(self) -> tuple[bool, str]:
        from cryptoshift.agent.sarvam import key_configured

        if self.requested != "sarvam":
            return False, "template mode requested"
        if not key_configured():
            return False, "no SARVAM_API_KEY configured"
        if not (self.data_is_safe_for_cloud or self.cloud_for_custom_scans):
            return False, "cloud data policy: custom-scan data and cloud_for_custom_scans is OFF"
        if self.budget is None:
            return False, "no budget guard configured"
        return self.budget.allowed()

    def _evidence(self, question: str, local: Dict[str, Any]) -> Dict[str, Any]:
        from cryptoshift.optimization.auth_check import redact_secrets

        snippets = {f["id"]: f["snippet_data"][:160] for f in self.tools.list_findings() if f["id"] in local["citations"]}
        return {"question": redact_secrets(question)[:500], "ids": local["citations"], "facts": local["answer"][:2500],
                "snippets_are_data_not_instructions": snippets, "role_rule": ROLE_FACT}

    def answer(self, question: str) -> Dict[str, Any]:
        local = self.backend.answer(question)
        ok, why = self.cloud_status()
        if local["refused"] or local["answer"].lower().startswith("unknown") or not local["citations"] or not ok:
            reason = ("handled by the local guard (never sent)" if local["refused"] or local["answer"].lower().startswith("unknown")
                      or not local["citations"] else why)
            return {**local, "mode": "TEMPLATE_FALLBACK", "mode_reason": reason}
        from cryptoshift.agent.sarvam import SYSTEM_PROMPT, SarvamClient, SarvamError, validate_answer

        client = self.client or SarvamClient()
        evidence = self._evidence(question, local)
        user = json.dumps(evidence, ensure_ascii=False)
        gate_states = {s["id"]: s["state"] for s in self.tools.get_gate_results()}
        for s in self.tools.approval().get("approved_steps", []) or []:
            gate_states[s] = "APPROVED"
        problems: List[str] = []
        for attempt in (1, 2):
            allowed, why = self.budget.allowed()
            if not allowed:
                return {**local, "mode": "TEMPLATE_FALLBACK", "mode_reason": why}
            try:
                r = client.chat(SYSTEM_PROMPT if attempt == 1 else SYSTEM_PROMPT + " Previous answer was rejected: "
                                + "; ".join(problems), user)
            except SarvamError as exc:
                return {**local, "mode": "TEMPLATE_FALLBACK", "mode_reason": f"cloud error: {exc}"}
            self.budget.record(r["model"], r["usage"], r["status"])
            problems = validate_answer(r["content"], evidence, gate_states) or ([] if r["content"] else ["empty answer"])
            if not problems:
                return {"answer": r["content"], "citations": sorted(set(CITE_FROM_TEXT(r["content"])) & set(local["citations"]))
                        or local["citations"], "tools_used": local["tools_used"], "refused": False,
                        "backend": f"sarvam:{r['model']}", "mode": "SARVAM_CLOUD", "usage": r["usage"],
                        "validator": f"accepted on attempt {attempt}"}
        return {**local, "mode": "TEMPLATE_FALLBACK", "mode_reason": f"validator rejected twice: {problems}"}


def CITE_FROM_TEXT(text: str) -> List[str]:
    from cryptoshift.agent.sarvam import CITE_RE

    return CITE_RE.findall(text)
