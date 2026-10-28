# FitPulse - ROUTINE run in HDFS mode: ingest Bronze CSV -> Spark ETL (HDFS in, HDFS out) -> verify.
#
#   .\run_fitpulse_hdfs.ps1              ingest (only if missing/changed) + ETL + verification
#   .\run_fitpulse_hdfs.ps1 -SkipEtl     only (re)run verification
#
# Requires HDFS to be running (.\start_hdfs.ps1). Never formats the NameNode or deletes HDFS directories
# (the ETL only replaces /fitpulse/silver through its staged swap).
param([switch]$SkipEtl)
$ErrorActionPreference = "Continue"   # native commands write progress to stderr
. "$PSScriptRoot\scripts\hdfs_env.ps1"
Set-Location $ProjectRoot
$ev = Join-Path $ProjectRoot "faculty_evidence\hdfs"; New-Item -ItemType Directory -Force $ev | Out-Null

$uri = Get-FsDefault
& hdfs dfs -ls / *> $null
if ($LASTEXITCODE -ne 0 -or $uri -notlike "hdfs://*") {
    Write-Error "HDFS is not reachable (fs.defaultFS='$uri'). Run .\start_hdfs.ps1 first. NOT falling back to local storage."; exit 2
}
Write-Host "HDFS mode - $uri" -ForegroundColor Cyan
$env:FITPULSE_STORAGE = "hdfs"; $env:FITPULSE_HDFS_URI = $uri

if (-not $SkipEtl) {
    # --- Ingest Bronze (idempotent: fixed name, skipped when the size already matches) ---
    & hdfs dfs -mkdir -p /fitpulse/bronze
    $local = Join-Path $ProjectRoot "data\raw\fitpulse_raw.csv"
    $dest  = "/fitpulse/bronze/fitpulse_raw.csv"
    $du = (& hdfs dfs -du $dest 2>$null | Select-Object -First 1)      # "<bytes> <bytes-with-replicas> <path>"
    $remoteSize = if ($LASTEXITCODE -eq 0 -and $du) { [int64](($du -split "\s+")[0]) } else { -1 }
    if ($remoteSize -eq (Get-Item $local).Length) {
        Write-Host "Bronze already in HDFS with identical size ($remoteSize bytes) - skipping upload."
    } else {
        Write-Host "Uploading Bronze CSV to HDFS: $dest"
        & hdfs dfs -put -f $local $dest
        if ($LASTEXITCODE -ne 0) { throw "hdfs dfs -put failed" }
    }
    # --- ETL ---
    $log = Join-Path $ev "etl_hdfs_run.log"
    $env:PYTHONUNBUFFERED = "1"
    cmd /c "`"$Py`" etl\spark_etl.py --storage hdfs --hdfs-uri $uri --report `"$(Join-Path $ev 'etl_hdfs_run_report.json')`" > `"$log`" 2>&1"
    $etlExit = $LASTEXITCODE
    Get-Content $log | Where-Object { $_ -notmatch '^\s*$' -and $_ -notmatch '^\[Stage' }
    $LASTEXITCODE = $etlExit
    if ($LASTEXITCODE -ne 0) { Write-Error "ETL failed (exit $LASTEXITCODE)"; exit $LASTEXITCODE }
}
& $Py scripts/verify_hdfs.py --hdfs-uri $uri
exit $LASTEXITCODE
