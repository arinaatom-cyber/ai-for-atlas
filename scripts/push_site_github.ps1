# Обновить сайт и отправить на GitHub (откроется на любом ПК)
# Требует: git remote + gh auth login
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== Push Discovery site to GitHub ===" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git не найден"
}

$remote = git remote get-url origin 2>$null
if (-not $remote) {
    Write-Host ""
    Write-Host "Нет remote. Один раз:" -ForegroundColor Yellow
    Write-Host "  gh auth login"
    Write-Host "  gh repo create arinaatom-cyber/ai-for-atlas --public --source=. --push"
    Write-Host "  # или: git remote add origin https://github.com/USER/ai-for-atlas.git"
    exit 1
}

python run_discovery.py publish
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

git add docs/site/ docs/index.html docs/.nojekyll data/discovery_history/latest.json
$status = git status --porcelain
if (-not $status) {
    Write-Host "Нет изменений для push." -ForegroundColor Green
    exit 0
}

$msg = "site: discovery update $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git commit -m $msg
git push -u origin HEAD

Write-Host ""
Write-Host "Готово. Сайт обновится через 1-2 мин (GitHub Actions -> Pages)." -ForegroundColor Green
Write-Host "URL: https://arinaatom-cyber.github.io/ai-for-atlas/site/discovery.html"
Write-Host "     (замените USER/REPO если другой репозиторий)"
