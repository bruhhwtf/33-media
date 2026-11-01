param([switch]$AcceptLargeDownload)
$ErrorActionPreference = 'Stop'
if (-not $AcceptLargeDownload) { throw 'This explicitly installs several GB of official PyTorch CUDA 12.4 packages plus SAM 2 (Apache-2.0). Re-run with -AcceptLargeDownload to proceed. No model weights are downloaded by this script.' }
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE)." } }
$backend = Join-Path $PSScriptRoot '..\backend'
$python = $env:CUTLAB_PYTHON
if (-not $python) { $python = Join-Path $env:LOCALAPPDATA 'BANDKLAN-CUTLAB\python\Scripts\python.exe' }
if (-not (Test-Path $python)) { throw 'Run setup-windows.ps1 first, or set CUTLAB_PYTHON to a Python 3.11 virtual environment executable.' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Install Git for Windows first; the SAM 2 source is pinned to an official Git commit.' }
& $python -m pip install setuptools==75.8.0 wheel==0.45.1; Check-Exit
& $python -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124; Check-Exit
& $python -m pip install hydra-core==1.3.2 omegaconf==2.3.0 iopath==0.1.10 tqdm==4.67.1 PyYAML==6.0.3 portalocker==3.2.0 'antlr4-python3-runtime==4.9.3'; Check-Exit
# Officially supported flag; no custom CUDA extension is needed for tracking.
$env:SAM2_BUILD_CUDA = '0'
& $python -m pip install --no-build-isolation --requirement (Join-Path $backend 'requirements-model.txt'); Check-Exit
& $python -c 'import torch,sam2; print("PyTorch",torch.__version__,"CUDA",torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU fallback (slow)")'; Check-Exit
Write-Host 'Open CUTLAB > Model setup > Download official Tiny weights (~156 MB).'
