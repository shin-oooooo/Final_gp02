# Figure0.2 · 训练期相关性热力图（研究）

本文与 Phase 0 主列热力图对齐：`figure_title="Figure0.2"`（`dash_app/app.py` 调用 `fig_correlation_heatmap`）。占位符 `**—**` · `**—**` · `**{cross_threshold}**` · `**{n_symbols}**` 可由 Caption/`_fmt_vars` 或快照解析注入。

---

## 1. 图形管线（端到端）

```text
data.json（或管线配置的 close 宽表）
  → research.pipeline.run_pipeline → research.phase0.run_phase0
  → environment_report["train_corr_preview"]  (= 嵌套 dict，Pearson ρ)
  → Dash：fig_correlation_heatmap(train_corr_preview, symbols, ...)
  → Figure0.2（Plotly Heatmap）
```

---

## 2. 数据溯源（Data Provenance）


| 项目           | 说明                                                                                                                                                                   |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **原始数据**     | 日频价格宽表 `**close: pd.DataFrame`**（列 = 标的收盘价/调整价；索引为交易日）。典型加载路径见项目 `**data.json`** 与 README 中 `ass1_core` → 管线衔接；**并非**统一的 `df_raw` 变量名。                               |
| **训练时间窗**    | 由 `**Phase0Input`** 的起止日与可用交易日求交得到 `train.index`；解析后的 ISO 字符串常写入 `**phase0.meta.resolved_windows`**（训练起止与 `phase0.train_index` 一致，见 `research/pipeline.py` 元数据填充逻辑）。 |
| **采样频率**     | **交易日（Daily）**。                                                                                                                                                      |
| **矩阵所用收益定义** | `**run_phase0`** 中 `rets = close[cols].pct_change().dropna(how="all")`，即各列 **简单日收益率** r_{t} = P_t/P_{t-1}-1（**非** Phase 1 诊断里对 ADF 用的对数收益；二者用途分离）。                   |


---

## 3. 方法论与数学对象

- **统计量**：训练窗内 `train_rets` 的 **Pearson 相关矩阵** \boldsymbol{\rho}，\rho_{ij}=\mathrm{corr}(\mathbf r_i,\mathbf r_j)。实现对 `**pandas.DataFrame.corr()`** 默认方法（Pearson）。  
- **金融含义**：\rho_{ij} 刻画线性同向/反向联动；对角线为 1；|**ρ**| 大的非对角元提示训练期内资产同步性强，名义分散化可能受限（需结合 `**beta_steady`/`beta_stress`** 与组间正交性预警）。  
- **可视化映射**：**RdBu_r** 色标，`zmin=-1, zmax=1, zmid=0`（`dash_app/figures.py` `**fig_correlation_heatmap`**），与 \rho 数值一一对应，无随机绘制层。

---

## 4. 计算过程链（Calculation Chain）


| 步骤  | 计算对象             | 输入                                                    | 输出                                                                                | 逻辑 / 函数                                                   |
| --- | ---------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------- |
| 1   | 训练窗切片            | `close`、`Phase0Input` 训练起止                            | `train`                                                                           | `AssetManager.slice_train` / `train_test_indices`         |
| 2   | 全样本简单收益          | `close[cols]`                                         | `rets`                                                                            | `pct_change()`；`dropna(how="all")`                        |
| 3   | 训练期收益子表          | `rets` ∩ `train.index`                                | `train_rets`                                                                      | 索引交集                                                      |
| 4   | 相关矩阵             | `train_rets`（≥2 列且非空）                                 | `corr`                                                                            | `**train_rets.corr().to_dict()`**                         |
| 5   | 快照字段             | `corr`                                                | `environment_report["train_corr_preview"]`（及 **train_low_correlation_graph** 同引用） | `**research/phase0.py`** · `**run_phase0`**               |
| 6   | 热力图矩阵 **M**、星标文本 | `train_corr_preview`、`symbols`、组内排序、`cross_threshold` | Plotly `**Heatmap(z=M)`**                                                         | `**dash_app/figures.py`** · `**fig_correlation_heatmap`** |


**UI 参数**：`cross_threshold` 默认 **0.3**（`app.py` 回调传入）；仅控制 **非对角** 单元格在 |\rho|> 阈值时是否追加星标，**不改变** \rho 本身。

---

## 5. 关键数据计算示例

本节数字与 `**python research/figure02_res_key_example.py`**（仓库根目录执行）打印的 JSON 同源：更换 `**data.json`**（或 `**AIE1902_DATA_JSON**`）、或 `**resolve_dynamic_train_test_windows**` / `**Phase0Input**` 默认值变更后，应重跑脚本并对照更新本节。（热力图行列排序、缺失键、`nan` 装配与坐标轴着色仍由 `**dash_app/figures.py**` 中 `**fig_correlation_heatmap**`、`**_sort_syms_by_group`**、`**_sym_color`** 负责。）

### 5.0 Phase2 影子择模前提（与 `Figure2.1-Res.md` §6.1 同源）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

完整 **择模表 / NVDA MSE / combined** 见 **`Figure2.1-Res.md` §6.2～§6.4**。热力图 **不依赖** `best_model_per_symbol`，本节 **5.0** 仅用于横向审计。

### 5.1 前提（与管线 Phase0 入口一致）


