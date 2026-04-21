"""Phase 3: AdaptiveOptimizer (Sharpe / weighted semantic penalty / conditional CVaR) + vectorized jump-diffusion MC."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from research.defense_state import DefenseLevel
from research.schemas import DefensePolicyConfig, Phase3DefenseValidation, Phase3Input, Phase3Output

RISK_FREE = 0.0  # AnsToInq：r_f 常数 0，不暴露配置


def _path_max_drawdown_pct(path_1d: np.ndarray) -> float:
    peak = np.maximum.accumulate(path_1d)
    dd = (peak - path_1d) / np.maximum(peak, 1e-12)
    return float(np.max(dd) * 100.0)


def _apply_blocked_renorm(
    w: Dict[str, float], symbols: List[str], blocked: frozenset
) -> Dict[str, float]:
    out = {s: float(w.get(s, 0.0)) for s in symbols}
    for s in blocked:
        if s in out:
            out[s] = 0.0
    tot = sum(out.values())
    if tot > 1e-12:
        return {k: float(v) / tot for k, v in out.items()}
    alive = [s for s in symbols if s not in blocked]
    if alive:
        u = 1.0 / len(alive)
        return {s: (u if s in alive else 0.0) for s in symbols}
    return {s: 1.0 / max(len(symbols), 1) for s in symbols}


def _simulate_mc_paths(
    w_by_sym: Dict[str, float],
    syms: List[str],
    mu: np.ndarray,
    cov: np.ndarray,
    inp: Phase3Input,
    rng_main: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray, float, float, float, float]:
    """Same jump-diffusion MC as Phase3 main chart; parallel rng seeds give comparable shocks across portfolios."""
    w_arr = np.array([float(w_by_sym.get(s, 0.0)) for s in syms], dtype=float)
    w_arr = w_arr / (w_arr.sum() or 1.0)
    mu_p = float(w_arr @ mu)
    var_p = float(w_arr @ cov @ w_arr)
    sig_p = float(np.sqrt(max(var_p, 1e-18)))

    s0 = 1.0
    dt = 1.0 / 252.0
    T = inp.mc_horizon_days * dt
    n_paths = 10_000
    n_steps_target = max(int(round(float(inp.mc_horizon_days))), 1)
    sig_b = float(max(sig_p, 0.014))

    st_path = inp.mc_sentiment_path
    use_st = st_path is not None and len(st_path) >= n_steps_target
    if use_st:
        st_arr = np.asarray([float(x) for x in st_path[:n_steps_target]], dtype=float)
        lam_sched, imp_sched = sentiment_path_to_jump_schedules(st_arr)
        paths0, paths1 = jump_diffusion_paths_vectorized_scheduled(
            s0,
            mu_p,
            sig_b,
            T=T,
            dt=dt,
            n_paths=n_paths,
            jump_lambda_annual_per_step=lam_sched,
            jump_log_impact_per_step=imp_sched,
            rng=rng_main,
        )
    else:
        lam = float(np.clip(inp.jump_p, 0.0, 1.0))
        impact = float(np.clip(inp.jump_impact, -0.3, 0.3))
        paths0, paths1 = jump_diffusion_paths_vectorized(
            s0,
            mu_p,
            sig_b,
            T=T,
            dt=dt,
            n_paths=n_paths,
            jump_lambda_annual=lam,
            jump_log_impact=impact,
            rng=rng_main,
        )

    if inp.scenario_inject_step is not None:
        n_steps_raw = int(paths1.shape[1] - 1)
        step = int(np.clip(inp.scenario_inject_step, 1, n_steps_raw - 1))
        shock = float(np.clip(inp.scenario_inject_impact, -0.5, 0.0))
        log1 = np.log(np.maximum(paths1, 1e-12))
        log1[:, step + 1 :] += shock
        paths1 = np.exp(log1)

    ends = paths1[:, -1]
    p5_idx = int(np.argmin(np.abs(ends - float(np.percentile(ends, 5)))))
    stress_p5_path = paths1[p5_idx]
    mdd_rep = _path_max_drawdown_pct(stress_p5_path)
    peak_all = np.maximum.accumulate(paths1, axis=1)
    dd_all = (peak_all - paths1) / np.maximum(peak_all, 1e-12)
    mdd_all_pct = np.max(dd_all, axis=1) * 100.0
    mc_mdd_p95 = float(np.percentile(mdd_all_pct, 95))
    mean_end = float(np.mean(paths0[:, -1]))
    p5_end = float(np.percentile(paths1[:, -1], 5))
    return paths0, paths1, mean_end, p5_end, mdd_rep, mc_mdd_p95


def _realized_cumul_and_mdd(R: np.ndarray, w_arr: np.ndarray) -> Tuple[float, float]:
    if R.size == 0 or w_arr.size == 0:
        return float("nan"), float("nan")
    rp = R @ w_arr
    if len(rp) == 0:
        return float("nan"), float("nan")
    price = np.cumprod(1.0 + rp)
    cum_ret = float(price[-1] - 1.0)
    peak = np.maximum.accumulate(price)
    dd = (peak - price) / np.maximum(peak, 1e-12)
    return cum_ret, float(np.max(dd) * 100.0)


def _realized_equity_series_and_mdd(
    R: np.ndarray, w_by_sym: Dict[str, float], syms: List[str]
) -> Tuple[List[float], float, float]:
    """Simple compound cumulative return series (wealth-1) and max drawdown % on test window."""
    w = np.array([float(w_by_sym.get(s, 0.0)) for s in syms], dtype=float)
    w = w / (w.sum() or 1.0)
    if R.size == 0 or w.size == 0:
        return [], float("nan"), float("nan")
    rp = R @ w
    if len(rp) == 0:
        return [], float("nan"), float("nan")
    price = np.cumprod(1.0 + rp)
    curve = (price - 1.0).tolist()
    peak = np.maximum.accumulate(price)
    dd = (peak - price) / np.maximum(peak, 1e-12)
    return curve, float(curve[-1]), float(np.max(dd) * 100.0)


def subset_returns_for_cvar(
    R: np.ndarray,
    window: int = 21,
    vol_quantile_band: float = 0.15,
    min_rows: int = 30,
    fallback_tail: int = 60,
) -> np.ndarray:
    """
    AnsToInq §5.3：与当前「逻辑断裂」特征相似的历史日收益子样本。
    规则：滚动组合波动率分位落在 [q_now−0.15, q_now+0.15]（在分位空间），
    且滚动平均成对 |ρ| 处于历史上三分位以上；不足 min_rows 则取最近 fallback_tail 行。
    """
    R = np.asarray(R, dtype=float)
    T, n = R.shape
    if T < window + 3:
        return R
    vols: List[float] = []
    corrs: List[float] = []
    for t in range(window, T + 1):
        seg = R[t - window : t]
        pv = seg.mean(axis=1)
        vols.append(float(np.std(pv, ddof=1)))
        cm = np.corrcoef(seg.T)
        tri = cm[np.triu_indices(n, k=1)]
        tri = tri[np.isfinite(tri)]
        corrs.append(float(np.mean(np.abs(tri))) if tri.size > 0 else 0.0)
    vols_a = np.asarray(vols)
    corrs_a = np.asarray(corrs)
    ends = np.arange(window - 1, T, dtype=int)
    vol_now = vols_a[-1]
    q_now = float(np.mean(vols_a <= vol_now))
    q_lo = max(0.0, q_now - vol_quantile_band)
    q_hi = min(1.0, q_now + vol_quantile_band)
    v_lo = float(np.quantile(vols_a, q_lo))
    v_hi = float(np.quantile(vols_a, q_hi))
    if v_lo > v_hi:
        v_lo, v_hi = v_hi, v_lo
    mask_v = (vols_a >= v_lo) & (vols_a <= v_hi)
    thr_c = float(np.quantile(corrs_a, 2.0 / 3.0))
    mask_c = corrs_a >= thr_c
    pick = ends[mask_v & mask_c]
    if pick.size < min_rows:
        return R[max(0, T - fallback_tail) : T]
    return R[np.sort(pick)]


def _portfolio_mu_vol(w: np.ndarray, mu: np.ndarray, cov: np.ndarray, trading_days: int = 252) -> Tuple[float, float]:
    mu_d = float(w @ mu)
    vol_d = float(np.sqrt(max(w @ cov @ w, 0.0)))
    return mu_d * trading_days, vol_d * np.sqrt(trading_days)


def _cvar_loss(w: np.ndarray, R: np.ndarray, alpha: float) -> float:
    rp = R @ w
    q = float(np.quantile(rp, alpha))
    tail = rp[rp <= q]
    if len(tail) == 0:
        return float(-np.mean(rp))
    return float(-np.mean(tail))


def _neg_sent_per_asset(symbols: List[str], sentiments: Dict[str, float]) -> np.ndarray:
    return np.array([max(0.0, -float(sentiments.get(s, 0.0))) for s in symbols], dtype=float)


class AdaptiveOptimizer:
    """
    Phase3.md：按 DefenseLevel 切换目标。
    Level 0：minimize -(Sharpe) 等价 maximize (μ−r_f)/σ，r_f=0。
    Level 1：minimize σ_port + λ * Σ w_i * neg_sent_i（AnsToInq 加权负面语义均值）。
    Level 2：minimize CVaR_α，历史样本为条件子样本。
    """

    def __init__(
        self,
        mu_daily: np.ndarray,
        cov_daily: np.ndarray,
        symbols: List[str],
        sentiments: Dict[str, float],
        policy: DefensePolicyConfig,
        hist_returns: Optional[np.ndarray] = None,
    ) -> None:
        self.mu = np.asarray(mu_daily, dtype=float)
        self.cov = np.asarray(cov_daily, dtype=float)
        self.symbols = list(symbols)
        self.sentiments = sentiments
        self.policy = policy
        self.hist_returns = hist_returns
        self._neg = _neg_sent_per_asset(self.symbols, sentiments)

    def _sharpe_obj(self, w: np.ndarray) -> float:
        mu_a, vol_a = _portfolio_mu_vol(w, self.mu, self.cov)
        # minimize negative Sharpe with r_f = 0
        return -(mu_a - RISK_FREE) / vol_a if vol_a > 1e-12 else 0.0

    def _caution_obj(self, w: np.ndarray) -> float:
        _, vol_a = _portfolio_mu_vol(w, self.mu, self.cov)
        weighted_neg = float(np.dot(w, self._neg))
        return vol_a + self.policy.lambda_semantic * weighted_neg

    def optimize(self, level: DefenseLevel) -> Tuple[Dict[str, float], str, Optional[float], Optional[float]]:
        n = len(self.symbols)
        w0 = np.ones(n) / n
        cons = {"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}
        bounds = tuple((0.0, 1.0) for _ in range(n))

        if level == DefenseLevel.STANDARD:
            res = minimize(self._sharpe_obj, w0, method="SLSQP", bounds=bounds, constraints=cons, options={"maxiter": 500})
            w = res.x
            mu_a, vol_a = _portfolio_mu_vol(w, self.mu, self.cov)
            sh = (mu_a - RISK_FREE) / vol_a if vol_a > 1e-12 else float("nan")
            return {self.symbols[i]: float(w[i]) for i in range(n)}, "max_sharpe", sh, None

        if level == DefenseLevel.CAUTION:
            res = minimize(self._caution_obj, w0, method="SLSQP", bounds=bounds, constraints=cons, options={"maxiter": 500})
            w = res.x
            mu_a, vol_a = _portfolio_mu_vol(w, self.mu, self.cov)
            sh = (mu_a - RISK_FREE) / vol_a if vol_a > 1e-12 else float("nan")
            return {self.symbols[i]: float(w[i]) for i in range(n)}, "caution_semantic", sh, None

        R = self.hist_returns
        if R is None or R.size == 0:
            R = np.random.default_rng(0).normal(self.mu, np.sqrt(np.diag(self.cov)), size=(200, n))
        else:
            R = subset_returns_for_cvar(np.asarray(R, dtype=float))

        def cvar_obj(w: np.ndarray) -> float:
            return _cvar_loss(w, R, self.policy.cvar_alpha)

        res = minimize(cvar_obj, w0, method="SLSQP", bounds=bounds, constraints=cons, options={"maxiter": 500})
        w = np.maximum(res.x, 0)
        w = w / (w.sum() or 1.0)
        rp = R @ w
        q = float(np.quantile(rp, self.policy.cvar_alpha))
        tail = rp[rp <= q]
        cvar = float(-np.mean(tail)) if len(tail) else float(-np.mean(rp))
        return {self.symbols[i]: float(w[i]) for i in range(n)}, "min_cvar", None, cvar


def optimize_adaptive(
    mu_daily: np.ndarray,
    cov_daily: np.ndarray,
    sentiments: Dict[str, float],
    symbols: List[str],
    level: DefenseLevel,
    policy: DefensePolicyConfig,
    hist_returns: Optional[np.ndarray] = None,
) -> Tuple[Dict[str, float], str, Optional[float], Optional[float]]:
    return AdaptiveOptimizer(mu_daily, cov_daily, symbols, sentiments, policy, hist_returns).optimize(level)


def annual_jump_intensity_to_step_prob(lambda_annual: float, dt: float) -> float:
    """泊松强度 λ（年化）→ Euler 步内至少一次跳跃的等价 Bernoulli 概率。"""
    lam = max(float(lambda_annual), 0.0)
    return float(np.clip(1.0 - np.exp(-lam * float(dt)), 0.0, 1.0))


def jump_diffusion_paths_vectorized(
    s0: float,
    mu: float,
    sigma: float,
    T: float,
    dt: float,
    n_paths: int,
    jump_lambda_annual: float,
    jump_log_impact: float,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    对数空间 Euler：ΔlnS = μΔt + σ√Δt Z + J·Bernoulli(p_step)；
    jump_lambda_annual ∈ [0,1] 为年化强度；jump_log_impact 为对数跳跃增量。
    返回 (无跳路径, 含跳路径)。
    """
    rng = rng or np.random.default_rng(42)
    n_steps = int(T / dt) if dt > 0 else int(T)
    n_steps = max(n_steps, 1)
    Z = rng.standard_normal(size=(n_paths, n_steps))
    inc_base = mu * dt + sigma * np.sqrt(dt) * Z
    log_s0 = np.log(max(s0, 1e-12))
    log0 = np.zeros((n_paths, n_steps + 1))
    log0[:, 0] = log_s0
    log0[:, 1:] = log_s0 + np.cumsum(inc_base, axis=1)
    paths0 = np.exp(log0)

    p_step = annual_jump_intensity_to_step_prob(jump_lambda_annual, dt)
    bern = (rng.random(size=(n_paths, n_steps)) < p_step).astype(float)
    jump_inc = jump_log_impact * bern
    inc_j = inc_base + jump_inc
    log1 = np.zeros((n_paths, n_steps + 1))
    log1[:, 0] = log_s0
    log1[:, 1:] = log_s0 + np.cumsum(inc_j, axis=1)
    paths1 = np.exp(log1)
    return paths0, paths1


