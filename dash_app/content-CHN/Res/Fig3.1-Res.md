# Figure3.1 · 各标的最佳模型收益期望与波动预测（研究 · B 类）

**对象类型（B）**：以 **无竖向条框的三行小表格** 离散展示每个标的在 **影子择模胜者** 下的 **次日收益期望 μ̂** 与 **波动预测 σ̂**。数值来自 `**phase2.model_mu[best_model_per_symbol[s]][s]`** 与 `**phase2.model_sigma[best_model_per_symbol[s]][s]`**——即 **Fig2.1 像素矩阵点亮的那一格模型** 在测试窗末端给出的 **(\mu,\sigma)** 对。本图 **不绘制时间序列**，仅呈现 **横截面标尺**；Phase 3 下游 `**AdaptiveOptimizer`** 正是以该 **μ̂ 向量** 作为边际收益先验。

**择模方法论（holdout 切分、MSE+JSD 综合分、\alpha、击败规则）不在本文重复展开**，请参阅 `**Figure2.1-Res.md`** **§2–§6**（单一真理源）。本文重心在 **μ̂／σ̂ 的生成路径**、**表格的三行语义** 与 **与 Phase 3 μ 向量组装（`research/pipeline.py`）的数值一致性**。

表格布局（无竖向条框、行方向读数）：


| 行号  | 含义                                                                     |
| --- | ---------------------------------------------------------------------- |
| 行 1 | **标的** `sym`（列顺序 = `snap_json["phase0"]["meta"]["symbols_resolved"]`）  |
| 行 2 | **最佳模型 μ̂**（`model_mu[best_model_per_symbol[sym]][sym]`，单位：日收益率）       |
| 行 3 | **最佳模型 σ̂**（`model_sigma[best_model_per_symbol[sym]][sym]`，单位：日收益率标准差） |


占位符：`**{n_symbols}`** · `**0`** · `**{objective_name}`** ·（若需与 Phase 2 下拉联动）`**{p2_selected_symbol}**`

---

## 1. 图形管线（端到端）

```text
data.json → run_phase2 →
  phase2.best_model_per_symbol  （每标的胜出模型键）
  phase2.model_mu               （四模型 × 标的 → μ̂，测试窗末端或均值）
  phase2.model_sigma            （四模型 × 标的 → σ̂）
    → 主回调按 sym 索引 best_model_per_symbol[sym] → 取对应 μ̂、σ̂
    → 组装三行表格（无竖框）：[symbols; μ̂_best; σ̂_best]
    → 输出至 Phase 3 主栏 fig_label=Figure3.1
```


| 概念            | 说明                                                                                                                                                                       |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **数据真理源**     | `**phase2.model_mu`**、`**phase2.model_sigma`**、`**phase2.best_model_per_symbol**`（`**research/phase2.py**` `**run_phase2`** 聚合；详见 Fig2.1-Res §3）                         |
| **列 / 标的顺序**  | `**snap_json["phase0"]["meta"]["symbols_resolved"]`**（与 Fig3.2 柱状横轴一致）                                                                                                   |
| **时间定位**      | 每格数值为 **测试窗末端** 的 **一步预测 μ̂／σ̂**；若 `**model_mu_test_ts`** / `**model_sigma_test_ts`** 存在则取其末点，否则退回全样本标量（与 `**dash_app/ui/main_p2.py`** `**_p2_mu_sigma_table`** 的取值规则一致） |
| **Phase 3 侧** | `build_p3_panel`（`dash_app/ui/main_p3.py`）内挂载三行 μ̂／σ̂ 表，外包 `**fig_label=FIG.F3_1`**（`**Figure3.1`**）                                                                     |
| **无竖向条框**     | Dash/HTML `**dbc.Table(..., borderless=True)`** 或 CSS `**border-left:0; border-right:0`**；仅保留行分隔线，读数沿 **列向（每标的一栏三行）** 完整                                                 |


**与 Fig2.1 像素矩阵的职责边界**：Fig2.1 回答 **"每个标的选哪一族模型"**（离散键）；Fig3.1 回答 **"被选中的那族模型在此刻给出的 μ̂ 与 σ̂ 是多少"**（连续标量）。两图 **共用 `best_model_per_symbol`**，但数据维度互补。

