# Start / stop / check the local CryptoShift Assistant (FastAPI + uvicorn) bound to 127.0.0.1 only.
#   powershell -ExecutionPolicy Bypass -File scripts\run_agent.ps1 start   [-Port 8765]
#   powershell -ExecutionPolicy Bypass -File scripts\run_agent.ps1 status
#   powershell -ExecutionPolicy Bypass -File scripts\run_agent.ps1 stop
param(
    [Parameter(Position = 0)][ValidateSet("start", "stop", "status")][string]$Action = "status",
    [int]$Port = 8765
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Run = Join-Path $Root "scratch\derived\member3"
$PidFile = Join-Path $Run "agent.pid"
New-Item -ItemType Directory -Force $Run | Out-Null

switch ($Action) {
    "start" {
        if ((Test-Path $PidFile) -and (Get-Process -Id (Get-Content $PidFile) -ErrorAction SilentlyContinue)) {
            Write-Output "already running (pid $(Get-Content $PidFile))"; break
        }
        $env:PYTHONPATH = "$Root\src;$Root"
        $p = Start-Process -FilePath $Py -WorkingDirectory $Root -WindowStyle Hidden -PassThru `
            -ArgumentList "-m", "uvicorn", "cryptoshift.agent.server:app", "--host", "127.0.0.1", "--port", "$Port", "--log-level", "warning" `
            -RedirectStandardOutput (Join-Path $Run "agent.out") -RedirectStandardError (Join-Path $Run "agent.err")
        $p.Id | Set-Content $PidFile
        for ($i = 0; $i -lt 40; $i++) {
            try { $h = Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2; break } catch { Start-Sleep -Milliseconds 250 }
        }
        Write-Output "started pid $($p.Id) on http://127.0.0.1:$Port  health=$($h | ConvertTo-Json -Compress)"
    }
    "status" {
        try { Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2 | ConvertTo-Json -Compress } catch { "not running" }
    }
    "stop" {
        if (Test-Path $PidFile) {
            Stop-Process -Id (Get-Content $PidFile) -Force -ErrorAction SilentlyContinue
            Remove-Item $PidFile
            Write-Output "stopped"
        } else { Write-Output "not running" }
    }
}
