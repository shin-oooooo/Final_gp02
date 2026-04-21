# FigX.4 · 可信度评分（研究 · B 类）

**对象类型（B）**：本图给出 Phase 2 产生的**可信度评分** `phase2.credibility_score`（与 `phase2.consistency_score` 数值完全相同），并在侧栏/研究模式中联动展示三类证据：**密度检验（NLL / DM / 覆盖率）**、**模型三态灯（红黄绿）**、以及基于**三角 JSD** 的可解释打分分解（基准项 − 覆盖惩罚）。该评分是防御等级解析 `resolve_defense_level(...)` 的核心输入之一：当 `credibility_score` 低于阈值 `τ_L1/τ_L2` 时，将触发 **Level 1/2** 的防御路径（见 `research/defense_state.py`）。

本文与侧栏渲染模板对齐：`dash_app/render/explain/sidebar_right/figx4.py` · `build_figx4_explain_body(...)` 读取 `snap_json["phase2"]` + `DefensePolicyConfig` 并把占位符注入到 `FigX.4-Res.md`。因此本文必须保留占位符：`{train_start}`、`{train_end}`、`{test_start}`、`{test_end}`、`{p0_symbols_csv}`、`{jsd_triangle_mean}`、`{credibility}`、`{credibility_base_jsd}`、`{credibility_coverage_penalty}`、`{density_test_failed}`、`{prob_full_fail}`、`{prob_coverage_naive}`、`{tau_l2}`、`{tau_l1}`、`{defense_level}`、以及自动展开块 `{prob_nll_md}` / `{prob_dm_p_md}` / `{prob_cov_md}` / `{traffic_lights_md}`。

占位符：`**{n_symbols}`** · `**{credibility}`** · `**{credibility_base_jsd}`** · `**{credibility_coverage_penalty}`** · `**{density_test_failed}**` · `**{tau_l2}**` · `**{tau_l1}**` · `**{defense_level}**`。

---

## 1. 图形管线（端到端）

```text
data.json → load_bundle → close_universe
  → daily_returns(close_universe[symbols]) = returns
  → resolve_dynamic_train_test_windows(...) → train_mask / test_mask / test_dates
  → run_phase2(returns, train_mask, test_mask, ..., policy=DefensePolicyConfig)
      → 生成 prob_*（NLL / DM / coverage / traffic light）
      → 生成 jsd_triangle_mean + density_test_failed
      → 生成 credibility_base_jsd / credibility_coverage_penalty
      → credibility_score = clip(base − penalty, min, max)
      → consistency_score = credibility_score
  → PipelineSnapshot.phase2 写入 JSON（snap_json["phase2"][...])
  → Dash：FigX.4 文本解释块（sidebar 模板）+ 仪表盘（fig_p2_consistency_gauge）
```

---

## 2. 自研算法逻辑架构（方法论核心）

### 2.1 为什么要自研：从“模型分歧”到“可审计的一维可信度”

可信度评分的任务不是预测收益，而是回答一个更工程化的问题：**当前测试窗上，结构模型（ARIMA/LightGBM/Kronos）给出的概率密度是否仍与现实收益“同一物理世界”对齐**。金融收益在测试窗常出现厚尾、结构突变与非平稳；如果仅用单一误差（例如点预测 MSE 或某个模型的 NLL）会导致两类问题：

- **跨模型不可比**：不同模型的 μ/σ 生成机制不同（统计拟合、树模型、外部 Kronos 适配），单一指标很难在“模型集”上形成可解释的统一量纲。
- **只看点误差会漏掉密度失配**：即便均值预测贴近，实现分布若更尖/更胖尾，名义 95% 区间可能系统性失真；这属于“概率层面的断裂”，需要显式惩罚。

因此本项目在 Phase 2 内构造一个**低维、可解释、可回放**的评分：以 **三角 JSD（模型分歧）为主因子给出“基准可信度”，并在覆盖率相对 Naive 更差**时追加惩罚，把“模型分歧”与“概率覆盖失败”统一压缩到 `credibility_score ∈ [cred_min, cred_max]` 的标量中。该标量随后被 `resolve_defense_level` 直接消费，从而实现“诊断→状态机→防御策略”的闭环。

### 2.2 核心数学算子（公式 + 变量字典）

记测试窗上三结构模型两两 JSD 的三角均值为：

\overline{\mathrm{JSD}}_{\triangle} = \texttt{phase2.jsd_triangle_mean}

**(1) 基准项（惩罚前可信度）**  
由 `DefensePolicyConfig.credibility_baseline_jsd_scale = α` 给出：