---

## 2. 影子择模方法论（交叉引用）


| 主题                     | 说明                                                                         |
| ---------------------- | -------------------------------------------------------------------------- |
| **择模定义与目的**            | 见 `**Figure2.1-Res.md`** **§2.1**（择模容器 vs 严格 OOS）                          |
| **Holdout 切分**         | `**Figure2.1-Res.md`** **§2.2**                                            |
| **MSE + JSD + \alpha** | `**Figure2.1-Res.md`** **§2.3–§2.5**                                       |
| **实现变量与公式表**           | `**Figure2.1-Res.md`** **§3–§4**                                           |
| **数值复现脚本**             | `**python research/figure21_res_key_example.py`**（与 Fig2.1 §6 **同源 JSON**） |


本节若只阅读 **Fig3.1**：记住 —— **胜者模型由训练尾影子综合分 `argmin combined` 决定**（Fig2.1）；本文 **直接取用该胜者在测试窗末端的 (\mu,\sigma)** 作为三行数字，**不重新择模**，也 **不在测试窗上反推任何分数**。

---

## 3. 数据溯源（Data Provenance）


| 项目                   | 说明                                                                                                                                                     |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **胜者字典**             | `**snap_json["phase2"]["best_model_per_symbol"]`**（与 Fig2.1 逐键一致）                                                                                      |
| **μ̂（全量字典）**         | `**snap_json["phase2"]["model_mu"]`** · `**{model: {sym: μ̂}}`**（四模型 × 标的）                                                                             |
| **σ̂（全量字典）**         | `**snap_json["phase2"]["model_sigma"]`** · `**{model: {sym: σ̂}}`**                                                                                    |
| **μ̂(t) / σ̂(t) 时序** | `**snap_json["phase2"]["model_mu_test_ts"]`** / `**["model_sigma_test_ts"]`**（`**{model: {sym: [..]}}`**；取末元素即测试窗末日一步预测，与 `**_p2_mu_sigma_table`** 一致） |
| **列顺序 / 标的**         | `**snap_json["phase0"]["meta"]["symbols_resolved"]`**（与投资视图 `**Figure3.1-Inv.md`** 表格一致）                                                               |
| **下游消费（Phase 3）**    | `**research/pipeline.py`** `**mu = [p2.model_mu[p2.best_model_per_symbol[s]][s] for s in symbols]`**；Fig3.1 行 2 与该向量 **逐元素相等**（容忍浮点精度）                 |


---

## 4. 公式速览（与绘图和 §2 对应）

**行 2（最佳模型 μ̂）**：  
**\hat\mu^{\star}_s=\mathrm{modelmu}[\mathrm{bestmodelpersymbol}[s]][s]**

**行 3（最佳模型 σ̂）**：  
**\hat\sigma^{\star}_s=\mathrm{modelsigma}[\mathrm{bestmodelpersymbol}[s]][s]**

**时间定位（若 OOS 时序可用）**：  
**\hat\mu^{\star}_s = \mathrm{modelmutestts}[m^{\star}_s][s][-1]**，**\hat\sigma^{\star}_s = \mathrm{modelsigmatestts}[m^{\star}_s][s][-1]**，其中 **m^{\star}_s = \mathrm{bestmodelpersymbol}[s]**。

**管线级缺省回退**（与 `**research/pipeline.py`** **μ 组装**一致）：  
若 `**m^\star_s`** 在 `**model_mu`** 中缺键或返回 `**None`**，回退 **\hat\mu^{\star}_s \leftarrow \bar r_s^{\mathrm{train}}**（`**hist_mu.get(s, 0.0)`**）；**\hat\sigma^{\star}_s** 在本图对应单元渲染为占位符 **"—"**（上游未失败的前提下，该回退几乎不触发）。

---

## 5. 计算过程链（Calculation Chain）