def p0_pure_mc_median_cumulative_returns(
    mu: np.ndarray,
    cov: np.ndarray,
    symbols: List[str],
    n_days: int,
    *,
    n_paths: int = 5000,
    rng_seed: int = 42,
) -> List[float]:
    """
    P0「单纯蒙特卡洛」对照：等权组合、无跳跃（λ=0），对数正态欧拉离散；
    返回与测试窗交易日对齐的**中位数路径累计收益**（长度 n_days）。
    """
    n_days = int(max(n_days, 0))
    if n_days < 1 or not symbols:
        return []
    mu = np.asarray(mu, dtype=float).reshape(-1)
    cov = np.asarray(cov, dtype=float)
    n = len(symbols)
    if mu.size != n or cov.shape != (n, n):
        return []
    w = np.ones(n, dtype=float) / float(n)
    mu_p = float(w @ mu)
    var_p = float(w @ cov @ w)
    sig_p = float(np.sqrt(max(var_p, 1e-18)))
    sig_b = float(max(sig_p, 0.014))
    dt = 1.0 / 252.0
    T = float(n_days) * dt
    rng = np.random.default_rng(int(rng_seed))
    paths0, _paths1 = jump_diffusion_paths_vectorized(
        1.0,
        mu_p,
        sig_b,
        T=T,
        dt=dt,
        n_paths=int(n_paths),
        jump_lambda_annual=0.0,
        jump_log_impact=0.0,
        rng=rng,
    )
    med = np.median(paths0, axis=0)
    n_out = min(max(len(med) - 1, 0), n_days)
    if n_out == 0:
        return []
    out = (med[1 : 1 + n_out] - 1.0).astype(float).tolist()
    if len(out) < n_days:
        out.extend([out[-1]] * (n_days - len(out)))
    return out[:n_days]


