#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${PWD}"
if [[ ! -f frontend/dist/index.html ]]; then
  echo "Building frontend..."
  (cd frontend && npm run build)
fi
exec uvicorn backend.api.main:app --host 0.0.0.0 --port 43127
