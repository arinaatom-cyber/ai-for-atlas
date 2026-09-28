# Register Windows Task Scheduler: every Monday 09:00 local time
# Runs scripts/run_weekly_discovery.ps1 (Ollama / Qwen on this computer)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $Root "scripts\run_weekly_discovery.ps1"
$taskName = "Atlas Discovery Weekly"

if (-not (Test-Path $script)) {
    throw "Missing $script"
}

$ps = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$tr = "`"$ps`" -NoProfile -ExecutionPolicy Bypass -File `"$script`""

Write-Host "Creating scheduled task: $taskName"
Write-Host "  Monday 09:00 local time"
Write-Host "  $tr"

schtasks /Create /TN $taskName /TR $tr /SC WEEKLY /D MON /ST 09:00 /RL LIMITED /F
if ($LASTEXITCODE -ne 0) {
    throw "schtasks failed: $LASTEXITCODE"
}

Write-Host ""
Write-Host "OK. Next run:"
schtasks /Query /TN $taskName /FO LIST /V | Select-String -Pattern "Task Name|Status|Next Run|Start Time|Days"
Write-Host ""
Write-Host "Run now:  schtasks /Run /TN `"$taskName`""
Write-Host "Remove:   schtasks /Delete /TN `"$taskName`" /F"
