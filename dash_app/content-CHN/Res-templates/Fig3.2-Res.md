# Figure3.2 · 权重对比柱状图（研究 · B 类）

**对象类型（B）**：并排柱状图对比 **基准权重（灰）** 与 `**phase3.weights`（蓝）**。蓝柱来自 `**research/phase3.py`** `**AdaptiveOptimizer**` 在给定 `**DefenseLevel**` 下的 **SLSQP** 解，并经 `**blocked_symbols`** **再归一化**。**方法论主轴为 §2**（防御等级切换目标 + 阻断再分配）；`**dash_app/figures.py`** `**fig_weights_compare`** 仅负责两组条形映射与可选自定义对照。

本文与 Phase 3 主栏 `**dcc.Graph(id="fig-p3-weights")**`（`**dash_app/ui/ids.py`** · `**IDS.P3_W`**，外包 `**FIG.F3_2`** · `**Figure3.2**`）对齐；主回调中 `**fig_weights_compare(..., figure_title="Figure3.2")**`（`**dash_app/app.py**` / `**dash_app/services/pipeline_factories.py**`）。

占位符：`**{n_symbols}**` · `**{defense_level}**` · `**{objective_name}**`（可与快照 `**snap_json["phase3"]**` / `**snap_json["defense_level"]**` 对齐注入）。投资叙事见 `**Figure3.2-Inv.md**`。

---

## 1. 图形管线（端到端）

```text
data.json → run_pipeline → PipelineSnapshot.phase3.weights · meta.symbols_resolved · defense_level
  → Dash：fig_weights_compare(weights, symbols_resolved, tpl, figure_title="Figure3.2")
  → 并排柱（灰：基准分支；蓝：phase3.weights）
```

---

## 2. AdaptiveOptimizer 与防御等级（方法论核心）

本节说明 **Fig3.2 蓝柱数值含义**：**在给定边际收益向量 μ、协方差 Σ、情绪词典与策略参数下，按 `DefenseLevel` 求解组合权重**，再施加 **阻断集合** **清零与归一**。柱状图本身是 **离散权重向量**，**不绘制收益轨迹**。

### 2.1 目的：优化权重 vs 柱状「基准」灰柱


| 维度         | 蓝柱（`**phase3.weights`**）                                                                      | 灰柱（`**fig_weights_compare`** 第一组）                                           |
| ---------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| **来源**     | `**run_phase3`** → `**AdaptiveOptimizer.optimize(level)`** → `**_apply_blocked_renorm**`      | `**custom_weights**` 参数：有则 **「自定义权重（饼图）」**；**否则** **等权 `1/N`**              |
| **与测试窗标签** | 优化使用 **训练窗 μ、Σ**（及 Level 2 的历史收益子样本）；**不显式用测试窗收益参与目标**（测试窗实现对比在 `**defense_validation`** 等字段） | **纯对照**：当前 `**dash_app/app.py`** **未传入** `**custom_weights`** → **运行时恒为等权** |
| **用途**     | **资本分配结果** → 同日 **Fig3.3** MC 使用该 `**w`** 生成组合路径                                              | **视觉锚点**：观察优化相对 **1/N（或将来接入的饼图向量）** 的偏离                                     |


管线内另算 `**w_custom`**（来自 `**_custom_weights_for_symbols`** 映射后的 `**Phase3Input.custom_portfolio_weights**`），用于 `**defense_validation**` 中与 反事实轨迹对照；除非下游回调向 `**fig_weights_compare**` **显式传入** `**custom_weights`**，否则 **Fig3.2 灰柱不展示 `w_custom`**。

### 2.2 `**DefenseLevel` → 目标函数（实现名 → `phase3.objective_name`）**

`**research/defense_state.py`** `**DefenseLevel`**：STANDARD=0 · CAUTION=1 · MELTDOWN=2。`**resolve_defense_level`**（`**run_pipeline`** 内）依据 Phase1/2 诊断 **解析** `**level`**。

`**AdaptiveOptimizer.optimize`**（`**research/phase3.py`**）：

