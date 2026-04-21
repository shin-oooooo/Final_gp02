# Figure0.3 · Dynamic Beta（稳态 vs 断裂）（研究）

本文与 Phase 0 主列 Beta 条形图对齐：`figure_title="Figure0.3"`（`dash_app/app.py` 调用 `fig_beta_regime_compare`）。占位符 `**{benchmark}**` · `**{train_start}**` · `**{train_end}**` · `**{test_start}**` · `**{test_end}**` 可由 Caption/`_fmt_vars` 或快照解析注入。

---

## 1. 图形管线（端到端）

```text
data.json → load_bundle.close_universe
  → research.pipeline.run_pipeline（解析动态窗）→ research.phase0.run_phase0
  → phase0.beta_steady / phase0.beta_stress（Dict[str,float]）
  → Dash：fig_beta_regime_compare(beta_steady, beta_stress, symbols, benchmark, tpl)
  → Figure0.3（Plotly 分组柱状）
```

**命名说明**：`fig_beta_regime_compare` 第二参在源码中形参名为 `**beta_break`**；管线写入的快照字段为 `**beta_stress`**（`research/schemas.py` · `**Phase0Output**`）。`environment_report["beta_break"]` 与 `**beta_stress**` 指向同一套断裂窗估计（见 `**research/phase0.py**` · `**run_phase0**`）。

---

## 2. 数据溯源（Data Provenance）


| 项目            | 说明                                                                                                                                                      |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **原始数据**      | 日频价格宽表 `**close: pd.DataFrame`**（列 = 标的收盘价；索引为交易日）。加载路径：`**resolve_market_data_json_path()`** → 默认仓库根目录 `**data.json**`（或环境变量 `**AIE1902_DATA_JSON**`）。 |
| **收益序列**      | `**run_phase0`** 内 `**rets = close[cols].pct_change().dropna(how="all")`**，即各列 **简单日收益率**。                                                              |
| **基准**        | `**Phase0Input.benchmark`**（默认 `**SPY`**），须出现在 `**close**` 列中，否则 `**Dynamic_Beta_Tracker**` 返回空字典。                                                      |
| **稳态窗（训练）**   | 交易日 `**rets.index`** 落入 `**train.index`** 的行（`**train.index`** 由 `**Phase0Input**` 训练起止与 `**close**` 求交得到）。                                             |
| **断裂窗（测试锚定）** | 默认为测试窗内与 `**regime_break_start`**～`**regime_break_end`** 求交后的 `**rets**` 行；若命中行数 < 5，回退为 整条测试窗 内的 `**rets**` 行（见 `**research/phase0.py**`）。             |
| **采样频率**      | **交易日（Daily）**。                                                                                                                                         |


---

## 3. 方法论与数学对象

- **定义（单资产 i 相对基准 b）**：在选定时间掩码 T 上，取 `**rets`** 的子表 `**sub = rets.loc[mask].dropna(how="any")`**（要求当日 **所有列** 均有收益，否则整行剔除）。

\hat\beta_{i}=\frac{\widehat{\mathrm{Cov}}(r_b,r_i)}{\widehat{\mathrm{Var}}(r_b)}=\frac{\mathrm{cov}*{\mathrm{sample}}(r_b,r_i)}{\mathrm{var}*{\mathrm{sample}}(r_b)}

其中样本协方差 / 方差均采用 `**numpy`** / `**pandas`** 默认 **ddof = 1**（与 `**np.cov(..., ddof=1)`**、`**np.var(..., ddof=1)`** 一致），实现见 `**Dynamic_Beta_Tracker._beta_for_mask**`。

- **金融含义**：**\hat\beta_i** 刻画标的收益相对基准收益的 **线性敏感度**；稳态栏与断裂栏并列，用于观察 **地缘/测试锚定窗** 内敏感度相对训练期的 **偏移**（非买卖信号本身）。
- **图示**：蓝色柱 = `**beta_steady`**，橙色柱 = `**beta_stress`**；`**y=1**` 参考虚线（`**dash_app/figures.py**`）。

---

## 4. 计算过程链（Calculation Chain）


| 步骤  | 计算对象                                 | 输入                                                                        | 输出                                                  | 逻辑 / 函数                                    |
| --- | ------------------------------------ | ------------------------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------ |
| 1   | 列集合 `**cols**`                       | `**Phase0Input**` tech/hedge/safe + `**benchmark**` ∩ `**close.columns**` | 有序列名列表                                              | `**run_phase0**`                           |
| 2   | 全样本收益 `**rets**`                     | `**close[cols]**`                                                         | `**pct_change**` 后删全行缺失                             | `**run_phase0**`                           |
| 3   | 稳态掩码 `**steady_mask**`               | `**rets.index**` ∈ `**train.index**`                                      | `**pd.Series(bool)**`                               | `**run_phase0**`                           |
| 4   | 断裂掩码 `**break_mask**`                | 测试 ∩ `**regime_break_***`；不足 5 行则回退                                       | `**pd.Series(bool)**`                               | `**run_phase0**`                           |
| 5   | `**beta_steady**`, `**beta_stress**` | `**rets**` + 掩码                                                           | `**Dict[str,float]**`                               | `**Dynamic_Beta_Tracker.steady_vs_break**` |
| 6   | 快照顶层字段                               | 同上                                                                        | `**phase0.beta_steady**` / `**phase0.beta_stress**` | `**Phase0Output**`                         |
| 7   | 条形图高度                                | 两字典 + `**symbols**`（剔除基准）                                                 | `**go.Bar**` `**y**` 向量                             | `**fig_beta_regime_compare**`              |


---

## 5. 关键数据计算示例

