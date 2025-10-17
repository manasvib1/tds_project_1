#!/usr/bin/env bash
set -euo pipefail

# Print a little debug info (HF runtime shows these logs)
echo "[BOOT] Environment snapshot (partial):"
echo "OPENAI_BASE_URL=${OPENAI_BASE_URL:-<not set>}"
echo "OPENAI_API_KEY set?: ${OPENAI_API_KEY:+yes}"
echo "EXPECTED_SECRET=${EXPECTED_SECRET:-<not set>}"
echo "GITHUB_USERNAME=${GITHUB_USERNAME:-<not set>}"

# Run uvicorn on port 7860
exec uvicorn api.server:app --host 0.0.0.0 --port 7860 --proxy-headers
