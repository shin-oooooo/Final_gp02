# Figure2.2 · 时间 × 收益密度热图（测试窗严格 OOS）

**对象类型（B′）**：在 **测试窗** 每个交易日 **t** 上，用各模型输出的 **(\hat\mu_{m,s,t},\hat\sigma_{m,s,t})** 构造 **Gaussian 预测密度** **p_{m,s,t}(r)**，在时间 × 下一期收益 **r** 平面上堆叠为 **半透明热力图层**；并叠加 **μ_{m,s,t} 脊线**（Scatter）及（可选）**已实现简单收益真值折线**。与 **Fig2.1 / Fig3.1** 的 **离散像素择模** 共用 **`phase2.best_model_per_symbol`** 与 **`phase2`** 快照，但 **不负责择模**，仅展示 **概率层严格样本外** 的动态。

本文对齐：**`dcc.Graph(id="fig-p2-density")`** · `dash_app/ui/main_p2.py` **`fig_label="Figure2.2"`** · 图形函数 **`dash_app/figures.py::fig_p2_density_heatmap`**（文档字符串内历史编号曾写作 Figure 2.3，**外包标题以 `figure_title="Figure2.2"` 为准**）。

占位符：`{p2_selected_symbol}` · 与 `phase2.test_forecast_dates` 等长的一维序列占位（可由模板注入）。

---

## 1. 图形管线（端到端）

```text
data.json → run_pipeline → run_phase2
  → test_forecast_dates（长度 T）
  → model_mu_test_ts[m][sym]、model_sigma_test_ts[m][sym]（各模型各标的各 T 步 OOS 矩）
  → （可选）dash_app/figures._test_returns(json_path, sym, t0, t1) → test_vals（长度 T，与 dates 对齐）
  → fig_p2_density_heatmap(dates, mu_ts, sigma_ts, sym, tpl, test_vals=..., figure_title="Figure2.2")
  → Output("fig-p2-density", "figure")
```

**局部刷新**：`dash_app/callbacks/p2_symbol.py` 在 **`p2-symbol`** 变更时，用同一快照重算 **`fig-p2-density`**（与像素图、交通灯一并更新）。R1.10 后主题切换已移除，`theme-store` 值常驻 `"dark"`，仅作 `State` 读取不再触发本回调。

---

## 2. 与 Fig2.1 的职责边界（必读）

| 维度 | Fig2.1 像素矩阵 | Fig2.2 密度热图 |
| --- | --- | --- |
| **时间范围** | **训练窗** 末端 **`n_tail_eff`** 日影子 holdout | **测试窗** 每个日历交易日 **t** |
| **信息集** | holdout 内逐步拟合（定义见 **`Figure2.1-Res.md`** §2） | **严格 OOS**：`**returns.index < t`** 条件下逐步预测 |
| **输出语义** | 离散 **`best_model_per_symbol[s]`**（择模标签） | 连续 **密度层 + μ 脊线**（**不输出**新择模结果） |
| **用途** | 回答「谁赢」 | 回答「赢家的 **概率叙事** 在测试窗如何随时间展开」 |

二者 **不得混读**：影子 holdout **不消耗测试窗标签**；Fig2.2 **消费** **`model_mu_test_ts` / `model_sigma_test_ts`**，与 **`Figure2.1-Res.md`** §2.1 对照表一致。

---

## 3. 数据溯源（Data Provenance）

| 项目 | 说明 |
| --- | --- |
| **测试日期轴** | `snap_json["phase2"]["test_forecast_dates"]`（长度 **T**） |
| **OOS μ/σ** | `snap_json["phase2"]["model_mu_test_ts"][model][symbol]`、`model_sigma_test_ts`（各 **len = T** 且与 dates 对齐；否则该模型对该标的 **不参与** 绘图） |
| **实现收益叠加** | `fig_p2_density_heatmap(..., test_vals=...)`：`dash_app/figures._test_returns`**(**`json_path`, `sym`, **首末**测试日**)** 返回与 **`test_forecast_dates`** **逐元对齐** 的简单收益序列；**长度不等则无上色真值线** |
| **当前标的** | 下拉 **`p2-symbol`**；初始值由 `dash_app/render/main_p2.py::_resolve_p2_symbol_selection` 解析 |

---

## 4. 数学对象与绘图规则（与 `figures.py` 一致）

1. **密度**：对每个有效模型 **m**、每个 **t**，在收益网格 **r_centers** 上计算 Gaussian **PDF**，再 **`log1p`**、按列 **`z/zmax`** 归一化并 **`clip^γ`**（**γ=1.75**）以增强低密区对比度。
2. **y 轴范围**：`**[min(μ)−4σ_max, max(μ)+4σ_max]**`，缺数据时回退 **±0.05**。
3. **网格档数**：`**n_r_bins=120**`（默认）。
4. **多模型**：`**model="all"`** 时 **Naive / ARIMA / LightGBM / Kronos** 四层 Heatmap **半透明叠加**；每层后追加对应 **μ 脊线**（**Kronos** 实线加粗，其它虚线）。
5. **图例**：热力图与 μ 线 **legendgroup** 一致，便于单击隐藏 **同一模型** 的密度 + 脊线。

---

## 5. 计算过程链（Calculation Chain）

| 步骤 | 计算对象 | 输入 | 输出 |
| --- | --- | --- | --- |
| 1 | 测试窗逐步 OOS 矩 | `run_phase2` 内严格掩码 | `model_mu_test_ts`、`model_sigma_test_ts` |
| 2 | 实现序列 | `_test_returns` | `test_vals` 或 **None** |
| 3 | Plotly 对象 | `fig_p2_density_heatmap` | `go.Figure` → **`fig-p2-density`** |

