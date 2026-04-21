"""Phase 0: asset universe, time splits, orthogonality, environment report, dynamic beta."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from research.crawl4ai_config import risk_search_params_dict
from research.schemas import Phase0Input, Phase0Output


def _intersect_cols(df: pd.DataFrame, symbols: Sequence[str]) -> List[str]:
    return [s for s in symbols if s in df.columns]


class AssetManager:
    """Hierarchical asset groups with orthogonality pre-check."""

    def __init__(
        self,
        close: pd.DataFrame,
        train_start: str,
        train_end: str,
        test_start: str,
        test_end: str,
    ) -> None:
        self.close = close.sort_index()
        self.train_start = pd.Timestamp(train_start)
        self.train_end = pd.Timestamp(train_end)
        self.test_start = pd.Timestamp(test_start)
        self.test_end = pd.Timestamp(test_end)

    def slice_train(self) -> pd.DataFrame:
        m = (self.close.index >= self.train_start) & (self.close.index <= self.train_end)
        return self.close.loc[m].copy()

    def slice_test(self) -> pd.DataFrame:
        m = (self.close.index >= self.test_start) & (self.close.index <= self.test_end)
        return self.close.loc[m].copy()

    def pre_check_correlation(
        self,
        tech: Sequence[str],
        safe: Sequence[str],
        threshold: float = 0.3,
    ) -> Tuple[bool, str]:
        train = self.slice_train()
        tech_c = _intersect_cols(train, tech)
        safe_c = _intersect_cols(train, safe)
        if len(tech_c) < 1 or len(safe_c) < 1:
            return True, "缺少科技或避险组可用列，跳过正交性检验。"
        rets = train[tech_c + safe_c].pct_change().dropna(how="any")
        if rets.empty or len(rets) < 10:
            return True, "训练收益率样本不足，跳过正交性检验。"
        cross = []
        for a in tech_c:
            for b in safe_c:
                cross.append(float(rets[a].corr(rets[b])))
        mx = float(np.nanmax(np.abs(cross))) if cross else 0.0
        if mx > threshold:
            return (
                True,
                f"警告：训练期内科技组与避险组最大|Pearson相关|={mx:.3f} > {threshold}，"
                "对冲失效实验显著性可能被削弱，建议调整标的。",
            )
        return False, f"训练期科技-避险最大相关 |ρ|={mx:.3f}（阈值 {threshold}）。"


class Dynamic_Beta_Tracker:
    """各资产对基准（如 SPY）的 OLS Beta；用于稳态期 vs 断裂期对比（Phase0.md §4）。"""

    def __init__(self, returns: pd.DataFrame, benchmark: str) -> None:
        self.returns = returns.sort_index()
        self.benchmark = benchmark

    def _beta_for_mask(self, mask: pd.Series) -> Dict[str, float]:
        if self.benchmark not in self.returns.columns:
            return {}
        sub = self.returns.loc[mask].dropna(how="any")
        if sub.empty or len(sub) < 5:
            return {}
        yb = sub[self.benchmark].to_numpy(dtype=float)
        vx = float(np.var(yb, ddof=1)) or 1e-12
        out: Dict[str, float] = {}
        for c in sub.columns:
            if c == self.benchmark:
                continue
            y = sub[c].to_numpy(dtype=float)
            out[c] = float(np.cov(yb, y, ddof=1)[0, 1] / vx)
        return out

    def steady_vs_break(
        self,
        steady_mask: pd.Series,
        break_mask: pd.Series,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        return self._beta_for_mask(steady_mask), self._beta_for_mask(break_mask)


def train_test_indices(close: pd.DataFrame, inp: Phase0Input) -> Tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    tr = close.loc[(close.index >= pd.Timestamp(inp.train_start)) & (close.index <= pd.Timestamp(inp.train_end))]
    te = close.loc[(close.index >= pd.Timestamp(inp.test_start)) & (close.index <= pd.Timestamp(inp.test_end))]
    return tr.index, te.index


def _mean_beta_group(betas: Dict[str, float], syms: Sequence[str]) -> Optional[float]:
    vals = [betas[s] for s in syms if s in betas]
    if not vals:
        return None
    return float(np.mean(vals))


def run_phase0(close: pd.DataFrame, inp: Phase0Input) -> Phase0Output:
    close = close.sort_index()
    mgr = AssetManager(close, inp.train_start, inp.train_end, inp.test_start, inp.test_end)
    warn, msg = mgr.pre_check_correlation(inp.tech_symbols, inp.safe_symbols, inp.corr_warn_threshold)

    tr_idx, te_idx = train_test_indices(close, inp)
    train = close.reindex(tr_idx).dropna(how="all", axis=0)
    test = close.reindex(te_idx).dropna(how="all", axis=0)
    all_syms = sorted(set(inp.tech_symbols) | set(inp.hedge_symbols) | set(inp.safe_symbols) | {inp.benchmark})
    cols = [c for c in all_syms if c in close.columns]
    rets = close[cols].pct_change().dropna(how="all")

    steady_mask = pd.Series(rets.index.isin(train.index), index=rets.index)

    brk_a = pd.Timestamp(inp.regime_break_start)
    brk_b = pd.Timestamp(inp.regime_break_end)
    test_ix_set = set(test.index)
    in_break = rets.index.isin(test_ix_set) & (rets.index >= brk_a) & (rets.index <= brk_b)
    break_mask = pd.Series(in_break, index=rets.index)
    if int(break_mask.sum()) < 5:
        break_mask = pd.Series(rets.index.isin(test.index), index=rets.index)

    tracker = Dynamic_Beta_Tracker(rets, inp.benchmark)
    beta_steady, beta_stress = tracker.steady_vs_break(steady_mask, break_mask)

    train_rets = rets.loc[rets.index.intersection(train.index)]
    if not train_rets.empty and len(train_rets.columns) > 1:
        corr = train_rets.corr().to_dict()
    else:
        corr = {}

    tech_r = [s for s in inp.tech_symbols if s in cols and s != inp.benchmark]
    hedge_r = [s for s in inp.hedge_symbols if s in cols and s != inp.benchmark]
    safe_r = [s for s in inp.safe_symbols if s in cols and s != inp.benchmark]

    beta_group_steady = {
        "tech_mean": _mean_beta_group(beta_steady, tech_r),
        "hedge_mean": _mean_beta_group(beta_steady, hedge_r),
        "safe_mean": _mean_beta_group(beta_steady, safe_r),
    }

    test_rets = rets.loc[rets.index.intersection(test.index)]
    early_vol_mean: Optional[float] = None
    full_test_vol_mean: Optional[float] = None
    if not test_rets.empty and len(test_rets) >= 5:
        full_test_vol_mean = float(test_rets.std().mean())
        n_early = min(10, max(3, len(test_rets) // 2))
        early_vol_mean = float(test_rets.iloc[:n_early].std().mean())

    env = {
        "train_corr_preview": corr,
        "train_low_correlation_graph": corr,
        "test_semantic_noise_baseline": {
            "early_test_realized_vol_cross_section_mean": early_vol_mean,
            "full_test_realized_vol_cross_section_mean": full_test_vol_mean,
            "note": (
                "数值代理：测试集（初期/全段）日收益截面标准差均值，作背景波动基准；"
                "接入 Crawl4AI 后以语义噪声指标替换或并列展示。"
            ),
        },
        "beta_distribution_by_group_steady": beta_group_steady,
        "beta_steady": beta_steady,
        "beta_break": beta_stress,
        "crawl4ai_search_anchor": risk_search_params_dict(),
        "orthogonality_check": {"warning": warn, "message": msg},
        "time_series_split_note": (
            "训练/测试索引已隔离；下游 Scaler 须仅 fit 训练窗（本项目收益与协方差估计均按 train_mask 切片）。"
        ),
    }

    return Phase0Output(
        orthogonality_warning=warn,
        orthogonality_message=msg,
        train_index=[str(x.date()) for x in train.index],
        test_index=[str(x.date()) for x in test.index],
        environment_report=env,
        beta_steady=beta_steady,
        beta_stress=beta_stress,
        meta={
            "symbols_resolved": cols,
            "benchmark": inp.benchmark,
            "tech_symbols": tech_r,
            "hedge_symbols": hedge_r,
            "safe_symbols": safe_r,
            "regime_break": [str(brk_a.date()), str(brk_b.date())],
        },
    )
