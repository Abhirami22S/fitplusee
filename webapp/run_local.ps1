# FitPulse per-user web dashboard - run on localhost (PowerShell, any folder).
#   .\webapp\run_local.ps1            then open the URL it prints (it also opens your browser once the server answers)
# Press Ctrl+C in this window to stop. Works offline (127.0.0.1 is your own computer; Wi-Fi is not involved).
param([int]$Port = 8765)
$ErrorActionPreference = "Stop"
$Public = Join-Path $PSScriptRoot "public"
$Venv = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) ".venv\Scripts\python.exe"
$Py = if (Test-Path $Venv) { $Venv } else { (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $Py) { Write-Error "Python not found"; exit 1 }
if (-not (Test-Path (Join-Path $Public "data\insights.json"))) { Write-Error "public\data\insights.json missing - run: python webapp\export_insights.py"; exit 1 }

# pick a free port
while (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { $Port++ }
$url = "http://127.0.0.1:$Port/?user=1503"

$srv = Start-Process -FilePath $Py -ArgumentList "-m", "http.server", "$Port", "--bind", "127.0.0.1", "--directory", "`"$Public`"" -PassThru -WindowStyle Hidden
try {
    $ok = $false
    for ($i = 0; $i -lt 40; $i++) {                       # wait up to ~10 s for the server to answer
        Start-Sleep -Milliseconds 250
        try { if ((Invoke-WebRequest "http://127.0.0.1:$Port/data/insights.json" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { $ok = $true; break } } catch {}
    }
    if (-not $ok) { Write-Error "Server did not start on port $Port"; exit 1 }
    Write-Host "FitPulse dashboard running at $url   (Ctrl+C to stop)" -ForegroundColor Green
    Start-Process $url
    Wait-Process -Id $srv.Id
} finally {
    if ($srv -and -not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
}