def sentiment_path_to_jump_schedules(st: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Vectorized ``sentiment_to_jump_params`` along a path (S_t → λ_t, impact_t per step)."""
    st = np.asarray(st, dtype=float)
    neg = np.maximum(0.0, -st)
    lam = np.clip(0.02 + 0.55 * neg, 0.0, 1.0)
    imp = np.clip(-0.06 - 0.24 * neg, -0.3, 0.3)
    return lam.astype(float), imp.astype(float)


def jump_diffusion_paths_vectorized_scheduled(
    s0: float,
    mu: float,
    sigma: float,
    T: float,
    dt: float,
    n_paths: int,
    jump_lambda_annual_per_step: np.ndarray,
    jump_log_impact_per_step: np.ndarray,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Same as ``jump_diffusion_paths_vectorized`` but per-Euler-step λ and log jump size."""
    rng = rng or np.random.default_rng(42)
    n_steps = int(T / dt) if dt > 0 else int(T)
    n_steps = max(n_steps, 1)
    la = np.asarray(jump_lambda_annual_per_step, dtype=float).reshape(-1)
    ji = np.asarray(jump_log_impact_per_step, dtype=float).reshape(-1)
    if la.shape[0] < n_steps:
        pad = n_steps - la.shape[0]
        la = np.pad(la, (0, pad), mode="edge")
        ji = np.pad(ji, (0, pad), mode="edge")
    la = la[:n_steps]
    ji = ji[:n_steps]

    Z = rng.standard_normal(size=(n_paths, n_steps))
    inc_base = mu * dt + sigma * np.sqrt(dt) * Z
    log_s0 = np.log(max(s0, 1e-12))
    log0 = np.zeros((n_paths, n_steps + 1))
    log0[:, 0] = log_s0
    log0[:, 1:] = log_s0 + np.cumsum(inc_base, axis=1)
    paths0 = np.exp(log0)

    p_steps = np.array([annual_jump_intensity_to_step_prob(float(la[i]), dt) for i in range(n_steps)])
    bern = (rng.random(size=(n_paths, n_steps)) < p_steps[np.newaxis, :]).astype(float)
    jump_inc = ji[np.newaxis, :] * bern
    inc_j = inc_base + jump_inc
    log1 = np.zeros((n_paths, n_steps + 1))
    log1[:, 0] = log_s0
    log1[:, 1:] = log_s0 + np.cumsum(inc_j, axis=1)
    paths1 = np.exp(log1)
    return paths0, paths1


def run_phase3(
    inp: Phase3Input,
    policy: DefensePolicyConfig,
    level: DefenseLevel,
    hist_returns: Optional[np.ndarray] = None,
) -> Phase3Output:
    mu = np.asarray(inp.mu_daily, dtype=float)
    cov = np.asarray(inp.cov_daily, dtype=float)
    syms = inp.symbols
    if mu.size != len(syms) or cov.shape != (len(syms), len(syms)):
        return Phase3Output(objective_name="error", weights={})

    opt = AdaptiveOptimizer(mu, cov, syms, inp.sentiments, policy, hist_returns)
    w_raw, name, sharpe, cvar = opt.optimize(level)
    blocked = frozenset(inp.blocked_symbols or [])
    w = _apply_blocked_renorm(w_raw, syms, blocked)

    if level != DefenseLevel.STANDARD:
        w_cf_raw, _, _, _ = opt.optimize(DefenseLevel.STANDARD)
        w_cf = _apply_blocked_renorm(w_cf_raw, syms, blocked)
    else:
        w_cf = dict(w)

    w_cvar_raw, _, _, _ = opt.optimize(DefenseLevel.MELTDOWN)
    w_cvar = _apply_blocked_renorm(w_cvar_raw, syms, blocked)

    cw_src = inp.custom_portfolio_weights
    if cw_src:
        w_custom = {s: max(0.0, float(cw_src.get(s, 0.0))) for s in syms}
        tw = sum(w_custom.values())
        if tw < 1e-15:
            w_custom = {s: 1.0 / max(len(syms), 1) for s in syms}
        else:
            w_custom = {s: float(w_custom[s]) / tw for s in syms}
    else:
        w_custom = {s: 1.0 / max(len(syms), 1) for s in syms}
    w_custom = _apply_blocked_renorm(w_custom, syms, blocked)

    dt = 1.0 / 252.0
    n_paths = 10_000
    rng_base = np.random.default_rng(7)
    paths0, paths1, mean_end, p5_end, mdd_rep, mc_mdd_p95 = _simulate_mc_paths(
        w, syms, mu, cov, inp, rng_base
    )

    med_path = np.median(paths0, axis=0)
    ends = paths1[:, -1]
    p5 = float(np.percentile(ends, 5))
    p5_idx = int(np.argmin(np.abs(ends - p5)))
    stress_p5_path = paths1[p5_idx]

    n_steps = int(paths0.shape[1])
    max_pts = 200
    idx_time = np.unique(np.linspace(0, n_steps - 1, num=min(max_pts, n_steps), dtype=int))
    times = (idx_time * float(dt)).tolist()
    med_ds = med_path[idx_time].tolist()
    p5_ds = stress_p5_path[idx_time].tolist()

    rng_sub = np.random.default_rng(11)
    n_cloud = min(40, n_paths)
    pick = rng_sub.choice(n_paths, size=n_cloud, replace=False)
    base_sub = paths0[pick][:, idx_time]
    stress_sub = paths1[pick][:, idx_time]

    # Show the true worst terminal path among ALL 10,000 stress paths.
    # We append its downsampled path to the displayed stress cloud and point worst_idx to it.
    worst_all_idx = int(np.argmin(paths1[:, -1]))
    worst_all_ds = paths1[worst_all_idx][idx_time]
    stress_sub = np.vstack([stress_sub, worst_all_ds[np.newaxis, :]])
    worst_sub = int(stress_sub.shape[0] - 1)

    defense_validation: Optional[Phase3DefenseValidation] = None
    if level == DefenseLevel.STANDARD:
        defense_validation = Phase3DefenseValidation(
            comparison_active=False,
            counterfactual_weights=dict(w),
            actual_stress_p5_terminal=p5_end,
            baseline_stress_p5_terminal=p5_end,
            actual_mdd_p95_pct=mc_mdd_p95,
            baseline_mdd_p95_pct=mc_mdd_p95,
        )
    else:
        rng_cf = np.random.default_rng(7)
        _, _, _, p5_cf, _, mdd_p95_cf = _simulate_mc_paths(
            w_cf, syms, mu, cov, inp, rng_cf
        )
        lift = None
        if p5_cf is not None and abs(p5_cf) > 1e-12:
            lift = float((p5_end - p5_cf) / abs(p5_cf) * 100.0)
        mdd_imp = None
        if mdd_p95_cf is not None:
            mdd_imp = float(mdd_p95_cf - mc_mdd_p95)
        defense_validation = Phase3DefenseValidation(
            comparison_active=True,
            baseline_objective="max_sharpe",
            counterfactual_weights=dict(w_cf),
            actual_stress_p5_terminal=p5_end,
            baseline_stress_p5_terminal=p5_cf,
            stress_p5_terminal_lift_pct=lift,
            actual_mdd_p95_pct=mc_mdd_p95,
            baseline_mdd_p95_pct=mdd_p95_cf,
            mdd_p95_improvement_pctpts=mdd_imp,
        )

    tr = inp.test_returns_daily
    if tr is not None and len(tr) > 0:
        R = np.asarray(tr, dtype=float)
        if R.ndim == 2 and R.shape[1] == len(syms):
            wa = np.array([w.get(s, 0.0) for s in syms], dtype=float)
            wb = np.array([w_cf.get(s, 0.0) for s in syms], dtype=float)
            wa = wa / (wa.sum() or 1.0)
            wb = wb / (wb.sum() or 1.0)
            c_a, d_a = _realized_cumul_and_mdd(R, wa)
            c_b, d_b = _realized_cumul_and_mdd(R, wb)
            eq_ms, tr_ms, mdd_ms = _realized_equity_series_and_mdd(R, w_cf, syms)
            eq_cu, tr_cu, mdd_cu = _realized_equity_series_and_mdd(R, w_custom, syms)
            eq_cv, tr_cv, mdd_cv = _realized_equity_series_and_mdd(R, w_cvar, syms)
            if defense_validation is not None:
                defense_validation = defense_validation.model_copy(
                    update={
                        "test_cumulative_return_actual": c_a,
                        "test_cumulative_return_baseline": c_b,
                        "test_max_drawdown_pct_actual": d_a,
                        "test_max_drawdown_pct_baseline": d_b,
                        "test_equity_max_sharpe": eq_ms,
                        "test_equity_custom_weights": eq_cu,
                        "test_equity_cvar": eq_cv,
                        "test_terminal_cumret_max_sharpe": tr_ms,
                        "test_terminal_cumret_custom_weights": tr_cu,
                        "test_terminal_cumret_cvar": tr_cv,
                        "test_mdd_pct_max_sharpe": mdd_ms,
                        "test_mdd_pct_custom_weights": mdd_cu,
                        "test_mdd_pct_cvar": mdd_cv,
                        "resolved_custom_weights": dict(w_custom),
                    }
                )

    return Phase3Output(
        objective_name=name,
        weights=w,
        sharpe=sharpe,
        cvar=cvar,
        mc_conservative_mean=[mean_end],
        mc_stress_p5=[p5_end],
        mc_timesteps=n_steps,
        mc_paths_baseline=base_sub.tolist(),
        mc_paths_stress=stress_sub.tolist(),
        mc_times=times,
        mc_worst_stress_path_index=worst_sub,
        mc_expected_max_drawdown_pct=mdd_rep,
        mc_mdd_p95=mc_mdd_p95,
        mc_path_median_nojump=med_ds,
        mc_path_jump_p5=p5_ds,
        mc_stress_percentile5_path_index=p5_idx,
        defense_validation=defense_validation,
    )


def sentiment_to_jump_params(sentiment: float) -> Tuple[float, float]:
    """
    Sentiment_to_Jump_Params：输出 (p, impact) JSON 语义映射。
    p：年化泊松强度 ∈ [0,1]；impact：对数跳跃幅度 ∈ [-0.3, 0.3]。
    """
    neg = max(0.0, -float(sentiment))
    lam = float(np.clip(0.02 + 0.55 * neg, 0.0, 1.0))
    impact = float(np.clip(-0.06 - 0.24 * neg, -0.3, 0.3))
    return lam, impact
