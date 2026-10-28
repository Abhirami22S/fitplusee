# FitPulse - parse the generated TMDL semantic model with Microsoft's own TMDL deserializer (Tabular Object Model).
#
#   .\powerbi\validate_tmdl.ps1 [-TomDir <folder with Microsoft.AnalysisServices.Tabular.dll>]
#
# Checks syntax and object-model validity of the TMDL files (tables, columns, measures, relationships, expressions).
# It does NOT evaluate DAX or load data - only Power BI Desktop does that.
# One-time prerequisite (official Microsoft NuGet package, ~7 MB, kept outside the repo):
#   curl.exe -L -o as.zip https://api.nuget.org/v3-flatcontainer/microsoft.analysisservices.retail.amd64/19.84.1/microsoft.analysisservices.retail.amd64.19.84.1.nupkg
#   Expand-Archive as.zip D:\bigdata\fitpulsee\tools\nuget\as_pkg
param(
    [string]$TomDir = (Join-Path (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))) "tools\nuget\as_pkg\lib\net45"),
    [string]$Definition = (Join-Path $PSScriptRoot "project\FitPulse_PowerBI_Dashboard.SemanticModel\definition")
)
$ErrorActionPreference = "Stop"
foreach ($d in "Microsoft.AnalysisServices.Core.dll", "Microsoft.AnalysisServices.dll", "Microsoft.AnalysisServices.Tabular.Json.dll", "Microsoft.AnalysisServices.Tabular.dll") {
    $p = Join-Path $TomDir $d
    if (-not (Test-Path $p)) { Write-Error "Missing $p - see the prerequisite in this script's header"; exit 2 }
    [void][System.Reflection.Assembly]::LoadFrom($p)
}
if (-not (Test-Path $Definition)) { Write-Error "TMDL folder not found: $Definition (run build_powerbi.py)"; exit 2 }
try {
    $db = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder($Definition)
} catch {
    Write-Host "TMDL PARSE FAILED: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.InnerException) { Write-Host $_.Exception.InnerException.Message }
    exit 1
}
$m = $db.Model
$result = [ordered]@{
    parsed = $true
    compatibilityLevel = $db.CompatibilityLevel
    tables = @($m.Tables | ForEach-Object {
        [ordered]@{ name = $_.Name; columns = @($_.Columns | ForEach-Object { $_.Name }); measures = @($_.Measures | ForEach-Object { $_.Name })
                    partitions = @($_.Partitions | ForEach-Object { $_.Name }); dataCategory = $_.DataCategory }
    })
    relationships = @($m.Relationships | ForEach-Object {
        "$($_.FromTable.Name).$($_.FromColumn.Name) -> $($_.ToTable.Name).$($_.ToColumn.Name) [$($_.FromCardinality):$($_.ToCardinality), $($_.CrossFilteringBehavior)]" })
    expressions = @($m.Expressions | ForEach-Object { $_.Name })
}
$out = Join-Path (Split-Path -Parent $PSScriptRoot) "faculty_evidence\powerbi"
New-Item -ItemType Directory -Force $out | Out-Null
$result | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 (Join-Path $out "tmdl_parse_result.json")
Write-Host ("TMDL parsed OK: {0} tables, {1} columns, {2} measures, {3} relationships, {4} expressions" -f `
    $m.Tables.Count, ($m.Tables | ForEach-Object { $_.Columns.Count } | Measure-Object -Sum).Sum, ($m.Tables | ForEach-Object { $_.Measures.Count } | Measure-Object -Sum).Sum, $m.Relationships.Count, $m.Expressions.Count) -ForegroundColor Green
$m.Relationships | ForEach-Object { Write-Host "  $($_.FromTable.Name).$($_.FromColumn.Name) -> $($_.ToTable.Name).$($_.ToColumn.Name)" }
exit 0
