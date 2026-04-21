# All Labels · 顶栏 / 右侧栏 / 主栏（P0–P4）按钮与散装文案

> Dash 应用**全站静态字符串的单一事实来源**。修改规则：**只改引号内文字，不改左侧键**
> —— 键被 Python 源码引用，改名会断链。新增键时优先复用前缀（`btn_`, `tab_`, `modal_`,
> `p0_`, `p1_`, `p2_`, `p3_`, `p4_`, `aux_`, `overview_`, `diag_`, `level_status_`）。
>
> 统一读取：`services/copy.py::get_topbar_label(key, default)` 或其同义别名
> `get_app_label(key, default)`。回退链：`all_labels.md` →（历史）`topbar_labels.md` →
> `assets/topbar_labels.json` → `default`。中英文由 `?lang=chn|eng` 切换 **各自目录**
> 下的 `all_labels.md`（`content-CHN/` 与 `content-ENG/` **互不穿透**）。

---

## 0 · 大篇幅讲解与叙述 —— 源文件直达（只链接、不内联）

下列模块/文件产出**带业务逻辑条件拼接**或**长篇正文**的内容，占位符密集、改动成本高，
不适合在扁平 `key: "value"` 里维护。修改时请直接编辑对应源文件；新增规则时同步更新
`Inv/-Inv.md` 与 `Res/-Res.md` 双版本（见 `services/copy.py::get_md_text_by_mode`）。

### 讲解 MD（用户可直接编辑）

- 左栏「防御策略与参数」小节正文 · `[sidebar_left.md](sidebar_left.md)` / `[sidebar_left_params_explanations.md](sidebar_left_params_explanations.md)`
- P1 统计方法长文（ADF / Ljung-Box / P 值含义）· `[p1_stat_method.md](p1_stat_method.md)`
- P2 影子择模与像素矩阵正文 · `[p2_pixel_shadow_intro.md](p2_pixel_shadow_intro.md)` · `[p2_fig21_intro.md](p2_fig21_intro.md)`
- P3 AdaptiveOptimizer 自适应优化器正文 · `[p3_section_31_adaptive.md](p3_section_31_adaptive.md)` · `[p3_section_32_dual_mc.md](p3_section_32_dual_mc.md)`
- 每图讲解（Invest 简介）· `[Inv/Fig0.1-Inv.md](Inv/Fig0.1-Inv.md)` · `[Inv/Fig0.2-Inv.md](Inv/Fig0.2-Inv.md)` · `[Inv/Fig1.1-Inv.md](Inv/Fig1.1-Inv.md)` · `[Inv/Fig2.1-Inv.md](Inv/Fig2.1-Inv.md)` · `[Inv/Fig2.2-Inv.md](Inv/Fig2.2-Inv.md)` · `[Inv/Fig3.1-Inv.md](Inv/Fig3.1-Inv.md)` · `[Inv/Fig4.1-Inv.md](Inv/Fig4.1-Inv.md)` · `[Inv/FigX.1-Inv.md](Inv/FigX.1-Inv.md)` · `[Inv/FigX.2-Inv.md](Inv/FigX.2-Inv.md)` · `[Inv/FigX.3-Inv.md](Inv/FigX.3-Inv.md)` · `[Inv/FigX.4-Inv.md](Inv/FigX.4-Inv.md)` · `[Inv/FigX.6-Inv.md](Inv/FigX.6-Inv.md)`
- 每图讲解（Research 数据/参数/方法论详情）· `[Res/](Res/)` 目录下同名 `-Res.md`
- 项目综述 · `[project_intro.md](project_intro.md)`
- 各阶段 Introduction · `[phase1_intro.md](phase1_intro.md)` · `[phase2_intro.md](phase2_intro.md)` · `[phase3_intro.md](phase3_intro.md)` · `[phase4_intro.md](phase4_intro.md)` · `[phase0_tab_intro.md](phase0_tab_intro.md)`
- 顶栏「使用提示」· `[hint_for_webapp.md](hint_for_webapp.md)`
- 顶栏「三列防御介绍」· `[defense_intro.md](defense_intro.md)` · `[defense_reasons.md](defense_reasons.md)`
- Kronos 权重状态提示 · `[kronos_hints.md](kronos_hints.md)`
- 图表标题 / 图下小字 / 状态信息 · `[figures_titles.md](figures_titles.md)` · `[figures_hints.md](figures_hints.md)` · `[status_messages.md](status_messages.md)`
- 方法论局限性 · `[Methodology_constraints.md](Methodology_constraints.md)`

