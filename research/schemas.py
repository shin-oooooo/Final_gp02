"""Pydantic schemas for Phase 0–3 (input/output contracts)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from research.sentiment_calendar import DEFAULT_TEST_START, today_iso


class DefensePolicyConfig(BaseModel):
    """Sidebar-tunable defense thresholds (single source of truth for resolver)."""

    tau_l2: float = Field(0.45, description="Consistency ≤ this → Level 2")
    tau_l1: float = Field(0.70, description="Consistency > this (with sentiment band) → Level 0")
    tau_h1: float = Field(0.50, description="Structural entropy below → Level 1")
    tau_vol_melt: float = Field(
        0.32,
        description="Phase1 伪平稳（ADF 通过且训练期等权年化波动 ≥ 此值）→ 防御 Level 1 警示",
    )
    tau_return_ac1: float = Field(
        -0.08,
        description="Phase2 逻辑断裂：训练期截面均值收益的一阶自相关系数 < 此值（振荡/均值回复过强）",
    )
    semantic_cosine_window: int = Field(
        5,
        ge=1,
        le=10,
        description="语义–数值余弦相似度的滚动窗口长度 W（交易日）；首次 cos_t<0 即为背离日",
    )
    # --- Fig4.1 预警成功验证参数（固定 5 日窗；基线均来自训练窗滚动序列分位）---
    verify_train_tail_days: int = Field(
        60,
        ge=20,
        le=260,
        description="训练窗尾部池化用的最近交易日数（用于厚尾左右尾基线与对照）。",
    )
    verify_crash_quantile_pct: int = Field(
        90,
        ge=50,
        le=99,
        description="大跌阈值分位（百分位）。用于从训练窗滚动复合收益分布估计逐标阈值（取 1-q 的左尾）。",
    )
    verify_std_quantile_pct: int = Field(
        90,
        ge=50,
        le=99,
        description="横截面 Std 基线分位（百分位）。训练窗滚动序列取该分位作为阈值。",
    )
    verify_tail_quantile_pct: int = Field(
        90,
        ge=50,
        le=99,
        description="厚尾占比基线分位（百分位）。训练窗滚动序列取该分位作为阈值。",
    )
    tau_s_low: float = Field(-0.20, description="Level 0 sentiment lower bound")
    tau_s_high: float = Field(1.00, description="Level 0 sentiment upper bound")
    sentiment_halflife_days: float = Field(
        2.0,
        gt=0.0,
        le=60.0,
        description=(
            "S_t 指数核半衰期（日历日）。每条新闻日 i 对交易日 t 的记忆项权重为 "
            "w(i,t)=2^{-(t-i)/H}；v3.1 默认 H=2（配合 α=1.0/β=0.2/γ=0.10 一起放大日间波动）；"
            "H=3 偏短期、H=7 偏慢变、H=14 用于慢速事件。"
            "该参数只影响 S_t 的生成，不改变状态机对 min(S_t) 的消费口径。"
        ),
    )
    tau_h_gamma: float = Field(0.40, description="Gamma boost when H_struct below (Phase1)")
    k_jsd: float = Field(
        2.0,
        description=(
            "安全系数 k：当任意 W=semantic_cosine_window 日滚动三角 JSD 均值超过 "
            "k×max(jsd_baseline_mean, ε) 时触发 jsd_stress。"
            "统计口径与 FigX.6 语义–数值滚动余弦共用同一窗口 W。"
        ),
    )
    jsd_baseline_eps: float = Field(
        1e-9,
        gt=0,
        le=0.01,
        description="屈服阈下界 ε：应力水平线 τ = k_jsd × max(jsd_baseline_mean, ε)，与 phase2 判定及 FigX.4 图一致",
    )
    lambda_semantic: float = Field(0.5, description="Semantic penalty weight Level 1")
    cvar_alpha: float = Field(0.05, gt=0, lt=1, description="CVaR tail mass Level 2")
    alpha_model_select: float = Field(
        0.5, ge=0.0, le=1.0,
        description="Model selection composite weight: α·norm(MSE) + (1−α)·norm(JSD_to_empirical); 1=pure MSE, 0=pure JSD",
    )
    shadow_holdout_days: int = Field(
        40,
        ge=5,
        le=120,
        description=(
            "训练窗内影子 holdout 长度（交易日，仅用训练标签，不碰测试窗）；"
            "越短越快、方差越大；越长越稳、Kronos 调用越多。与 oos_fit_steps 搭配可调严谨性/算力。"
        ),
    )
    oos_fit_steps: int = Field(
        10, ge=1, le=60,
        description="OOS test window上实际拟合模型的最大步数；步数之间前向填充，越小越快（最小1=仅训练末拟合一次）",
    )
    data_refresh_max_age_hours: float = Field(
        18.0, gt=0,
        description=(
            "（2026-04 起仅保留字段）数据文件最大陈旧时间（小时）；原语义：超过则触发"
            "增量下载。当前 UI 已无对应控件，字段值不被任何运行时路径读取，仅用于"
            "policy 序列化/日志兼容。实际数据刷新改由 ``executor._ensure_data_json_exists``"
            "在 data.json 缺失时惰性执行。"
        ),
    )
    data_auto_refresh: bool = Field(
        True,
        description=(
            "（2026-04 起仅保留字段）是否在启动时自动检查并下载当日数据。当前"
            "无运行时路径读取该字段，默认值保持 True 以与旧 snapshot 对齐。"
        ),
    )
    # Phase 2 可信度：基准项 1/(1 + α·JSD_triangle)，惩罚项（覆盖率逊于 Naive 时）min(上限, β·JSD_triangle)
    credibility_baseline_jsd_scale: float = Field(
        6.0,
        gt=0,
        description="可信度基准项中 JSD 三角均值的系数 α（越大则同样分歧下得分越低）",
    )
    credibility_penalty_jsd_scale: float = Field(
        0.12,
        ge=0,
        description="惩罚项中 JSD 三角均值的系数 β（覆盖失败时；0 表示不施加 JSD 比例惩罚）",
    )
    credibility_penalty_cap: float = Field(
        0.35,
        ge=0,
        description="覆盖率惩罚单项上限（与 β·JSD 取 min）",
    )
    credibility_score_min: float = Field(
        -0.5,
        description="可信度输出下界（clip）",
    )
    credibility_score_max: float = Field(
        1.0,
        description="可信度输出上界（clip）",
    )

    @field_validator("semantic_cosine_window", mode="before")
    @classmethod
    def _clamp_semantic_cosine_window(cls, v: Any) -> int:
        try:
            x = int(v)
        except (TypeError, ValueError):
            return 5
        return max(1, min(10, x))


def _regime_break_start_default() -> str:
    """~3 weeks before today, clipped to not precede test_start."""
    t0 = date.fromisoformat(DEFAULT_TEST_START)
    t = date.today() - timedelta(days=21)
    if t < t0:
        t = t0
    return t.isoformat()


# --- Phase 0 ---
class Phase0Input(BaseModel):
    train_start: str = "2024-01-01"
    train_end: str = "2026-01-31"
    test_start: str = DEFAULT_TEST_START
    test_end: str = Field(
        default_factory=today_iso,
        description="测试窗末端：默认与运行当日日历日一致（与数据最后交易日求交由 windowing 处理）。",
    )
    regime_break_start: str = Field(
        default_factory=_regime_break_start_default,
        description="断裂期 Beta 回归起点（与测试集求交）；样本过少时回退为整段测试窗。",
    )
    regime_break_end: str = Field(
        default_factory=today_iso,
        description="断裂期 Beta 回归终点（默认与 test_end 同为今日）。",
    )
    tech_symbols: List[str] = Field(default_factory=lambda: ["NVDA", "MSFT", "TSMC", "GOOGL", "AAPL"])
    hedge_symbols: List[str] = Field(default_factory=lambda: ["XLE"])
    safe_symbols: List[str] = Field(default_factory=lambda: ["GLD", "TLT"])
    benchmark: str = "SPY"
    corr_warn_threshold: float = 0.3


class Phase0Output(BaseModel):
    orthogonality_warning: bool = False
    orthogonality_message: str = ""
    train_index: List[str] = Field(default_factory=list)
    test_index: List[str] = Field(default_factory=list)
    environment_report: Dict[str, Any] = Field(default_factory=dict)
    beta_steady: Dict[str, float] = Field(default_factory=dict)
    beta_stress: Dict[str, float] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)


# --- Phase 1 ---
class Phase1Input(BaseModel):
    symbols: List[str]
    returns_train: Optional[List[List[float]]] = None  # optional serialized; prefer DataFrame in code path
    sentiment_score: float = 0.0
    adf_p_threshold: float = 0.05
    entropy_window: int = 21
    h_struct_low: float = 0.4


class AssetDiagnostic(BaseModel):
    symbol: str
    # ADF on log returns r_t = ln(P_t/P_{t-1}); H0: unit root. p≥0.05 → 尝试一阶/二阶差分（见 Phase1 实现）。
    adf_p: float
    stationary: bool
    # ADF p-value on the differenced series that achieved stationarity (or last test if failure).
    adf_p_returns: float = 1.0
    stationary_returns: bool = False
    diff_order: int = 0
    basic_logic_failure: bool = False
    ljung_box_p: Optional[float] = None
    white_noise: bool = False
    low_predictive_value: bool = Field(
        False,
        description="Ljung–Box 不拒绝无自相关：前端提示低预测价值，不剔除、不压权重。",
    )
    max_weight_cap: Optional[float] = None
    weight_zero: bool = False
    vol_ann: float = 0.0
    ac1: float = 0.0
    p1_protocol_exclude: bool = Field(
        False,
        description="已弃用硬拦截；保留字段以兼容旧快照，恒为 False。",
    )


class Phase1Output(BaseModel):
    h_struct: float = 1.0
    gamma_multiplier: float = 1.0
    diagnostics: List[AssetDiagnostic] = Field(default_factory=list)
    pseudo_melt: bool = False  # 已弃用：恒 False；防御侧改由 diagnostics + ADF 过关判定
    pseudo_melt_detail: str = ""
    sentiment_score: float = 0.0


# --- Phase 2 ---
class Phase2Input(BaseModel):
    symbols: List[str]
    validation_residuals_std: Dict[str, float] = Field(default_factory=dict)
    jsd_baseline_window: int = 5


class Phase2Output(BaseModel):
    credibility_score: float = Field(
        0.7,
        description="clip(基准−惩罚)；与 consistency_score 数值相同",
    )
    credibility_base_jsd: float = Field(
        0.7,
        description="1/(1+α·JSD_triangle)，惩罚前",
    )
    credibility_coverage_penalty: float = Field(
        0.0,
        description="覆盖率逊于 Naive 时的惩罚（含 β·JSD 与上限）",
    )
    density_test_failed: bool = Field(
        False,
        description="任一路结构模型 OOS 名义 95% 覆盖低于 Naive",
    )
    prob_coverage_naive: Optional[float] = Field(
        None,
        description="Naive 模型 pooled OOS 实证覆盖率",
    )
    consistency_score: float = 0.7
    jsd_matrix: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    jsd_baseline_mean: float = 0.0
    jsd_pairs_mean: float = 0.0
    # Jensen-Shannon divergence triangle (Kronos / LightGBM=GBM / ARIMA): symmetric, bounded ~[0,0.347]
    jsd_kronos_arima_mean: float = 0.0
    jsd_kronos_gbm_mean: float = 0.0
    jsd_gbm_arima_mean: float = 0.0
    jsd_triangle_mean: float = 0.0
    jsd_triangle_max: float = 0.0
    # Per-symbol test-window mean JSD (keys: kronos_arima, kronos_gbm, gbm_arima, triangle)
    jsd_by_symbol: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    jsd_stress: bool = False
    logic_break: bool = False
    logic_break_from_ac1: bool = Field(
        False,
        description="训练期市场均收益一阶自相关 AC1 < τ_AC1",
    )
    logic_break_semantic_cosine_negative: bool = Field(
        False,
        description="测试窗 S_t 与数值预测的滚动余弦相似度在任意窗口内 < 0（语义–数值背离）",
    )
    train_return_ac1: float = Field(
        0.0,
        description="训练期截面均值对数收益的一阶自相关系数 ρ₁（AC1）",
    )
    semantic_numeric_cosine_computed: bool = Field(
        False,
        description="是否在测试窗上成功计算 S_t 与数值趋势的余弦相似度",
    )
    cosine_semantic_numeric: float = Field(
        0.0,
        description=(
            "当 semantic_numeric_cosine_computed 为真：滚动余弦相似度（通常取最后一个有效窗）；否则为 0（占位）。"
        ),
    )
    mse_naive: Optional[float] = None
    mse_kronos: Optional[float] = None
    mse_arima: Optional[float] = None
    mse_lightgbm: Optional[float] = None
    # Per-asset best model selected by shadow holdout MSE (model name → symbol key)
    best_model_per_symbol: Dict[str, str] = Field(default_factory=dict)
    shadow_note: str = ""
    # model -> symbol -> point estimate (last OOS test day) for UI overlays
    model_mu: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    model_sigma: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    # Strict OOS time-series: model -> symbol -> list aligned to test_forecast_dates
    # Each entry i = prediction made at test date i using only info before test date i
    test_forecast_dates: List[str] = Field(default_factory=list)
    # 测试窗逐日截面均值三角 JSD（与 test_forecast_dates 对齐）；用于失效识别提前量验证
    test_daily_triangle_jsd_mean: List[float] = Field(default_factory=list)
    # 测试窗逐日各模型对截面均值 JSD（与 test_forecast_dates 对齐）
    test_daily_jsd_kronos_arima: List[float] = Field(default_factory=list)
    test_daily_jsd_kronos_gbm: List[float] = Field(default_factory=list)
    test_daily_jsd_gbm_arima: List[float] = Field(default_factory=list)
    # 测试窗逐日影子最优模型 μ 截面均值（各标的取影子最优模型的 μ，再等权平均）
    test_daily_best_model_mu_mean: List[float] = Field(
        default_factory=list,
        description="每个测试日，各标的按影子最优模型取 μ 后截面等权均值，用于语义背离度计算",
    )
    model_mu_test_ts: Dict[str, Dict[str, List[float]]] = Field(default_factory=dict)
    model_sigma_test_ts: Dict[str, Dict[str, List[float]]] = Field(default_factory=dict)
    # True when Kronos ran real Transformer inference (not statistical proxy)
    kronos_real_inference: bool = False
    # OOS Gaussian log-score (negative log-likelihood), pooled over test×symbols
    prob_nll_mean: Dict[str, float] = Field(
        default_factory=dict,
        description="Mean NLL per model (naive, arima, lightgbm, kronos) under N(μ,σ²)",
    )
    prob_dm_pvalue_vs_naive: Dict[str, float] = Field(
        default_factory=dict,
        description="Diebold–Mariano two-sided p-value: H0 E[NLL_naive−NLL_m]=0 (arima, lightgbm, kronos)",
    )
    prob_dm_statistic: Dict[str, float] = Field(
        default_factory=dict,
        description="DM HAC t-statistic for the same test",
    )
    prob_coverage_95: Dict[str, float] = Field(
        default_factory=dict,
        description="Empirical coverage of nominal 95% Gaussian intervals",
    )
    model_traffic_light: Dict[str, str] = Field(
        default_factory=dict,
        description="arima/lightgbm/kronos → green|yellow|red from NLL+DM+coverage",
    )
    prob_full_pipeline_failure: bool = Field(
        False,
        description="True when all three structural models are red (全流程概率预测失效)",
    )


# --- Phase 3 ---
class Phase3Input(BaseModel):
    symbols: List[str]
    defense_level: int = 0
    mu_daily: List[float] = Field(default_factory=list)
    cov_daily: List[List[float]] = Field(default_factory=list)
    sentiments: Dict[str, float] = Field(default_factory=dict)
    jump_p: float = Field(
        0.05,
        description="年化泊松跳跃强度 λ∈[0,1]（Sentiment_to_Jump_Params 的 p）；步内概率 1−exp(−λΔt)。",
    )
    jump_impact: float = Field(
        -0.15,
        description="对数跳跃幅度∈[-0.3,0.3]（负值表示下跌）。",
    )
    mc_horizon_days: int = Field(252, ge=10, description="蒙特卡洛模拟交易日数（44≈测试期；252≈一年）")
    scenario_inject_step: Optional[int] = Field(
        None, description="在第 N 步对所有压力路径注入确定性对数冲击（None=不注入；30≈美伊冲突时点）"
    )
    scenario_inject_impact: float = Field(
        -0.12, description="情景注入对数收益率冲击∈[-0.5,0]（-0.12≈-11%单日跌幅）"
    )
    mc_sentiment_path: Optional[List[float]] = Field(
        None,
        description=(
            "若长度≥mc_horizon_days：MC 每步跳跃强度/幅度由 S_t 经 sentiment_to_jump_params 映射；"
            "否则回退为常数 jump_p / jump_impact。"
        ),
    )
    blocked_symbols: List[str] = Field(
        default_factory=list,
        description="Phase1 拦截标的：权重置零后按剩余标的归一化（与管线一致）。",
    )
    test_returns_daily: Optional[List[List[float]]] = Field(
        None,
        description="测试窗日收益矩阵 [T×N]，列顺序与 symbols 一致；用于已实现路径上的防御对照。",
    )
    custom_portfolio_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Phase 0 饼图「自定义权重」，键为数据列名（如 TSM）；缺省则测试窗对照用等权。",
    )


class Phase3DefenseValidation(BaseModel):
    """反事实对照 + 0.3 研究答案结构化证据（管线写入）。"""

    comparison_active: bool = False
    baseline_objective: str = "max_sharpe"
    counterfactual_weights: Dict[str, float] = Field(default_factory=dict)
    # 含跳 MC 终端财富（同 rng seed=7 的并行流，可比）
    actual_stress_p5_terminal: Optional[float] = None
    baseline_stress_p5_terminal: Optional[float] = None
    stress_p5_terminal_lift_pct: Optional[float] = None
    actual_mdd_p95_pct: Optional[float] = None
    baseline_mdd_p95_pct: Optional[float] = None
    mdd_p95_improvement_pctpts: Optional[float] = None
    # 测试窗简单复利（可选）
    test_cumulative_return_actual: Optional[float] = None
    test_cumulative_return_baseline: Optional[float] = None
    test_max_drawdown_pct_actual: Optional[float] = None
    test_max_drawdown_pct_baseline: Optional[float] = None
    # 测试窗三条可比净值：Level0 Max-Sharpe / 自定义权重 / Level2 CVaR（同一样本外收益矩阵）
    test_equity_max_sharpe: Optional[List[float]] = None
    test_equity_custom_weights: Optional[List[float]] = None
    test_equity_cvar: Optional[List[float]] = None
    test_terminal_cumret_max_sharpe: Optional[float] = None
    test_terminal_cumret_custom_weights: Optional[float] = None
    test_terminal_cumret_cvar: Optional[float] = None
    test_mdd_pct_max_sharpe: Optional[float] = None
    test_mdd_pct_custom_weights: Optional[float] = None
    test_mdd_pct_cvar: Optional[float] = None
    resolved_custom_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="与三轨累计曲线一致的自定义权重（拦截后归一）。",
    )
    # --- 0.3 预期答案：分歧 / 退守 / 语义先验 ---
    research_consistency_score: Optional[float] = None
    research_tau_l2: Optional[float] = None
    research_tau_l1: Optional[float] = None
    research_defense_sentiment_min_st: Optional[float] = None
    research_tau_s_low: Optional[float] = None
    research_semantic_numeric_divergence: bool = False
    research_jsd_stress: bool = False
    research_prob_full_pipeline_failure: bool = False
    research_semantic_alarm_day_offset: Optional[int] = Field(
        None,
        description="测试窗内首次 S_t 跌破 τ_S_low 的日序号（0 起）。",
    )
    research_price_instability_day_offset: Optional[int] = Field(
        None,
        description="等权组合 5 日波动突破全窗 85% 分位的首日序号（0 起）。",
    )
    research_semantic_lead_trading_days: Optional[int] = Field(
        None,
        description="价格不稳日序 − 语义告警日序；正数表示语义先验更早。",
    )
    research_test_window_label: str = ""
    research_scenario_inject_step: Optional[int] = None
    research_early_april_2026_window: bool = Field(
        False,
        description="测试窗是否与 2026-04 上旬相交（叙事：4 月初非稳态）。",
    )
    # 失效识别有效性：相对「价格不稳」参照日的提前量（交易日；正 = 信号更早）
    research_failure_ref_label: str = Field(
        "",
        description="参照「失效/压力实现」日的操作化定义（与 price_off 同源）。",
    )
    research_alarm_day_rolling_h_struct: Optional[int] = Field(
        None,
        description="滚动协方差结构熵首次低于 τ_h1 的测试窗日序号（0 起）。",
    )
    research_alarm_day_rolling_jsd_stress: Optional[int] = Field(
        None,
        description=(
            "滚动 W=semantic_cosine_window 日三角 JSD 均值首次超过 "
            "k_jsd×max(jsd_baseline_mean, jsd_baseline_eps) 的日序号（0 起）。"
        ),
    )
    research_alarm_day_credibility_l1: Optional[int] = Field(
        None,
        description="由逐日三角 JSD 推出的可信度代理首次 ≤ τ_l1 的日序号。",
    )
    research_alarm_day_semantic_cosine_negative: Optional[int] = Field(
        None,
        description="前缀样本上滚动余弦相似度首次 <0 的日序号（语义–数值背离）。",
    )
    research_lead_ref_vs_h_struct: Optional[int] = None
    research_lead_ref_vs_jsd_stress: Optional[int] = None
    research_lead_ref_vs_credibility: Optional[int] = None
    research_lead_ref_vs_semantic_cosine: Optional[int] = None
    research_failure_early_warning_verdict: str = Field(
        "",
        description="是否命中「提前 1～5 交易日」口径的短文结论。",
    )
    # 告警后逐标的实现收益：大跌定义、横截面混乱度、尾部加厚（无组合权重）
    research_crash_definition_label: str = Field(
        "",
        description="逐标的大跌操作化定义（训练分位阈值 + 后 3 日复合收益）说明。",
    )
    research_post_jsd_realized: Optional[Dict[str, Any]] = Field(
        None,
        description="JSD 应力首次告警行之后 1–3 日的逐标的 R^(3)、混乱度与尾部对比。",
    )
    research_post_cos_realized: Optional[Dict[str, Any]] = Field(
        None,
        description="语义–数值余弦首次负向告警行之后同上。",
    )
    # Fig4.1 主栏「预警有效性」Plotly 叠加层专用（与上方研究字段独立存储）
    fig41_ew_ref_test_row: Optional[int] = Field(
        None,
        description="参照压力日在 Phase2 测试窗内的行序（0 起）。",
    )
    fig41_ew_ref_date_iso: Optional[str] = Field(
        None,
        description="参照压力日 ISO 日期（YYYY-MM-DD）。",
    )
    fig41_ew_jsd_alarm_row: Optional[int] = Field(
        None,
        description="JSD 应力首次触发在测试窗内的行序（与 FigX.5 同源）。",
    )
    fig41_ew_cos_alarm_row: Optional[int] = Field(
        None,
        description="语义余弦首次 <0 在测试窗内的行序（与 FigX.6 同源）。",
    )
    fig41_ew_lead_effective_lo: int = Field(
        1,
        ge=1,
        description="提前量有效区间下界（交易日）。",
    )
    fig41_ew_lead_effective_hi: int = Field(
        5,
        ge=1,
        description="提前量有效区间上界（交易日）。",
    )
    fig41_verify: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Fig4.1 固定 5 日窗的预警成功验证产物（以更早的 t0 为锚）。"
            "包含单资产日收益/尾比、全资产 Std/占比、点阵，以及三维度交通灯判定（成功/较成功/失败）。"
        ),
    )
    fig41_verify_mm: Optional[Dict[str, Any]] = Field(
        None,
        description="Fig4.1 模型—模型检验（t0 = JSD 首次告警日）独立结果；结构同 fig41_verify。",
    )
    fig41_verify_mv: Optional[Dict[str, Any]] = Field(
        None,
        description="Fig4.1 模型—市场检验（t0 = 余弦首次背离日）独立结果；结构同 fig41_verify。",
    )


class Phase3Output(BaseModel):
    objective_name: str = ""
    weights: Dict[str, float] = Field(default_factory=dict)
    sharpe: Optional[float] = None
    cvar: Optional[float] = None
    mc_conservative_mean: Optional[List[float]] = None
    mc_stress_p5: Optional[List[float]] = None
    mc_timesteps: int = 0
    # Subsampled paths for Dash (baseline=no jump, stress=jump); rows = paths, cols = time index
    mc_paths_baseline: List[List[float]] = Field(default_factory=list)
    mc_paths_stress: List[List[float]] = Field(default_factory=list)
    mc_times: List[float] = Field(default_factory=list)
    mc_worst_stress_path_index: int = 0
    mc_expected_max_drawdown_pct: Optional[float] = Field(
        None,
        description="Representative max drawdown (%) along the P5 stress path for UI annotation.",
    )
    mc_mdd_p95: Optional[float] = Field(
        None,
        description="95th-percentile MDD (%) across ALL 10,000 stress paths — distributional tail risk.",
    )
    # Phase3.md / AnsToInq：无跳路径中位数轨 & 含跳 5% 分位单轨（与 mc_times 对齐，已下采样）
    mc_path_median_nojump: List[float] = Field(default_factory=list)
    mc_path_jump_p5: List[float] = Field(default_factory=list)
    mc_stress_percentile5_path_index: int = 0
    # ISO date strings aligned with mc_times (computed in pipeline from test period index)
    mc_date_labels: List[str] = Field(default_factory=list)
    defense_validation: Optional[Phase3DefenseValidation] = Field(
        None,
        description="防御有效性：实际优化 vs 反事实 Level0 的尾部与已实现对照。",
    )


class PipelineSnapshot(BaseModel):
    """Full run output for API/UI."""

    phase0: Phase0Output
    phase1: Phase1Output
    phase2: Phase2Output
    phase3: Phase3Output
    defense_level: int = 0
    defense_policy: DefensePolicyConfig = Field(default_factory=DefensePolicyConfig)
    policy_version: str = "1"
    shadow_blind_cumulative: List[float] = Field(default_factory=list)
    shadow_fused_cumulative: List[float] = Field(default_factory=list)
    shadow_p0_mc_median_cumulative: List[float] = Field(
        default_factory=list,
        description="P0 式纯 MC：等权组合、无跳跃扩散，10k 路径财富中位数减 1，与 shadow 日期对齐。",
    )
    shadow_index_labels: List[str] = Field(default_factory=list)
    shadow_mdd_blind_pct: float = 0.0
    shadow_mdd_fused_pct: float = 0.0
