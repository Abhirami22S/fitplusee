# FitPulse - ONE-TIME HDFS setup (Windows-native Hadoop 3.4.1, single node, JDK 17).
#
#   .\setup_hdfs.ps1                 install Hadoop (if missing), validate config, format NameNode ONLY if never initialised
#
# Safe to re-run: it never reformats an initialised NameNode and never deletes HDFS data.
# Routine use afterwards:  .\start_hdfs.ps1  ->  .\run_fitpulse_hdfs.ps1  ->  .\stop_hdfs.ps1
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\hdfs_env.ps1"

Write-Host "== 1. Java / Hadoop compatibility ==" -ForegroundColor Cyan
if (-not (Test-Path "$JdkDir\bin\java.exe")) { throw "JDK 17 not found at $JdkDir (shared with the Spark setup)" }
cmd /c "`"$JdkDir\bin\java.exe`" -version 2>&1" | ForEach-Object { Write-Host "   $_" }
$pysparkHadoop = Get-ChildItem (Join-Path $Workspace ".venv\Lib\site-packages\pyspark\jars") -Filter "hadoop-client-api-*.jar" | Select-Object -First 1
Write-Host "   PySpark bundles Hadoop client: $($pysparkHadoop.Name)  -> server version chosen: $HadoopVer"
foreach ($f in "winutils.exe","hadoop.dll") { if (-not (Test-Path "$WinutilsDir\$f")) { throw "$f missing in $WinutilsDir" } }

Write-Host "== 2. Hadoop distribution ==" -ForegroundColor Cyan
if (-not (Test-Path "$HadoopDir\bin\hdfs.cmd")) {
    $free = (Get-PSDrive -Name ($Tools.Substring(0,1))).Free / 1GB
    Write-Host ("   Free space on {0}: {1:N1} GB (need ~3 GB for download + extract)" -f $Tools.Substring(0,2), $free)
    if ($free -lt 3) { throw "Not enough free disk space for Hadoop" }
    $tgz = Join-Path $Tools "downloads\hadoop-$HadoopVer.tar.gz"
    New-Item -ItemType Directory -Force (Split-Path $tgz) | Out-Null
    if (-not (Test-Path $tgz)) {
        curl.exe -L -o $tgz "https://dlcdn.apache.org/hadoop/common/hadoop-$HadoopVer/hadoop-$HadoopVer.tar.gz"
        if ($LASTEXITCODE -ne 0) { throw "download failed" }
    }
    $sha = (curl.exe -sL "https://dlcdn.apache.org/hadoop/common/hadoop-$HadoopVer/hadoop-$HadoopVer.tar.gz.sha512") -join " "
    $want = ($sha -split "\s+" | Where-Object { $_ -match '^[0-9a-fA-F]{128}$' } | Select-Object -First 1)
    $got  = (Get-FileHash $tgz -Algorithm SHA512).Hash
    if ($want -and $want -ne $got) { throw "SHA-512 mismatch for $tgz - delete it and retry" }
    Write-Host "   SHA-512 verified. Extracting (tar) ..."
    tar -xzf $tgz -C $Tools
    if (-not (Test-Path "$HadoopDir\bin\hdfs.cmd")) { throw "extraction failed" }
} else { Write-Host "   Hadoop already present: $HadoopDir" }
# Windows native helpers (reused from the existing Spark setup; not downloaded again)
foreach ($f in "winutils.exe","hadoop.dll") {
    if (-not (Test-Path "$HadoopDir\bin\$f")) { Copy-Item "$WinutilsDir\$f" "$HadoopDir\bin\$f" }
}

Write-Host "== 3. Configuration ==" -ForegroundColor Cyan
foreach ($x in "core-site.xml","hdfs-site.xml") { [xml](Get-Content "$ConfDir\$x") | Out-Null; Write-Host "   $x is well-formed XML" }
$fsd = Get-FsDefault
Write-Host "   fs.defaultFS = $fsd"
if ($fsd -notlike "hdfs://*") { throw "fs.defaultFS is not an hdfs:// URI - check HADOOP_CONF_DIR=$ConfDir" }

Write-Host "== 4. NameNode initialisation ==" -ForegroundColor Cyan
$nnDir = Join-Path $HdfsData "namenode"
New-Item -ItemType Directory -Force $nnDir, (Join-Path $HdfsData "datanode"), (Join-Path $HdfsData "tmp"), $HdfsLogs | Out-Null
if (Test-Path "$nnDir\current\VERSION") {
    Write-Host "   NameNode already formatted ($nnDir\current\VERSION exists) - NOT reformatting."
} elseif ((Get-ChildItem $nnDir -Force | Measure-Object).Count -gt 0) {
    throw "$nnDir is non-empty but has no current\VERSION. Refusing to format; inspect it manually."
} else {
    Write-Host "   Fresh, empty NameNode directory - formatting once."
    & hdfs namenode -format -nonInteractive -clusterId fitpulse
    if ($LASTEXITCODE -ne 0) { throw "namenode -format failed" }
}
Write-Host "`nSetup complete. Next: .\start_hdfs.ps1" -ForegroundColor Green
