# Atlas Discovery — установка на любом Windows-ПК
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== Atlas Discovery Setup ===" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python не найден. Установите Python 3.12+ с python.org"
}

python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path "config.yaml")) {
    Copy-Item "config.example.yaml" "config.yaml"
    Write-Host "Создан config.yaml из config.example.yaml"
}

if (-not (Test-Path "data/projects.csv")) {
    Write-Warning "Нет data/projects.csv — положите свой каталог (read-only для агента)"
}

Write-Host ""
Write-Host "Готово. Команды:" -ForegroundColor Green
Write-Host "  python run_discovery.py scan          # поиск новых проектов"
Write-Host "  streamlit run discovery_app.py        # UI http://localhost:8501"
Write-Host "  start docs\site\discovery.html        # сайт локально"
Write-Host "  powershell -File scripts\push_site_github.ps1  # на GitHub (любой ПК)"
Write-Host ""
Write-Host "GitHub Pages: Settings -> Pages -> Source: GitHub Actions"
Write-Host "Каталог Excel НЕ публикуется — только новые проекты + ИИ-анализ."
