# Weekly Discovery Agent — Windows Task Scheduler
# Does NOT modify catalog (Excel TMT ATLAS; CSV mirror never auto-deleted)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Atlas Discovery Agent — weekly scan"
Write-Host "Catalog: read-only (Excel TMT ATLAS; CSV mirror never auto-deleted)"

# GPT4All CUDA DLL often fails on Windows — skip unless fixed locally
$env:ATLAS_SKIP_GPT4ALL = "1"

python run_discovery.py scan
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python run_discovery.py publish
Write-Host "Done. Local: docs\site\discovery.html"
Write-Host "TMT site: powershell -File scripts\export_site_for_tmt.ps1"
Write-Host "GitHub:   powershell -File scripts\push_site_github.ps1"