---

## 6. 关键数据计算示例（重要数值）

以下数值与 **`Figure2.1-Res.md` §6** 共用同一 **`data.json`** 快照逻辑；**§6.1～§6.4** 中与 **影子择模** 直接相关的表与 **`Figure2.1-Res.md` §6.1～§6.4 同源**。**§6.5** 仅服务于 Fig2.2（测试窗张量）。

### 6.1 前提（当前仓库快照）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

### 6.2 全截面 `best_model_per_symbol`（快照）

| 标的    | 影子最优模型   |
| ----- | -------- |
| NVDA  | lightgbm |
| MSFT  | arima    |
| TSMC  | lightgbm |
| GOOGL | lightgbm |
| AAPL  | lightgbm |
| XLE   | arima    |
| GLD   | arima    |
| TLT   | lightgbm |
| SPY   | lightgbm |

### 6.3 示例标的 NVDA — 影子 holdout 一步 MSE 与 combined（与 `argmin combined` 一致）

**一步 MSE（影子尾段，四模型）：**

| 模型       | MSE                     |
| -------- | ----------------------- |
| naive    | 7.288432628021102×10⁻⁴  |
| kronos   | 1.0991749996076322×10⁻³ |
| arima    | 6.198924012450381×10⁻⁴  |
| lightgbm | 3.777983970682029×10⁻⁴  |

**归一化综合分（越小越优）：**

| 模型       | combined               |
| -------- | ---------------------- |
| naive    | 0.8315410480871027     |
| arima    | 0.3512274957669465     |
| lightgbm | **0.3086266433365771** |
| kronos   | 0.5077540684324975     |

→ **`best_model_per_symbol["NVDA"] = "lightgbm"`**（与 Fig2.1 像素列一致）。

### 6.4 全样本影子 MSE 均值（侧栏叙事辅助）

管线另输出跨标的平均影子 MSE（`**phase2.mse_naive`** …）。当前快照（同 §6.1）：**3.5476386523745484×10⁻⁴** / **2.4045472704104052×10⁻⁴** / **2.0083813547912×10⁻⁴** / **2.63723246389078×10⁻³**。**Fig2.2 热力图不直接读取该组标量**，但可与侧栏叙事对照。

### 6.5 Fig2.2 专属 — 测试窗 OOS 张量（结构核对）

从同一快照读取（**路径示例**）：

| 检查项 | 期望 |
| --- | --- |
| **`len(snap["phase2"]["test_forecast_dates"])`** | **T**（与任一有效模型的 **`len(model_mu_test_ts[m][NVDA])`** 相等） |
| **`snap["phase2"]["model_mu_test_ts"]["lightgbm"]["NVDA"]`** | 长度 **T** 的浮点列表（**脊线 y = 该序列**） |
| **`snap["phase2"]["model_sigma_test_ts"]["lightgbm"]["NVDA"]`** | 同长 **T**（热力图每列 Gaussian 的 σ） |
| **`_test_returns`** 对齐 | 若返回的第二项长度 **= T**，则出现粉色 **已实现收益** 轨；否则仅模型层 |

更换数据后：**勿手编** — 从 `**data.json**` 或 **`python research/figure21_res_key_example.py`**（若仓库提供）与 **`run_phase2`** 输出核对。

---

## 7. 源码锚点（可追溯）

```python
# dash_app/figures.py — fig_p2_density_heatmap（节选）
for m in models_valid:
    for t_idx in range(T):
        mu_t = mus_m[t_idx]
        sig_t = max(sigs_m[t_idx], 1e-8)
        density_grid[:, t_idx] = _gaussian_pdf(r_centers, mu_t, sig_t)
    fig.add_trace(go.Heatmap(x=dates, y=r_centers, z=z_norm, ...))
    fig.add_trace(go.Scatter(x=dates, y=mus_m, mode="lines", ...))  # μ 脊线
```

```python
# dash_app/render/main_p2.py — build_main_p2_components（节选）
fig_p2_dens = fig_p2_density_heatmap(
    state.test_forecast_dates,
    state.model_mu_test_ts or {},
    state.model_sigma_test_ts or {},
    val, state.tpl,
    test_vals=test_vals, figure_title="Figure2.2",
)
```

---

## 8. 一致性检验

1. **`len(test_forecast_dates) == len(model_mu_test_ts[m][sym]) == len(model_sigma_test_ts[m][sym])`** 对每个参与绘图的 **m** 成立。
2. 切换 **`p2-symbol`**：热力图与脊线 **symbol** 同步变更；与 **`fig-p2-best-pixels`** 高亮列 **同一标的**。
3. **真值线**：仅当 **`_test_returns`** 与日期轴 **逐日对齐** 时出现；否则界面提示缺数据 **不视为 Phase2 失败**。
4. **与 Fig2.1**：同一快照下 **`best_model_per_symbol`** 与像素矩阵 **一致**（见 **`Figure2.1-Res.md`** §8）。

---

## 9. 与 Fig3.1 / Phase3（简）

- **Fig3.1** 表格与 **Fig2.2** 共用 **`model_mu` / `model_sigma` / `model_mu_test_ts`** 等同源字段；差别在 **呈现形态**（表 vs 时空密度）。
- **Phase3** 组装 **`mu_daily`** 时使用 **`model_mu[best_model_per_symbol[s]][s]`**（训练窗边际），**Fig2.2** 展示的是 **测试窗逐日** **μ̂_{m,s,t}**，二者 **口径不同**，不得数值混写。

---

**占位**：`**{p2_selected_symbol}`** · **测试窗长度 T**