### 业务逻辑文案（正文随 snapshot 动态拼接，需改 Python 源）

- Phase 0 顶栏聚合行（Level 判定驱动项一行总结）· `[../render/explain/topbar/p0_aggregate_line.py](../render/explain/topbar/p0_aggregate_line.py)`
- 顶栏每条诊断行（ADF / H_struct / 概率失效 / JSD / 余弦 / S_t）· `[../render/explain/topbar/diagnosis.py](../render/explain/topbar/diagnosis.py)`
- 顶栏三列 Level 介绍（defense_intro 的 dcc.Markdown 构造器）· `[../render/explain/topbar/defense_intro.py](../render/explain/topbar/defense_intro.py)`
- P0 长叙述（分类排序 / 均衡度 / 资产类占比）· `[../render/explain/main_p0/narrative.py](../render/explain/main_p0/narrative.py)` · `[../render/explain/main_p0/card_titles.py](../render/explain/main_p0/card_titles.py)`
- P1 组合分析长文 · `[../render/explain/main_p1/narrative.py](../render/explain/main_p1/narrative.py)`
- P4 Fig4.1/Fig4.2 实验栈叙述 · `[../render/explain/main_p4/fig41.py](../render/explain/main_p4/fig41.py)` · `[../render/explain/main_p4/fig42.py](../render/explain/main_p4/fig42.py)`
- FigX.3/4/6 侧栏逻辑条件行（高波动资产清单 / 三态灯 / 滚动余弦）· `[../render/explain/sidebar_right/figx3.py](../render/explain/sidebar_right/figx3.py)` · `[../render/explain/sidebar_right/figx4.py](../render/explain/sidebar_right/figx4.py)` · `[../render/explain/sidebar_right/figx6.py](../render/explain/sidebar_right/figx6.py)`
- Figure caption bundle（四图下方小字，带占位符注入）· `[../render/explain/figure_captions.py](../render/explain/figure_captions.py)`

---

# ─── 顶栏 · Topbar ─────────────────────────────────────────────────────────────

app_title: "AIE1902 防御研究"

btn_invest: "投资"
btn_research: "研究"
btn_lang_chn: "中"
btn_lang_eng: "EN"
btn_lang_chn_title: "切换到中文文案（加载 content-CHN/）"
btn_lang_eng_title: "Switch to English copy (loads content-ENG/)"

btn_run: "保存运行"
btn_run_icon: "fa-play"
btn_run_title_default: "保存配置并执行全链路（原「保存并运行」）"

btn_download_data_json: "下载 data.json"
btn_kronos_pull_icon: "fa-download"

btn_toggle_hints_label: "Webapp运行与使用提示"
btn_toggle_hints: "查看使用提示"
btn_toggle_defense_reasons: "展开查看各防御条件汇总"

defense_dashboard: "防御数据看板"
defense_status_prefix: "当前防御状态："
kronos_pull_fallback_warning: "未检测到完整 Kronos 权重：保存并运行后 Phase2 对 Kronos 将使用收益统计回退（非 Transformer）。建议先拉取权重。"

# Tabs（主栏 5 Tab 名与 tooltip）

tab_p0: "资产与研究前提"
tab_p1: "数据诊断"
tab_p2: "信号对抗"
tab_p3: "自动防御"
tab_p4: "实验结论"

tab_p0_title: "资产自定义面板与研究前提"
tab_p1_title: "数据诊断与失效前兆识别"
tab_p2_title: "多范式信号对抗与模型失效识别"
tab_p3_title: "自动防御响应"
tab_p4_title: "实验结论展示"

# 主栏共享：Phase 级状态条与通用标签

fig_explain_title_fmt: "Figure{phase}.{sub}讲解：{caption}"

