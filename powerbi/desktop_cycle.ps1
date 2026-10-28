# FitPulse - open the generated PBIP in Power BI Desktop, load/refresh the data, and capture real page screenshots.
#
#   .\powerbi\desktop_cycle.ps1 [-Project <.pbip|.pbix>] [-OutDir <folder>] [-Fresh]
#
# Uses (1) Microsoft's Desktop Bridge CLI (open / status / screenshot-all) and
#      (2) Windows UI Automation to press Desktop's own "Refresh now" / "Apply changes" banners and the ribbon "Refresh"
#          (the bridge has no refresh command). Needs Power BI Desktop (Store build) running in the logged-in desktop session.
param(
    [string]$Project = (Join-Path $PSScriptRoot "project\FitPulse_PowerBI_Dashboard.pbip"),
    [string]$OutDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "faculty_evidence\powerbi\screenshots"),
    [switch]$Fresh
)
$ErrorActionPreference = "Continue"
$pkg = Get-AppxPackage Microsoft.MicrosoftPowerBIDesktop | Select-Object -First 1
if (-not $pkg) { Write-Error "Power BI Desktop (Store) is not installed"; exit 2 }
$env:PBI_DESKTOP_PATH = Join-Path $pkg.InstallLocation "bin\PBIDesktop.exe"
$cli = Join-Path $PSScriptRoot "_tools\node_modules\.bin\powerbi-desktop.cmd"
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$UIA = [System.Windows.Automation.AutomationElement]

function Get-Root { $p = Get-Process PBIDesktop -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1; if ($p) { $UIA::FromHandle($p.MainWindowHandle) } }
function Find-Named($root, $name) { $c = New-Object System.Windows.Automation.PropertyCondition($UIA::NameProperty, $name); $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $c) }
function Press($el) { $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }

if ($Fresh) {
    Get-Process PBIDesktop -ErrorAction SilentlyContinue | ForEach-Object { [void]$_.CloseMainWindow() }
    Start-Sleep 8
    Get-Process PBIDesktop -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue   # project has no unsaved state we need
    Start-Sleep 3
}
Write-Host "Opening $Project ..."
& $cli open $Project --timeout 240 *> $null
& $cli status --wait-seconds 120 | Out-Null

Write-Host "Loading data (pressing Desktop's own banner buttons once each, waiting for the bridge to become ready) ..."
function Wait-Ready($sec) { $t0 = Get-Date; while (((Get-Date) - $t0).TotalSeconds -lt $sec) { $j = (& $cli status --wait-seconds 5 2>$null | Out-String); if ($j -match '"status": "ready"') { return $true }; Start-Sleep 5 }; return $false }
[void](Wait-Ready 120)
$done = @{}
for ($round = 0; $round -lt 6; $round++) {
    Start-Sleep 5
    $root = Get-Root; if (-not $root) { continue }
    $pressed = $false
    foreach ($n in "Refresh now", "Apply changes") {
        $b = Find-Named $root $n
        if ($b.Count -gt 0 -and $done["$n$round"] -ne 1) { Press $b[0]; Write-Host "  pressed '$n' (round $round)"; $done["$n$round"] = 1; $pressed = $true; [void](Wait-Ready 240); break }
    }
    if (-not $pressed) { break }
}
New-Item -ItemType Directory -Force $OutDir | Out-Null
& $cli screenshot-all --output-dir $OutDir --scale 1 --settle 3000 *> $null
Get-ChildItem $OutDir -Filter *.png | Select-Object Name, Length, LastWriteTime
