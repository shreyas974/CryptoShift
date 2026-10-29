# Start / stop / check the CryptoShift console (Streamlit) bound to 127.0.0.1 only.
#   powershell -ExecutionPolicy Bypass -File scripts\run_ui.ps1 start   [-Port 8501]
#   powershell -ExecutionPolicy Bypass -File scripts\run_ui.ps1 status
#   powershell -ExecutionPolicy Bypass -File scripts\run_ui.ps1 stop
param(
    [Parameter(Position = 0)][ValidateSet("start", "stop", "status")][string]$Action = "status",
    [int]$Port = 8501
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Run = Join-Path $Root "scratch\derived\ui"
$PidFile = Join-Path $Run "ui.pid"
New-Item -ItemType Directory -Force $Run | Out-Null

switch ($Action) {
    "start" {
        if ((Test-Path $PidFile) -and (Get-Process -Id (Get-Content $PidFile) -ErrorAction SilentlyContinue)) {
            Write-Output "already running (pid $(Get-Content $PidFile)) on http://127.0.0.1:$Port"; break
        }
        $env:PYTHONPATH = "$Root\src;$Root"
        $p = Start-Process -FilePath $Py -WorkingDirectory $Root -WindowStyle Hidden -PassThru `
            -ArgumentList "-m", "streamlit", "run", "src/cryptoshift/ui/console/app.py", "--server.address", "127.0.0.1", `
                          "--server.port", "$Port", "--server.headless", "true", "--browser.gatherUsageStats", "false" `
            -RedirectStandardOutput (Join-Path $Run "ui.out") -RedirectStandardError (Join-Path $Run "ui.err")
        $p.Id | Set-Content $PidFile
        $ok = $false
        for ($i = 0; $i -lt 60; $i++) {
            try { Invoke-WebRequest "http://127.0.0.1:$Port/_stcore/health" -UseBasicParsing -TimeoutSec 2 | Out-Null; $ok = $true; break } catch { Start-Sleep -Milliseconds 500 }
        }
        if ($ok) { Write-Output "started pid $($p.Id): open http://127.0.0.1:$Port" } else { Write-Output "not healthy yet; see scratch\derived\ui\ui.err" }
    }
    "status" {
        try { Invoke-WebRequest "http://127.0.0.1:$Port/_stcore/health" -UseBasicParsing -TimeoutSec 2 | Out-Null; "running on http://127.0.0.1:$Port" } catch { "not running" }
    }
    "stop" {
        if (Test-Path $PidFile) {
            Stop-Process -Id (Get-Content $PidFile) -Force -ErrorAction SilentlyContinue
            Remove-Item $PidFile
            Write-Output "stopped"
        } else { Write-Output "not running" }
    }
}
