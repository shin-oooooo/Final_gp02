"""Phase 2: heterogeneous models, probabilistic alignment, KL/JSD, consistency, shadow MSE.

Key change: run_phase2 now accepts test_mask and computes strict OOS forecasts for every
test date t using only returns with index < t (information set I_{t-1}).  The resulting
per-day μ(t)/σ(t) sequences are stored in model_mu_test_ts / model_sigma_test_ts and
exposed to the UI for honest time-series visualisation.
"""

from __future__ import annotations

import warnings
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import norm

from research.schemas import DefensePolicyConfig, Phase2Input, Phase2Output
from research._phase2_metrics import (
    _dm_hac_t_pvalue,
    _gaussian_nll,
    _js_divergence,
    _jsd_stress_rolling_breach,
    _triangle_js,
)

# Module-level suppression: statsmodels 对我们喂入的 DatetimeIndex（不等距交易日，无 freq）
# 会在 ARIMA 的 fit / forecast / get_prediction 各个阶段反复抛 ValueWarning：
#   - "A date index has been provided, but it has no associated frequency information..."
#   - "No supported index is available. Prediction results will be given with an integer index..."
# 这两条 warning 与预测正确性无关，只影响控制台可读性。这里一次性在模块加载时屏蔽，
# 避免在每个 per-symbol / per-OOS-step 的调用点重复 `with catch_warnings()` 包裹。
try:
    from statsmodels.tools.sm_exceptions import ValueWarning as _SMValueWarning

    warnings.filterwarnings(
        "ignore", category=_SMValueWarning, module=r"statsmodels\..*"
    )
except Exception:
    warnings.filterwarnings(
        "ignore",
        message=r".*(date index|No supported index).*",
        module=r"statsmodels\..*",
    )

# Lazy import: loading kronos_predictor pulls torch + kronos_model and spikes RAM at import time
# (problematic on small HF Spaces / Docker runtimes with empty-looking crash logs).
_KronosOneStepFn = Callable[[pd.Series, int], Tuple[float, bool]]
_kronos_one_step_mu_from_close_impl: Optional[_KronosOneStepFn] = None


def kronos_one_step_mu_from_close(
    close_series: pd.Series, lookback_max: int = 400
) -> Tuple[float, bool]:
    global _kronos_one_step_mu_from_close_impl
    if _kronos_one_step_mu_from_close_impl is None:
        try:
            from kronos_predictor import kronos_one_step_mu_from_close as _fn

            _kronos_one_step_mu_from_close_impl = _fn
        except ImportError:

            def _stub(
                close_series: pd.Series, lookback_max: int = 400
            ) -> Tuple[float, bool]:
                s = close_series.dropna().astype(float)
                if len(s) < 2:
                    return 0.0, False
                return float(s.pct_change().dropna().tail(120).mean()), False

            _kronos_one_step_mu_from_close_impl = _stub
    try:
        return _kronos_one_step_mu_from_close_impl(close_series, lookback_max)
    except RuntimeError:
        # Kronos 权重文件存在但模型加载失败（常见于 safetensors 不完整、内存不足或依赖版本不匹配）
        s = close_series.dropna().astype(float)
        if len(s) < 2:
            return 0.0, False
        return float(s.pct_change().dropna().tail(120).mean()), False


# Gaussian KL / JSD / triangle JS / rolling-breach helpers live in
# research/_phase2_metrics.py; imported above as underscore-prefixed names.

# ---------------------------------------------------------------------------
# Per-model point estimators (called with history up to t-1)
# ---------------------------------------------------------------------------

def _naive_mu(returns: pd.Series) -> float:
    return float(returns.iloc[-1]) if len(returns) else 0.0


def _arima_mu(returns: pd.Series) -> Tuple[float, float]:
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except Exception:
        return float(returns.mean()), float(returns.std(ddof=1) or 1e-4)

    s = returns.dropna().astype(float)
    if len(s) < 40:
        return float(s.mean()), float(s.std(ddof=1) or 1e-4)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = ARIMA(s, order=(1, 0, 1)).fit()
            fc = m.forecast(1)
            mu = float(fc.iloc[0]) if hasattr(fc, "iloc") else float(fc[0])
            sig = float(m.resid.dropna().std(ddof=1) or 1e-4)
        return mu, sig
    except Exception:
        return float(s.mean()), float(s.std(ddof=1) or 1e-4)


def _lgb_mu_sigma(train_rets: pd.Series) -> Tuple[float, float]:
    try:
        import lightgbm as lgb
    except Exception:
        return float(train_rets.mean()), float(train_rets.std(ddof=1) or 1e-4)

    df = pd.DataFrame({"y": train_rets.shift(-1), "x": train_rets}).dropna()
    if len(df) < 30:
        return float(train_rets.mean()), float(train_rets.std(ddof=1) or 1e-4)
    X = df[["x"]].to_numpy()
    y = df["y"].to_numpy()
    try:
        model = lgb.LGBMRegressor(n_estimators=80, learning_rate=0.05, verbosity=-1)
        model.fit(X, y)
        last_x = np.array([[float(train_rets.iloc[-1])]])
        mu = float(model.predict(last_x)[0])
        resid = y - model.predict(X)
        sig = float(np.std(resid, ddof=1) or 1e-4)
        return mu, sig
    except Exception:
        return float(train_rets.mean()), float(train_rets.std(ddof=1) or 1e-4)


def _kronos_mu_sigma(returns: pd.Series) -> Tuple[float, float]:
    """Statistical proxy for Kronos layer: long-window rolling statistics."""
    tail = returns.dropna().tail(120)
    if len(tail) < 10:
        return float(returns.mean()), float(returns.std(ddof=1) or 1e-4)
    return float(tail.mean()), float(tail.std(ddof=1) or 1e-4)


def _validation_sigma(returns: pd.Series, frac: float = 0.2) -> float:
    s = returns.dropna()
    if len(s) < 10:
        return 1e-4
    n = max(int(len(s) * (1 - frac)), 5)
    val = s.iloc[n:]
    return float(val.std(ddof=1) or 1e-4)


