# Figure1.1 · 分组诊断与失效前兆识别（研究）

**对象类型（A）**：基础统计与结构图示。该“图”在 UI 上表现为两块内容：

- 左侧：逐资产诊断卡片网格（ADF / Ljung–Box / 差分阶 / 逻辑失败标签）。
- 右侧：根据诊断结果自动生成的“逐资产分析 + 整体结论”（Markdown）。

它们共同服务于一个目的：**在进入 Phase 2（概率层 OOS 与模型对抗）前，先把“数据可建模的统计前提”讲清**，并对可能需要从 Universe 排除的标的给出证据链。

本文对齐主栏 `dash_app/ui/main_p1.py` 的 `fig_label="Figure1.1"` 区块（输出 id：`p1-asset-cards`、`p1-group-analysis`）。

占位符（可选）：`**—`** · `**—**` · `**{n_symbols}**`

---

## 1. 图形/文本管线（端到端）

```text
data.json → load_bundle.close_universe
  → daily_returns(close[symbols]) = returns（简单收益）
  → resolve_dynamic_train_test_windows(...) → train_mask
  → Phase1: run_phase1(returns.loc[train_mask], Phase1Input, DefensePolicyConfig, close_train)
      → diagnostics: List[AssetDiagnostic]（逐资产 ADF/LB/差分/失败标记）
      → h_struct, gamma_multiplier（结构熵与 γ 倍增，供侧栏 FigX.2 / 防御状态机）
  → Dash 主回调：render_dashboard_outputs(...)
      → p1-asset-cards（卡片网格）
      → p1-group-analysis（narrative_p1_group_analysis 生成 Markdown）
```

---

## 2. 数据溯源（Data Provenance）


| 项目                  | 说明                                                                                                                         |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **原始数据**            | 日频收盘价宽表 `close: pd.DataFrame`（来自 `ass1_core.load_bundle`）。                                                                 |
| **训练窗收益**           | `rets = daily_returns(close[symbols]).dropna(how="all")`，再取 `rets.loc[train_mask]` 作为 Phase1 输入（见 `research/pipeline.py`）。 |
| **对数收益（用于 ADF/LB）** | 优先用训练窗收盘价 `close_train` 计算 \ln(P_t/P_{t-1})；否则回退 \ln(1+r_t)（见 `research/phase1.py:_log_returns`）。                          |
| **诊断输出**            | `snap_json["phase1"]["diagnostics"]`：每个标的一个字典，字段来自 `AssetDiagnostic`（见 `research/schemas.py`）。                             |


---

## 3. 方法论与数学对象

### 3.1 平稳性：ADF + 差分管线（最多二阶）

对每个标的的对数收益序列 x_t，进行 ADF 检验得到 p 值：

- 若 p < \texttt{adf_p_threshold}：认为可拒绝单位根（平稳），进入 Ljung–Box；
- 否则对 x_t 做差分 \Delta x_t，再做 ADF；
- 最多到二阶差分 \Delta^2 x_t。二阶仍不平稳则标记 `basic_logic_failure=True`，并在优化侧把 `weight_zero=True`。

实现：`research/phase1.py:_adf_diff_pipeline`。

### 3.2 规律性/可预测性：Ljung–Box（自相关是否显著）

在最终用于检验的序列上做 Ljung–Box（默认 lags=10）：

- `ljung_box_p > 0.05`：不拒绝“无自相关”，工程上标记 `white_noise=True` / `low_predictive_value=True`，**仅提示，不剔除**；
- `ljung_box_p ≤ 0.05`：拒绝白噪声假设，认为仍存在可结构化的残差规律。

实现：`research/phase1.py:_ljung_box_p` 与 `run_phase1` 中 `wn` 判定。

---

## 4. 计算过程链（Calculation Chain）


| 步骤  | 计算对象        | 输入                       | 输出                                                                          | 逻辑 / 函数                                                   |
| --- | ----------- | ------------------------ | --------------------------------------------------------------------------- | --------------------------------------------------------- |
| 1   | 对数收益序列      | `rets` + `close_train`   | `lr`                                                                        | `_log_returns`                                            |
| 2   | ADF + 差分    | `lr` + `adf_p_threshold` | `diff_order, stationary_returns, basic_logic_failure, adf_p, adf_p_returns` | `_adf_diff_pipeline`                                      |
| 3   | Ljung–Box   | 最终检验序列                   | `ljung_box_p`                                                               | `_ljung_box_p`                                            |
| 4   | 卡片分类（红/黄/绿） | `AssetDiagnostic`        | headline/badge                                                              | `dash_app/dashboard_face_render.py`                       |
| 5   | 组内结论文本      | `phase1.diagnostics`     | Markdown                                                                    | `dash_app/render/explain/main_p1/narrative.py:narrative_p1_group_analysis` |


