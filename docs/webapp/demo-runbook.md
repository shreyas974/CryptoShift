# 5-minute demo runbook (only features that worked in the recorded runs)

Before you start:
1. Run `scripts\run_full_demo.ps1 start` and sign in as an approver.
2. Optional: freeze a snapshot (`scripts/ui_snapshot.py`). If the network or a script fails, switch to Settings → DEMO.

| Time | Page | Show | Verified by |
|---|---|---|---|
| 0:00 | Overview | Honesty banner; the pipeline strip (each stage's status badge from the backend); Fig. 1 "Sorting line": crates in their real waves; the readout cycles through real services; the gate boom lifts only for READY; the stamp stays up (0 approved). Hover a crate or use the arrow keys. | E2E "overview…", "anatomy figure…" |
| 0:40 | Overview → ⓘ next to Findings | The evidence drawer: file, producer, label, SHA-256, regenerate command | E2E "evidence drawer…" |
| 1:00 | Inventory | Tick "Only HOLD": RSA key type with unknown purpose, so HOLD. Click the row to see the escaped snippet and rationale. | E2E demo path |
| 1:30 | Dependencies | OBSERVED solid, DECLARED dashed, INFERRED dotted; the text edge list with file:line; conflicts | E2E demo path |
| 2:00 | Migration plan | Wave timeline; baseline 299.1 = QpiAI Opt local solve 299.1 (**equal, not better**); QAOA **SIMULATOR**, P(opt) 0.085 vs uniform 0.0625 | E2E demo path |
| 2:40 | Verification | Gate matrix; compatibility matrix with negative cases; X25519 vs X25519MLKEM768 traces; overhead (loopback only) | E2E demo path |
| 3:20 | Approval & rollback | Review a PROPOSED step: Approve stays disabled. Review a READY step: it enables only after name + plan-hash prefix + acknowledgement. Rollback rehearsal and the 3DES warning. | E2E "approval dialog…" (the button is never clicked in tests) |
| 4:00 | Audit log | "Verify chain" gives PASS | pytest audit tests |
| 4:15 | ML & AI | CESNET "not a PQC model"; triage loses to the rules; ask the assistant to show the mode badge and Cloud AI OFF | E2E "viewer… assistant…" |
| 4:45 | Claims & limits | What we do not claim | E2E demo path |

Keyboard: Ctrl+K opens the palette ("Go to Verification", theme and accessibility toggles, exports).

**Fallback:**
- **DEMO mode:** the frozen snapshot works offline.
- **Screenshots:** `docs/webapp/screens/*.png`, captured by Playwright in the recorded run.
- **Legacy console:** `scripts\run_ui.ps1 start`.
- **Last resort:** `reports/member3/summary.md`.
