# Локальный Qwen без API-ключей: Ollama (лучше) + GPT4All (fallback)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== Atlas: локальный Qwen ===" -ForegroundColor Cyan

pip install -q -r "$Root\requirements.txt"

function Find-Ollama {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "$env:ProgramFiles\Ollama\ollama.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$ollama = Find-Ollama
if (-not $ollama) {
    Write-Host "`n[1/3] Ollama не найден — установка..." -ForegroundColor Yellow
    $installer = "$env:TEMP\OllamaSetup.exe"
    if (-not (Test-Path $installer)) {
        Write-Host "  Скачивание OllamaSetup.exe (~700 MB, подождите)..."
        Invoke-WebRequest -Uri "https://github.com/ollama/ollama/releases/download/v0.32.6/OllamaSetup.exe" `
            -OutFile $installer -UseBasicParsing
    }
    Start-Process -FilePath $installer -ArgumentList "/S" -Wait
    Start-Sleep -Seconds 8
    $ollama = Find-Ollama
}

if ($ollama) {
    Write-Host "`n[2/3] Ollama: $ollama" -ForegroundColor Green
    $env:Path = "$(Split-Path $ollama -Parent);$env:Path"
    Write-Host "  Загрузка qwen2.5:3b (~2 GB)..."
    & $ollama pull qwen2.5:3b
    Write-Host "  Проверка..."
    & $ollama list
} else {
    Write-Host "`n[!] Ollama не установился — используйте GPT4All (ниже)" -ForegroundColor Red
}

Write-Host "`n[3/3] GPT4All fallback (Qwen2-1.5B, уже в кэше или скачается при первом scan)" -ForegroundColor Yellow
python -c @"
from atlas_agent.local_gpt4all import is_gpt4all_available, DEFAULT_GPT4ALL_MODEL, model_is_cached
print('GPT4All:', 'OK' if is_gpt4all_available() else 'нет')
print('Model:', DEFAULT_GPT4ALL_MODEL, 'cached=' + str(model_is_cached(DEFAULT_GPT4ALL_MODEL)))
"@

Write-Host "`nПроверка активного движка:" -ForegroundColor Cyan
python run_discovery.py llm --test

Write-Host "`nГотово. Discovery scan:" -ForegroundColor Green
Write-Host "  python run_discovery.py scan"
