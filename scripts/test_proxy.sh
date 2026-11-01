#!/usr/bin/env bash
# Test proxy reachability FROM the Rock Pi (not from your PC).
# Usage:
#   PROXY='http://user:pass@host:port' bash scripts/test_proxy.sh
set -euo pipefail

PROXY="${PROXY:-${GEMINI_PROXY:-}}"
if [[ -z "${PROXY}" ]]; then
  echo "Set PROXY or GEMINI_PROXY first"
  exit 1
fi

HOSTPORT="$(python3 - <<'PY' "${PROXY}"
import sys
from urllib.parse import urlparse
u = urlparse(sys.argv[1])
print(f"{u.hostname} {u.port or 3128}")
PY
)"
HOST="$(echo "${HOSTPORT}" | awk '{print $1}')"
PORT="$(echo "${HOSTPORT}" | awk '{print $2}')"

echo "=== 1) TCP to proxy ${HOST}:${PORT} ==="
if command -v nc >/dev/null 2>&1; then
  nc -vz -w 5 "${HOST}" "${PORT}" || echo "TCP FAIL"
else
  timeout 5 bash -c "echo >/dev/tcp/${HOST}/${PORT}" && echo "TCP OK" || echo "TCP FAIL"
fi

echo
echo "=== 2) HTTPS via proxy to Google Generative Language ==="
curl -v -x "${PROXY}" --max-time 20 \
  "https://generativelanguage.googleapis.com/" || true

echo
echo "=== 3) List models (needs GEMINI_API_KEY) ==="
if [[ -n "${GEMINI_API_KEY:-}" ]]; then
  curl -sS -x "${PROXY}" --max-time 30 \
    "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_KEY}" \
    | head -c 400
  echo
else
  echo "Skip: export GEMINI_API_KEY=..."
fi
