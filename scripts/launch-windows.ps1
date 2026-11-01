$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not $env:CUTLAB_PYTHON) { $env:CUTLAB_PYTHON = Join-Path $env:LOCALAPPDATA 'BANDKLAN-CUTLAB\python\Scripts\python.exe' }
if (-not (Test-Path $env:CUTLAB_PYTHON)) { throw 'Python environment missing. Run scripts/setup-windows.ps1 first.' }
# Build once then launch the real desktop bundle; no separate web server needed.
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
npm run desktop
if ($LASTEXITCODE -ne 0) { throw 'Electron exited with an error.' }