\mathrm{base}=\frac{1}{1+\alpha\cdot \overline{\mathrm{JSD}}_{\triangle}}

对应标量写入 `phase2.credibility_base_jsd`。

**(2) 覆盖惩罚（只有当密度覆盖失败时才启用）**  
`density_test_failed` 的工程定义：在测试窗上，任一结构模型的名义 95% 覆盖率 `prob_coverage_95[m]` **严格差于** Naive 的 pooled 覆盖率 `prob_coverage_naive`（实现中带 1e-12 保护项）。当且仅当 `density_test_failed=True` 且 `β>0` 时，惩罚为：

\mathrm{pen}=\min(\gamma,\ \beta\cdot \overline{\mathrm{JSD}}_{\triangle})

其中：

- \beta = `DefensePolicyConfig.credibility_penalty_jsd_scale`  
- \gamma= `DefensePolicyConfig.credibility_penalty_cap`  
惩罚标量写入 `phase2.credibility_coverage_penalty`。

**(3) 输出 clip（可信度评分）**  
令 `cred_min/cred_max` 分别为 `DefensePolicyConfig.credibility_score_min/max`：

\texttt{credibilityscore}=\mathrm{clip}(\mathrm{base}-\mathrm{pen},\ \texttt{credmin},\ \texttt{credmax})

实现中直接令 `consistency_score = credibility_score`，因此后续防御状态机看到的 `consistency` 就是本评分。

### 2.3 参数 \theta 的物理意义与敏感度（侧栏可调）

可信度相关参数都来自 `DefensePolicyConfig`（侧栏滑条在 `dash_app/ui/sidebar_params/sections_credibility.py`）：

- `credibility_baseline_jsd_scale = α`：**分歧→扣分的斜率**。α 越大，同样的 \overline{\mathrm{JSD}}_{\triangle} 会导致更低 base（更保守、更易触发警戒/熔断）。
- `credibility_penalty_jsd_scale = β`：覆盖失败时惩罚的**比例系数**。β=0 等价关闭该惩罚，只剩 base。
- `credibility_penalty_cap = γ`：覆盖失败惩罚的**上限**，控制“最坏时最多扣多少”。
- `credibility_score_min/max`：最终 clip 区间；直接决定仪表盘和阈值比较的**动态范围**。
- `tau_l1 / tau_l2`：并不参与评分公式，但作为 **状态机阈值**决定“评分落在红/黄/绿哪一段”以及 `resolve_defense_level` 的分流。

---

## 3. 数据溯源与物理特征（Data Provenance & Physical Profile）

### 3.1 数据指纹 (Data Fingerprint)

- **原始数据集**：`data.json`（本地文件；路径由 `resolve_market_data_json_path()` / 环境变量控制）。  
- **来源**：[Insert Source/DB]（仓库运行时写入 `data.json["meta"]["source"]`；若缺失保留占位）。  
- **生命周期**：`{train_start}`～`{test_end}`（实际切片由 `resolve_dynamic_train_test_windows(...)` 在 `research/pipeline.py` 中解析并写入 `phase0.meta.resolved_windows`）。  
- **频率**：交易日（日频）。  
- **清洗后维度**：`returns` 形状约为 `[Rows] x {n_symbols}`（`Rows` 为交易日数；列为 `symbols_resolved`）。

关键派生表（与内存对象名一致）：

- `close_universe`: `pd.DataFrame`，索引=交易日，列=标的收盘价。  
- `returns = daily_returns(close_universe[symbols])`: `pd.DataFrame`，索引=交易日，列=标的简单收益。  
- `train = returns.loc[train_mask].dropna(how="any")`: 训练窗行完备收益表。  
- `test_dates = returns.index[test_mask]`: 测试窗交易日索引（用于 OOS 概率检验与 JSD 汇总）。

### 3.2 变量映射 (Variable Mapping)

- **核心输入变量 X**：
  - `returns`: `pd.DataFrame[date × symbol]`，简单收益 r_{t,s}。  
  - `mu_ts[m][sym]`: `List[float]`，测试窗逐日预测均值（每模型每标的）。  
  - `sig_ts[m][sym]`: `List[float]`，测试窗逐日预测波动（每模型每标的）。  
  - `prob_coverage_95[m]`: `float`，测试窗 pooled 名义 95% 覆盖率（每模型）。  
  - `prob_coverage_naive`: `float`，Naive pooled 覆盖率（基准）。  
  - `daily_tri`: `List[float]`，测试窗逐日“跨标的三角 JSD 的截面均值”（长度≈`len(test_dates)`，不足时可为空）。  
  - `policy`: `DefensePolicyConfig`，包含 α/β/γ/clip 上下界与阈值 `τ_L1/τ_L2`。
