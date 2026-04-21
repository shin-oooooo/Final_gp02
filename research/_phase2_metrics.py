"""Private math helpers for phase 2 (Gaussian divergences, JSD, DM test).

These are implementation details of ``research/phase2.py``; the public surface
lives there. Import with the underscore names preserved, e.g.:

    from research._phase2_metrics import (
        _gaussian_kl_forward,
        _js_divergence,
        _jsd_stress_rolling_breach,
        _triangle_js,
        _gaussian_nll,
        _dm_hac_t_pvalue,
    )
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from scipy.stats import norm


# ---------------------------------------------------------------------------
# Gaussian divergences
# ---------------------------------------------------------------------------

def _gaussian_kl_forward(m1: float, s1: float, m2: float, s2: float) -> float:
    """KL( N(m1,s1²) || N(m2,s2²) ), directional (internal to JSD)."""
    s1 = max(s1, 1e-8)
    s2 = max(s2, 1e-8)
    return float(np.log(s2 / s1) + (s1**2 + (m1 - m2) ** 2) / (2 * s2**2) - 0.5)


def _js_divergence(m1: float, s1: float, m2: float, s2: float) -> float:
    """Jensen-Shannon divergence between N(m1,s1²) and N(m2,s2²).

    Uses Gaussian moment-matched mixture approximation:
        μ_M = (m1+m2)/2,  σ²_M = (s1²+s2²)/2 + (m1-m2)²/4
    JSD ≈ 0.5·KL(P‖M) + 0.5·KL(Q‖M)
    Symmetric, bounded in [0, ~0.347].
    """
    s1 = max(s1, 1e-8)
    s2 = max(s2, 1e-8)
    mu_m = (m1 + m2) * 0.5
    var_m = (s1**2 + s2**2) * 0.5 + (m1 - m2) ** 2 * 0.25
    s_m = max(float(np.sqrt(var_m)), 1e-8)
    return float(
        0.5 * _gaussian_kl_forward(m1, s1, mu_m, s_m)
        + 0.5 * _gaussian_kl_forward(m2, s2, mu_m, s_m)
    )


def _jsd_stress_rolling_breach(
    daily_triangle_jsd: List[float],
    jsd_triangle_mean_full_window: float,
    *,
    n_window: int,
    k_jsd: float,
    jsd_baseline_mean: float,
    eps: float = 1e-9,
) -> bool:
    """True if any n_window-day rolling mean of triangle JSD exceeds k_jsd × training baseline."""
    thr = float(k_jsd) * max(float(jsd_baseline_mean), eps)
    nw = max(1, int(n_window))
    n = len(daily_triangle_jsd)
    if n >= nw:
        for t in range(nw - 1, n):
            roll = float(np.mean(daily_triangle_jsd[t + 1 - nw : t + 1]))
            if roll > thr:
                return True
        return False
    return float(jsd_triangle_mean_full_window) > thr


def _triangle_js(
    mus: Dict[str, float], sigs: Dict[str, float]
) -> Tuple[float, float, float, float]:
    """Pairwise JSD for the three primary models.

    Returns (jsd_kronos_arima, jsd_kronos_lgb, jsd_lgb_arima, mean).
    """
    mk, sk = mus["kronos"], sigs["kronos"]
    ma, sa = mus["arima"], sigs["arima"]
    ml, sl = mus["lightgbm"], sigs["lightgbm"]
    js_ka = _js_divergence(mk, sk, ma, sa)
    js_kg = _js_divergence(mk, sk, ml, sl)
    js_ga = _js_divergence(ml, sl, ma, sa)
    tri = (js_ka + js_kg + js_ga) / 3.0
    return js_ka, js_kg, js_ga, tri


# ---------------------------------------------------------------------------
# Likelihood / hypothesis-test helpers
# ---------------------------------------------------------------------------

def _gaussian_nll(y: float, mu: float, sigma: float) -> float:
    s = max(float(sigma), 1e-12)
    z = (float(y) - float(mu)) / s
    return float(0.5 * (np.log(2 * np.pi * s * s) + z * z))


def _dm_hac_t_pvalue(d: np.ndarray, lags: int = 5) -> Tuple[float, float]:
    """Diebold–Mariano style HAC t-stat; two-sided p under approximate normality."""
    d = np.asarray(d, dtype=float).flatten()
    n = len(d)
    if n < 8:
        return 0.0, 1.0
    mean_d = float(np.mean(d))
    dem = d - mean_d
    gamma0 = float(np.dot(dem, dem) / n)
    lr = gamma0
    for lag in range(1, min(lags, n - 1) + 1):
        w = 1.0 - lag / (lags + 1)
        cov = float(np.dot(dem[:-lag], dem[lag:]) / n)
        lr += 2.0 * w * cov
    var_mean = lr / max(n, 1)
    se = float(np.sqrt(max(var_mean, 1e-18)))
    t_stat = mean_d / se
    p_two = float(2.0 * (1.0 - norm.cdf(abs(t_stat))))
    return float(t_stat), p_two