| 项目                            | 取值（当前仓库快照）                                                                                                                         |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 行情文件                          | `**resolve_market_data_json_path()**` → `data.json`                                                                                |
| `bundle.meta["source"]`       | `akshare`                                                                                                                          |
| `bundle.meta["generated_at"]` | `2026-04-16T11:18:47.221640Z`                                                                                                      |
| 动态解析训练窗                       | `resolve_dynamic_train_test_windows(...)` 与 `**research.pipeline.run_pipeline**` 在调用 `**run_phase0**` 前写入 `**Phase0Input**` 的起止日一致 |
| 解析后训练窗（ISO 日）                 | `**2024-01-02**`～`**2026-01-30**`                                                                                                  |
| 测试窗（同脚本一并打印，热力图不用）            | `**2026-02-02**`～`**2026-04-15**`                                                                                                  |


### 5.2 对象变量（Python）

- `**close**`：`load_bundle(...).close_universe.sort_index()`  
- `**rets**`：`daily_returns(close[syms]).dropna(how="all")`（与 `**run_phase0**` 内 `**close[cols].pct_change()**` 同为简单日收益）  
- `**train_rets**`：`rets.loc[(rets.index >= train_start) & (rets.index <= train_end)]` → 行数 **521**  
- `**corr`**：`run_phase0(close, phase0_input_resolved)["environment_report"]["train_corr_preview"]`

### 5.3 非对角示例元 ρ（NVDA × MSFT）

1. **字典中的相关系数**（与 `**train_rets.corr()`** 一致）：
  `**corr["NVDA"]["MSFT"]`** = **0.5433401994876633**
2. **配对有效样本**：两列均无缺失的训练日共有 **503** 条（记为向量 **x**、**y**，即 `**train_rets`** 在 NVDA、MSFT 上的完备行）。
3. **样本协方差与样本标准差**（n=503，除数 n-1）：
  \hat\sigma_{xy}= **0.00019320962078640073**  
   \hat\sigma_x= **0.027796760463003504**，\hat\sigma_y= **0.012792715029779663**  
   \hat\rho_{xy}=\hat\sigma_{xy}/(\hat\sigma_x\hat\sigma_y)= **0.5433401994876643**（与 `**corr["NVDA"]["MSFT"]`** 在机器精度上一致）
4. **前三个有效交易日的配对收益**（交集索引上前几行）：


| `date`     | `train_rets["NVDA"]` | `train_rets["MSFT"]` |
| ---------- | -------------------- | -------------------- |
| 2024-01-02 | −0.02738784          | −0.01402414          |
| 2024-01-03 | −0.01245737          | −0.00074282          |
| 2024-01-04 | 0.00903443           | −0.00732359          |


### 5.4 热力图单元格文本（星标）

- `**cross_threshold`** = **0.3**（与 `**dash_app/app.py`** 传入 `**fig_correlation_heatmap`** 一致）。  
- **NVDA × MSFT**：**|ρ| > 0.3** → 文本 `**0.54 *`**（`**f"{v:.2f}"`** + `**tag = " *"`**，见 `**dash_app/figures.py`**）。

---

## 6. 源码锚点（可追溯）

**相关矩阵生成（核心）：**

```python
# research/phase0.py — run_phase0 内
train_rets = rets.loc[rets.index.intersection(train.index)]
if not train_rets.empty and len(train_rets.columns) > 1:
    corr = train_rets.corr().to_dict()
else:
    corr = {}
```

**热力图装配（核心）：**

- `**dash_app/figures.py`**：`fig_correlation_heatmap(...)` — 由嵌套 dict 构建 **M**、**go.Heatmap**、轴标注与星标文本规则。  
- `**dash_app/app.py`**：从 `**p0["environment_report"]`** 取 `**train_corr_preview**`，传入 `**fig_correlation_heatmap(..., cross_threshold=0.3, figure_title="Figure0.2")**`。

---

## 7. 一致性检验

1. 读取当次快照 `**snap_json["phase0"]["environment_report"]["train_corr_preview"]**`（嵌套 dict）。
2. 使用与 `**run_phase0**` 相同的 `**close**`、训练窗交集与列集合，得到 `**train_rets**`，计算 `**C = train_rets.corr()**`（`pandas` 默认 Pearson）。
3. 按 `**fig_correlation_heatmap**` 的标的顺序（含 `**_sort_syms_by_group**`）将快照 dict 装配为矩阵 `**M_snap**`，将 `**C**` 重排为同序矩阵 `**M_recalc**`。
4. 对两矩阵所有有限元素逐元检验 **|M_{\mathrm{snap},ij}-M_{\mathrm{recalc},ij}| < \varepsilon**，取 **\varepsilon = 10^{-9}**。
5. 对非对角元 **i\neq j**：若 **|\rho_{ij}| > \texttt{crossthreshold}**，则 `**fig_correlation_heatmap`** 对应单元格文本须含字符 `***`**；否则不得含 `*****`。

---

## 8. 与正交性预警、下游叙事（简）

- **组间相关性预检**（科技 vs 避险最大 |ρ|）见 `**AssetManager.pre_check_correlation`**，结果写入 `**environment_report["orthogonality_check"]`**；About 区 `**analysis_engine.about_phase0_logic**` 可在热力图旁卡片切换结论文案。  
- **结构熵 FigX.2** 等在后续 Phase 使用 **协方差/特征谱** 视角；本图是 **原始 Pearson 相关面板**，与之互补而非重复同一公式。

---

**占位**：`**—`** · `**—`** · `**{cross_threshold}`** · `**{n_symbols}`**