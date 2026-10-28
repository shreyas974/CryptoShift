# Demo runbook

Run commands from the project root using its virtual environment. The conversation log reported these entry points; first confirm they still match the code:

```powershell
.\.venv\Scripts\python.exe cryptoshift_cli.py --help
.\.venv\Scripts\python.exe cryptoshift_cli.py check-auth
.\.venv\Scripts\python.exe cryptoshift_cli.py demo
```

Do not display `.env` contents. `check-auth` must only report whether a key is present and whether a permitted authentication check succeeded; it must never print a key or raw exception containing one. Local QpiAI Opt solve and local QCloud simulator are distinct from remote platform/QPU execution. Do not run remote or paid operations without explicit authorization.

For every demo, record actual package versions, input revision, command, execution mode, status, and limitations. Clearly mark synthetic application data and mocked traces. Do not present results reported in an old conversation as current until re-run and checked.