# FitPulse - AFTER Power BI Desktop is installed: open the generated project and capture a real PNG of every report page
# through Microsoft's Power BI Desktop Bridge CLI (documented, preview). UNTESTED until Desktop is installed.
#
#   .\powerbi\capture_powerbi_screenshots.ps1 [-Project <.pbip or .pbix path>]
# Needs: Power BI Desktop (June 2026 build or later), Desktop Bridge enabled (File > Options > Security > Desktop Bridge; on by default),
#        npm install --prefix powerbi\_tools @microsoft/powerbi-report-authoring-cli   (also installs the bridge CLI)
# The bridge CAN open, reload and screenshot. It has NO save/export command: File > Save as .pbix is a manual step in Desktop.
param([string]$Project = (Join-Path $PSScriptRoot "project\FitPulse_PowerBI_Dashboard.pbip"))
$cli = Join-Path $PSScriptRoot "_tools\node_modules\.bin\powerbi-desktop.cmd"
$out = Join-Path (Split-Path -Parent $PSScriptRoot) "faculty_evidence\powerbi\screenshots"
New-Item -ItemType Directory -Force $out | Out-Null
& $cli open $Project --timeout 180
& $cli status
& $cli screenshot-all --output-dir $out --scale 2 --settle 3000 --wait-seconds 120
Get-ChildItem $out -Filter *.png | Select-Object Name, Length