- **目标观察变量 Y（可信度评分）**：
  - `credibility_score = snap_json["phase2"]["credibility_score"]`：标量，范围由 `cred_min/cred_max` clip 决定；绘制时（仪表盘）会再 clip 到 [0,1] 用于显示（见 `fig_p2_consistency_gauge`）。

---

## 4. 算法执行链（The Execution Chain）

下表按代码执行顺序还原数据流（核心句式：**输入 A 经过 B 函数，输出 C，最终在图表中映射为 D 元素**）。行号以当前仓库版本为准（后续版本漂移时以函数块为锚点）。  


| 序号  | 逻辑阶段       | 输入变量 (Variable)                                      | 输出目标 (Target)                                                                              | 核心算法/公式                                      | 代码锚点 (Function, File, Line)                                                                 |
| --- | ---------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 1   | 原始数据对齐     | `data.json` → `close_universe`                       | `close_universe`                                                                           | 交易日索引对齐、列为 universe                          | `load_bundle`, `ass1_core.py`, Line [Insert]                                                |
| 2   | 收益构造       | `close_universe[symbols]`                            | `returns`                                                                                  | `daily_returns`（简单收益）                        | `daily_returns`, `ass1_core.py`, Line [Insert]                                              |
| 3   | 窗口解析       | `returns.index` + 模板日期                               | `train_mask`/`test_mask`/`test_dates`                                                      | 动态解析训练/测试窗并写入 `phase0.meta.resolved_windows` | `resolve_dynamic_train_test_windows`, `research/pipeline.py`, Line [Insert]                 |
| 4   | OOS 密度预测序列 | `returns` + `test_dates`                             | `mu_ts`/`sig_ts`                                                                           | 各模型在测试窗逐日输出 \mathcal{N}(\mu,\sigma^2)        | `run_phase2`, `research/phase2.py`, Line [Insert]                                           |
| 5   | 概率检验汇总     | `returns.loc[test_dates]` + `mu_ts/sig_ts`           | `prob_nll_mean`/`prob_dm`_*/`prob_coverage_95`/`model_traffic_light`/`prob_coverage_naive` | NLL、DM(HAC) vs Naive、覆盖率；并映射为三态灯             | `_probabilistic_oos_bundle`, `research/phase2.py`, Line [252–376] 与调用段 Line [857–866]       |
| 6   | 三角 JSD 统计  | `mu_ts/sig_ts`（逐日、跨标的）                               | `daily_tri`/`jsd_triangle_mean`                                                            | 两两 JSD → 三角均值 → 日均再均值                        | `run_phase2`, `research/phase2.py`, Line [640–668]                                          |
| 7   | 覆盖失败判定     | `prob_coverage_95` + `prob_coverage_naive`           | `density_test_failed`                                                                      | 任一结构模型覆盖率 < Naive（带数值保护项）                    | `run_phase2`, `research/phase2.py`, Line [868–873]                                          |
| 8   | 可信度基准项     | `jsd_triangle_mean`, `α`                             | `credibility_base_jsd`                                                                     | `1/(1+α·jsd_triangle_mean)`                  | `run_phase2`, `research/phase2.py`, Line [771–773]                                          |
| 9   | 可信度惩罚项     | `density_test_failed`, `β`, `γ`, `jsd_triangle_mean` | `credibility_coverage_penalty`                                                             | `min(γ, β·jsd_triangle_mean)`（仅覆盖失败时）        | `run_phase2`, `research/phase2.py`, Line [875–881]                                          |
| 10  | clip 与快照写入 | `base`, `pen`, `cred_min/max`                        | `credibility_score`/`consistency_score`                                                    | `clip(base−pen, min, max)`；并令一致性=可信度         | `run_phase2`, `research/phase2.py`, Line [882–890]；字段见 `research/schemas.py` Line [210–231] |
| 11  | UI 映射（仪表盘） | `phase2.credibility_score`                           | gauge 值                                                                                    | 显示层再 clip 到 [0,1]，并用固定 0.45/0.70 分段着色        | `fig_p2_consistency_gauge`, `dash_app/figures.py`, Line [1072–1097]                         |
| 12  | 侧栏解释文案注入   | `snap_json["phase2"]` + `policy`                     | `FigX.4-Res.md` 的占位符替换结果                                                                   | 字符串模板替换（保留变量名与格式化精度）                         | `build_figx4_explain_body`, `dash_app/render/explain/sidebar_right/figx4.py`                   |