| 步骤  | 计算对象                           | 输入                              | 输出                                        | 逻辑                                                                    |
| --- | ------------------------------ | ------------------------------- | ----------------------------------------- | --------------------------------------------------------------------- |
| 1   | `**model_mu` / `model_sigma`** | 测试窗 `**returns`**、四模型 OOS 一步预测  | `**{m: {sym: μ̂}}`**、`**{m: {sym: σ̂}}`** | `**research/phase2.py`** `**run_phase2`** 内各模型分支（与 Fig2.2 密度图共用同一源）   |
| 2   | `**best_model_per_symbol`**    | 影子 holdout 综合分                  | `**{sym: model_key}`**                    | 见 `**Figure2.1-Res.md`** **§2、§4**                                    |
| 3   | `**μ̂^★`** 向量                  | 步骤 1、2                          | **长度 N 的 float 向量**                       | `**μ̂^★_s = model_mu[best_model_per_symbol[s]][s]`**（同源于 Phase3 μ 组装） |
| 4   | `**σ̂^★`** 向量                  | 步骤 1、2                          | **长度 N 的 float 向量**                       | 同上，换 `**model_sigma`**                                                |
| 5   | **Fig3.1 表格对象**                | 步骤 3、4 + `**symbols_resolved`** | **3×N 无竖框表格**                             | Dash `**dbc.Table(..., borderless=True, striped=False)`** 或等效 CSS     |


---

## 6. 关键数据计算示例（重要数值）

以下示例按 `**Figure2.1-Res.md`** **§6.1** 同一快照（`**data.json`**、`**shadow_holdout_days=40`**、`**alpha_model_select=0.5`**）展示 胜者表 + μ̂／σ̂ 取值。更新数据后同步重跑 `**python research/figure21_res_key_example.py`**（与 Fig2.1 §6 共用）后，按实际打印的 JSON 重写本节。

### 6.0 前提（与 Fig2.1 §6.1 同源）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

### 6.1 `**best_model_per_symbol`**（同 Fig2.1 §6.2）


| 标的    | 胜者模型 `**m^★_s`** |
| ----- | ---------------- |
| NVDA  | lightgbm         |
| MSFT  | arima            |
| TSMC  | lightgbm         |
| GOOGL | lightgbm         |
| AAPL  | lightgbm         |
| XLE   | arima            |
| GLD   | arima            |
| TLT   | lightgbm         |
| SPY   | lightgbm         |


### 6.2 三行表读法（示例占位 `{sym}` 列）


| sym     | NVDA        | MSFT        | TSMC | GOOGL | AAPL | XLE | GLD | TLT | SPY |
| ------- | ----------- | ----------- | ---- | ----- | ---- | --- | --- | --- | --- |
| μ̂^★（日） | `{μ̂_NVDA}` | `{μ̂_MSFT}` | …    | …     | …    | …   | …   | …   | …   |
| σ̂^★（日） | `{σ̂_NVDA}` | `{σ̂_MSFT}` | …    | …     | …    | …   | …   | …   | …   |


实际数字随快照变化，以 `**snap_json["phase2"]["model_mu"]`** / `**["model_sigma"]`** 为准；格式化建议 **6 位小数、等宽字体**（与 `**dash_app/ui/main_p2.py`** `**_p2_mu_sigma_table`** 一致）。

### 6.3 数值一致性命题（Fig3.1 ↔ Phase 3 μ 向量）

在同一次 `**last-snap`**、未切换 Universe 的前提下：

`**np.array([snap["phase2"]["model_mu"][snap["phase2"]["best_model_per_symbol"][s]][s] for s in snap["phase0"]["meta"]["symbols_resolved"]])**`

**逐元素等于** `**research/pipeline.py`** 组装的 `**Phase3Input.mu_daily`**（`**snap_json["phase3"]["mu_daily"]`**，在浮点精度内）。Fig3.1 表格行 2 即该向量的横截面可视化；行 3 为同胜者下的 σ̂，并不直接进入 AdaptiveOptimizer（优化使用训练窗样本协方差 `**Σ**`，见 `**Figure3.2-Res.md`** **§2.1**），**但为读者理解 Fig3.2 蓝柱给出了同步的"单资产波动标尺"。**

---

## 7. 源码锚点（可追溯）

**μ̂／σ̂ 字典生成（与 Fig2.2 密度同源）：**

