# Weekly Discovery Agent — Windows Task Scheduler
# Does NOT modify data/projects.csv

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Atlas Discovery Agent — weekly scan"
Write-Host "Catalog: read-only (projects.csv never deleted)"

python run_discovery.py scan
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. See reports/discovery_report_*.md and data/discovery_history/"
