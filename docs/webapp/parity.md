# Parity: legacy Streamlit console vs web app v2

Both UIs stay. The legacy one (`scripts\run_ui.ps1`, 127.0.0.1:8501) is the fallback.

| Page / feature | Legacy console | Web app v2 | Parity |
|---|---|---|---|
| Overview pipeline strip and honesty banner | yes | yes, plus Fig. 1 isometric figure and evidence drawer | ✔ exceeds |
| Data & evidence sources | yes | yes | ✔ |
| Inventory table, filters, snippet | yes | yes; sortable, virtualised table and a HOLD filter | ✔ |
| Dependencies graph | matplotlib image + text list | Cytoscape (solid / dashed / dotted) + text list | ✔ |
| Migration plan + scheduler comparison | yes | yes; wave timeline | ✔ |
| Verification (gates, compatibility, traces, overhead) | yes | yes | ✔ |
| Approval | typed name + hash; no auth | typed name + hash + acknowledgement; login, approver role, CSRF, audit | ✔ exceeds |
| Rollback record | yes | yes | ✔ |
| Detection evaluation (separate sets, CryptoAPI-Bench) | yes | yes; per-repo chart | ✔ |
| ML & AI + assistant | template assistant | assistant drawer via the backend proxy; mode badge; Cloud AI ON/OFF | ✔ |
| Claims & limits | yes | yes | ✔ |
| Audit log with tamper check | – | yes | new |
| Settings (data mode, cloud for custom scans) | data mode only | yes | ✔ |
| Run allow-listed commands | yes | yes, as background jobs with status | ✔ |
| Dataset upload → pipeline run → outputs | – | Pipelines → Datasets & runs: folder/zip/files, 3 pipelines, stage progress, results tabs, downloads | new |
| Users & roles | – (command line only) | Admin → Users & roles: add, change role, disable, reset password; audited | new |
| Printable report (PDF) | – | Pipelines → Reports: browser print to PDF | new |
| Activity feed + bell | – | top bar bell with unread count; Platform → Activity | new |
| Folder scan of an allow-listed root | – | API only (`/api/v1/scans`); dataset upload covers the UI need | PARTIAL |
| Markdown / JSON export | – | yes (command palette) | new |
| Themes + accessibility modes | light/dark via Streamlit | dark/light, reduced transparency, high contrast, reduced motion | ✔ exceeds |
