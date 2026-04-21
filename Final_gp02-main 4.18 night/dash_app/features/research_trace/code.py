"""Research trace — 源码读取 + 快照摘取。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from dash_app.features.research_trace.models import CodeRef


def load_code_excerpt(repo_root: str, ref: CodeRef) -> str:
    """读取 ``ref`` 指向的源码片段（带行号）为 Markdown 代码块字符串。"""
    p = Path(repo_root) / ref.path
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except Exception:
        return f"[无法读取源码] {ref.path}:{ref.start}-{ref.end}"
    s = max(1, int(ref.start))
    e = max(s, int(ref.end))
    chunk = lines[s - 1 : e]
    body = "\n".join(f"{i:>4}  {ln}" for i, ln in enumerate(chunk, start=s))
    return f"文件：`{ref.path}`（{s}–{e}）\n\n```\n{body}\n```"


def snapshot_value_excerpt(snap: Optional[Dict[str, Any]], trace_key: str) -> str:
    """Small human-readable excerpt for a given trace key from ``last-snap``。"""
    if not snap:
        return "（当前无快照；请先点击侧栏运行/应用）"
    p2 = snap.get("phase2") or {}
    p0 = snap.get("phase0") or {}
    meta = (p0.get("meta") or {}) if isinstance(p0.get("meta"), dict) else {}
    if trace_key == "p2_credibility":
        return (
            f"credibility_score={p2.get('credibility_score')} "
            f"base={p2.get('credibility_base_jsd')} "
            f"penalty={p2.get('credibility_coverage_penalty')} "
            f"jsd_triangle_mean={p2.get('jsd_triangle_mean')} "
            f"density_test_failed={p2.get('density_test_failed')}"
        )
    if trace_key == "p2_shadow_mse":
        return (
            f"mse_naive={p2.get('mse_naive')} mse_arima={p2.get('mse_arima')} "
            f"mse_lightgbm={p2.get('mse_lightgbm')} mse_kronos={p2.get('mse_kronos')} "
            f"best_model_per_symbol.size={len((p2.get('best_model_per_symbol') or {}))}"
        )
    if trace_key == "p2_prob_tests":
        return (
            f"prob_nll_mean={p2.get('prob_nll_mean')} "
            f"prob_dm_pvalue_vs_naive={p2.get('prob_dm_pvalue_vs_naive')} "
            f"prob_coverage_95={p2.get('prob_coverage_95')}"
        )
    if trace_key == "st_series":
        st = meta.get("test_sentiment_st") or {}
        ds = st.get("dates") or []
        vs = st.get("values") or []
        n = min(len(ds), len(vs))
        head = ", ".join(f"{ds[i]}:{vs[i]:+.3f}" for i in range(min(6, n))) if n else "—"
        return f"S_t points={n}; head={head}"
    if trace_key == "windows":
        rw = meta.get("resolved_windows") or {}
        return f"resolved_windows={rw}"
    return "—"
