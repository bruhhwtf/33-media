$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE)." } }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) { throw 'Install FFmpeg and ffprobe on PATH first. See docs/WINDOWS.md.' }
$venv = Join-Path $env:LOCALAPPDATA 'BANDKLAN-CUTLAB\python'
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) { py -3.11 -m venv $venv; Check-Exit }
$python = Join-Path $venv 'Scripts\python.exe'
& $python -m pip install --requirement backend/requirements.txt; Check-Exit
[Environment]::SetEnvironmentVariable('CUTLAB_PYTHON', $python, 'User')
$env:CUTLAB_PYTHON = $python
npm ci; Check-Exit
npm run build; Check-Exit
Write-Host "Base setup complete. Python: $python"
Write-Host 'For segmentation, run scripts/setup-model.ps1 -AcceptLargeDownload, then explicitly download weights in Model Setup.'
