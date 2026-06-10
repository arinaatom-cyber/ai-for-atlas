# Локальный Qwen без API-ключей (GPT4All + опционально Ollama)
Write-Host "=== Atlas: локальный ИИ ===" -ForegroundColor Cyan

pip install -r "$PSScriptRoot\..\requirements.txt"

Write-Host "`n1) GPT4All — Qwen2-1.5B (скачается при первом run_agent.py, ~1 GB)" -ForegroundColor Yellow
python -c "from gpt4all import GPT4All; print('Модели Qwen:', [m['filename'] for m in GPT4All.list_models() if 'qwen' in m.get('filename','').lower()][:5])"

Write-Host "`n2) Ollama (опционально, быстрее на GPU):" -ForegroundColor Yellow
Write-Host "   winget install Ollama.Ollama"
Write-Host "   ollama pull qwen2.5:3b"

Write-Host "`nЗапуск: python run_agent.py" -ForegroundColor Green