- **Level 0（STANDARD）**：最小化 `**-(μ_port − r_f)/σ_port`**（`**r_f = RISK_FREE = 0`**），等价 **最大化夏普**；返回名 `**max_sharpe`**，并给出 `**sharpe`**。
- **Level 1（CAUTION）**：最小化 `**σ_port + λ_semantic · Σ_i w_i · neg_sent_i`**，其中 `**neg_sent_i = max(0, −sentiment(symbol_i))`**；返回名 `**caution_semantic**`。
- **Level 2（MELTDOWN）**：在 **历史收益矩阵** `**R`** 上最小化 **样本 CVaRα**（`**policy.cvar_alpha`**）；`**R`** 来自 `**hist_returns**`，经 `**subset_returns_for_cvar**` 截条件子样本；若缺失则用 **RNG(0)** 合成样本；返回名 `**min_cvar`**，并给出 `**cvar`**。

约束：`**Σ w_i = 1**`，`**w_i ∈ [0,1]**`，**SLSQP** `**maxiter=500`**。

### 2.3 `**blocked_symbols` 再归一化**

Phase1 诊断 `**weight_zero`** 或 `**basic_logic_failure`** 的标的进入 `**blocked_symbols**`。`**_apply_blocked_renorm**`：**阻断仓位清零**，**剩余权重按和归一**；若无可分配标的则回退 **存活标的等权**。

### 2.4 **管线内自定义权重映射（`_custom_weights_for_symbols`）**

会话/UI 键（如 `**TSMC`** → `**TSM`**，`**GLD**` → `**AU0**`）合并为 **非负向量**，**单纯形归一**；全零时回退 **等权**。该结果写入 `**Phase3Input.custom_portfolio_weights`**，在 `**run_phase3`** 内同样经 `**_apply_blocked_renorm**` 得到 `**w_custom**`（用于防御验证字段），**与 Fig3.2 灰柱无强制绑定**（见 §2.1）。

---

## 3. 数据溯源（Data Provenance）


| 项目                 | 说明                                                                                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **蓝柱权重**           | `**snap_json["phase3"]["weights"]`**                                                                                                                    |
| **目标函数标签**         | `**snap_json["phase3"]["objective_name"]`** ∈ `**max_sharpe`** / `**caution_semantic**` / `**min_cvar**`                                                |
| **防御等级（整数）**       | `**snap_json["defense_level"]`**（与 `**DefenseLevel`** 枚举一致）                                                                                             |
| **列顺序 / Universe** | `**snap_json["phase0"]["meta"]["symbols_resolved"]`**（柱状 `**x`** 与该序列对齐，过滤 `**s in weights**`）                                                          |
| **边际 μ**           | `**pipeline` μ 组装**：`p2.model_mu.get(p2.best_model_per_symbol.get(s, "naive"), {}).get(s, float(hist_mu.get(s, 0.0)))`（摘义），见 `**research/pipeline.py`** |
| **Σ**              | **训练窗样本协方差**，对角 **下界 1e-10**                                                                                                                            |
| **阻断集合**           | Phase1 `**diagnostics`** `**weight_zero` / `basic_logic_failure`** 聚合                                                                                   |


---

## 4. 公式速览（与绘图和 §2 对应）

**基准灰柱（无 `custom_weights`）**：每根 **1/N**，**N=s\in symbols : s\in weights**（与 `**fig_weights_compare`** 实现一致）。

**可选灰柱（传入 `custom_weights`）**：与投资视图 `**Figure3.2-Inv.md`** 相同 —  
**\tilde w^{\mathrm{cust}}_i = \max(0,w^{\mathrm{cust}}_i) / \sum_j \max(0,w^{\mathrm{cust}}_j)**。

**夏普分支（Level 0）**：  
**\mu_{p}=w^\top\mu**，**\sigma_{p}=\sqrt{w^\top\Sigma w}**，目标最小化 `**−(μ_p − r_f)/σ_p`**（`**r_f=0`**）。

**警戒分支（Level 1）**：**\sigma_p + \lambda \sum_i w_i \cdot \max(0,-S_i)**（`**S_i`** 来自 `**inp.sentiments`**）。

**熔断分支（Level 2）**：在历史样本路径上 **最小化 CVaRα**（左尾均值损失），见源码 `**_cvar_loss`**。

---

## 5. 计算过程链（Calculation Chain）


