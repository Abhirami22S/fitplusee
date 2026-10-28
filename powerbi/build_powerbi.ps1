# FitPulse - one command: refresh exports -> validate -> generate the Power BI Project (PBIP) -> validate the project.
#
#   .\powerbi\build_powerbi.ps1                 full run
#   .\powerbi\build_powerbi.ps1 -SkipExport     reuse the existing CSVs in powerbi\data
#
# Output: powerbi\project\FitPulse_PowerBI_Dashboard.pbip  (open it in Power BI Desktop, then File > Save as > .pbix)
# This script cannot create the .pbix itself; only Power BI Desktop can.
param([switch]$SkipExport)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path (Split-Path -Parent $Root) ".venv\Scripts\python.exe"
Set-Location $Root
function Step($t) { Write-Host "`n== $t ==" -ForegroundColor Cyan }
function Run($args_) { & $Py @args_; if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $args_" -ForegroundColor Red; exit $LASTEXITCODE } }
if (-not $SkipExport) {
    Step "1. Export Power BI tables from the validated model outputs"
    Run @("powerbi\export_powerbi_data.py"); Run @("powerbi\export_model_evaluation.py")
}
Step "2. Validate exported data against the Silver data and saved evaluation files"
Run @("powerbi\validate_exports.py")
Step "3. Generate the PBIP project (TMDL semantic model + PBIR report)"
Run @("powerbi\build_powerbi.py")
Step "4. Validate the generated project (schema, references, measures, Microsoft validators)"
Run @("powerbi\validate_powerbi_project.py")
Write-Host "`nProject ready: $Root\powerbi\project\FitPulse_PowerBI_Dashboard.pbip" -ForegroundColor Green
Write-Host "Next (needs Power BI Desktop): open the .pbip, Refresh, check the cards against powerbi\EXPECTED_VALUES.csv, File > Save as > FitPulse_PowerBI_Dashboard.pbix"
