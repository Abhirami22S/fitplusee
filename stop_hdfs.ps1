# FitPulse - stop the HDFS daemons. Data stays on disk (tools\hdfs-data); nothing is deleted or formatted.
. "$PSScriptRoot\scripts\hdfs_env.ps1"
foreach ($cls in "org.apache.hadoop.hdfs.server.datanode.DataNode", "org.apache.hadoop.hdfs.server.namenode.NameNode") {
    $p = Get-HdfsJava $cls
    if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host "stopped $cls (pid $($_.ProcessId))" } }
    else    { Write-Host "$cls not running" }
}