level_status_l2: "STATUS: Level 2 — 熔毁防御"
level_status_l1: "STATUS: Level 1 — 警戒防御"
level_status_l0: "STATUS: Level 0 — 标准防御"
phase_intro_card_header: "Introduction（MeToAI §2）"
loading_card_title: "数据与图表加载中"
loading_text: "正在计算…"
loading_md_fallback: "正在计算全链路结果，请稍候…"
project_intro_fallback: "（请将项目综述写入 `dash_app/content-CHN/project_executive_summary.md`。）"
placeholder_compute_prompt: "点击左侧「应用并重算」开始计算"
inactive_variable_note: "{fig_lbl}: 未执行管线→当前变量对防御等级切换无影响"

# 研究模式三段手风琴（"结果→原始数据 / 计算过程 / 源码与模型参数"）

research_accordion_result_title: "结果 → 原始数据"
research_accordion_calc_title: "计算过程"
research_accordion_source_title: "源码与模型参数"
research_header_raw: "原始数据"
research_header_learning: "学习过程"
research_header_source: "源码原文"

# 主栏概览卡（研究项目综述 Tab 下 5 张折叠卡）

overview_p0_title: "P0 · 资产与研究前提"
overview_p1_title: "P1 · 数据诊断"
overview_p2_title: "P2 · 信号对抗"
overview_p3_title: "P3 · 自动防御"
overview_p4_title: "P4 · 实验结论"

# Modal · 新增资产对话框

modal_add_asset_title: "新增资产"
modal_add_sym_label: "股票代码"
modal_add_sym_placeholder: "如 NVDA"
modal_add_weight_label: "初始权重（0–1）"
modal_add_cat_label: "归入资产类"
modal_add_cat_opt_tech: "科技股"
modal_add_cat_opt_hedge: "对冲类"
modal_add_cat_opt_safe: "安全资产"
modal_add_cat_opt_new: "新建类别…"
modal_add_new_cat_placeholder: "新类别名称（仅在选择「新建类别」时）"
modal_add_reweight_hint: "保存后其余标的权重按原比例缩放，使总和为 1−新资产权重。"
modal_btn_cancel: "取消"
modal_btn_save: "保存"

# ─── 主栏 · P0（资产与研究前提）────────────────────────────────────────────────

cat_tech: "科技股"
cat_hedge: "对冲类"
cat_safe: "安全资产"
cat_benchmark: "基准"

diag_pending: "待诊断"
diag_nonstat_or_logic_fail: "非平稳或逻辑失败 · 不可作为建模前提"
diag_stable_structure: "平稳 · 存在可建模结构（拒绝纯噪声）"
diag_stable_weak: "平稳 · 残差近白噪声（弱规律）"
diag_nonstat_needs_diff: "非平稳 · 需差分或进一步检验"

# ─── 主栏 · P1（数据诊断）─────────────────────────────────────────────────────

# Fig1.1 讲解卡标题中的 caption（与 callbacks/research_panels.py::_fig_explain_title

# 拼接，会渲染为 "Figure1.1 讲解：……"）。

p1_stat_method_caption: "统计方法说明（ADF / Ljung-Box / P 值含义）"

# ─── 主栏 · P2（信号对抗）─────────────────────────────────────────────────────

