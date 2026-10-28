# FitPulse - failure-mode test: what happens in HDFS mode when HDFS is NOT running?
# Stops the HDFS daemons (data stays on disk), runs the ETL with --storage hdfs, records the real exit code/output,
# checks the local Silver dataset was left untouched, runs the LOCAL mode into a scratch folder to show it is a
# distinct, explicitly-labelled mode, then restarts HDFS. Output: faculty_evidence/hdfs/failure_mode_test.txt
. "$PSScriptRoot\hdfs_env.ps1"
Set-Location $ProjectRoot
$out = Join-Path $ProjectRoot "faculty_evidence\hdfs\failure_mode_test.txt"
$silver = Join-Path $ProjectRoot "data\processed\fitpulse_silver"
function Snapshot { $f = Get-ChildItem $silver -Recurse -File; "{0} files, {1} bytes, newest write {2:o}" -f $f.Count, ($f | Measure-Object Length -Sum).Sum, ($f | Sort-Object LastWriteTime | Select-Object -Last 1).LastWriteTime }
$log = New-Object System.Collections.Generic.List[string]
function Note($t) { $log.Add($t); Write-Host $t }

Note "FAILURE-MODE TEST  $(Get-Date -Format s)"
$before = Snapshot; Note "local Silver BEFORE: $before"

& "$ProjectRoot\stop_hdfs.ps1" | ForEach-Object { Note "  $_" }
Start-Sleep 3
Note "`n--- A) HDFS selected, NameNode stopped ---"
$env:PYTHONUNBUFFERED = "1"
$o = cmd /c "`"$Py`" etl\spark_etl.py --storage hdfs --hdfs-uri hdfs://localhost:9000 2>&1"
Note ("exit code: " + $LASTEXITCODE)
$o | Where-Object { $_ -match "ERROR|STORAGE" } | ForEach-Object { Note "  $_" }
$after = Snapshot; Note "local Silver AFTER : $after"
Note ("local Silver untouched: " + ($before -eq $after))

Note "`n--- B) HDFS selected but no URI configured ---"
$env:FITPULSE_HDFS_URI = ""
$o = cmd /c "`"$Py`" etl\spark_etl.py --storage hdfs 2>&1"
Note ("exit code: " + $LASTEXITCODE)
$o | Where-Object { $_ -match "ERROR" } | ForEach-Object { Note "  $_" }

Note "`n--- C) LOCAL mode (explicit fallback) while HDFS is down; output to a scratch dir ---"
$scratch = "data\processed\_local_mode_check"
$o = cmd /c "`"$Py`" etl\spark_etl.py --storage local --output $scratch 2>&1"
Note ("exit code: " + $LASTEXITCODE)
$o | Where-Object { $_ -match "STORAGE MODE|Storage mode used|Silver rows written|Read back" } | ForEach-Object { Note "  $_" }
if (Test-Path (Join-Path $ProjectRoot $scratch)) { Remove-Item -Recurse -Force (Join-Path $ProjectRoot $scratch) }   # only the scratch dir created above

$log | Set-Content -Encoding utf8 $out
Write-Host "`nRestarting HDFS ..."
& "$ProjectRoot\start_hdfs.ps1"
