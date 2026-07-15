# Первый запуск: создать репозиторий на GitHub и включить Pages
# Нужно один раз: gh auth login
param(
    [string]$Repo = "arinaatom-cyber/ai-for-atlas",
    [switch]$Public
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== GitHub Pages setup ===" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Установите Git: https://git-scm.com"
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Установите GitHub CLI: https://cli.github.com" -ForegroundColor Yellow
    Write-Host "Или вручную: создайте репо на github.com и git push"
    exit 1
}

$auth = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Сначала войдите в GitHub:" -ForegroundColor Yellow
    Write-Host "  gh auth login"
    exit 1
}

python run_discovery.py publish

# Файлы для сайта (без приватного Excel)
$siteFiles = @(
    "docs/",
    ".github/workflows/pages.yml",
    "data/discovery_history/latest.json",
    "scripts/publish_site.py",
    "atlas_agent/viz/",
    "requirements.txt"
)

git add docs/ .github/workflows/pages.yml data/discovery_history/latest.json
git add scripts/publish_site.py scripts/serve_site.ps1 scripts/setup_github_pages.ps1 scripts/push_site_github.ps1
git add atlas_agent/viz/ requirements.txt README.md 2>$null

$remote = git remote get-url origin 2>$null
if (-not $remote) {
    Write-Host "Создаём репозиторий $Repo ..." -ForegroundColor Cyan
    gh repo create $Repo --public --source=. --remote=origin --description "Atlas Discovery — TMT project finder"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Если репо уже есть:" -ForegroundColor Yellow
        Write-Host "  git remote add origin https://github.com/$Repo.git"
        exit 1
    }
}

$changes = git status --porcelain
if ($changes) {
    git add -A
    git reset HEAD -- "project of Proteomics.xlsx" "*.xlsx" "reports/" ".env" 2>$null
    git commit -m "Publish Discovery site and GitHub Pages workflow" 2>$null
    if ($LASTEXITCODE -ne 0) {
        git commit -m "Publish Discovery site" --allow-empty
    }
}

Write-Host "Push to GitHub..." -ForegroundColor Cyan
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    git push -u origin master
}

# Pages: GitHub Actions
$owner, $name = $Repo -split "/", 2
Write-Host "Enabling GitHub Pages (Actions)..." -ForegroundColor Cyan
gh api "repos/$Repo/pages" -X POST -f build_type=workflow 2>$null
if ($LASTEXITCODE -ne 0) {
    gh api "repos/$Repo/pages" -X PUT -f build_type=workflow 2>$null
}

Write-Host ""
Write-Host "Готово. Подождите 1-3 мин, затем откройте:" -ForegroundColor Green
Write-Host "  https://$($owner.ToLower()).github.io/$name/site/discovery.html"
Write-Host ""
Write-Host "Проверка Actions: https://github.com/$Repo/actions"
Write-Host "Локально (без GitHub): powershell -File scripts\serve_site.ps1"
