# Copy Discovery bundle into TMT repo (discovery/ only — root index.html = organ map)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

python -c "
import json
import shutil
from pathlib import Path
from atlas_agent.config import load_config
from atlas_agent.viz.publish_site import publish_discovery_site, publish_tmt_discovery_site

root = Path('.')
latest = root / 'data' / 'discovery_history' / 'latest.json'
report = json.loads(latest.read_text(encoding='utf-8'))
publish_discovery_site(report, root)

tmt_discovery = Path(load_config()['paths']['atlas_data_dir']).parent / 'discovery'
publish_tmt_discovery_site(report, tmt_discovery)

dest = root / 'export_for_tmt' / 'discovery'
if dest.exists():
    shutil.rmtree(dest)
shutil.copytree(tmt_discovery, dest)
print('OK', dest)
print('OK', tmt_discovery)
"

Write-Host ""
Write-Host "Done: docs/ + export_for_tmt/discovery + TMT discovery/" -ForegroundColor Green
Write-Host "TMT root index.html is NOT modified (organ map + ?organ= links)" -ForegroundColor Cyan
Write-Host "Portal: https://arinaatom-cyber.github.io/TMT/discovery/"
Write-Host "Map:    https://arinaatom-cyber.github.io/TMT/"