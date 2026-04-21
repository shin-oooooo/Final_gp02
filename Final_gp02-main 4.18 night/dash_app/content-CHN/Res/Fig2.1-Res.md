# Figure2.1 · 影子择模像素矩阵（研究 · B 类）

**对象类型（B）**：离散展示 **Naive / ARIMA / LightGBM / Kronos** 在训练窗尾部 **影子 holdout** 上的相对优劣；每个标的对应 **综合分最小** 的模型标签。**影子测试的定义、目的、时间切分、MSE+JSD 双目标及 \alpha 含义见 §2**（本节为全文方法论主轴）。像素图 **不绘制连续收益**，仅映射 `**best_model_per_symbol`** → 四行离散色块。

本文与 Phase 2 面板 `**fig-p2-best-pixels`**（侧栏 `**Figure2.1`** 单元，`dash_app/ui/ids.py` · `**FIG.F2_1**`）对齐。当前回调中 `**fig_p2_best_model_pixels**` 的 `**figure_title**` 参数在 `**dash_app/app.py**` / `**callbacks/p2_symbol.py**` 传入 `**"Figure3.1"**`，与外层 `**Figure2.1**` 标签并存；正文以 **侧栏展示的 Figure2.1** 为准。

占位符：`**{n_symbols}`** · `**{p2_selected_symbol}`** · 可与快照中 `**phase2.best_model_per_symbol`** 对齐注入。

---

## 1. 图形管线（端到端）

```text
data.json → daily_returns(close[universe])
  → run_phase2(...): 尾部 holdout → best_model_per_symbol（每标的一个模型键）
  → Dash：fig_p2_best_model_pixels(best_model_per_symbol, symbols, selected_symbol, ...)
  → 4×N 像素矩阵（列为标的，行为模型）
```

---

## 2. 影子测试方法论（核心）

本节说明 **Fig2.1 唯一依赖的择模逻辑**：**影子 holdout（Shadow holdout）**——在 **训练窗内部** 人为划出一段 **伪样本外** 尾窗，仅用 **已实现收益作标签**，比较四模型的一步预测质量，再为 **每个标的** 独立选出默认模型键。像素矩阵只是该字典的可视化，**方法论重心在影子实验设计而非绘图本身**。

### 2.1 目的：择模容器 vs 严格样本外


| 维度       | 影子测试（本图来源）                                             | Phase 2 主循环中的测试窗预测（服务 Fig2.2 / 可信度等）           |
| -------- | ------------------------------------------------------ | ---------------------------------------------- |
| **时间范围** | 仅 **训练窗** 末端 `**n_tail_eff`** 日                        | **测试窗** 每个交易日 t                                |
| **信息集**  | 对每一步预测使用截至该步之前的历史（见 `**_tail_holdout_scores`** 内各模型定义） | **严格**：仅用 **I_{t-1}**（`**returns.index < t`**） |
| **标签**   | holdout 段上的 **真实下一日收益**（训练样本内）                         | 测试窗 **真实收益**                                   |
| **用途**   | **模型间相对比较** → `**best_model_per_symbol[sym]`**（离散标签）   | 密度、JSD、DM、覆盖率等 **管道输出**                        |


二者 **不得混读**：影子 **不消耗测试窗标签**，从而避免「用同一测试集既择模又报告 OOS 表现」的乐观偏差；测试窗专门留给 **Fig2.2** 及可信度管线。

### 2.2 Holdout 构造（训练尾段切片）

对每个标的的收益序列 `**s`**（来自行完备的 `**train`**）：

1. **有效尾长** `**n_tail_eff`** = `**min(policy.shadow_holdout_days, max(5, n_train_pts − 30))`**（见 `**research/phase2.py`**），侧栏 `**shadow_holdout_days**` 默认 **40**、夹紧 **[5,120]**。
2. **拟合段** `**train_s = s.iloc[:-n_tail_eff]`**：ARIMA / LightGBM 等在该段上估计或滚动；长度不足时 `**_tail_holdout_scores`** 直接返回空图并回退 `**naive**`。
3. **评估段** `**val_s = s.iloc[-(n_tail_eff+1):]`**：在其上构造 `**n_tail_eff`** 个 **一步预测 vs 下一日实现** 的对照，计算各模型的 **影子 MSE**。
4. **Kronos**：在权重就绪时必须提供与 `**s`** **日历对齐** 的 `**close`** 列（`**close_sym`**），否则抛出或走统计代理（见源码分支）。

### 2.3 双目标综合：点预测（MSE）与密度对齐（JSD）

影子阶段不仅看点误差，还把 **模型隐含 Gaussian** 与 **holdout 实现** 的 **Jensen–Shannon 距离**纳入同一标尺：

