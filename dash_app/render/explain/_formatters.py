"""复用的 MD 格式化工具（跨 FigX 讲解卡片共用）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


ENTROPY_WINDOW_DEFAULT = 21


def cov_to_markdown_table(c: np.ndarray, headers: List[str]) -> str:
    """把协方差矩阵格式化为 MD 表格。"""
    if c.size == 0:
        return "—"
    n = c.shape[0]
    head = "| |" + "|".join(headers[:n]) + "|"
    sep = "|---|---|" + "|".join(["---"] * n) + "|"
    rows = [head, sep]
    for i in range(n):
        lab = headers[i] if i < len(headers) else str(i)
        cells = "|" + lab + "|"
        cells += "|".join(f"{float(c[i, j]):.6e}" for j in range(n)) + "|"
        rows.append(cells)
    return "\n".join(rows)


def compute_figx2_physics_vars(
    json_path: str,
    snap_json: Dict[str, Any],
    symbols: List[str],
) -> Dict[str, Any]:
    """FigX.2 讲解需要的物理量（协方差 / 特征值 / 原始熵等）。"""
    from ass1_core import daily_returns, load_bundle
    from research.schemas import Phase0Input

    out: Dict[str, Any] = {
        "entropy_window": str(ENTROPY_WINDOW_DEFAULT),
        "p1_n_assets": "—",
        "p1_tail_cov_matrix_md": "—",
        "p1_cov_eigenvalues_csv": "—",
        "p1_cov_eigenvalue_weights_csv": "—",
        "p1_h_raw": "—",
        "p1_h_struct_is_fallback": "是",
        "zero_order_close_tail_md": "—",
    }
    p0 = snap_json.get("phase0") or {}
    meta = p0.get("meta") or {}
    rw = meta.get("resolved_windows") or {}
    tr_idx = p0.get("train_index") or []
    p0d = Phase0Input()
    ts = str(rw.get("train_start") or (tr_idx[0] if tr_idx else p0d.train_start))
    te = str(rw.get("train_end") or (tr_idx[-1] if tr_idx else p0d.train_end))
    if not symbols:
        return out
    try:
        bundle = load_bundle(json_path)
        close = bundle.close_universe.sort_index()
    except Exception:
        return out
    syms = [s for s in symbols if s in close.columns]
    out["p1_n_assets"] = str(len(syms))
    if len(syms) < 2:
        return out
    try:
        rets = daily_returns(close[syms]).dropna(how="all")
        t0, t1 = pd.Timestamp(ts), pd.Timestamp(te)
        mask = (rets.index >= t0) & (rets.index <= t1)
        sub = rets.loc[mask].dropna(how="any")
        win = ENTROPY_WINDOW_DEFAULT
        if len(sub) < win:
            out["p1_h_struct_is_fallback"] = "是"
            return out
        out["p1_h_struct_is_fallback"] = "否"
        tail = sub.iloc[-win:]
        c = tail.cov().to_numpy(dtype=float)
        out["p1_tail_cov_matrix_md"] = cov_to_markdown_table(c, syms)
        w, _ = np.linalg.eigh(c)
        w = np.maximum(w, 1e-18)
        s = float(w.sum())
        p = w / s
        out["p1_cov_eigenvalues_csv"] = ",".join(f"{float(x):.8e}" for x in w.tolist())
        out["p1_cov_eigenvalue_weights_csv"] = ",".join(f"{float(x):.8f}" for x in p.tolist())
        n = len(p)
        if n > 1:
            h_raw = -float(np.sum(p * np.log(p)))
            out["p1_h_raw"] = f"{h_raw:.10f}"
        cmask = (close.index >= t0) & (close.index <= t1)
        csub = close.loc[cmask, syms].dropna(how="any")
        if len(csub) >= 1:
            tail_px = csub.iloc[-min(3, len(csub)):]
            head = "|date|" + "|".join(syms) + "|"
            sep = "|---|---|" + "|".join(["---"] * len(syms)) + "|"
            lines = [head, sep]
            for idx, row in tail_px.iterrows():
                lines.append(
                    "|" + str(idx.date()) + "|" + "|".join(f"{float(row[s]):.4f}" for s in syms) + "|"
                )
            out["zero_order_close_tail_md"] = "\n".join(lines)
    except Exception:
        pass
    return out


def fmt_dict_md_row(label: str, d: Any) -> str:
    """字典 → ``- **label**： ...`` 嵌套列表。"""
    if not isinstance(d, dict) or not d:
        return f"- **{label}**：—"
    parts = [f"- **{label}**（`research/phase2.py` 概率块输出）："]
    for k, v in sorted(d.items(), key=lambda x: str(x[0])):
        try:
            fv = float(v)
            parts.append(f"  - `{k}`: {fv:.6f}")
        except (TypeError, ValueError):
            parts.append(f"  - `{k}`: {v}")
    return "\n".join(parts)


def fmt_traffic_md(d: Any) -> str:
    """model → 灯色 字典 → MD 表格。"""
    if not isinstance(d, dict) or not d:
        return "—"
    rows = ["|模型|灯色|", "|---|---|"]
    for k, v in sorted(d.items(), key=lambda x: str(x[0])):
        rows.append(f"|`{k}`|{v}|")
    return "\n".join(rows)


def tail_csv(vals: List[float], n: int = 8) -> str:
    """尾部 n 项拼成 CSV。"""
    if not vals:
        return "—"
    tail = vals[-n:]
    return ",".join(f"{float(x):.6f}" for x in tail)


def merge_base_vm(
    ui_mode: Optional[str],
    snap_json: Dict[str, Any],
    pol: Any,
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    symbols: List[str],
) -> Dict[str, Any]:
    """合并 ``render.explain.figure_captions._fmt_vars`` 的基础变量 + 额外字段。"""
    from dash_app.render.explain.figure_captions import _fmt_vars

    mode = (ui_mode or "invest").lower()
    if mode not in ("invest", "research"):
        mode = "invest"
    vm: Dict[str, Any] = dict(_fmt_vars(mode, snap_json, pol, p2, meta))
    cred = float(p2.get("credibility_score", p2.get("consistency_score")) or 0.0)
    vm["credibility"] = f"{cred:.8f}"
    vm["consistency"] = vm["credibility"]
    vm["p0_symbols_csv"] = ",".join(symbols)
    return vm
