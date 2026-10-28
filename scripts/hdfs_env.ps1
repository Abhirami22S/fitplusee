# Dot-sourced by the FitPulse HDFS scripts. Defines paths + environment; does nothing destructive.
$script:ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script:Workspace   = Split-Path -Parent $ProjectRoot            # D:\bigdata\fitpulsee
$script:Tools       = Join-Path $Workspace "tools"
$script:HadoopVer   = "3.4.1"
$script:HadoopDir   = Join-Path $Tools "hadoop-$HadoopVer"       # real Hadoop distribution
$script:WinutilsDir = Join-Path $Tools "hadoop\bin"              # pre-existing winutils.exe + hadoop.dll (3.3.6 build)
$script:JdkDir      = Join-Path $Tools "jdk17"
$script:HdfsData    = Join-Path $Tools "hdfs-data"
$script:HdfsLogs    = Join-Path $Tools "hdfs-logs"
$script:ConfDir     = Join-Path $ProjectRoot "hadoop-conf"
$script:Py          = Join-Path $Workspace ".venv\Scripts\python.exe"

$env:JAVA_HOME        = $JdkDir
$env:HADOOP_HOME      = $HadoopDir
$env:HADOOP_CONF_DIR  = $ConfDir
$env:HADOOP_LOG_DIR   = $HdfsLogs
$env:TMP              = Join-Path $Tools "tmp"; $env:TEMP = $env:TMP
$env:PYSPARK_PYTHON   = $Py
$env:PYTHONIOENCODING = "utf-8"
if ($env:PATH -notlike "*$HadoopDir\bin*") { $env:PATH = "$JdkDir\bin;$HadoopDir\bin;$env:PATH" }

function Get-HdfsJava([string]$Class) {
    Get-CimInstance Win32_Process -Filter "Name='java.exe'" |
        Where-Object { $_.CommandLine -like "*$Class*" }
}
function Get-FsDefault { (& hdfs getconf -confKey fs.defaultFS 2>$null | Select-Object -Last 1).Trim() }