本节数字与 `**python research/figure03_res_key_example.py**`（仓库根目录执行）打印的 JSON **同源**：更换 `**data.json`**、动态窗或 `**regime_break_*`** 后应重跑脚本并对照更新本节。

### 5.1 前提（当前仓库快照）


| 项目                                                                      | 取值                                                                                                          |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 行情文件                                                                    | `**data.json**`（`**bundle.meta["source"]**` = `akshare`，`**generated_at**` = `2026-04-16T11:18:47.221640Z`） |
| **基准 `benchmark`**                                                      | `**SPY**`                                                                                                   |
| 解析后训练窗                                                                  | `**2024-01-02**`～`**2026-01-30**`                                                                           |
| 解析后测试窗                                                                  | `**2026-02-02**`～`**2026-04-15**`                                                                           |
| `**regime_break_start**`～`**regime_break_end**`（`**Phase0Input` 默认工厂**） | `**2026-03-30`**～`**2026-04-20`**                                                                           |
| 掩码 `**break_mask.sum()**`（回退前原始命中行数）                                    | **12**                                                                                                      |


### 5.2 示例标的 NVDA（`**beta_steady` / `beta_stress`**）

1. **字典输出（与图中蓝/橙柱高度一致）**
  - `**beta_steady["NVDA"]`** = **2.159458126680862**  
  - `**beta_stress["NVDA"]`** = **1.3660776160597603**  
  - **\Delta\beta** = **−0.7933805106211018**
2. **手算核验（与 `Dynamic_Beta_Tracker` 同一公式）**
  - **稳态子表**（掩码后 `**dropna(how="any")`**）有效行数 **457**；  
   \widehat{\mathrm{Var}}(r_{SPY})= **5.85924852109553×10⁻⁵**，  
   \widehat{\mathrm{Cov}}(r_{SPY},r_{NVDA})= **1.2652801835122564×10⁻⁴**  
   → **\hat\beta=** **1.2652801835122564×10⁻⁴ / 5.85924852109553×10⁻⁵** = **2.159458126680862**（与字典一致）。  
  - **断裂子表**有效行数 **11**；  
  \widehat{\mathrm{Var}}(r_{SPY})= **1.0954990434886374×10⁻⁴**，  
  \widehat{\mathrm{Cov}}(r_{SPY},r_{NVDA})= **1.4965367217247054×10⁻⁴**  
  → **\hat\beta=** **1.3660776160597603**（与字典一致）。
3. **稳态窗前三行简单收益（`sub` 内，列 SPY / NVDA）**


| `date`     | `r_SPY`   | `r_NVDA`  |
| ---------- | --------- | --------- |
| 2024-01-02 | −0.005793 | −0.027388 |
| 2024-01-03 | −0.008456 | −0.012457 |
| 2024-01-04 | −0.003336 | 0.009034  |


1. **断裂窗前三行简单收益（`sub` 内）**


| `date`     | `r_SPY`   | `r_NVDA`  |
| ---------- | --------- | --------- |
| 2026-03-30 | −0.003343 | −0.014028 |
| 2026-03-31 | 0.029068  | 0.055882  |
| 2026-04-01 | 0.007535  | 0.007741  |


### 5.3 Phase2 影子择模前提（与 `Figure2.1-Res.md` §6 对齐）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

**择模全表与 NVDA 分解**见 **`Figure2.1-Res.md` §6.2～§6.4**。本图 **Beta 分 regime** 与择模 **无直接同一公式**，本节仅服务全库 **同一快照** 审计。

---

## 6. 源码锚点（可追溯）

**Beta 估计（核心）：**

```python
# research/phase0.py — Dynamic_Beta_Tracker._beta_for_mask
sub = self.returns.loc[mask].dropna(how="any")
yb = sub[self.benchmark].to_numpy(dtype=float)
vx = float(np.var(yb, ddof=1)) or 1e-12
# ...
out[c] = float(np.cov(yb, y, ddof=1)[0, 1] / vx)
```

**条形图装配（核心）：**

- `**dash_app/figures.py`** · `**fig_beta_regime_compare`**：`syms` 剔除 `**benchmark`**，`**b0`/`b1**` 由 `**dict.get(..., nan)**` 组装。  
- `**dash_app/app.py**`：`**fig_beta_regime_compare(dict(p0["beta_steady"]), dict(p0["beta_stress"]), ...)**`，`**figure_title="Figure0.3"**`。

---

## 7. 一致性检验

1. 读取快照 `**snap_json["phase0"]["beta_steady"]**`、`**snap_json["phase0"]["beta_stress"]**`。
2. 使用相同 `**close**`、相同 `**Phase0Input**`（含解析后的训练/测试窗与 `**regime_break_***`）重新执行 `**run_phase0**`，得到 `**beta_steady'**`、`**beta_stress'**`。
3. 对每个键 `**s**`（两字典并集）：若 `**snap**` 与 `**'**` 两侧均为有限浮点，则检验 **|\beta_s-\beta'_s| < \varepsilon**，取 **\varepsilon = 10^{-9}**。
4. 对 `**fig_beta_regime_compare`** 所用 `**symbols`** 顺序，核对 `**y`** 条形值是否等于 `**float(beta_*.get(s))**`（缺失为 **NaN**，图中无柱）。

---

## 8. 与下游叙事（简）

- **Figure0.2** 给出训练期线性相关结构；本图将同一 `**rets`** 切片上的基准敏感度 **分 regime 对照**，常与 `**orthogonality_check`**、侧栏 `**about_phase0_logic`** 一并阅读。  
- `**defense_level**` 较高时 Beta 区卡片标题可由 `**analysis_engine.p0_beta_card_title**` 切换（与投资视图 Copy 对齐）。

---

**占位**：`**{benchmark}`** · `**{train_start}`** · `**{train_end}`** · `**{test_start}`** · `**{test_end}**`