| 步骤  | 计算对象                 | 输入                                                   | 输出                                               |
| --- | -------------------- | ---------------------------------------------------- | ------------------------------------------------ |
| 1   | `**train`** 收益表      | `**returns**`、`**train_mask`**                       | **行完备训练样本**（与 Phase2 一致 `**dropna(how="any")`**） |
| 2   | `**μ`**、`**Σ**`      | `**run_phase2**` 结果、训练收益                             | **边际向量 + 协方差矩阵**                                 |
| 3   | `**DefenseLevel`**   | Phase1/2 诊断 + `**DefensePolicyConfig`**              | `**level**`                                      |
| 4   | `**w_raw**`          | `**AdaptiveOptimizer.optimize(level)**`              | **字典权重 + `objective_name`**                      |
| 5   | `**phase3.weights**` | `**w_raw**` + `**blocked_symbols**`                  | `**_apply_blocked_renorm**`                      |
| 6   | **Fig3.2 图对象**       | `**weights`**、`**symbols`**、`**custom_weights**`（可选） | `**go.Bar`×2 · `barmode=group**`                 |


---

## 6. 关键数据计算示例（重要数值）

以下 **数例** 说明 **标尺与读图**；**具体蓝柱坐标**随 `**data.json`**、防御解析与阻断集合变化，**以同一次管线快照为准**。

### 6.0 前提（Phase2 影子择模，与 Fig2.1 §6.1 同源）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

**择模全表 / NVDA MSE / combined / 全样本影子 MSE** 见 **`Figure2.1-Res.md` §6.2～§6.4**。

### 6.1 **UI 基准（当前实现）**

`**dash_app/app.py`** 调用 `**fig_weights_compare(weights, symbols, tpl, ...)`** **未传** `**custom_weights`** → **灰柱名** **「等权基准」**，每标的高度 **1/N**。

### 6.2 **代数读图（与投资视图 §3 一致）**

设 **N=10**、无自定义对照：灰柱每根 **0.100**。若同一次运行中 `**phase3.weights["AU0"]=0.283`**（示例：金现沪主连），则 **蓝柱该列 0.283**，表示 **熔断/警戒等路径下** 优化将 **更多资本** 配置到该标的（相对等权）。

### 6.3 **快照核对**

1. `**sum(snap_json["phase3"]["weights"].values()) ≈ 1`**（浮点误差内）。
2. 对 `**snap_json["phase1"]["diagnostics"]`** 中 `**weight_zero`/`basic_logic_failure**` 标的 **k**：`**weights[k]=0`**。
3. `**snap_json["phase3"]["objective_name"]`** 与 `**snap_json["defense_level"]**` **语义一致**（**0↔max_sharpe**，**1↔caution_semantic**，**2↔min_cvar**，以源码 `**AdaptiveOptimizer.optimize`** 为准）。

---

## 7. 源码锚点（可追溯）

**优化与阻断：**

```python
# research/phase3.py — AdaptiveOptimizer.optimize（节选）
if level == DefenseLevel.STANDARD:
    res = minimize(self._sharpe_obj, w0, method="SLSQP", ...)
    return {self.symbols[i]: float(w[i]) for i in range(n)}, "max_sharpe", sh, None
# ... CAUTION / MELTDOWN ...
w = _apply_blocked_renorm(w_raw, syms, blocked)
```

**柱状图：**

```python
# dash_app/figures.py — fig_weights_compare（节选）
if custom_weights:
    w_cust = [max(0.0, float(custom_weights.get(s, 0.0))) for s in syms]
    t = sum(w_cust) or 1.0
    first_y = [v / t for v in w_cust]
else:
    first_y = [eq] * n   # eq = 1.0 / n
```

---

## 8. 一致性检验

1. 读取 `**snap_json["phase3"]["weights"]**` 与 `**symbols_resolved**`（顺序一致）。
2. 使用同一 `**DefensePolicyConfig**`、收益 `**returns**`、窗口掩码及 Phase1/2 **输出**，重跑 `**run_pipeline`**（或源码级重放 `**run_phase3`** 输入）。
3. `**weights**` 字典 **逐键数值一致**（容忍机器精度）。
4. **手动抽检**：被阻断标的 **权重为 0**；非阻断 **非负且和为 1**。

---

## 9. 与 Fig3.3 / Phase 2（简）

- **Fig3.3**（双轨 MC）使用 **同一组优化权重** `**w`**（经 `**_simulate_mc_paths`**）生成组合价格路径；Fig3.2 是该 `**w**` 的 **静态横截面**。  
- **Fig3.1** / **Fig2.1** 像素矩阵决定 **μ 先验中 `model_mu` 的列选择**（见 `**run_pipeline`** **μ 组装**）；**Fig3.2** **不重复**择模逻辑，仅展示 **Phase 3 优化结果**。

---

**占位**：`**{n_symbols}`** · `**{defense_level}`** · `**{objective_name}`**