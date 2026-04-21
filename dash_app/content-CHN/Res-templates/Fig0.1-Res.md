# Figure0.1 · 组合权重饼图（研究）

**对象类型（A）**：基础统计与结构图示。该图不依赖概率模型输出；它把“当前 Universe 下的组合权重向量 w”做成可交互饼图，用于后续 Phase 3 的 **custom weights（用户自定义组合）** 对照与实验控制。

本文对齐主栏图 `dcc.Graph(id="fig-p0-pie")`，由 `dash_app/callbacks/p0_assets.py:_update_pie` 调用 `dash_app/figures.py:fig_p0_portfolio_pie(..., figure_title="Figure0.1")` 生成。

占位符（可选）：`**{n_symbols}`** · `**{p0_pie_selected_symbol}**`

---

## 1. 图形管线（端到端）

```text
UI（Phase 0 左侧 Universe / 划线） + p0-weight-store（权重字典）
  → callbacks/p0_assets.py::_update_pie（权重/顺序/分组颜色解析）
  → figures.py::fig_p0_portfolio_pie(weights, symbols, ..., pie_selected)
  → Figure0.1（Plotly Pie / Donut）
  → 交互：clickData → p0-pie-selected；slider → 写回 p0-weight-store
```

---

## 2. 数据溯源（Data Provenance）


| 项目               | 说明                                                                                                                                 |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **权重字典（主输入）**    | `dcc.Store(id="p0-weight-store")`。键为标的代码（大写），值为权重（非负浮点）。                                                                           |
| **权重顺序（决定扇区顺序）** | `asset-universe-store`（Universe 配置）经 `_flatten_universe` 展开后的 `order_full`（`dash_app/dash_ui_helpers.py`）。                         |
| **默认权重来源**       | 若 UI 尚未写入且存在快照：回退 `snap["phase3"]["weights"]`；若连快照也没有：回退等权 `1/N`（见 `callbacks/p0_assets.py:_update_pie`）。                          |
| **分组颜色**         | 优先取快照 `snap["phase0"]["meta"]` 中的 `tech_symbols/hedge_symbols/safe_symbols/benchmark`；否则取 Universe 当前值（见 `_update_pie` 约 53–64 行）。 |
| **选中扇区**         | `dcc.Store(id="p0-pie-selected")`：来自饼图点击 `clickData.points[0].label`，或左侧列表“准星”按钮。                                                  |


---

## 3. 方法论与数学对象

### 3.1 权重向量与归一化

`fig_p0_portfolio_pie` 以输入字典 `weights` 构造向量：

- `values[s] = max(weights.get(s, 0), 0)`
- 若 \sum_s values_s \le 10^{-15}：整列回退等权；
- 否则归一化为 w_s = values_s / \sum_j values_j。

因此图中百分比永远满足 \sum_s w_s = 1，并且**不会**展示负权重。

### 3.2 “选中扇区外拉（pull）”语义

当 `pie_selected` 存在且与某扇区 `label` 匹配时，该扇区 `pull=0.07` 以视觉上锁定“当前正在被滑块调整的标的”（见 `dash_app/figures.py`）。

---

## 4. 计算过程链（Calculation Chain）


| 步骤  | 计算对象          | 输入                              | 输出                          | 逻辑 / 函数                               |
| --- | ------------- | ------------------------------- | --------------------------- | ------------------------------------- |
| 1   | Universe 展开顺序 | `asset-universe-store`          | `order_full`                | `_flatten_universe`                   |
| 2   | 权重来源合并        | `p0-weight-store` + `last-snap` | `w`                         | `_merge_alias_weight_keys` + fallback |
| 3   | 分组解析          | `snap.phase0.meta` 或 Universe   | `tech/hedge/safe/benchmark` | `_update_pie`                         |
| 4   | 饼图数据          | `w` + `symbols`                 | `labels/values/colors/pull` | `fig_p0_portfolio_pie`                |
| 5   | 交互写回（可选）      | slider + selected               | `p0-weight-store` 新字典       | `_pie_slider`（其余按比例缩放）                |


---

## 5. 交互规则（研究模式建议重点讲清）

### 5.1 滑块的“其余标的按原比例缩放”

设选中标的为 s^，滑块设定新值 w'*{s^}\in[0,1]。其余标的集合为 S\setminuss^，令旧权重和为 O=\sum*{j\ne s^} w_j。实现采用比例缩放：


w'*j = w_j\cdot\frac{1-w'*{s^}}{O}\quad (j\ne s^)


若 O=0 则保持其余为 0，仅更新 s^（源码见 `callbacks/p0_assets.py:_pie_slider` 约 151–163 行）。

### 5.2 划线与“应用”的边界

- 划线仅决定“当前参与组合的标的集合”与“等权重置规则”（`reset_eq`）；
- 饼图本身只是 `p0-weight-store` 的可视化与写入器，**不会**直接触发 Phase 0～3 的计算；需要点击侧栏 **应用 / 应用并重算** 进入管线。

---

## 6. 关键数据计算示例（重要数值）

**饼图权重** 与 **Phase2 择模** 无直接公式关系；下列 **前提表** 与 **`Figure2.1-Res.md` §6.1** 同源，供全库 **同一 `data.json` 会话** 内与 **影子 holdout 参数** 对照。择模全表见 **`Figure2.1-Res.md` §6.2～§6.4**。

### 6.1 前提（与 Fig2.1 §6.1 同源）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

---

## 7. 源码锚点（可追溯）

- **主布局挂载**：`dash_app/ui/main_p0.py`：`dcc.Graph(id="fig-p0-pie")` + `dcc.Slider(id="p0-pie-slider")`
- **饼图生成**：`dash_app/callbacks/p0_assets.py:_update_pie` → `dash_app/figures.py:fig_p0_portfolio_pie`
- **点击选中**：`dash_app/callbacks/p0_assets.py:_pie_click`
- **滑块写回权重**：`dash_app/callbacks/p0_assets.py:_pie_slider`
- **别名合并（TSMC→TSM / GLD→AU0）**：`dash_app/dash_ui_helpers.py:_merge_alias_weight_keys`（用于 UI 与管线符号对齐）

---

## 8. 一致性检验

1. 取当前 `p0-weight-store` 与 `asset-universe-store` 展开顺序 `order_full`。
2. 按 `fig_p0_portfolio_pie` 的逻辑手动归一化得到 w。
3. 核对饼图 hover 中每扇区的百分比与 w_s 在容忍误差内一致。
4. 点击任一扇区后，检查 `p0-pie-selected` 更新为该 `label`，且该扇区外拉（pull）可见。

---

## 9. 与下游叙事（简）

- **与 Fig3.2（权重对比）**：Phase 3 的 `fig_weights_compare` 若传入 `custom_weights`，灰柱展示“饼图自定义权重”；当前主回调未传入时灰柱为等权基准（见 `dash_app/figures.py:fig_weights_compare`）。
- **与 Phase3Input.custom_portfolio_weights**：管线会把 UI 权重映射到管线 symbol（TSMC/GLD 别名），再归一写入 `Phase3Input.custom_portfolio_weights`（见 `research/pipeline.py:_custom_weights_for_symbols`）。