_SHADOW_TAIL_DEFAULT = 40  # default; overridden by DefensePolicyConfig.shadow_holdout_days
_MODELS = ["naive", "arima", "lightgbm", "kronos"]
# Default max test-date steps; overridden by DefensePolicyConfig.oos_fit_steps at runtime.
# Reduces ARIMA/LightGBM fit calls from O(T_test×N_sym) to O(oos_fit_steps×N_sym).
_MAX_OOS_STEPS = 10


def _mus_sigs_for_series(
    s: pd.Series,
    validation_sigma: float,
    kronos_mu_override: Optional[float] = None,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Compute (mu, sigma) for all four models given history s (I_{t-1})."""
    sig_val = max(float(validation_sigma), 1e-8)
    mus: Dict[str, float] = {}
    sigs: Dict[str, float] = {}
    mus["naive"] = _naive_mu(s)
    sigs["naive"] = sig_val
    ma, sa = _arima_mu(s)
    mus["arima"] = ma
    sigs["arima"] = max(sa, 1e-6)
    ml, sl = _lgb_mu_sigma(s)
    mus["lightgbm"] = ml
    sigs["lightgbm"] = max(sl, 1e-6)
    mk, sk = _kronos_mu_sigma(s)
    if kronos_mu_override is not None:
        mk = float(kronos_mu_override)
        sk = max(float(s.tail(60).std(ddof=1) or 1e-4), 1e-6)
    mus["kronos"] = mk
    sigs["kronos"] = max(sk, 1e-6)
    return mus, sigs


def _kronos_params_ok() -> bool:
    try:
        from kronos_predictor import kronos_parameters_available

        return bool(kronos_parameters_available())
    except Exception:
        return False


def _tail_holdout_scores(
    s: pd.Series,
    n_tail: int = _SHADOW_TAIL_DEFAULT,
    alpha_mse: float = 0.5,
    close_sym: Optional[pd.Series] = None,
    symbol: str = "",
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Per-model holdout evaluation on the last n_tail days of s.

    Returns (mse_scores, combined_scores).  combined = α·norm(MSE) + (1-α)·norm(JSD_to_empirical).
    Lower combined = better.

    When ``kronos_parameters_available()`` is True, Kronos MSE uses ``kronos_one_step_mu_from_close``
    on the **aligned** close series (same calendar index as ``s``); otherwise a 5-day rolling-mean
    proxy is used (no weights / no torch).
    """
    s = s.dropna().astype(float)
    n = len(s)
    if n < n_tail + 30:
        return {}, {}

    train_s = s.iloc[:-n_tail]
    val_s = s.iloc[-(n_tail + 1) :]
    actuals = [float(val_s.iloc[t + 1]) for t in range(n_tail)]
    mse_scores: Dict[str, float] = {}

    # Naive
    preds_n = [float(val_s.iloc[t]) for t in range(n_tail)]
    mse_scores["naive"] = float(np.mean([(p - a) ** 2 for p, a in zip(preds_n, actuals)]))

    sym_name = symbol or (str(s.name) if s.name is not None else "sym")
    if _kronos_params_ok():
        if close_sym is None:
            raise ValueError(
                "Kronos 权重已就绪：影子验证需要训练窗内对齐的收盘价列（请向 run_phase2 传入包含该标的的 close）。"
            )
        cser = close_sym.reindex(s.index).astype(float).ffill().bfill()
        k_errs: List[float] = []
        for t in range(n_tail):
            end_d = val_s.index[t]
            c_hist = cser.loc[cser.index <= end_d].dropna().astype(float)
            c_hist.name = sym_name
            if len(c_hist) < 30:
                raise ValueError(
                    f"影子验证 Kronos：截至 {end_d} 的收盘价不足 30 个交易日（标的 {sym_name}）。"
                )
            mu_k, _ok = kronos_one_step_mu_from_close(c_hist)
            k_errs.append((mu_k - actuals[t]) ** 2)
        mse_scores["kronos"] = float(np.mean(k_errs))
    else:
        # Kronos proxy when weights / torch stack unavailable
        ctx = list(train_s.values[-5:])
        k_errs = []
        for t in range(n_tail):
            pred_k = float(np.mean(ctx[-5:]))
            k_errs.append((pred_k - float(val_s.iloc[t + 1])) ** 2)
            ctx.append(float(val_s.iloc[t]))
        mse_scores["kronos"] = float(np.mean(k_errs))

    # ARIMA
    try:
        from statsmodels.tsa.arima.model import ARIMA as _ARIMA
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m_fit = _ARIMA(train_s, order=(1, 0, 1)).fit()
        resid = m_fit.resid.dropna()
        tail_r = resid.iloc[-n_tail:] if len(resid) >= n_tail else resid
        mse_scores["arima"] = float((tail_r ** 2).mean())
    except Exception:
        mse_scores["arima"] = mse_scores["naive"]

    # LightGBM
    try:
        import lightgbm as lgb
        df_tr = pd.DataFrame({"y": train_s.shift(-1), "x": train_s}).dropna()
        if len(df_tr) >= 30:
            model = lgb.LGBMRegressor(n_estimators=50, verbosity=-1)
            model.fit(df_tr[["x"]].to_numpy(), df_tr["y"].to_numpy())
            x_val = np.array([[float(val_s.iloc[t])] for t in range(n_tail)])
            lgb_preds = model.predict(x_val).flatten()
            mse_scores["lightgbm"] = float(np.mean((lgb_preds - np.array(actuals)) ** 2))
        else:
            mse_scores["lightgbm"] = mse_scores["naive"]
    except Exception:
        mse_scores["lightgbm"] = mse_scores["naive"]

    # JSD-to-empirical scores
    mu_emp = float(np.mean(actuals))
    sig_emp = float(np.std(actuals, ddof=1) or 1e-6)
    ms, ss = _mus_sigs_for_series(train_s, sig_emp)
    jsd_scores: Dict[str, float] = {
        m: _js_divergence(ms[m], ss[m], mu_emp, sig_emp) for m in _MODELS
    }

    max_mse = max(mse_scores.values()) or 1.0
    max_jsd = max(jsd_scores.values()) or 1.0
    alpha = float(np.clip(alpha_mse, 0.0, 1.0))
    combined: Dict[str, float] = {
        m: alpha * (mse_scores.get(m, max_mse) / max_mse)
        + (1.0 - alpha) * (jsd_scores.get(m, max_jsd) / max_jsd)
        for m in _MODELS
    }
    return mse_scores, combined


# _gaussian_nll / _dm_hac_t_pvalue live in research/_phase2_metrics.py.


def _probabilistic_oos_bundle(
    returns: pd.DataFrame,
    test_dates: pd.Index,
    symbols: List[str],
    mu_ts: Dict[str, Dict[str, List[float]]],
    sig_ts: Dict[str, Dict[str, List[float]]],
) -> Tuple[
    Dict[str, float],
    Dict[str, float],
    Dict[str, float],
    Dict[str, str],
    Dict[str, float],
    bool,
    float,
]:
    """Pooled Gaussian NLL, DM vs naive, coverage, traffic lights (3 models), full fail, naive cov."""
    models_struct = ["arima", "lightgbm", "kronos"]
    models_all = ["naive", "arima", "lightgbm", "kronos"]
    nll_lists: Dict[str, List[float]] = {m: [] for m in models_all}
    cov_hit: Dict[str, List[float]] = {m: [] for m in models_struct}
    cov_hit_naive: List[float] = []

    for j, t in enumerate(test_dates):
        for sym in symbols:
            try:
                y = float(returns.loc[t, sym])
            except Exception:
                continue
            if not np.isfinite(y):
                continue
            nll_row: Dict[str, float] = {}
            ok = True
            for m in models_all:
                ts_mu = (mu_ts.get(m) or {}).get(sym) or []
                ts_sg = (sig_ts.get(m) or {}).get(sym) or []
                if j >= len(ts_mu) or j >= len(ts_sg):
                    ok = False
                    break
                mu = float(ts_mu[j])
                sg = float(ts_sg[j])
                if not (np.isfinite(mu) and np.isfinite(sg)):
                    ok = False
                    break
                nll_row[m] = _gaussian_nll(y, mu, sg)
            if not ok or len(nll_row) != len(models_all):
                continue
            for m in models_all:
                nll_lists[m].append(nll_row[m])
            for m in models_struct:
                mu = float((mu_ts.get(m) or {}).get(sym)[j])
                sg = float((sig_ts.get(m) or {}).get(sym)[j])
                cov_hit[m].append(1.0 if abs(y - mu) <= 1.96 * max(sg, 1e-12) else 0.0)
            mu_n = float((mu_ts.get("naive") or {}).get(sym)[j])
            sg_n = float((sig_ts.get("naive") or {}).get(sym)[j])
            cov_hit_naive.append(1.0 if abs(y - mu_n) <= 1.96 * max(sg_n, 1e-12) else 0.0)

    prob_nll_mean: Dict[str, float] = {}
    for m in models_all:
        if nll_lists[m]:
            prob_nll_mean[m] = float(np.mean(nll_lists[m]))

    prob_dm_p: Dict[str, float] = {}
    prob_dm_t: Dict[str, float] = {}
    prob_cov: Dict[str, float] = {}
    lights: Dict[str, str] = {}

    nvec = np.array(nll_lists["naive"], dtype=float) if nll_lists["naive"] else np.array([])
    for m in models_struct:
        if nvec.size < 5 or not nll_lists.get(m) or len(nll_lists[m]) != len(nvec):
            prob_dm_p[m] = 1.0
            prob_dm_t[m] = 0.0
            prob_cov[m] = float(np.mean(cov_hit[m])) if cov_hit[m] else 0.0
            lights[m] = "red"
            continue
        vm = np.array(nll_lists[m], dtype=float)
        d = nvec - vm
        t_stat, p_two = _dm_hac_t_pvalue(d)
        prob_dm_p[m] = p_two
        prob_dm_t[m] = t_stat
        prob_cov[m] = float(np.mean(cov_hit[m])) if cov_hit[m] else 0.0
        mean_d = float(np.mean(d))
        p_one = float(1.0 - norm.cdf(t_stat)) if mean_d >= 0 else float(norm.cdf(t_stat))
        cov_ok = 0.85 <= prob_cov[m] <= 0.99
        if mean_d > 0 and p_one < 0.05 and cov_ok:
            lights[m] = "green"
        elif mean_d > 0 and p_one < 0.05:
            lights[m] = "yellow"
        elif mean_d > 0:
            lights[m] = "yellow"
        else:
            lights[m] = "red"

    full_fail = (
        len(lights) == len(models_struct)
        and all(lights.get(m) == "red" for m in models_struct)
    )
    prob_cov_naive = float(np.mean(cov_hit_naive)) if cov_hit_naive else 0.0
    return prob_nll_mean, prob_dm_p, prob_dm_t, lights, prob_cov, full_fail, prob_cov_naive


def _cross_section_mean_mu_per_day(
    mu_ts: Dict[str, Dict[str, List[float]]],
    models: List[str],
    symbols: List[str],
    n_days: int,
) -> np.ndarray:
    """One scalar per test day: mean of all finite model×symbol OOS μ."""
    out = np.full(n_days, np.nan, dtype=float)
    for k in range(n_days):
        vs: List[float] = []
        for m in models:
            row = mu_ts.get(m) or {}
            for s in symbols:
                arr = row.get(s) or []
                if k < len(arr):
                    v = arr[k]
                    if np.isfinite(v):
                        vs.append(float(v))
        if vs:
            out[k] = float(np.mean(vs))
    return pd.Series(out).ffill().bfill().to_numpy(dtype=float)


# ---------------------------------------------------------------------------
# Internal helpers (extracted 2026-04-21 from ``run_phase2`` body to keep that
# function under ~400 lines without altering its public signature/return shape).
# All helpers below are pure transforms over their explicit arguments.
# ---------------------------------------------------------------------------

def _rolling_mean_seq(seq: List[float], w: int) -> List[float]:
    """Right-aligned simple rolling mean of ``seq`` over window ``w``.

    Returns an empty list when ``len(seq) < w``. Pure; matches the inline
    helper that previously lived inside ``run_phase2``.
    """
    ww = max(1, int(w))
    if len(seq) < ww:
        return []
    out: List[float] = []
    for i in range(ww - 1, len(seq)):
        out.append(float(np.mean(seq[i + 1 - ww : i + 1])))
    return out


def _train_baseline_rolling_jsd(
    *,
    train: pd.DataFrame,
    symbols: List[str],
    models: List[str],
    inp: Phase2Input,
    policy: DefensePolicyConfig,
    jsd_triangle_mean: float,
) -> float:
    """Compute rolling triangle-JSD baseline on the train window (mean over rolling means).

    Mirrors the OOS test-loop information-set semantics: for each train day t,
    fit μ/σ on history < t and compute triangle JSD. To keep cost manageable on
    long train windows, fits are subsampled (``baseline_fit_steps``) and forward-
    padded otherwise. Returns the rolling-window mean (window = ``policy.semantic_cosine_window``,
    floor = 5). Falls back to per-day mean if rolling window cannot be formed,
    and ultimately to ``jsd_triangle_mean`` if the train window has no rows.
    """
    daily_tri_train: List[float] = []
    train_idx = train.index
    _stress_w = int(getattr(policy, "semantic_cosine_window", 5) or 5)
    # Need enough history to let ARIMA/LGB stabilize; the stress window itself is small
    # (W = semantic_cosine_window, default 5), so enforce a floor of 40 trading days.
    min_hist = int(max(40, _stress_w, 15))

    n_train = len(train_idx)
    baseline_fit_steps = int(max(6, min(30, getattr(policy, "oos_fit_steps", 10) * 2)))
    if n_train <= baseline_fit_steps:
        fit_positions = set(range(n_train))
    else:
        fit_positions = set(int(round(i)) for i in np.linspace(0, n_train - 1, baseline_fit_steps))

    _last_ms_train: Dict[str, Dict[str, float]] = {m: {s: 0.0 for s in symbols} for m in models}
    _last_ss_train: Dict[str, Dict[str, float]] = {m: {s: 1e-4 for s in symbols} for m in models}

    for t_pos, t in enumerate(train_idx):
        if t_pos < min_hist:
            continue
        tri_sym: List[float] = []
        for sym in symbols:
            if t_pos in fit_positions:
                hist = train.loc[train.index < t, sym].dropna().astype(float)
                if len(hist) < 15:
                    continue
                sig_v = float(inp.validation_residuals_std.get(sym) or _validation_sigma(hist))
                msb, ssb = _mus_sigs_for_series(hist, sig_v)
                for m in models:
                    _last_ms_train[m][sym] = float(msb[m])
                    _last_ss_train[m][sym] = float(ssb[m])
            else:
                msb = {m: _last_ms_train[m][sym] for m in models}
                ssb = {m: _last_ss_train[m][sym] for m in models}
            _, _, _, tri = _triangle_js(msb, ssb)
            if np.isfinite(tri):
                tri_sym.append(float(tri))
        if tri_sym:
            daily_tri_train.append(float(np.mean(tri_sym)))

    train_roll = _rolling_mean_seq(daily_tri_train, _stress_w)
    if train_roll:
        return float(np.mean(train_roll))
    if daily_tri_train:
        return float(np.mean(daily_tri_train))
    return float(jsd_triangle_mean)


def _build_jsd_matrix(
    *,
    dates_iso: List[str],
    models: List[str],
    mu_ts: Dict[str, Dict[str, List[float]]],
    sig_ts: Dict[str, Dict[str, List[float]]],
    mus: Dict[str, Dict[str, float]],
    sigs: Dict[str, Dict[str, float]],
    symbols: List[str],
) -> Dict[str, Dict[str, float]]:
    """Build the per-pair-of-models triangular JS-divergence matrix.

    Test-period averaged when OOS rows exist (``dates_iso`` non-empty); otherwise
    falls back to train-end scalars in ``mus``/``sigs``.
    """
    jsd_mat: Dict[str, Dict[str, float]] = {}
    if dates_iso:
        for i, mi in enumerate(models):
            for mj in models[i + 1:]:
                day_means: List[float] = []
                for j in range(len(dates_iso)):
                    pair_sym: List[float] = []
                    for sym in symbols:
                        if j >= len(mu_ts[mi][sym]):
                            continue
                        a = mu_ts[mi][sym][j]
                        b = sig_ts[mi][sym][j]
                        c = mu_ts[mj][sym][j]
                        d = sig_ts[mj][sym][j]
                        if not all(np.isfinite([a, b, c, d])):
                            continue
                        pair_sym.append(_js_divergence(float(a), float(b), float(c), float(d)))
                    if pair_sym:
                        day_means.append(float(np.mean(pair_sym)))
                jsd_mat.setdefault(mi, {})[mj] = float(np.mean(day_means)) if day_means else 0.0
    else:
        for i, mi in enumerate(models):
            for mj in models[i + 1:]:
                jsd_mat.setdefault(mi, {})[mj] = float(
                    np.mean([_js_divergence(mus[mi][s], sigs[mi][s], mus[mj][s], sigs[mj][s]) for s in symbols])
                )
    return jsd_mat


def _compose_shadow_note(
    *,
    mse_avail: Dict[str, float],
    credibility_score: float,
    policy: DefensePolicyConfig,
    full_fail: bool,
    density_test_failed: bool,
    credibility_coverage_penalty: float,
    prob_cov_naive_e: float,
) -> str:
    """Compose the human-readable shadow-note string emitted in ``Phase2Output.shadow_note``.

    Three additive segments: shadow-MSE summary (gated by τ_L1/τ_L2),
    full-pipeline-failure rider, and coverage-penalty rider. Empty when none apply.
    """
    note = ""
    if mse_avail:
        best_g = min(mse_avail, key=mse_avail.get)
        worst_g = max(mse_avail, key=mse_avail.get)
        mse_str = "、".join(
            f"{m}={v * 1e4:.2f}e-4" for m, v in sorted(mse_avail.items(), key=lambda x: x[1])
        )
        if credibility_score <= policy.tau_l2:
            note = (
                f"⛔ 熔断：影子验证最优 {best_g}、最差 {worst_g}（{mse_str}）；"
                "各资产均值已路由至影子最优模型预测。"
            )
        elif credibility_score <= policy.tau_l1:
            note = (
                f"⚠ 警戒：模型分歧上升，影子最优 {best_g}，{worst_g} 偏差最大（{mse_str}）；"
                "各资产使用影子最优模型均值预测。"
            )

    if full_fail:
        note = ((note + " ") if note else "") + (
            "【概率·全流程】ARIMA/LightGBM/Kronos 相对 Naive 的样本外 NLL 未通过 DM 改良检验（三模型均红灯），"
            "判定概率预测全流程失效。"
        )
    if density_test_failed and credibility_coverage_penalty > 0.0:
        note = ((note + " ") if note else "") + (
            f"【可信度】名义 95% 带实证覆盖率低于 Naive（Cov_Naive≈{prob_cov_naive_e:.2f}），"
            f"已扣减惩罚 {credibility_coverage_penalty:.3f}（β·JSD 与上限取 min）。"
        )
    return note


def _recompute_semantic_logic_break(
    *,
    st_arr: Optional[np.ndarray],
    best_model_per_symbol: Dict[str, str],
    dates_iso: List[str],
    symbols: List[str],
    mu_ts: Dict[str, Dict[str, List[float]]],
    cos_win: int,
) -> Tuple[bool, bool, float]:
    """Re-evaluate the semantic-vs-numeric rolling cosine logic-break.

    Returns ``(logic_break_sem, sem_cos_ok, cos_out)``. Uses the shadow-optimal
    μ cross-section mean as the numeric side; degenerate cases all return
    ``(False, False, 0.0)`` (matches legacy behaviour).
    """
    if st_arr is None or not best_model_per_symbol or len(dates_iso) < cos_win:
        return False, False, 0.0
    n_days_cos = len(dates_iso)
    best_mu_tmp: List[float] = []
    for day_idx in range(n_days_cos):
        vals_tmp: List[float] = []
        for sym in symbols:
            bm_tmp = best_model_per_symbol.get(sym, "naive")
            ts_row_tmp = mu_ts.get(bm_tmp, {}).get(sym) or []
            if day_idx < len(ts_row_tmp) and np.isfinite(ts_row_tmp[day_idx]):
                vals_tmp.append(float(ts_row_tmp[day_idx]))
        best_mu_tmp.append(float(np.mean(vals_tmp)) if vals_tmp else float("nan"))
    best_mu_np = pd.Series(best_mu_tmp).ffill().bfill().to_numpy(dtype=float)
    if best_mu_np.size != n_days_cos:
        return False, False, 0.0
    from research.pipeline import _rolling_cosine_series as _rcs  # avoid circular at module level

    roll_cos = _rcs(st_arr, best_mu_np, cos_win)
    logic_break_sem = any(np.isfinite(v) and v < 0.0 for v in roll_cos)
    last_valid = next((v for v in reversed(roll_cos) if np.isfinite(v)), None)
    if last_valid is None:
        return bool(logic_break_sem), False, 0.0
    return bool(logic_break_sem), True, float(last_valid)


# ---------------------------------------------------------------------------
# Main Phase 2 entry point
# ---------------------------------------------------------------------------

def run_phase2(
    returns: pd.DataFrame,
    train_mask: pd.Series,
    test_mask: pd.Series,
    inp: Phase2Input,
    policy: DefensePolicyConfig,
    sentiment_series: Optional[pd.Series] = None,
    close: Optional[pd.DataFrame] = None,
    test_st_series: Optional[pd.Series] = None,
) -> Phase2Output:
    """Strict OOS Phase 2.

    For each test date t, predicts r_t using only returns with index < t (I_{t-1}).
    KL/JSD and consistency are aggregated over the test window, not train-end scalars.
    Falls back to train-end scalars when no test rows exist.
    """
    symbols = [s for s in inp.symbols if s in returns.columns]
    if not symbols:
        return Phase2Output(
            credibility_score=0.5,
            credibility_base_jsd=0.5,
            consistency_score=0.5,
            shadow_note="无可用标的",
            jsd_by_symbol={},
            test_daily_triangle_jsd_mean=[],
        )

    if _kronos_params_ok():
        if close is None:
            raise ValueError(
                "Kronos 权重已就绪：run_phase2 必须传入 close（各标的收盘价，与收益日历对齐）。"
            )
        miss_close = [s for s in symbols if s not in close.columns]
        if miss_close:
            head = ", ".join(miss_close[:10])
            more = " …" if len(miss_close) > 10 else ""
            raise ValueError(
                "Kronos 已就绪但 close 缺少下列标的列: " + head + more
            )

    kronos_real_any = False
    models = _MODELS
    tm = train_mask
    qm = test_mask
    if hasattr(tm, "reindex"):
        tm = tm.reindex(returns.index).fillna(False)
    if hasattr(qm, "reindex"):
        qm = qm.reindex(returns.index).fillna(False)
    train = returns.loc[tm].dropna(how="any")
    test_dates = returns.index[qm]

    # OOS time series containers
    mu_ts: Dict[str, Dict[str, List[float]]] = {m: {s: [] for s in symbols} for m in models}
    sig_ts: Dict[str, Dict[str, List[float]]] = {m: {s: [] for s in symbols} for m in models}
    dates_iso: List[str] = []

    # Endpoint scalars (last test day or train-end fallback)
    mus: Dict[str, Dict[str, float]] = {m: {} for m in models}
    sigs: Dict[str, Dict[str, float]] = {m: {} for m in models}

    daily_ka: List[float] = []
    daily_kg: List[float] = []
    daily_ga: List[float] = []
    daily_tri: List[float] = []
    jsd_all_pairs: List[float] = []
    jsd_acc: Dict[str, Dict[str, List[float]]] = {
        s: {"ka": [], "kg": [], "ga": [], "tri": []} for s in symbols
    }

    if len(test_dates) > 0:
        # Subsample fit dates; forward-pad unchanged μ/σ for intermediate steps.
        # oos_fit_steps comes from policy (sidebar-tunable); fallback to module default.
        oos_steps = max(1, int(getattr(policy, "oos_fit_steps", _MAX_OOS_STEPS)))
        n_test = len(test_dates)
        if n_test <= oos_steps:
            fit_indices = set(range(n_test))
        else:
            fit_indices = set(
                int(round(i)) for i in np.linspace(0, n_test - 1, oos_steps)
            )

        # Last fitted μ/σ per model per symbol (used for forward-pad)
        _last_ms: Dict[str, Dict[str, float]] = {m: {s: 0.0 for s in symbols} for m in models}
        _last_ss: Dict[str, Dict[str, float]] = {m: {s: 1e-4 for s in symbols} for m in models}

        for idx, t in enumerate(test_dates):
            dates_iso.append(str(t.date()))
            tri_sym: List[float] = []
            ka_sym: List[float] = []
            kg_sym: List[float] = []
            ga_sym: List[float] = []
            for sym in symbols:
                if idx in fit_indices:
                    hist = returns.loc[returns.index < t, sym].dropna().astype(float)
                    if len(hist) < 15:
                        for m in models:
                            mu_ts[m][sym].append(float("nan"))
                            sig_ts[m][sym].append(float("nan"))
                        continue
                    sig_val = float(inp.validation_residuals_std.get(sym) or _validation_sigma(hist))
                    k_override = None
                    if close is not None and sym in close.columns:
                        c_hist = close.loc[close.index < t, sym].dropna().astype(float)
                        c_hist.name = str(sym)
                        if _kronos_params_ok():
                            if len(c_hist) < 30:
                                raise ValueError(
                                    f"Kronos：标的 {sym} 在 {t} 之前不足 30 个有效收盘日（当前 {len(c_hist)}）。"
                                )
                            mu_k, ok_k = kronos_one_step_mu_from_close(c_hist)
                            k_override = mu_k
                            if ok_k:
                                kronos_real_any = True
                        elif len(c_hist) >= 30:
                            mu_k, ok_k = kronos_one_step_mu_from_close(c_hist)
                            k_override = mu_k
                            if ok_k:
                                kronos_real_any = True
                    ms, ss = _mus_sigs_for_series(hist, sig_val, kronos_mu_override=k_override)
                    for m in models:
                        _last_ms[m][sym] = ms[m]
                        _last_ss[m][sym] = ss[m]
                else:
                    ms = {m: _last_ms[m][sym] for m in models}
                    ss = {m: _last_ss[m][sym] for m in models}
                for m in models:
                    mu_ts[m][sym].append(ms[m])
                    sig_ts[m][sym].append(ss[m])
                js_ka, js_kg, js_ga, tri = _triangle_js(ms, ss)
                tri_sym.append(tri)
                ka_sym.append(js_ka)
                kg_sym.append(js_kg)
                ga_sym.append(js_ga)
                acc = jsd_acc.setdefault(sym, {"ka": [], "kg": [], "ga": [], "tri": []})
                acc["ka"].append(float(js_ka))
                acc["kg"].append(float(js_kg))
                acc["ga"].append(float(js_ga))
                acc["tri"].append(float(tri))
                for i in range(len(models)):
                    for j in range(i + 1, len(models)):
                        jsd_all_pairs.append(
                            _js_divergence(
                                ms[models[i]], ss[models[i]],
                                ms[models[j]], ss[models[j]],
                            )
                        )
            if tri_sym:
                daily_tri.append(float(np.mean(tri_sym)))
            if ka_sym:
                daily_ka.append(float(np.mean(ka_sym)))
            if kg_sym:
                daily_kg.append(float(np.mean(kg_sym)))
            if ga_sym:
                daily_ga.append(float(np.mean(ga_sym)))

        jsd_kronos_arima_mean = float(np.mean(daily_ka)) if daily_ka else 0.0
        jsd_kronos_gbm_mean = float(np.mean(daily_kg)) if daily_kg else 0.0
        jsd_gbm_arima_mean = float(np.mean(daily_ga)) if daily_ga else 0.0
        jsd_triangle_mean = float(np.mean(daily_tri)) if daily_tri else 0.0
        jsd_triangle_max = float(max(jsd_kronos_arima_mean, jsd_kronos_gbm_mean, jsd_gbm_arima_mean))
        jsd_pairs_mean = float(np.mean(jsd_all_pairs)) if jsd_all_pairs else 0.0

        jsd_by_symbol: Dict[str, Dict[str, float]] = {}
        for s in symbols:
            acc = jsd_acc.get(s) or {}
            jsd_by_symbol[s] = {
                "kronos_arima": float(np.mean(acc["ka"])) if acc.get("ka") else 0.0,
                "kronos_gbm": float(np.mean(acc["kg"])) if acc.get("kg") else 0.0,
                "gbm_arima": float(np.mean(acc["ga"])) if acc.get("ga") else 0.0,
                "triangle": float(np.mean(acc["tri"])) if acc.get("tri") else 0.0,
            }

        # Endpoint scalars = last test-day OOS values
        for sym in symbols:
            for m in models:
                arr_m = mu_ts[m][sym]
                arr_s = sig_ts[m][sym]
                v = next((x for x in reversed(arr_m) if np.isfinite(x)), 0.0)
                w = next((x for x in reversed(arr_s) if np.isfinite(x)), 1e-4)
                mus[m][sym] = float(v)
                sigs[m][sym] = float(w)
    else:
        jsd_by_symbol = {}
        # No test rows: compute train-end scalars only
        tri_per_sym: List[Tuple[float, float, float, float]] = []
        for sym in symbols:
            s = train[sym].astype(float)
            sig_val = float(inp.validation_residuals_std.get(sym) or _validation_sigma(s))
            k_override = None
            if close is not None and sym in close.columns:
                c_hist = close.loc[close.index <= train.index[-1], sym].dropna().astype(float)
                c_hist.name = str(sym)
                if _kronos_params_ok():
                    if len(c_hist) < 30:
                        raise ValueError(
                            f"Kronos：标的 {sym} 在训练窗末不足 30 个有效收盘日（当前 {len(c_hist)}）。"
                        )
                    mu_k, ok_k = kronos_one_step_mu_from_close(c_hist)
                    k_override = mu_k
                    if ok_k:
                        kronos_real_any = True
                elif len(c_hist) >= 30:
                    mu_k, ok_k = kronos_one_step_mu_from_close(c_hist)
                    k_override = mu_k
                    if ok_k:
                        kronos_real_any = True
            ms, ss = _mus_sigs_for_series(s, sig_val, kronos_mu_override=k_override)
            for m in models:
                mus[m][sym] = ms[m]
                sigs[m][sym] = ss[m]
            tri_per_sym.append(_triangle_js(ms, ss))
        for sym, tup in zip(symbols, tri_per_sym):
            jsd_by_symbol[sym] = {
                "kronos_arima": float(tup[0]),
                "kronos_gbm": float(tup[1]),
                "gbm_arima": float(tup[2]),
                "triangle": float(tup[3]),
            }
        jsd_kronos_arima_mean = float(np.mean([t[0] for t in tri_per_sym])) if tri_per_sym else 0.0
        jsd_kronos_gbm_mean = float(np.mean([t[1] for t in tri_per_sym])) if tri_per_sym else 0.0
        jsd_gbm_arima_mean = float(np.mean([t[2] for t in tri_per_sym])) if tri_per_sym else 0.0
        jsd_triangle_mean = float(np.mean([t[3] for t in tri_per_sym])) if tri_per_sym else 0.0
        jsd_triangle_max = float(max(jsd_kronos_arima_mean, jsd_kronos_gbm_mean, jsd_gbm_arima_mean))
        fb_pairs: List[float] = []
        for i in range(len(models)):
            for j in range(i + 1, len(models)):
                for sym in symbols:
                    fb_pairs.append(
                        _js_divergence(
                            mus[models[i]][sym], sigs[models[i]][sym],
                            mus[models[j]][sym], sigs[models[j]][sym],
                        )
                    )
        jsd_pairs_mean = float(np.mean(fb_pairs)) if fb_pairs else 0.0

    # Rolling triangle-JSD baseline on train (extracted to ``_train_baseline_rolling_jsd``).
    _stress_w = int(getattr(policy, "semantic_cosine_window", 5) or 5)
    jsd_baseline_mean = _train_baseline_rolling_jsd(
        train=train, symbols=symbols, models=models,
        inp=inp, policy=policy, jsd_triangle_mean=jsd_triangle_mean,
    )
    jsd_stress = _jsd_stress_rolling_breach(
        daily_tri,
        jsd_triangle_mean,
        n_window=_stress_w,
        k_jsd=float(policy.k_jsd),
        jsd_baseline_mean=float(jsd_baseline_mean),
        eps=float(getattr(policy, "jsd_baseline_eps", 1e-9) or 1e-9),
    )

    # Credibility baseline: 1/(1 + α·JSD_triangle); α from policy
    alpha = float(max(policy.credibility_baseline_jsd_scale, 1e-9))
    credibility_base_jsd = float(1.0 / (1.0 + alpha * jsd_triangle_mean))

    # Train market return lag-1 autocorrelation (numeric logic-break; no sentiment)
    mr = train.mean(axis=1).dropna().astype(float)
    ac1 = 0.0
    if len(mr) > 20:
        try:
            ac1 = float(mr.autocorr(lag=1))
        except Exception:
            ac1 = 0.0
        if not np.isfinite(ac1):
            ac1 = 0.0
    logic_break_from_ac1 = ac1 < float(policy.tau_return_ac1)

    cos_win = int(getattr(policy, "semantic_cosine_window", 5))
    sem_cos = 0.0
    sem_cos_ok = False
    logic_break_sem = False
    _st_arr_for_cosine: Optional[np.ndarray] = None

    if (
        test_st_series is not None
        and len(test_dates) > 0
        and len(dates_iso) == len(test_dates)
        and len(dates_iso) >= max(5, cos_win)
    ):
        st_aligned = test_st_series.reindex(test_dates).ffill().bfill()
        st_arr_tmp = st_aligned.to_numpy(dtype=float)
        _st_arr_for_cosine = st_arr_tmp
        # semantic cosine will be computed below after shadow-optimal μ is ready

    # Placeholder; will be overridden after best_model_per_symbol is built
    logic_break = bool(logic_break_from_ac1)
    cos_out = float(sem_cos) if sem_cos_ok else 0.0

    jsd_mat = _build_jsd_matrix(
        dates_iso=dates_iso, models=models,
        mu_ts=mu_ts, sig_ts=sig_ts,
        mus=mus, sigs=sigs, symbols=symbols,
    )

    prob_nll_mean_e: Dict[str, float] = {}
    prob_dm_p_e: Dict[str, float] = {}
    prob_dm_t_e: Dict[str, float] = {}
    prob_cov_e: Dict[str, float] = {}
    lights_e: Dict[str, str] = {}
    full_fail = False
    prob_cov_naive_e = 0.0
    if len(test_dates) > 0:
        (
            prob_nll_mean_e,
            prob_dm_p_e,
            prob_dm_t_e,
            lights_e,
            prob_cov_e,
            full_fail,
            prob_cov_naive_e,
        ) = _probabilistic_oos_bundle(returns, test_dates, symbols, mu_ts, sig_ts)

    struct_models = ("arima", "lightgbm", "kronos")
    density_test_failed = False
    if len(test_dates) > 0 and prob_cov_e and prob_cov_naive_e > 0.0:
        density_test_failed = any(
            prob_cov_e.get(m, 0.0) + 1e-12 < prob_cov_naive_e for m in struct_models
        )

    beta_pen = float(policy.credibility_penalty_jsd_scale)
    cap_pen = float(policy.credibility_penalty_cap)
    credibility_coverage_penalty = 0.0
    if density_test_failed and beta_pen > 0.0:
        raw_pen = beta_pen * float(jsd_triangle_mean)
        credibility_coverage_penalty = float(min(cap_pen, raw_pen))

    cmin = float(policy.credibility_score_min)
    cmax = float(policy.credibility_score_max)
    if cmin >= cmax:
        cmin, cmax = -0.5, 1.0
    credibility_score = float(
        np.clip(credibility_base_jsd - credibility_coverage_penalty, cmin, cmax)
    )
    consistency_score = credibility_score

    # Shadow validation: per-model per-asset（仅训练窗尾部；长度见 policy.shadow_holdout_days）
    _shadow_cfg = int(getattr(policy, "shadow_holdout_days", _SHADOW_TAIL_DEFAULT))
    _shadow_cfg = max(5, min(_shadow_cfg, 120))
    _mse_lists: Dict[str, List[float]] = {m: [] for m in models}
    best_model_per_symbol: Dict[str, str] = {}
    for sym in symbols:
        close_sym: Optional[pd.Series] = None
        if close is not None and sym in close.columns:
            close_sym = close.loc[train.index, sym]
        n_train_pts = int(train[sym].astype(float).dropna().shape[0])
        n_tail_eff = min(_shadow_cfg, max(5, n_train_pts - 30))
        mse_map, combined_map = _tail_holdout_scores(
            train[sym].astype(float),
            n_tail=n_tail_eff,
            alpha_mse=policy.alpha_model_select,
            close_sym=close_sym,
            symbol=str(sym),
        )
        if combined_map:
            best_sym = min(combined_map, key=combined_map.get)
            best_model_per_symbol[sym] = best_sym
            for m in _mse_lists:
                _mse_lists[m].append(mse_map.get(m, float("nan")))
        else:
            best_model_per_symbol[sym] = "naive"

    mse_n = float(np.nanmean(_mse_lists["naive"])) if _mse_lists["naive"] else None
    mse_k = float(np.nanmean(_mse_lists["kronos"])) if _mse_lists["kronos"] else None
    mse_a = float(np.nanmean(_mse_lists["arima"])) if _mse_lists["arima"] else None
    mse_l = float(np.nanmean(_mse_lists["lightgbm"])) if _mse_lists["lightgbm"] else None

    mse_avail = {
        m: v
        for m, v in [("naive", mse_n), ("arima", mse_a), ("lightgbm", mse_l), ("kronos", mse_k)]
        if v is not None and np.isfinite(v)
    }
    note = _compose_shadow_note(
        mse_avail=mse_avail, credibility_score=credibility_score, policy=policy,
        full_fail=full_fail, density_test_failed=density_test_failed,
        credibility_coverage_penalty=credibility_coverage_penalty,
        prob_cov_naive_e=prob_cov_naive_e,
    )

    _lb_sem, _ok, _cos = _recompute_semantic_logic_break(
        st_arr=_st_arr_for_cosine,
        best_model_per_symbol=best_model_per_symbol,
        dates_iso=dates_iso, symbols=symbols, mu_ts=mu_ts, cos_win=cos_win,
    )
    if _ok:
        sem_cos_ok = True
        cos_out = _cos
    logic_break_sem = _lb_sem
    logic_break = bool(logic_break_from_ac1 or logic_break_sem)

    # Compute per-day cross-section mean of best-model μ (shadow optimal per symbol)
    daily_best_mu: List[float] = []
    if len(test_dates) > 0 and best_model_per_symbol:
        n_days = len(dates_iso)
        for day_idx in range(n_days):
            vals: List[float] = []
            for sym in symbols:
                bm = best_model_per_symbol.get(sym, "naive")
                ts_row = mu_ts.get(bm, {}).get(sym) or []
                if day_idx < len(ts_row) and np.isfinite(ts_row[day_idx]):
                    vals.append(float(ts_row[day_idx]))
            daily_best_mu.append(float(np.mean(vals)) if vals else float("nan"))

    return Phase2Output(
        credibility_score=credibility_score,
        credibility_base_jsd=credibility_base_jsd,
        credibility_coverage_penalty=credibility_coverage_penalty,
        consistency_score=consistency_score,
        density_test_failed=density_test_failed,
        prob_coverage_naive=prob_cov_naive_e if len(test_dates) > 0 else None,
        jsd_matrix=jsd_mat,
        jsd_baseline_mean=jsd_baseline_mean,
        jsd_pairs_mean=jsd_pairs_mean,
        jsd_kronos_arima_mean=jsd_kronos_arima_mean,
        jsd_kronos_gbm_mean=jsd_kronos_gbm_mean,
        jsd_gbm_arima_mean=jsd_gbm_arima_mean,
        jsd_triangle_mean=jsd_triangle_mean,
        jsd_triangle_max=jsd_triangle_max,
        jsd_by_symbol=jsd_by_symbol,
        jsd_stress=jsd_stress,
        logic_break=logic_break,
        logic_break_from_ac1=logic_break_from_ac1,
        logic_break_semantic_cosine_negative=logic_break_sem,
        train_return_ac1=float(ac1),
        semantic_numeric_cosine_computed=sem_cos_ok,
        cosine_semantic_numeric=cos_out,
        mse_naive=mse_n,
        mse_kronos=mse_k,
        mse_arima=mse_a,
        mse_lightgbm=mse_l,
        best_model_per_symbol=best_model_per_symbol,
        shadow_note=note,
        model_mu={m: dict(mus[m]) for m in models},
        model_sigma={m: dict(sigs[m]) for m in models},
        test_forecast_dates=dates_iso,
        test_daily_jsd_kronos_arima=list(daily_ka) if len(test_dates) > 0 else [],
        test_daily_jsd_kronos_gbm=list(daily_kg) if len(test_dates) > 0 else [],
        test_daily_jsd_gbm_arima=list(daily_ga) if len(test_dates) > 0 else [],
        test_daily_best_model_mu_mean=daily_best_mu,
        model_mu_test_ts={m: dict(mu_ts[m]) for m in models},
        model_sigma_test_ts={m: dict(sig_ts[m]) for m in models},
        kronos_real_inference=bool(kronos_real_any),
        prob_nll_mean=prob_nll_mean_e,
        prob_dm_pvalue_vs_naive=prob_dm_p_e,
        prob_dm_statistic=prob_dm_t_e,
        prob_coverage_95=prob_cov_e,
        model_traffic_light=lights_e,
        prob_full_pipeline_failure=bool(full_fail),
        test_daily_triangle_jsd_mean=list(daily_tri) if len(test_dates) > 0 else [],
    )
