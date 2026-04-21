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

# Kronos weights presence check — surfaces LFS/pointer errors immediately in HF
# logs rather than waiting for the first /api/analyze request to blow up.
if ! python - <<'PY'
from kronos_predictor import kronos_parameters_available
if kronos_parameters_available():
    print("[lreport] kronos weights ok (model + tokenizer .safetensors present)")
    raise SystemExit(0)
print("[lreport] kronos weights NOT READY — check kronos_weights/kronos-small + tokenizer-base LFS state")
raise SystemExit(1)
PY
then
  echo "[lreport] WARN: Kronos weights not ready; continuing (phase2 will fall back to non-Kronos models)"
fi

# News-fetch cache seed check — on HF we replay the committed snapshot instead
# of running live Crawl4AI / RSS fetches (see research/sentiment/sources_cache.py).
python - <<'PY' || true
import os, json
p = os.environ.get("LREPORT_NEWS_FETCH_JSON") or "/app/news_fetch_log.json"
if os.path.isfile(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            n = len((json.load(f) or {}).get("headlines") or [])
        print(f"[lreport] news cache seed ok: {n} headlines at {p}")
    except Exception as e:
        print(f"[lreport] news cache seed unreadable ({e}) — sentiment will fall back to fallback=0.0")
else:
    print(f"[lreport] news cache seed MISSING at {p} — sentiment pipeline will attempt live fetch")
PY

exec python -u -m uvicorn api.main:app --host 0.0.0.0 --port "${PORT}" --log-level info
