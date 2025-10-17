#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=api
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
