# CryptoShift web app v2: single-process demo (FastAPI serves web/dist) bound to 127.0.0.1 only.
#   powershell -ExecutionPolicy Bypass -File scripts\run_full_demo.ps1 start   [-Port 8600]
#   powershell -ExecutionPolicy Bypass -File scripts\run_full_demo.ps1 status
#   powershell -ExecutionPolicy Bypass -File scripts\run_full_demo.ps1 stop
# First time only, create your own local account (password typed at a hidden prompt):
#   .\.venv\Scripts\python.exe -m cryptoshift.api.admin create-user <name> approver
param(
    [Parameter(Position = 0)][ValidateSet("start", "stop", "status")][string]$Action = "status",
    [int]$Port = 8600
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Run = Join-Path $Root "scratch\derived\webapp"
$PidFile = Join-Path $Run "server.pid"
New-Item -ItemType Directory -Force $Run | Out-Null
$env:PYTHONPATH = "$Root\src;$Root"

switch ($Action) {
    "start" {
        if ((Test-Path $PidFile) -and (Get-Process -Id (Get-Content $PidFile) -ErrorAction SilentlyContinue)) {
            Write-Output "already running: http://127.0.0.1:$Port"; break
        }
        if (-not (Test-Path (Join-Path $Root "web\dist\index.html"))) {
            Write-Output "web\dist missing: build it first with  cd web; npm ci; npm run build"; break
        }
        # Optional: Member 3's assistant service (TEMPLATE_FALLBACK unless the owner enables cloud mode for it).
        if (Test-Path (Join-Path $Root "scratch\derived\member3\bundle\plan.json")) {
            powershell -ExecutionPolicy Bypass -File (Join-Path $Root "scripts\run_agent.ps1") start | Out-Null
        }
        $p = Start-Process -FilePath $Py -WorkingDirectory $Root -WindowStyle Hidden -PassThru `
            -ArgumentList "-m", "uvicorn", "--factory", "cryptoshift.api.main:app_factory", "--host", "127.0.0.1", "--port", "$Port", `
                          "--no-server-header", "--log-level", "warning" `
            -RedirectStandardOutput (Join-Path $Run "server.out") -RedirectStandardError (Join-Path $Run "server.err")
        $p.Id | Set-Content $PidFile
        $ok = $false
        for ($i = 0; $i -lt 60; $i++) {
            try { Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2 | Out-Null; $ok = $true; break } catch { Start-Sleep -Milliseconds 500 }
        }
        if ($ok) { Write-Output "started pid $($p.Id): open http://127.0.0.1:$Port" } else { Write-Output "not healthy yet; see scratch\derived\webapp\server.err" }
        $users = & $Py -m cryptoshift.api.admin list-users 2>$null
        if (-not $users) { Write-Output "No local accounts yet. Create one:  .\.venv\Scripts\python.exe -m cryptoshift.api.admin create-user <name> approver" }
    }
    "status" {
        try { Invoke-RestMethod "http://127.0.0.1:$Port/ready" -TimeoutSec 3 | ConvertTo-Json -Compress } catch { "not running" }
    }
    "stop" {
        if (Test-Path $PidFile) {
            Stop-Process -Id (Get-Content $PidFile) -Force -ErrorAction SilentlyContinue
            Remove-Item $PidFile
            Write-Output "stopped"
        } else { Write-Output "not running" }
    }
}
