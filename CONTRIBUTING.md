# Contributing to CryptoShift

Thank you for working on **CryptoShift (Quant-A-Maze 3.0 — PQC-01: Verification-Gated Cryptographic Migration Across Banking Applications)**. Follow this concise workflow to keep the repository reproducible, accurate, and secret-free.

---

## 1. Canonical Package Layout

- Keep all Python package code under `src/cryptoshift/`. Do **not** recreate a duplicate top-level `cryptoshift/` package.
- Run commands using the project virtual environment (`.venv`). Do not install dependencies globally.

```powershell
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

---

## 2. Secret & Credential Hygiene

1. **Never commit secrets:** `.env`, `.env.local`, `qcloud.env`, `*.key`, `*.pem`, and `.venv/` must remain in [.gitignore](.gitignore).
2. **Templates only:** `.env.example` and `qcloud.env.example` must contain blank placeholders only.
3. **No echoing secrets:** Never print, log, or include API keys or tokens in terminal output, exception strings, or committed reports.
4. **Pre-commit scan:** Always run the repository hygiene check before committing:
   ```powershell
   .\.venv\Scripts\python.exe scripts/verify_repo.py
   ```

---

## 3. Technical & Reporting Standards

- **Algorithm roles:** Map **ML-KEM (FIPS 203)** strictly to key establishment/encapsulation, and **ML-DSA (FIPS 204)** / **SLH-DSA (FIPS 205)** strictly to digital signatures. If a finding's operation purpose is unknown, hold automatic mapping for human review.
- **Honest labeling:** Clearly label synthetic banking fixtures (`demo_bank_app/`, `data/fixtures/synthetic/`), mocked/modelled protocol traces (`src/cryptoshift/protocol_demo.py`), and classical statevector simulator results (`QpiAI-QSV-Local`).
- **No unapproved paid execution:** Keep QpiAI Opt in `mode="local"` and QpiAI Quantum on `QpiAI-QSV-Local`. Never call `mode="platform"`, `submit()`, or hardware QPUs without explicit owner authorization.