- **MSE**：下一期收益 **点预测** 是否贴近实现（各模型预测定义不同，见 `**_tail_holdout_scores`**）。  
- **JSD**：在 holdout 上构造经验矩 **(\mu_{\mathrm{emp}},\sigma_{\mathrm{emp}})**，与各模型矩算 **对称 JSD**（`**_js_divergence`**），反映 **概率形态** 是否离谱。

综合分  
**\mathrm{combined}_m=\alpha\cdot \frac{\mathrm{MSE}_m}{\max_j \mathrm{MSE}_j}+(1-\alpha)\cdot \frac{\mathrm{JSD}_m}{\max_j \mathrm{JSD}_j}**，  
其中 **\alpha=** `**DefensePolicyConfig.alpha_model_select`**（默认 0.5）：**\alpha\to 1** 更偏 **点预测排位**；**\alpha\to 0** 更偏 **分布贴合**。这是在工程上把「点误差」与「密度偏差」放进 **同一可比标尺** 的显式旋钮。

### 2.4 择优规则与像素语义

- **每标的独立**：**\arg\min_m \mathrm{combined}_m** → `**best_model_per_symbol[sym]`**；跨标的 平均影子 MSE（`**phase2.mse_*`**）仅作侧栏叙事，**不参与**单列点亮。  
- **Fig2.1**：列 = 标的，行 = `**_P2_MODELS`** 固定顺序；**亮格 = 该列最优模型**，竖虚线标示当前下拉标的（若适用）。

### 2.5 可调参数（与侧栏一致）


| 参数                        | 作用                            |
| ------------------------- | ----------------------------- |
| `**shadow_holdout_days`** | 尾窗越长 → 估计越稳、算力越高；越短 → 方差越大、越快 |
| `**alpha_model_select`**  | 纯 MSE vs 纯 JSD 之间的连续权衡        |


---

## 3. 数据溯源（Data Provenance）


| 项目                | 说明                                                                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **行情**            | `**resolve_market_data_json_path()`** · `**load_bundle`** · `**close_universe`**                                                            |
| **收益**            | `**daily_returns`**（与 `**run_phase2`** 输入 `**returns**` 一致）：简单日收益                                                                           |
| **训练子样本 `train`** | `**returns.loc[train_mask].dropna(how="any")**`：**任一方缺收益的交易日整行剔除**（与 `**research/phase2.py`** `**run_phase2`** 一致）                          |
| **影子长度**          | `**DefensePolicyConfig.shadow_holdout_days`**（默认 40，夹紧 [5,120]）；有效尾部 `**n_tail_eff = min(shadow_holdout_days, max(5, n_train_pts − 30))`**  |
| **模型键空间**         | `**research/phase2.py`** · `**_MODELS`** = `**["naive","arima","lightgbm","kronos"]`**（与 `**dash_app/figures.py`** · `**_P2_MODELS**` 顺序一致） |


---

## 4. 评分分量与公式速览（与 §2 对应）

**Holdout 切分、与测试窗 OOS 的分工、\alpha 的统计含义以 §2 为准**；下表为 **实现级** 变量对照，便于与 `**_tail_holdout_scores`** 对照阅读。


| 分量                  | 含义                                                                                                                                                |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `**mse_scores[m]`** | 模型 `**m`** 的影子 **MSE**（Naive 用当日收益预测次日；ARIMA/LGB 见源码；Kronos 在权重就绪时对 `**close`** 序列调用 `**kronos_one_step_mu_from_close`**，否则 **5 日均值代理**）          |
| `**jsd_scores[m]`** | 各模型 **Gaussian** 矩 vs **持有期 empirical** 收益的 **JSD**（经 `**_js_divergence`**）                                                                       |
| **综合分（越小越好）**       | `**combined[m] = α · norm(MSE_m) + (1−α) · norm(JSD_m)`**，其中 `**norm(x_m)=x_m / max_j x_j`** 跨四模型，`**α = policy.alpha_model_select**`（默认 **0.5**） |


**优胜规则**：`**best_model_per_symbol[sym] = argmin_m combined[m]`**；若 `**combined_map`** 为空则 `**"naive"**`。

---

## 5. 计算过程链（Calculation Chain）


| 步骤  | 计算对象                         | 输入                                            | 输出                                                  | 逻辑                                                    |
| --- | ---------------------------- | --------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------- |
| 1   | `**train**`                  | `**returns**`、`**train_mask**`                | 行完备训练表                                              | `**dropna(how="any")**`                               |
| 2   | `**mse_map`/`combined_map**` | `**train[sym]**`、`**n_tail_eff**`、`**close**` | 每模型标量                                               | `**research/phase2.py**` · `**_tail_holdout_scores**` |
| 3   | `**best_model_per_symbol**`  | 各 `**sym**` 的 `**combined**`                  | `**Dict[str, str]**`（标的→模型键）                        | `**run_phase2**` 聚合循环                                 |
| 4   | `**phase2**` 快照字段            | Phase2Output                                  | `**PipelineSnapshot.phase2.best_model_per_symbol**` | `**run_pipeline` / API**                              |
| 5   | 像素坐标                         | `**best_model_per_symbol`**、`**symbols`**     | `**go.Scatter**` 亮色方块                               | `**fig_p2_best_model_pixels**`                        |