```python
# research/phase2.py — run_phase2 返回（节选）
return Phase2Output(
    ...
    model_mu={m: dict(mus[m]) for m in models},
    model_sigma={m: dict(sigs[m]) for m in models},
    best_model_per_symbol=best_model_per_symbol,
    test_daily_best_model_mu_mean=daily_best_mu,
    model_mu_test_ts={m: dict(mu_ts[m]) for m in models},
    model_sigma_test_ts={m: dict(sig_ts[m]) for m in models},
)
```

**管线侧 μ 组装（下游消费者）：**

```python
# research/pipeline.py（节选）
hist_mu = rets.loc[train_mask].mean()
mu = np.array(
    [
        p2.model_mu.get(p2.best_model_per_symbol.get(s, "naive"), {}).get(
            s, float(hist_mu.get(s, 0.0))
        )
        for s in symbols
    ],
    dtype=float,
)
```

**表格取值规则（末日快照）：**

```python
# dash_app/ui/main_p2.py — _p2_mu_sigma_table（节选；Fig3.1 按同规则取 best 行）
if model_mu_test_ts and model_sigma_test_ts:
    ts_m = (model_mu_test_ts.get(m) or {}).get(symbol) or []
    ts_s = (model_sigma_test_ts.get(m) or {}).get(symbol) or []
    if ts_m and ts_s:
        mu, sg = ts_m[-1], ts_s[-1]
if mu is None:
    mu = model_mu.get(m, {}).get(symbol)
    sg = model_sigma.get(m, {}).get(symbol)
```

**Phase 3 挂载（外包 Figure3.1）：**

```text
dash_app/ui/main_p3.py — build_p3_panel
  三行 μ̂/σ̂ 表（borderless）
  fig_label = FIG.F3_1  → "Figure3.1"
```

---

## 8. 一致性检验

1. **胜者对齐**：`**snap["phase2"]["best_model_per_symbol"][s]`** 与 Fig2.1 像素亮格 **逐标的一致**（Fig2.1 §8）。
2. **μ 对齐 Phase 3**：对每个 `**s ∈ symbols_resolved`**，
  `**snap["phase2"]["model_mu"][best_model_per_symbol[s]][s]`** **≈** `**snap["phase3"]["mu_daily"][idx(s)]`**（容忍机器精度；若不一致，检查 Kronos 分支是否走了代理或 `**hist_mu`** 回退）。
3. **σ 非负**：`**snap["phase2"]["model_sigma"][m^★_s][s] ≥ 0`**；若为 `**None`** 或 `**NaN**`，表格对应单元渲染 `"—"`，不得静默填 0。
4. **时序一致**：若存在 `**model_mu_test_ts`** / `**model_sigma_test_ts`**，末元素与 `**model_mu`** / `**model_sigma`** 标量一致（同一源，差异应来自"末日 vs 全样本均值"的口径说明；以 §4 规则为准）。
5. **无竖框渲染**：DOM 检查表格单元 **无 `**border-left`** / `**border-right**`**，仅保留行分隔；列方向读数时视觉连贯。

---

## 9. Phase 3 阅读顺序（Fig3.1 → Fig3.2 → Fig3.3）


| 顺序  | 图号             | 作用                                                                                                                 |
| --- | -------------- | ------------------------------------------------------------------------------------------------------------------ |
| 1   | **Fig3.1**（本文） | 展示 **每标的影子胜者** 在测试窗末端给出的 **(μ̂,σ̂)**；行 2 的 μ̂ 向量即 `**AdaptiveOptimizer`** 接收的边际收益先验（详见 `**research/pipeline.py`**） |
| 2   | **Fig3.2**     | 在同一 μ̂ 先验 + 训练窗 Σ 下求解 `**phase3.weights`**，与等权/自定义灰柱对比（`**Figure3.2-Res.md`**）                                     |
| 3   | **Fig3.3**     | 双轨蒙特卡洛，在同一随机引擎下观察 `**defense_level`** / 目标函数与情景差异                                                                  |


占位符语境：`**0`**、`**{objective_name}`** 与 `**objective-banner**`（优化目标叙述）对齐侧栏 `**DefensePolicyConfig**`；本图 **只暴露 μ̂／σ̂ 原始数值**，不做 **目标函数** 的任何重标度。

---

**占位**：`**{n_symbols}`** · `**0`** · `**{objective_name}`** · `**{p2_selected_symbol}**`