---

## 5. UI 语义（卡片颜色与字段）

主栏卡片的颜色分组（`dash_app/dashboard_face_render.py`）：

- **红（danger）**：`basic_logic_failure=True` 或 `stationary_returns=False` → “非平稳或逻辑失败 · 不可建模”
- **黄（warning）**：`stationary_returns=True` 且 `low_predictive_value=True` → “平稳 · 残差近白噪声（弱规律）”
- **绿（success）**：`stationary_returns=True` 且 `low_predictive_value=False` → “平稳 · 存在可建模结构（拒绝纯噪声）”

卡片中展示的三个 p 值/字段：

- `ADF 对数收益 p`：`adf_p`
- `差分阶 / ADF(终) p`：`diff_order` 与 `adf_p_returns`
- `Ljung–Box p`：`ljung_box_p`

---

## 6. 关键数据计算示例（重要数值）

以下栏目与 **`Figure2.1-Res.md` §6** 组织方式一致，便于横向审计：**Phase2 影子择模** 的全表数值以 **`Figure2.1-Res.md` §6.2～§6.4** 为单一真理源；本节仅重申 **前提** 并标明 **与本图（Phase1）** 的读法边界。

### 6.1 前提（Phase2 影子择模，与 Fig2.1 §6.1 同源）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

### 6.2～6.4 择模全截面、NVDA 分解、全样本影子 MSE

完整表格与说明见 **`Figure2.1-Res.md` §6.2～§6.4**（同一 `data.json` 快照下不得与此处矛盾）。

### 6.5 本图（Phase1）对照读法

**Figure1.1** 左栏卡片来自 **`snap_json["phase1"]["diagnostics"]`**（ADF / Ljung–Box / 差分阶 / 逻辑失败标签），**与 §6.3 中 NVDA 的影子 MSE 表属于不同对象**：前者是 **训练窗统计检验**，后者是 **训练尾 holdout 择模评分**，**禁止混算同一 p 值或同一列数字**。

---

## 7. 源码锚点（可追溯）

- **Phase1 计算**：`research/phase1.py:run_phase1`
- **ADF / Ljung–Box**：`_adf_pvalue`、`_ljung_box_p`、`_adf_diff_pipeline`
- **对数收益构造**：`_log_returns`（优先 close_train）
- **主栏渲染**：`dash_app/dashboard_face_render.py`（`p1_grid` / `p1_group_analysis`）
- **组内叙事生成**：`dash_app/render/explain/main_p1/narrative.py:narrative_p1_group_analysis`
- **方法说明文档（补充）**：`dash_app/content/p1_stat_method.md`（UI 中作为 Figure1.2 展示）

---

## 8. 一致性检验

1. 固定同一份 `data.json` 与解析后的训练窗起止日，重跑 `research.pipeline.run_pipeline`。
2. 抽取 `snap_json["phase1"]["diagnostics"]`，对任一标的手动复算：
  - 对数收益（优先 `close_train`）；
  - ADF(p) 与差分阶；
  - Ljung–Box(p)。
3. 核对：
  - `basic_logic_failure` 与二阶差分失败条件一致；
  - `low_predictive_value` 与 `ljung_box_p > 0.05` 一致（在 `ljung_box_p` 非空时）。

---

## 9. 与下游叙事（简）

- **与 Phase 3 阻断集合**：`basic_logic_failure=True` 或 `weight_zero=True` 的标的会进入 `blocked_symbols` 并在优化时权重清零再归一（见 `research/pipeline.py` 与 `research/phase3.py`）。
- **与 FigX.2（结构熵）**：Phase1 同时输出 `h_struct`，是防御状态机与侧栏结构熵卡片的直接输入；Figure1.1 的诊断解释“单资产前提”，FigX.2 解释“横截面结构压力”。

