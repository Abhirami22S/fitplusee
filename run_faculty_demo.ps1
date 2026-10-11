# FitPulse faculty demo launcher (Windows PowerShell)
#
#   .\run_faculty_demo.ps1            -> opens the notebook in Jupyter Lab
#   .\run_faculty_demo.ps1 pipeline   -> runs data/prepare_raw_dataset.py + etl/spark_etl.py
#   .\run_faculty_demo.ps1 execute    -> re-executes the whole notebook headless (~6 min), saving outputs
#
# Sets up the local JDK 17 + Hadoop winutils (in ..\tools) that Spark needs on this machine,
# and keeps Spark's temp files on D: (C: is almost full).
param([string]$Mode = "open")

$Root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Tools = Join-Path (Split-Path -Parent $Root) "tools"
$Py    = Join-Path (Split-Path -Parent $Root) ".venv\Scripts\python.exe"

$env:JAVA_HOME       = Join-Path $Tools "jdk17"
$env:HADOOP_HOME     = Join-Path $Tools "hadoop"
$env:PATH            = "$env:JAVA_HOME\bin;$env:HADOOP_HOME\bin;$env:PATH"
$env:TMP             = Join-Path $Tools "tmp"
$env:TEMP            = $env:TMP
$env:KAGGLEHUB_CACHE = Join-Path $Tools "kagglehub"
$env:PYSPARK_PYTHON  = $Py
$env:PYTHONIOENCODING = "utf-8"

Set-Location $Root
switch ($Mode) {
    "pipeline" {
        & $Py data/prepare_raw_dataset.py
        if ($LASTEXITCODE -eq 0) { & $Py etl/spark_etl.py }
    }
    "execute" {
        & $Py -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 FitPulse_Faculty_Demo.ipynb
    }
    default {
        & $Py -m jupyterlab FitPulse_Faculty_Demo.ipynb
    }
}