---

## 5. 源码级证据与参数断言（Source Code Traceability）

### 5.1 核心逻辑骨干（保留真实变量名）

```text
# research/phase2.py（摘义）
jsd_triangle_mean ← mean(daily_tri)
alpha ← max(policy.credibility_baseline_jsd_scale, 1e-9)
credibility_base_jsd ← 1 / (1 + alpha * jsd_triangle_mean)

density_test_failed ← any(prob_coverage_95[m] < prob_coverage_naive for m in ("arima","lightgbm","kronos"))

penalty ← 0
if density_test_failed and policy.credibility_penalty_jsd_scale > 0:
    penalty ← min(policy.credibility_penalty_cap,
                  policy.credibility_penalty_jsd_scale * jsd_triangle_mean)

credibility_score ← clip(credibility_base_jsd - penalty,
                         policy.credibility_score_min,
                         policy.credibility_score_max)
consistency_score ← credibility_score
```

### 5.2 参数断言（参数如何决定图表形态）

- `policy.credibility_baseline_jsd_scale = {cred_alpha}`：决定基准项曲率；α 越大，仪表盘数值在同一 `jsd_triangle_mean` 下越低。  
- `policy.credibility_penalty_jsd_scale = {cred_beta_pen}` 与 `policy.credibility_penalty_cap = {cred_pen_cap}`：只在 `{density_test_failed}` 为“是”时生效；决定扣分斜率与最大扣分。  
- `policy.credibility_score_min/max = {cred_min} / {cred_max}`：决定输出 clip 区间；若设置异常导致 `min≥max`，代码会回退到 `[-0.5, 1.0]`。  
- `policy.tau_l2={tau_l2}`、`policy.tau_l1={tau_l1}`：决定红/黄/绿阈值，并通过 `resolve_defense_level` 影响 `defense_level={defense_level}`。

---

## 6. 关键数据计算示例（运行时注入）

### 6.0 Phase2 影子择模前提（与 `Figure2.1-Res.md` §6 对齐）

下列 **前提表** 与 **`Figure2.1-Res.md` §6.1** 同源；**`best_model_per_symbol` / NVDA MSE / combined / 全样本影子 MSE** 全表见 **`Figure2.1-Res.md` §6.2～§6.4**。FigX.4 **可信度评分** 与择模 **共用 `phase2` 快照**，但 **不**改写择模结果。

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

### 6.1 零阶输入：样本外收益与模型分布

**原始对象**：测试窗 `test_dates` 上的已实现简单收益 r_{t,s}，以及同日各结构模型预测的 \mathcal{N}(\mu_{m,s,t},\sigma_{m,s,t}^2)。  

- 训练：`**{train_start}`**～`**{train_end}`**  
- 测试：`**{test_start}**`～`**{test_end}**`  
- 标的：`**{p0_symbols_csv}**`

### 6.2 一阶：概率检验（自动展开块）

{prob_nll_md}

{prob_dm_p_md}

{prob_cov_md}

{traffic_lights_md}

### 6.3 二阶：可信度分解（base − penalty）

记 \overline{\mathrm{JSD}}_{\triangle}=`phase2.jsd_triangle_mean`。本运行：`**{jsd_triangle_mean}**`。

- 基准项：`credibility_base_jsd` = `**{credibility_base_jsd}**`，其中 α = `**{cred_alpha}**`。  
- 覆盖惩罚：`credibility_coverage_penalty` = `**{credibility_coverage_penalty}**`，仅当 `density_test_failed`=`**{density_test_failed}**` 时启用；β = `**{cred_beta_pen}**`，上限 γ = `**{cred_pen_cap}**`。  
- clip：区间 `**{cred_min}**`～`**{cred_max}**`，最终 `credibility_score` = `**{credibility}**`（亦即 `consistency_score` = `**{consistency}**`）。

### 6.4 管线失败标记与阈值


| 字段                           | 值                           |
| ---------------------------- | --------------------------- |
| `prob_full_pipeline_failure` | `**{prob_full_fail}**`      |
| `prob_coverage_naive`        | `**{prob_coverage_naive}**` |


阈值与状态：**τ_L2=`{tau_l2}`**，**τ_L1=`{tau_l1}`**；`**defense_level**` = `**{defense_level}**`。

---

## 7. 一致性检验（可复现核对步骤）

