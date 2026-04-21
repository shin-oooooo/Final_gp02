"""Research trace — 组装弹窗四段（结果 / 计算 / 参数 / 学习）。"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from dash_app.features.research_trace.code import snapshot_value_excerpt
from dash_app.features.research_trace.models import TraceModalSections, get_trace


def _data_layer_md() -> str:
    """所有 trace 共用的底层数据来源说明（放在 result_raw 末尾）。"""
    return (
        "底层行情与交易日索引来自本地 **`data.json`**（或环境变量 **`AIE1902_DATA_JSON`**）；"
        "`research.pipeline.run_pipeline` 读取后在各 Phase 中按 `phase0.train_index` / `test_index` "
        "与 `phase0.meta.resolved_windows` 对齐切片。"
    )


def _policy_fields_md(snap: Optional[Dict[str, Any]], *keys: str) -> str:
    """把快照里 ``defense_policy`` 的若干字段格式化成 Markdown 列表。"""
    pol = (snap or {}).get("defense_policy") if isinstance(snap, dict) else None
    if not isinstance(pol, dict) or not pol:
        return "（当前快照中无 `defense_policy` 或为空；可信度相关系数可能为后端默认。）"
    lines = [f"- `{k}`：`{pol.get(k)}`" for k in keys if k in pol]
    if not lines:
        return "（所选策略字段在快照中缺失。）"
    return "与侧栏 **`last-snap.defense_policy`** 对齐：\n\n" + "\n".join(lines)


def _sections_credibility(snap: Optional[Dict[str, Any]], why_md: str, base_result: str) -> tuple[str, str, str, str]:
    p2 = (snap or {}).get("phase2") if isinstance(snap, dict) else {}
    p2 = p2 if isinstance(p2, dict) else {}
    calc = (
        f"{why_md}\n\n"
        "1. 在测试窗上，将各模型与 Naive 的 **密度预测** 与 **经验收益分布** 离散到同一网格，得到三角上的分布三元组。\n"
        "2. **基准项**：`credibility_base_jsd = 1 / (1 + α · JSD_triangle_mean)`，其中 α 为 `credibility_baseline_jsd_scale`。\n"
        "3. **惩罚项**：若名义 95% 预测区间覆盖率整体劣于 Naive（`density_test_failed`），"
        "则按 `min(上限, β · JSD_triangle_mean)` 累加惩罚，β 为 `credibility_penalty_jsd_scale`，上限为 `credibility_penalty_cap`。\n"
        "4. **输出**：`credibility_score = clip(基准 − 惩罚, min, max)`，与侧栏红黄绿阈值比较。"
    )
    pol_md = _policy_fields_md(
        snap,
        "k_jsd",
        "semantic_cosine_window",
        "jsd_baseline_eps",
        "credibility_baseline_jsd_scale",
        "credibility_penalty_jsd_scale",
        "credibility_penalty_cap",
        "credibility_score_min",
        "credibility_score_max",
    )
    raw_align = (
        f"{base_result}\n\n"
        "本指标直接消费 **测试窗内** 各模型的一步前向密度（与 Naive 对照），"
        "其输入收益序列与 `phase0` 解析出的训练/测试日期对齐；"
        f"标量结果写入 **`last-snap.phase2`**（如 `credibility_score`、`jsd_triangle_mean`、`density_test_failed` 等）。\n\n"
        f"**密度检验相关中间量**（若存在）：`density_test_failed={p2.get('density_test_failed')}`。"
    )
    learn = (
        "可信度为 **单次 pipeline 运行** 上的确定性聚合，不另设独立「训练步」；"
        "α、β、clip 界等 **模型参数** 来自侧栏策略（`defense_policy`），与本次快照一并序列化。\n\n"
        "各预测模型（ARIMA / LightGBM / Kronos 等）的 **拟合/滚动预测** 过程见「影子验证 MSE」与「概率检验」溯源项。"
    )
    return raw_align, calc, pol_md, learn


def _sections_shadow_mse(snap: Optional[Dict[str, Any]], why_md: str, base_result: str) -> tuple[str, str, str, str]:
    calc = (
        f"{why_md}\n\n"
        "在训练窗末端留出 **影子尾段**（长度 `DefensePolicyConfig.shadow_holdout_days`，默认 40；伪样本外，仅训练数据），"
        "对各模型与 Naive 计算一步预测 MSE；再结合 JSD 到经验分布等指标，用 `alpha_model_select` 做 **MSE–JSD 综合择模**，"
        "得到 `best_model_per_symbol` 与像素矩阵着色。"
    )
    pol_md = _policy_fields_md(
        snap, "alpha_model_select", "shadow_holdout_days", "oos_fit_steps"
    )
    p0 = (snap or {}).get("phase0") if isinstance(snap, dict) else {}
    p0 = p0 if isinstance(p0, dict) else {}
    ti, te = len(p0.get("train_index") or []), len(p0.get("test_index") or [])
    raw_align = (
        f"{base_result}\n\n"
        f"**切片规模**：`phase0.train_index` 长度 {ti}，`test_index` 长度 {te}。"
        "影子 MSE 使用的真实标的价格/收益仍来自 `data.json`，仅在时间索引上与上述窗求交。"
    )
    learn = (
        "**Naive**：历史均值基线，无参数学习。\n\n"
        "**ARIMA**：在训练窗（或 pipeline 规定的滚动子窗）上用 `statsmodels` 自动阶选择并拟合，再在影子尾段上滚动一步预测。\n\n"
        "**LightGBM**：在训练特征上拟合梯度提升树（默认超参由 `research/phase2.py` 给出），在尾段上逐步预测。\n\n"
        "**Kronos**（若启用）：按仓库内适配器在训练段校准，再在尾段上给出 μ/σ 或样本路径供 MSE 计算。"
    )
    return raw_align, calc, pol_md, learn


def _sections_prob_tests(snap: Optional[Dict[str, Any]], why_md: str, base_result: str) -> tuple[str, str, str, str]:
    calc = (
        f"{why_md}\n\n"
        "在 **正式测试窗** 上收集各模型的一步前向高斯（或 pipeline 设定）预测，与实现收益对比：\n"
        "- **NLL**：负对数似然按日平均；\n"
        "- **DM 检验**：相对 Naive 的 Diebold–Mariano，HAC 稳健标准误；\n"
        "- **覆盖率**：名义 95% 区间命中实现收益的比例。"
    )
    pol_md = _policy_fields_md(snap, "oos_fit_steps", "alpha_model_select")
    raw_align = (
        f"{base_result}\n\n"
        "概率指标完全由 **测试窗对齐** 的预测分布与实现收益构造；"
        "原始收益仍出自 `data.json`，结果字段在 **`last-snap.phase2`**（如 `prob_nll_mean`、`prob_dm_pvalue_vs_naive`、`prob_coverage_95`）。"
    )
    learn = (
        "与影子 MSE 类似：各结构模型在训练段完成 **参数学习**，测试窗只做 **前向评估** 与统计检验；"
        "DM/NLL 不引入额外超参，显著性由样本路径上的预测误差序列驱动。"
    )
    return raw_align, calc, pol_md, learn


def _sections_st_series(snap: Optional[Dict[str, Any]], why_md: str, base_result: str) -> tuple[str, str, str, str]:
    meta = {}
    if isinstance(snap, dict):
        p0 = snap.get("phase0")
        if isinstance(p0, dict):
            meta = p0.get("meta") if isinstance(p0.get("meta"), dict) else {}
    calc = (
        f"{why_md}\n\n"
        "对 `sentiment_detail`（或等价结构）中的新闻级情绪，在 **测试窗交易日** 上聚合为日度得分，再按配置做 **分段累积** 得到 S_t；"
        "随后可与四模型 OOS μ 序列一起做滚动余弦相似度（窗口 W=`semantic_cosine_window`）。"
    )
    pol_md = _policy_fields_md(snap, "semantic_cosine_window", "tau_s_low", "tau_s_high")
    extra = ""
    if meta.get("test_sentiment_st"):
        extra = "\n\n序列已物化在 **`phase0.meta.test_sentiment_st`**（`dates` / `values`）。"
    raw_align = f"{base_result}\n\n**情绪原始层**：来自运行当次注入的 `sentiment_detail` 与新闻日历跨度；{extra}"
    learn = (
        "S_t 的 **学习** 指：VADER（或当前 pipeline 配置）对文本打分的统计规则，加上按日的累积与对齐；"
        "不涉及与价格联合的梯度训练。滚动余弦仅对已有序列做窗口计算，窗口由 `semantic_cosine_window` 决定。"
    )
    return raw_align, calc, pol_md, learn


def _sections_windows(snap: Optional[Dict[str, Any]], why_md: str, base_result: str) -> tuple[str, str, str, str]:
    meta = {}
    if isinstance(snap, dict):
        p0 = snap.get("phase0")
        if isinstance(p0, dict):
            meta = p0.get("meta") if isinstance(p0.get("meta"), dict) else {}
    rw = meta.get("resolved_windows") or {}
    calc = (
        f"{why_md}\n\n"
        "解析顺序概览：`Phase0Input` 中的起止日与 `data.json` 可用交易日求交，必要时按新闻可用范围收缩，"
        "最终写入 `phase0.meta.resolved_windows` 供后续 Phase 统一引用。"
    )
    rw_txt = json.dumps(rw, ensure_ascii=False, indent=2, default=str) if rw else "{}"
    raw_align = f"{base_result}\n\n**已解析窗体**（摘自快照）：\n\n```\n{rw_txt}\n```"
    pol_md = (
        "该步骤 **不读取** 侧栏 `defense_policy` 中的模型超参；"
        "与窗体相关的只有 `Phase0Input`（训练/测试起止、`regime_break_*` 等），其生效值见本次请求的 phase0 输入载荷（与快照中 `phase0` 输出并列于运行日志侧）。"
    )
    learn = "纯规则解析与集合求交，无随机优化或梯度学习。"
    return raw_align, calc, pol_md, learn


# 注册表：trace_key → section builder
_BUILDERS = {
    "p2_credibility": _sections_credibility,
    "p2_shadow_mse": _sections_shadow_mse,
    "p2_prob_tests": _sections_prob_tests,
    "st_series": _sections_st_series,
    "windows": _sections_windows,
}


def get_trace_modal_sections(snap: Optional[Dict[str, Any]], trace_key: str) -> Optional[TraceModalSections]:
    """Structured sections for the research trace modal（方案1 索引树）。

    外部接口签名保持不变；内部按 ``trace_key`` 分发到 ``_sections_*`` helper。
    """
    t = get_trace(trace_key)
    if t is None:
        return None
    ex = snapshot_value_excerpt(snap, trace_key)
    base_result = f"**快照摘录**：`{ex}`\n\n**原始数据链路**：{_data_layer_md()}"

    builder = _BUILDERS.get(trace_key)
    if builder is not None:
        raw_align, calc, pol_md, learn = builder(snap, t.why_md, base_result)
        return TraceModalSections(raw_align, calc, pol_md, learn, t.code)

    # 未注册的 trace_key：回退到最小段落组装
    return TraceModalSections(
        base_result, t.why_md, "（本索引项未拆分策略字段。）", "（无单独学习过程说明。）", t.code
    )
