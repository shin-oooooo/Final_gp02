"""顶栏诊断 headline — 由 main_p0 的 diag_alert 调用展示。"""

from __future__ import annotations


def system_diagnosis_headline(
    defense_level: int,
    jsd_stress: bool,
    jsd_tri_mean: float,
    jsd_thr: float,
    adf_asset_failure: bool,
    h_struct: float,
    tau_h1: float,
    prob_full_pipeline_failure: bool = False,
) -> str:
    """组装一行系统级诊断文字（含 JSD / ADF / 结构熵 / 概率层失效的逐项提示）。"""
    parts: list[str] = []
    if defense_level >= 2:
        parts.append(
            "【结论】系统处于 Level 2 熔断：以尾部损失控制优先，由模型间一致性过低（≤ τ_L2）触发。"
        )
    elif defense_level == 1:
        parts.append(
            "【结论】系统处于 Level 1 警戒：模型分歧、结构熵偏低、ADF 把关失败或其它告警可能已触发，语义惩罚已介入资产配置。"
        )
    else:
        parts.append("【结论】系统处于 Level 0 常规：统计与模型层未突破主要熔断阈值。")
    if jsd_stress:
        parts.append(
            f"JSD 应力：测试窗内存在 W=semantic_cosine_window 日滚动三角 JSD 超过 k×训练基线（阈值约 {jsd_thr:.3f}）；"
            f"全窗三角 JSD 均值约 {jsd_tri_mean:.3f}。"
        )
    elif jsd_tri_mean > jsd_thr:
        parts.append(
            f"三角 JSD 全窗均值 {jsd_tri_mean:.3f} 高于参照阈值 {jsd_thr:.3f}（k×训练期基线），但滚动应力未触发。"
        )
    if adf_asset_failure:
        parts.append("Phase1：存在标的未通过 ADF（单位根/差分）管线检验，已计入 Level 1 警示。")
    if h_struct < tau_h1:
        parts.append(f"结构熵 {h_struct:.3f} 低于 τ_H1={tau_h1:.2f}，资产趋同风险上升。")
    if prob_full_pipeline_failure:
        parts.append(
            "【概率层】样本外高斯对数得分（NLL）下 Diebold–Mariano 检验显示 ARIMA/LightGBM/Kronos 相对 Naive 的改良均不显著（三模型均为红灯），"
            "判定概率预测全流程失效。"
        )
    return " ".join(parts)