1. 从快照读取 `snap_json["phase2"]["credibility_score"]`、`["credibility_base_jsd"]`、`["credibility_coverage_penalty"]`、`["jsd_triangle_mean"]`、`["density_test_failed"]`。
2. 用同一份 `returns`、同一 `train_mask/test_mask`、同一 `DefensePolicyConfig` 重新执行 `research.phase2.run_phase2(...)`，确认输出字段逐一一致。
3. 手动复算基准项：用 `α=policy.credibility_baseline_jsd_scale` 与 `jsd_triangle_mean` 计算 1/(1+α·JSD)，与 `credibility_base_jsd` 相等（容忍浮点误差 `[Insert eps]`）。
4. 若 `density_test_failed=True`：用 `β`、`cap` 计算 `min(cap, β·jsd_triangle_mean)`，与 `credibility_coverage_penalty` 相等；若为 False，则惩罚应为 0。
5. 复算 `clip(base−pen, cred_min, cred_max)` 得到 `credibility_score`，并核对 `consistency_score` 与其数值相同。
6. 将 `credibility_score` 与 `τ_L1/τ_L2` 比较，确认与 UI 的红/黄/绿区间及 `resolve_defense_level` 的分支一致。

---

## 8. 与其它对象的关系（职责边界）

- **与 FigX.5（JSD 应力）**：二者共享 `jsd_triangle_mean`；FigX.5 强调滚动应力触发（`jsd_stress` 与动态阈），FigX.4 将 `jsd_triangle_mean` 进一步映射为**可比较的可信度标量**（并叠加覆盖惩罚）。  
- **与 FigX.6（语义余弦）**：FigX.6 关注语义–数值背离（`cosine_semantic_numeric` / `logic_break_semantic_cosine_negative`），可直接触发 Level 2；FigX.4 是纯“数值–概率一致性”的压缩评分。  
- **与防御等级**：`run_pipeline` 将 `phase2.credibility_score` 作为 `consistency` 传入 `resolve_defense_level`，并结合 `jsd_stress`、`h_struct`、`pseudo_melt`、`sentiment` 等共同决定 `defense_level`。  
- **与 UI**：仪表盘 `fig_p2_consistency_gauge` 仅展示（并对显示值 clip 到 [0,1]），真实用于状态机的是 `phase2.credibility_score` 原始标量（clip 到 `cred_min/max` 后的结果）。

---

**占位**：`**{n_symbols}`** · `**{credibility}`** · `**{tau_l2}`** · `**{tau_l1}`** · `**{defense_level}**`

---

## 9. 方法局限性

- **评分是“压缩指标”**：`credibility_score` 将测试窗内的**模型分歧**（`jsd_triangle_mean`）与**覆盖失败**（`density_test_failed`）压缩为一个标量，便于状态机消费；代价是丢失了“分歧来自哪一对模型/哪一组标的/哪一天最严重”的结构信息。若要定位根因，必须回到 `phase2.jsd_by_symbol`、`phase2.jsd_matrix`、`prob_coverage_95` 与逐日 `mu_ts/sig_ts`。
- **覆盖惩罚触发是相对规则**：`density_test_failed` 采用“结构模型覆盖率 < Naive 覆盖率”的相对比较；当 Naive 本身覆盖率异常（例如收益分布突变导致所有模型覆盖都偏离）时，该触发条件可能无法区分“整体坏”与“相对更坏”，从而使惩罚项对某些极端窗不够敏感。
- **JSD 三角均值是截面聚合**：`jsd_triangle_mean` 本质是“日内跨标的 JSD 均值，再跨日求均值”的聚合量；若分歧集中在少数标的或少数日期，该均值会被稀释，导致 `base = 1/(1+α·JSD)` 的扣分不够尖锐（除非通过更大的 `α` 放大）。
- **惩罚项是线性 + 上限**：`pen = min(cap, β·jsd_triangle_mean)` 是线性惩罚并带上限；它不会区分“轻微覆盖失败但持续多日”和“单日严重失败”，也不会随着失败强度（例如覆盖率差距大小）非线性增强。该设计是为了保持可解释性与稳定性，但会牺牲对尾部极端情况的分辨率。
- **显示层与数据层范围不同**：UI 仪表盘 `fig_p2_consistency_gauge` 会把显示值再 clip 到 [0,1]，而数据层 `credibility_score` 的 clip 区间由 `credibility_score_min/max` 决定（允许 `<0`）。因此在做审计/复算时必须以 `snap_json["phase2"]["credibility_score"]` 为准，而不是仅凭仪表盘显示数值判断“是否触发阈值”。

