# FitPulse - run the SUPERVISED experiments E1-E5 (Spark MLlib) on Windows PowerShell.
#
#   .\run_supervised.ps1 -Experiment E1                 one experiment on the LOCAL Silver Parquet
#   .\run_supervised.ps1 -Experiment All                E1..E5 in order, then the scikit-learn cross-check
#   .\run_supervised.ps1 -Experiment All -Storage hdfs  same, reading Silver from HDFS (start_hdfs.ps1 first; never falls back to local)
#   .\run_supervised.ps1 -Experiment Check              only the independent scikit-learn cross-check
#
# Results:  exports\E<n>_results.csv (+ E<n>_feature_importance.csv)   evidence: faculty_evidence\supervised\
# An HDFS run writes to faculty_evidence\supervised\hdfs_rerun\ (never over the local-run results) unless -Out is given.
# Sets the local JDK 17 + winutils that Spark needs on this machine (same as run_faculty_demo.ps1 / hdfs_env.ps1).
param(
    [ValidateSet("E1", "E2", "E3", "E4", "E5", "All", "Check")][string]$Experiment = "All",
    [ValidateSet("local", "hdfs")][string]$Storage = "local",
    [string]$Out = ""
)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Ws   = Split-Path -Parent $Root
$Py   = Join-Path $Ws ".venv\Scripts\python.exe"
Set-Location $Root

if ($Storage -eq "hdfs") {
    . "$Root\scripts\hdfs_env.ps1"                 # JAVA_HOME, HADOOP_HOME, HADOOP_CONF_DIR, ... (defines Get-FsDefault)
    $uri = Get-FsDefault
    & hdfs dfs -ls / *> $null
    if ($LASTEXITCODE -ne 0 -or $uri -notlike "hdfs://*") {
        Write-Error "HDFS is not reachable (fs.defaultFS='$uri'). Run .\start_hdfs.ps1 first. NOT falling back to local storage."; exit 2
    }
    $modeArgs = @("--storage", "hdfs", "--hdfs-uri", $uri)
    if (-not $Out) { $Out = Join-Path $Root "faculty_evidence\supervised\hdfs_rerun" }
} else {
    $Tools = Join-Path $Ws "tools"
    $env:JAVA_HOME = Join-Path $Tools "jdk17"; $env:HADOOP_HOME = Join-Path $Tools "hadoop"
    $env:PATH = "$env:JAVA_HOME\bin;$env:HADOOP_HOME\bin;$env:PATH"
    $env:TMP = Join-Path $Tools "tmp"; $env:TEMP = $env:TMP
    $env:PYSPARK_PYTHON = $Py; $env:PYTHONIOENCODING = "utf-8"
    $modeArgs = @("--storage", "local")
}
$env:PYTHONUNBUFFERED = "1"
if (-not $env:FITPULSE_DRIVER_MEMORY) { $env:FITPULSE_DRIVER_MEMORY = "3g" }

$scripts = [ordered]@{
    E1 = "models\sup_e1_goal_same_day.py"; E2 = "models\sup_e2_goal_next_day.py"; E3 = "models\sup_e3_user_high_achiever.py"
    E4 = "models\sup_e4_activity_level.py"; E5 = "models\sup_e5_calories.py"
}
$outArgs = @()
if ($Out) { $outArgs = @("--exports-dir", (Join-Path $Out "exports"), "--evidence-dir", $Out) }
$logDir = if ($Out) { $Out } else { Join-Path $Root "faculty_evidence\supervised" }
New-Item -ItemType Directory -Force $logDir | Out-Null

$todo = if ($Experiment -eq "All") { @($scripts.Keys) } elseif ($Experiment -eq "Check") { @() } else { @($Experiment) }
$worst = 0
foreach ($e in $todo) {
    $log = Join-Path $logDir "$e`_run.log"
    Write-Host "=== $e ($Storage) -> $log" -ForegroundColor Cyan
    cmd /c "`"$Py`" $($scripts[$e]) $($modeArgs -join ' ') $($outArgs -join ' ') > `"$log`" 2>&1"
    if ($LASTEXITCODE -ne 0) { Write-Host "$e FAILED (exit $LASTEXITCODE) - see $log" -ForegroundColor Red; $worst = $LASTEXITCODE; break }
    Get-Content $log | Select-String -NotMatch -Pattern "WARN|incubator|log4j|SUCCESS: The process|^\s*$" | Select-Object -Last 40
}
if ($worst -eq 0 -and ($Experiment -eq "All" -or $Experiment -eq "Check")) {
    $chkArgs = if ($Out) { @("--dir", $Out) } else { @() }
    & $Py scripts\sup_sklearn_crosscheck.py @chkArgs
    $worst = $LASTEXITCODE
}
exit $worst
