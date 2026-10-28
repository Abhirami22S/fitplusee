# FitPulse - start HDFS (NameNode + DataNode) and wait until it is really usable. Routine, non-destructive.
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\hdfs_env.ps1"
if (-not (Test-Path "$HdfsData\namenode\current\VERSION")) { throw "NameNode not initialised - run .\setup_hdfs.ps1 first" }
New-Item -ItemType Directory -Force $HdfsLogs | Out-Null

function Start-Daemon($name, $cls) {
    if (Get-HdfsJava $cls) { Write-Host "   $name already running"; return }
    Start-Process -FilePath "$HadoopDir\bin\hdfs.cmd" -ArgumentList $name.ToLower() -WindowStyle Hidden `
        -RedirectStandardOutput "$HdfsLogs\$name.out.log" -RedirectStandardError "$HdfsLogs\$name.err.log"
    Write-Host "   $name starting (logs: $HdfsLogs)"
}
Write-Host "== Starting HDFS daemons ==" -ForegroundColor Cyan
Start-Daemon "NameNode" "org.apache.hadoop.hdfs.server.namenode.NameNode"
Start-Daemon "DataNode" "org.apache.hadoop.hdfs.server.datanode.DataNode"

Write-Host "== Waiting for readiness (up to 120 s) ==" -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds(120); $ready = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    if (-not (Get-HdfsJava "namenode.NameNode")) { Write-Host "   NameNode process died - see $HdfsLogs"; break }
    $rep = & hdfs dfsadmin -report 2>$null
    $live = ($rep | Select-String "Live datanodes \((\d+)\)")
    if ($live -and $live.Matches[0].Groups[1].Value -ge 1) { $ready = $true; break }
    Write-Host "   ... not ready yet"
}
if (-not $ready) { Write-Error "HDFS did not become ready. Check $HdfsLogs\*.log"; exit 1 }
& hdfs dfsadmin -safemode wait | Out-Null
Write-Host "HDFS is up: $(Get-FsDefault)  (NameNode UI http://localhost:9870)" -ForegroundColor Green
