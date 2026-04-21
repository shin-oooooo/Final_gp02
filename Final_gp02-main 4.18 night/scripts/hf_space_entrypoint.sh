#!/usr/bin/env sh
# Hugging Face Docker Space: emit early logs (otherwise "runtime error" can show with empty container logs).
# app_port in README.md must match the port we bind (default 8000).
set -eu
PORT="${PORT:-8000}"
cd /app
echo "[lreport] starting uvicorn at $(date -u +%Y-%m-%dT%H:%M:%SZ) port=${PORT} PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-}"
python -c "import sys; print('[lreport] python', sys.version.split()[0])"
python -c "import api.main; print('[lreport] api.main import ok')" || {
  echo "[lreport] FATAL: api.main import failed — see traceback above"
  exit 1
}
exec python -u -m uvicorn api.main:app --host 0.0.0.0 --port "${PORT}" --log-level info
