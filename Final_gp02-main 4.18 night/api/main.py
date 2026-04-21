"""FastAPI: health, pipeline snapshot, background Monte Carlo."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

_THIS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_THIS)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import BackgroundTasks, FastAPI
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from research.crawl4ai_config import risk_search_params_dict
from research.integrations import load_external_integrations
from research.pipeline import run_pipeline, snapshot_to_jsonable
from research.schemas import DefensePolicyConfig, Phase0Input
from research.phase3 import jump_diffusion_paths_vectorized

app = FastAPI(title="AIE1902 Research API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_mc_cache: Dict[str, Any] = {}
_dash_mount_error: Optional[str] = None

# Mount Dash before defining /dash redirect. If mount fails, do not register GET /dash or
# Starlette's redirect_slashes will alternate /dash ↔ /dash/ (browser: too many redirects).
try:
    try:
        from a2wsgi import WSGIMiddleware  # type: ignore
    except Exception:  # pragma: no cover
        from starlette.middleware.wsgi import WSGIMiddleware  # type: ignore

    from dash_app.app import create_dash_app

    dash_app = create_dash_app(route_prefix="/", requests_prefix="/dash/")
    app.mount("/dash", WSGIMiddleware(dash_app.server))
except Exception as e:
    import logging

    _dash_mount_error = repr(e)
    logging.exception("Dash mount skipped: %s", e)

if _dash_mount_error is None:

    @app.get("/dash")
    def dash_no_trailing_slash() -> RedirectResponse:
        """Match /dash → /dash/ so the mounted WSGI app receives a consistent prefix."""
        return RedirectResponse(url="/dash/")


@app.get("/")
def root() -> Any:
    """Landing page: bare GET / used to return 404 JSON; redirect to Dash UI."""
    if _dash_mount_error is None:
        return RedirectResponse(url="/dash/")
    return HTMLResponse(
        status_code=200,
        content=(
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>AIE1902 API</title></head><body>"
            "<h1>AIE1902 Research API</h1>"
            "<p>Dash UI did not mount. Open <a href='/docs'>/docs</a> or "
            "<a href='/api/health'>GET /api/health</a>.</p>"
            f"<pre>{_dash_mount_error}</pre></body></html>"
        ),
    )


@app.get("/api")
def api_index() -> Dict[str, Any]:
    """GET /api alone used to 404; return a small discovery document."""
    return {
        "service": "AIE1902 Research API",
        "docs": "/docs",
        "redoc": "/redoc",
        "dash_ui": "/dash/",
        "health": "/api/health",
        "analyze": {"method": "POST", "path": "/api/analyze", "note": "JSON body: sentiment, policy, data_path, phase0"},
        "integrations": "/api/integrations",
    }


class AnalyzeBody(BaseModel):
    data_path: Optional[str] = None
    sentiment: float = -0.1
    policy: Optional[Dict[str, Any]] = None
    phase0: Optional[Dict[str, Any]] = None
    sentiment_detail: Optional[Dict[str, Any]] = None
    custom_portfolio_weights: Optional[Dict[str, float]] = None


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "stack": "FastAPI+Dash"}


@app.get("/api/integrations")
def integrations_config() -> Dict[str, Any]:
    """Crawl4AI / Ollama / 财经资讯 URL 配置（供各 Phase 与前端统一读取）。"""
    return load_external_integrations().model_dump()


@app.get("/api/integrations/ollama/health")
def ollama_health() -> Dict[str, Any]:
    import requests

    cfg = load_external_integrations()
    url = f"{cfg.ollama_base_url.rstrip('/')}/api/tags"
    try:
        r = requests.get(url, timeout=3.0)
        return {"reachable": r.ok, "status_code": r.status_code, "url": url}
    except Exception as e:
        return {"reachable": False, "error": repr(e), "url": url}


@app.get("/api/integrations/crawl4ai/seeds")
def crawl4ai_seeds() -> Dict[str, Any]:
    return risk_search_params_dict()


@app.post("/api/analyze")
def analyze(body: AnalyzeBody) -> Dict[str, Any]:
    pol = DefensePolicyConfig(**body.policy) if body.policy else DefensePolicyConfig()
    p0 = Phase0Input(**body.phase0) if body.phase0 else Phase0Input()
    snap = run_pipeline(
        json_path=body.data_path,
        phase0_in=p0,
        policy=pol,
        sentiment_score=body.sentiment,
        sentiment_detail=body.sentiment_detail,
        custom_portfolio_weights=body.custom_portfolio_weights,
    )
    return snapshot_to_jsonable(snap)


def _run_mc_task(key: str, s0: float, mu: float, sigma: float, p_jump: float, impact: float) -> None:
    import numpy as np

    p0, p1 = jump_diffusion_paths_vectorized(
        s0=s0,
        mu=mu,
        sigma=sigma,
        T=1.0,
        dt=1 / 252,
        n_paths=20_000,
        jump_lambda_annual=float(np.clip(p_jump, 0.0, 1.0)),
        jump_log_impact=float(np.clip(impact, -0.3, 0.3)),
    )
    _mc_cache[key] = {
        "conservative_median_end": float(np.median(p0[:, -1])),
        "conservative_mean_end": float(np.mean(p0[:, -1])),
        "stress_p5": float(np.percentile(p1[:, -1], 5)),
    }


@app.post("/api/monte-carlo")
def monte_carlo_bg(
    background_tasks: BackgroundTasks,
    s0: float = 1.0,
    mu: float = 0.0002,
    sigma: float = 0.01,
    p_jump: float = 0.05,
    impact: float = -0.15,
    task_key: str = "default",
):
    background_tasks.add_task(_run_mc_task, task_key, s0, mu, sigma, p_jump, impact)
    return {"queued": True, "key": task_key}


@app.get("/api/monte-carlo/{key}")
def monte_carlo_result(key: str) -> Dict[str, Any]:
    return _mc_cache.get(key, {"status": "pending"})


@app.get("/api/dash-status")
def dash_status() -> Dict[str, Any]:
    """Debug endpoint to verify Dash mount status."""
    return {"mounted": _dash_mount_error is None, "error": _dash_mount_error}


@app.get("/api/routes")
def list_routes() -> Dict[str, Any]:
    """Debug endpoint: list route paths to verify mounts."""
    out = []
    for r in app.router.routes:
        path = getattr(r, "path", None) or getattr(r, "path_format", None) or str(r)
        name = getattr(r, "name", None)
        out.append({"path": path, "name": name, "type": type(r).__name__})
    return {"n": len(out), "routes": out}


@app.get("/api/news/newapi")
def news_newapi(
    q: str = Query(
        default="",
        description="Search query for NewAPI (NewsAPI-like). Empty → default geo seed bundles.",
    ),
    date_from: str = Query(default="", description="YYYY-MM-DD. Empty → today-54d."),
    date_to: str = Query(default="", description="YYYY-MM-DD. Empty → today."),
    language: str = Query(default="en", description="Language code (default: en)."),
    max_items: int = Query(default=120, ge=1, le=500),
) -> Dict[str, Any]:
    """Debug endpoint: pull dated headlines from NewAPI provider.

    Requires env ``NEWSAPI_KEY``. Returns items with ``title``, ``published`` (day),
    ``publishedAt`` (API string), ``source``. Uses per-day chronological fetch; may be
    slower than a single-window call when the date span is wide.
    """
    from datetime import date as _date, timedelta as _td

    from research.crawl4ai_config import GEO_NEWS_QUERY_BUNDLES
    from research.news_newapi import fetch_newapi_headlines

    if not q.strip():
        q = " OR ".join(f"({x})" for x in GEO_NEWS_QUERY_BUNDLES)
    d_to = _date.fromisoformat(date_to) if date_to.strip() else _date.today()
    d_from = _date.fromisoformat(date_from) if date_from.strip() else (d_to - _td(days=54))

    rows, meta = fetch_newapi_headlines(
        q=q,
        max_items=int(max_items),
        date_from=d_from,
        date_to=d_to,
        language=str(language or "en"),
    )
    out = [
        {"title": t, "published": d.isoformat(), "publishedAt": pat, "source": src}
        for (t, d, src, pat) in rows
    ]
    return {"meta": meta, "items": out}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
