"""Fig4.1 数据契约（dataclass；冻结；纯数据无行为）。

所有字段均为标准 Python 类型（float/int/str/list/dict/Optional）或其它冻结
dataclass；不含任何 Dash / Plotly 对象，便于序列化、单元测试与最小复现。

**关键设计决策**：

* 冻结（``frozen=True``）：防止上游函数意外修改 Bundle；所有变更必须产生新的
  Bundle 实例。
* ``Fig41Context``：把渲染时需要的 6 个外部输入（tpl / ui_mode / snap_json
  / policy / p2 / meta / symbols）打包成一个对象，避免函数签名爆炸。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Fig41Baselines:
    """训练窗侧生成的三条基线（用于与实测值比对）。"""

    std_thr: Optional[float]              # 横截面 Std 基线阈值
    crash_ratio_thr: Optional[float]      # 大跌资产占比基线阈值
    tail_ratio_thr: Optional[float]       # 厚尾占比基线阈值
    tail_p_each_side: float               # 来自 policy.verify_tail_quantile_pct 的单侧 p
    # 逐标的大跌阈值（R^(h) 下分位）；供 UI 侧 focus 搜索重绑定时为新焦点取阈值
    per_symbol_crash_thr: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Fig41Hits:
    """三维命中判定（与 verdict 一起构成 hero alert 的核心）。"""

    verdict: str                          # "成功" | "较成功" | "失败" | "—"
    n_hit: Optional[int]                  # 0..3；None 表示无数据
    std_above_baseline: bool
    crash_ratio_above_baseline: bool
    tail_ratio_above_baseline: bool


@dataclass(frozen=True)
class Fig41PostAlarm:
    """告警后 1..h 日的逐标的实现指标。"""

    symbols: List[str]
    per_symbol_crash: Dict[str, Any]      # {sym: truthy→大跌}
    tail_flags_5xN: List[List[int]]       # 最多 5 行（天），每行长度 == len(symbols)
    crash_ratio: Optional[float]
    tail_ratio: Optional[float]
    cross_section_std_Rh: Optional[float]
    post_dates: List[str]
    # 以下为 UI 侧 focus 搜索重绑定所需（additive；旧快照缺失时为空）
    per_symbol_Rh: Dict[str, float] = field(default_factory=dict)
    per_symbol_daily_returns: Dict[str, List[float]] = field(default_factory=dict)
    tail_left_thr: Optional[float] = None
    tail_right_thr: Optional[float] = None


@dataclass(frozen=True)
class Fig41DualVerdict:
    """模型—模型（JSD）与模型—市场（余弦）两路 verdict + 告警日。"""

    mm_verdict: str                       # JSD 信号 verdict（"成功" / "较成功" / "失败" / "—"）
    mv_verdict: str                       # 余弦信号 verdict
    mm_t0_date: Optional[str]             # 模型—模型 告警日（ISO，YYYY-MM-DD）
    mv_t0_date: Optional[str]             # 模型—市场 告警日（ISO）
    earliest_t0_date: Optional[str]       # 更早者；若两路全失败为 None（兼容旧字段）
    # 新规则：mv 优先 > mm；仅当至少一路成功时非 None
    final_t0_date: Optional[str] = None


@dataclass(frozen=True)
class Fig41Bundle:
    """Fig4.1 的**完整输入**（抽取自快照），不可变纯数据。

    所有下游渲染只能从此对象读数据，严禁回头再 ``snap_json.get(...)``。
    """

    focus_symbol: str
    hits: Fig41Hits
    post: Optional[Fig41PostAlarm]        # None ⇒ 渲染走 fallback 分支
    baselines: Fig41Baselines
    focus_daily_returns: List[float]
    focus_post_dates: List[str]
    focus_tail_left_ratio: Optional[float]
    focus_tail_right_ratio: Optional[float]
    cross_section_std_by_k: List[float]
    # Part 1 右栏：当前标的 R^(h) vs 逐标大跌阈值
    focus_Rh: Optional[float] = None
    focus_crash_thr_Rh: Optional[float] = None
    focus_is_crash: Optional[bool] = None
    # Part 5/6：双信号 verdict + 最终结论分析所需最早预警日
    dual: Optional[Fig41DualVerdict] = None

    @property
    def has_post(self) -> bool:
        """是否有告警后实现数据（决定 panel 走主分支还是 markdown fallback）。"""
        return self.post is not None


@dataclass(frozen=True)
class Fig41Context:
    """渲染所需的外部上下文（打包避免函数签名爆炸）。

    Attributes:
        tpl: Plotly template（通常 ``"plotly_dark"`` / ``"plotly"``）。
        ui_mode: ``"invest"`` / ``"research"``；用于 fallback markdown 选择。
        snap_json: 原始快照（仅 fallback 分支用到）。
        policy: 策略配置（主要用于 ``verify_tail_quantile_pct``）。
        p2: ``snap_json["phase2"]`` 的浅拷贝，fallback markdown 注入用。
        meta: ``snap_json["phase0"]["meta"]``。
        symbols: 当前标的列表。
    """

    tpl: str
    ui_mode: Optional[str]
    snap_json: Dict[str, Any]
    policy: Any                           # DefensePolicyConfig（避免循环 import）
    p2: Dict[str, Any]
    meta: Dict[str, Any]
    symbols: List[str]
    # UI 侧搜索重绑定：若非 None 且 ∈ post.symbols，则把 focus_* 系列字段切到该标的
    focus_override: Optional[str] = None
    # 顶行 "XX 预警日" banner 的标题（如 "模型—模型应力预警日"）
    signal_label: Optional[str] = None
    # 顶行 banner 的日期（ISO YYYY-MM-DD）；None 时在渲染层回退到 bundle.dual.final_t0_date
    alarm_date_iso: Optional[str] = None


@dataclass(frozen=True)
class Fig41Components:
    """渲染输出（一路检验的组件）：hero + banner + daily chart + 分析面板。

    结论卡 **不在此处**，由调用方（``render/main_p4.py``）另行构造为独立 Card。
    """

    hero: Any                             # Part 1 右栏 "当前标的 + 大跌提示"（亮红 / 银灰）
    panel: Any                            # html.Div（Part 2-5）或 dcc.Markdown（fallback）
    fig_daily_returns: Any                # go.Figure — Chart 1 折线图
    alarm_banner: Any = None              # 顶行 "XX 预警日：YY.MM.DD"（黑底黄字）
