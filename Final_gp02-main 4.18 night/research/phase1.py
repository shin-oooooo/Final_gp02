"""Phase 1: ADF / Ljung–Box on log returns (with differencing), structural entropy (per-asset diagnostics)."""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from research.schemas import AssetDiagnostic, DefensePolicyConfig, Phase1Input, Phase1Output


def _adf_pvalue(series: np.ndarray) -> float:
    try:
        from statsmodels.tsa.stattools import adfuller
    except Exception:
        return 0.5

    x = np.asarray(series, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 10:
        return 1.0
    return float(adfuller(x, autolag="AIC")[1])


def _ljung_box_p(series: np.ndarray, lags: int = 10) -> Optional[float]:
    try:
        from statsmodels.stats.diagnostic import acorr_ljungbox
    except Exception:
        return None
    r = np.asarray(series, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < lags + 5:
        return None
    lb = acorr_ljungbox(r, lags=[lags], return_df=True)
    return float(lb["lb_pvalue"].iloc[0])


def _log_returns(sym: str, rets: pd.DataFrame, close_train: Optional[pd.DataFrame]) -> np.ndarray:
    """Primary: ln(P_t/P_{t-1}) from training close; fallback: ln(1+r_simple) from pipeline returns."""
    if close_train is not None and sym in close_train.columns:
        px = close_train[sym].dropna().astype(float)
        px = px[px > 0]
        if len(px) >= 31:
            lr = np.diff(np.log(px.to_numpy(dtype=float)))
            return lr[np.isfinite(lr)]
    if sym not in rets.columns:
        return np.array([])
    s = rets[sym].dropna().to_numpy(dtype=float)
    s = s[np.isfinite(s)]
    if len(s) < 30:
        return np.array([])
    return np.log1p(s).astype(float)


def _adf_diff_pipeline(
    lr: np.ndarray,
    thresh: float,
) -> Tuple[int, bool, bool, float, float, Optional[float], np.ndarray]:
    """
    ADF on log returns; if p>=thresh, difference until order 2.
    Returns: diff_order, stationary_final, basic_logic_failure, adf_p_level0, adf_p_final, lb_p, series_for_lb
    """
    lr = np.asarray(lr, dtype=float)
    lr = lr[np.isfinite(lr)]
    if len(lr) < 30:
        return 0, False, True, 1.0, 1.0, None, lr

    p0 = _adf_pvalue(lr)
    if p0 < thresh:
        lb_s = lr
        lb_p = _ljung_box_p(lb_s)
        return 0, True, False, p0, p0, lb_p, lb_s

    d1 = np.diff(lr)
    if len(d1) < 10:
        return 1, False, True, p0, 1.0, None, d1
    p1 = _adf_pvalue(d1)
    if p1 < thresh:
        lb_p = _ljung_box_p(d1)
        return 1, True, False, p0, p1, lb_p, d1

    d2 = np.diff(d1)
    if len(d2) < 10:
        return 2, False, True, p0, p1, None, d2
    p2 = _adf_pvalue(d2)
    if p2 < thresh:
        lb_p = _ljung_box_p(d2)
        return 2, True, False, p0, p2, lb_p, d2

    lb_p = _ljung_box_p(d2)
    return 2, False, True, p0, p2, lb_p, d2


def structural_entropy(cov: np.ndarray) -> float:
    """Normalized structural entropy from eigenvalues of covariance."""
    w, _ = np.linalg.eigh(cov)
    w = np.maximum(w, 1e-18)
    s = w.sum()
    p = w / s
    n = len(p)
    if n <= 1:
        return 1.0
    h = -float(np.sum(p * np.log(p)))
    return float(h / np.log(n))


def run_phase1(
    returns: pd.DataFrame,
    inp: Phase1Input,
    policy: DefensePolicyConfig,
    close_train: Optional[pd.DataFrame] = None,
) -> Phase1Output:
    rets = returns.dropna(how="all").copy()
    thresh = float(inp.adf_p_threshold)
    diagnostics: List[AssetDiagnostic] = []

    for sym in inp.symbols:
        lr = _log_returns(sym, rets, close_train)
        if len(lr) < 30:
            diagnostics.append(
                AssetDiagnostic(
                    symbol=sym,
                    adf_p=1.0,
                    stationary=False,
                    adf_p_returns=1.0,
                    stationary_returns=False,
                    diff_order=0,
                    basic_logic_failure=False,
                    ljung_box_p=None,
                    white_noise=False,
                    low_predictive_value=False,
                    max_weight_cap=None,
                    weight_zero=True,
                    p1_protocol_exclude=False,
                )
            )
            continue

        order, stat_ok, fail, p0, p_fin, lb_p, _lb_series = _adf_diff_pipeline(lr, thresh)
        wn = lb_p is not None and lb_p > 0.05
        vol_ann = 0.0
        if len(lr) >= 10:
            try:
                vol_ann = float(np.std(lr, ddof=1) * (252.0 ** 0.5))
            except Exception:
                vol_ann = 0.0
        ac1 = 0.0
        if len(lr) > 20:
            try:
                s = pd.Series(lr)
                ac1 = float(s.autocorr(lag=1) or 0.0)
            except Exception:
                ac1 = 0.0
        diagnostics.append(
            AssetDiagnostic(
                symbol=sym,
                adf_p=p0,
                stationary=stat_ok,
                adf_p_returns=p_fin,
                stationary_returns=stat_ok,
                diff_order=order,
                basic_logic_failure=fail,
                ljung_box_p=lb_p,
                white_noise=wn,
                low_predictive_value=wn,
                max_weight_cap=None,
                weight_zero=fail,
                vol_ann=vol_ann,
                ac1=ac1,
                p1_protocol_exclude=False,
            )
        )

    win = inp.entropy_window
    sub = rets.dropna(how="any")
    h_struct = 1.0
    if len(sub) >= win:
        tail = sub.iloc[-win:]
        c = tail.cov().to_numpy()
        h_struct = structural_entropy(c)

    gamma_mult = 3.0 if h_struct < policy.tau_h_gamma else 1.0

    return Phase1Output(
        h_struct=h_struct,
        gamma_multiplier=gamma_mult,
        diagnostics=diagnostics,
        pseudo_melt=False,
        pseudo_melt_detail="",
        sentiment_score=inp.sentiment_score,
    )
