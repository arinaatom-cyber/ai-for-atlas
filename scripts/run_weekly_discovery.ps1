# Atlas Discovery Agent — Monday local neural net (Ollama / Qwen)
# Does NOT modify catalog (Excel TMT ATLAS; CSV mirror never auto-deleted)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$env:ATLAS_SKIP_GPT4ALL = "1"
$logDir = Join-Path $Root "data\discovery_history"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$log = Join-Path $logDir "weekly_$stamp.log"

function Write-Log($msg) {
    $line = "{0}  {1}" -f (Get-Date -Format "s"), $msg
    Add-Content -Path $log -Value $line
    Write-Host $line
}

Write-Log "Atlas Discovery — Monday local scan"
Write-Log "Catalog: read-only"

$ollama = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "$env:ProgramFiles\Ollama\ollama.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($ollama) {
    $env:Path = "$(Split-Path $ollama -Parent);$env:Path"
    Write-Log "Ollama: $ollama"
    try { & $ollama list | Out-Null } catch { Write-Log "Ollama list failed (server may still start)" }
} else {
    Write-Log "Ollama not found — scan will use regex fallback unless another engine is configured"
}

python run_discovery.py scan *>> $log
if ($LASTEXITCODE -ne 0) {
    Write-Log "scan failed: $LASTEXITCODE"
    exit $LASTEXITCODE
}

python run_discovery.py publish *>> $log
if ($LASTEXITCODE -ne 0) {
    Write-Log "publish failed: $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Log "Done. Local site: docs\site\discovery.html"
Write-Log "Push: powershell -File scripts\push_site_github.ps1"
exit 0
