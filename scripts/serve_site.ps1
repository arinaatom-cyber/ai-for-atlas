# Локальный сайт (пока GitHub не настроен) — http://localhost:8765
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

python run_discovery.py publish 2>$null

$port = 8765
Write-Host "Discovery site: http://localhost:$port/site/discovery.html" -ForegroundColor Green
Write-Host "Ctrl+C to stop"
Start-Process "http://localhost:$port/site/discovery.html"
python -m http.server $port --directory docs
