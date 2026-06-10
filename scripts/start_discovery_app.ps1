# Launch Atlas Discovery desktop app (browser UI)
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Starting Atlas Discovery Agent app..."
Write-Host "Browser will open at http://localhost:8501"
Write-Host "Press Ctrl+C to stop."

python -m streamlit run discovery_app.py --server.headless false