---

## 6. 关键数据计算示例（重要数值）

以下数值是 **§2 影子方法论** 在 `**data.json`** 当前快照下的 **一次实例化**（与 `**python research/figure21_res_key_example.py`** 打印的 JSON **同源**；脚本仅跑到 **Phase 2**，约 **90s**，含 Kronos）。更换 `**data.json`**、`**shadow_holdout_days`**、`**alpha_model_select**` 或 Kronos 环境后须重跑并对照更新。

### 6.1 前提（当前仓库快照）


| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| `**data.json` meta**                                 | `**source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | `**2024-01-02`**～`**2026-01-30`**                                           |
| `**shadow_holdout_days**`（cfg / 生效 `**n_tail_eff**`） | **40** / **40**                                                             |
| `**alpha_model_select`**                             | **0.5**                                                                     |


### 6.2 全截面 `**best_model_per_symbol`**（快照）


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


### 6.3 示例标的 NVDA（与 `**argmin combined`** 一致）

**一步 MSE（影子尾段，四模型）：**


| 模型       | MSE                     |
| -------- | ----------------------- |
| naive    | 7.288432628021102×10⁻⁴  |
| kronos   | 1.0991749996076322×10⁻³ |
| arima    | 6.198924012450381×10⁻⁴  |
| lightgbm | 3.777983970682029×10⁻⁴  |


**归一化综合分（越小越优；实现先取各模型 max(MSE)、max(JSD) 再线性组合）：**


| 模型       | combined               |
| -------- | ---------------------- |
| naive    | 0.8315410480871027     |
| arima    | 0.3512274957669465     |
| lightgbm | **0.3086266433365771** |
| kronos   | 0.5077540684324975     |


→ `**best_model_per_symbol["NVDA"] = "lightgbm"`**；像素矩阵在 **NVDA** 列点亮 **LightGBM** 行（行序自上而下对应 Naive→ARIMA→LightGBM→Kronos）。

### 6.4 全样本影子 MSE 均值（侧栏叙事辅助，非单格点亮依据）

管线另输出跨标的平均影子 MSE（`**phase2.mse_naive`** …），与单标的 **综合分** 无直接一一关系。当前快照（同 **§6.1** 脚本）：**3.5476386523745484×10⁻⁴** / **2.4045472704104052×10⁻⁴** / **2.0083813547912×10⁻⁴** / **2.63723246389078×10⁻³**。**像素仍只由每标的 `argmin combined` 决定。**

---

## 7. 源码锚点（可追溯）

**综合分与择优：**

```python
# research/phase2.py — _tail_holdout_scores（节选）
max_mse = max(mse_scores.values()) or 1.0
max_jsd = max(jsd_scores.values()) or 1.0
alpha = float(np.clip(alpha_mse, 0.0, 1.0))
combined = {
    m: alpha * (mse_scores.get(m, max_mse) / max_mse)
    + (1.0 - alpha) * (jsd_scores.get(m, max_jsd) / max_jsd)
    for m in _MODELS
}
```

**聚合进 Phase2：**

```python
# research/phase2.py — run_phase2 内（节选）
best_sym = min(combined_map, key=combined_map.get)
best_model_per_symbol[sym] = best_sym
```

**像素绘制：**

```python
# dash_app/figures.py — fig_p2_best_model_pixels（节选）
row_of = {m: i for i, m in enumerate(_P2_MODELS)}
bm = str(best_model_per_symbol.get(sym) or "naive")
if bm not in row_of:
    bm = "naive"
mi = row_of[bm]
```

---

## 8. 一致性检验

1. 读取快照 `**snap_json["phase2"]["best_model_per_symbol"]**`。
2. 使用同一 `**returns**`、`**train_mask**` / `**test_mask**`、`**DefensePolicyConfig**`、`**close**`，重新执行 `**run_phase2**`（或运行 `**research/figure21_res_key_example.py**` 内 `**_run_p2_only**` 路径）。
3. 对每个标的 `**s**`：**字符串标签须完全一致**。
4. （可选）对任一 `**s`** 调用 `**_tail_holdout_scores`**，核对 `**argmin(combined)`** 与快照一致。

---

## 9. 与 Phase 3 / Fig2.2（简）

- `**Phase3Input**` 组装边际 `**μ**` 时优先取 `**model_mu[best_model_per_symbol[s]][s]**`（见 `**research/pipeline.py**` 近 `**hist_mu`/`mu**` 段）。  
- **Fig2.2** 密度图在同一 `**symbols`** 下拉下展示 **各模型** 全测试窗分布；本图 **仅标记择模胜者**，二者共用 `**phase2`** 快照。

---

**占位**：`**{n_symbols}`** · `**{p2_selected_symbol}`**