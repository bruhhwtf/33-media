#!/usr/bin/env bash
set -euo pipefail
cd /workspace/33-media
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
# Electron's supported download proxy, with checksum/TLS verification retained.
export ELECTRON_GET_USE_PROXY=1
export GLOBAL_AGENT_HTTP_PROXY="${HTTPS_PROXY:-${HTTP_PROXY:-}}"
npm ci
npm run build
.venv/bin/python -m unittest discover -s tests -v