p2_mse_best_prefix: "MSE 均值最优 ≈ {mse}×10⁻⁴"
p2_shadow_mse_unavailable: "全样本影子 MSE 不可用"
p2_credibility_hint: "可信度得分 = {score}（α·JSD 基准 + 覆盖惩罚；侧栏可调 α/β）"
p2_table_header_model: "模型"
p2_table_header_mu: "μ̂（OOS末日）"
p2_table_header_sigma: "σ̂"
p2_prob_caption: "三模型概率验证（样本外 NLL + DM(HAC) vs Naive + 区间覆盖率）"
p2_logic_break_header_prefix: "逻辑断裂提示"
p2_logic_ac1_line: "- 训练期市场收益 AC1={ac1} 低于 τ_AC1（逻辑断裂）。"
p2_logic_cos_line_prefix: "- 测试窗 S_t 与数值预测 μ（截面均值）滚动余弦相似度 {cos}"
p2_logic_cos_break_suffix: "；语义与数值趋势背离（逻辑断裂）"
p2_symbol_search_label: "标的（可搜索）"
p2_symbol_search_placeholder: "搜索代码…"
p2_density_hint: "提示：高/低密度区对比已加强；单击图例可隐藏该模型密度与 μ 脊线。"
p2_caption_jsd_current: "*三边与 **JSD_三角均值（当前标的）** 为 **{sym}** 在测试窗上的日度平均；全市场聚合三角均值＝{g_tri}。*"
p2_caption_missing_sym: "*三边与三角均值为全市场聚合（当前标的无分项缓存时请重新跑批以写入 `jsd_by_symbol`）。*"
p2_caption_global: "*三边与三角均值为全市场聚合。*"
p2_fig21_caption: "影子择模与像素矩阵（MSE / 影子验证 / 综合分）"
p2_fig22_caption: "时间×收益密度（纵轴 · μ 脊线 · 着色）"

# ─── 主栏 · P3（自动防御）─────────────────────────────────────────────────────

p3_adaptive_header: "AdaptiveOptimizer 与三阶段防御"
p3_st_reuse_note: "测试窗 S_t 与侧栏 FigX.1 同源；影子择模结果已移至 Phase 2 顶部展示。"
p3_fig33_caption: "双轨蒙特卡洛"

# ─── 主栏 · P4（实验结论）─────────────────────────────────────────────────────

p4_fig41_title: "Figure 4.1 · 预警有效性检验（固定 5 日窗）"
p4_fig411_title: "Figure 4.1.1 · 当前标的告警后 5 日简单日收益"
p4_symbol_search_placeholder: "搜索标的（如 NVDA）"
p4_placeholder_daily_return: "日收益"

# ─── 右侧栏 · Sidebar-Right（防御指标）────────────────────────────────────────

# 右侧栏的标题与占位符统一走 `get_figure_title` / `get_status_message`，

# 详见 `figures_titles.md` 与 `status_messages.md`。本节仅列允许自定义的入口键

# 以方便检索：fig_x_1..fig_x_6（卡片外标题），fig_x_1_explain..6（Invest 讲解卡标题），

# fig_x_1_explain_res..6_res（Research 讲解卡标题），idle_placeholder（未运行占位），

# placeholder_jsd / placeholder_cosine（图骨架占位），figx_run_prompt（运行前提示）。

# ─── 左侧栏 · Sidebar-Left 参数区（辅助小字）──────────────────────────────────

# 参数主标题与问号说明沿用 `sidebar_left.md` + `sidebar_left_params_explanations.md`。

# 此处仅收录 `_aux_label("...")` 直接构造的灰色辅助文字。

aux_k_jsd_scale: "k_jsd 基线放大倍数"
aux_epsilon_floor: "ε 基线基准值"
aux_alpha_base: "α 基准项系数"
aux_beta_penalty: "β 惩罚项系数"
aux_gamma_cap: "γ 惩罚上限"
aux_shadow_alpha_mse: "α 为 MSE 权重，1−α 为 JSD 权重"
aux_shadow_holdout: "影子 holdout 长度（仅训练窗尾部）"
aux_oos_fit_steps: "OOS 拟合步数"
aux_oos_mark_fastest: "1（最快）"
aux_oos_mark_full: "全量"
aux_mc_scenario_step: "自测试集起点，「黑天鹅事件」注入的第 N 个交易日"
aux_mc_scenario_impact: "「黑天鹅事件」冲击幅度（对数收益率）"

# ─── 左侧栏 Tabs · 自检与反馈（研究项目综述 / 防御策略 Tab）──────────────────

sidebar_tab_overview_label: "研究项目综述"
sidebar_tab_params_label: "防御策略与参数自定义"
sidebar_thought_process_header: "System Thought Process"
sidebar_theme_dark_switch: "深色主题"
sidebar_copy_report_btn: "复制报告+补充说明"
sidebar_feedback_placeholder: "可选：补充描述现象（如「点重算后一直转圈」）"
sidebar_collapse_toggle_label: "<<"