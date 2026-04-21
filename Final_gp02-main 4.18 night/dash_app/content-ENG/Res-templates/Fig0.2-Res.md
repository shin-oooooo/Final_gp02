# Figure0.2 · Correlation heat map during training period (research)

This article is aligned with the Phase 0 main column heatmap: `figure_title="Figure0.2"` (`dash_app/app.py` calls `fig_correlation_heatmap`). Placeholders `**{train_start}**` · `**{train_end}**` · `**{cross_threshold}**` · `**{n_symbols}**` can be injected by Caption/`_fmt_vars` or snapshot parsing.

---

## 1. Graphics pipeline (end-to-end)
```text
data.json (or close wide table of pipeline configuration)
  → research.pipeline.run_pipeline → research.phase0.run_phase0
→ environment_report["train_corr_preview"] (= nested dict, Pearson ρ)
  → Dash：fig_correlation_heatmap(train_corr_preview, symbols, ...)
  → Figure0.2（Plotly Heatmap）
```---

## 2. Data Provenance


| Project | Description |
| ------------ |-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Original data** | Daily frequency price wide table `**close: pd.DataFrame`** (column = underlying closing price/adjustment price; index is trading day). For typical loading paths, see project `**data.json`** and `ass1_core` → pipeline connection in README; **not** a unified `df_raw` variable name.                               |
| **Training time window** | `train.index` is obtained by intersecting the start and end days of `**Phase0Input`** and the available trading days; the parsed ISO string is often written into `**phase0.meta.resolved_windows`** (the start and end of training are consistent with `phase0.train_index`, see `research/pipeline.py` metadata filling logic). |
| **Sampling Frequency** | **Trading Day (Daily)**.                                                                                                                                                      |
| **Revenue definition used in matrix** | `**run_phase0`** In `rets = close[cols].pct_change().dropna(how="all")`, that is, each column **simple daily return** r_{t} = P_t/P_{t-1}-1 (**not** the logarithmic return used for ADF in Phase 1 diagnosis; the two uses are separated).                   |


---

## 3. Methodology and mathematical objects

- **Statistics**: **Pearson correlation matrix** of `train_rets` within the training window \boldsymbol{\rho}, \rho_{ij}=\mathrm{corr}(\mathbf r_i,\mathbf r_j). Implements the `**pandas.DataFrame.corr()`** default method (Pearson).  
- **Financial Implication**: \rho_{ij} depicts linear co-directional/reverse linkage; the diagonal is 1; |**ρ**| Large off-diagonal elements indicate strong asset synchronization during the training period, and nominal diversification may be limited (needs to be combined with `**beta_steady`/`beta_stress`** and inter-group orthogonality warning).  
- **Visual mapping**: **RdBu_r** color scale, `zmin=-1, zmax=1, zmid=0` (`dash_app/figures.py` `**fig_correlation_heatmap`**), corresponds to \rho value one-to-one, without random drawing layer.

---

## 4. Calculation Chain


| step | calculation object | input | output | logic/function |
| --- | ---------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 1 | Training window slice | `close`, `Phase0Input` training start and end | `train` | `AssetManager.slice_train` / `train_test_indices` |
| 2 | Full sample simple return | `close[cols]` | `rets` | `pct_change()`; `dropna(how="all")` |
| 3 | Training period income subtable | `rets` ∩ `train.index` | `train_rets` | Index intersection |
| 4 | Correlation matrix | `train_rets` (≥2 columns and not empty) | `corr` | `**train_rets.corr().to_dict()`** |
| 5 | Snapshot field | `corr` | `environment_report["train_corr_preview"]` (same reference as **train_low_correlation_graph**) | `**research/phase0.py`** · `**run_phase0`** |
| 6 | Heat map matrix **M**, star text | `train_corr_preview`, `symbols`, sorting within groups, `cross_threshold` | Plotly `**Heatmap(z=M)`** | `**dash_app/figures.py`** · `**fig_correlation_heatmap`** |


**UI parameters**: `cross_threshold` defaults to **0.3** (passed in by `app.py` callback); only controls whether **off-diagonal** cells append stars when |\rho|> threshold, **does not change** \rho itself.

---

## 5. Key data calculation example

The numbers in this section have the same source as the JSON printed by `**python research/figure02_res_key_example.py`** (executed in the warehouse root directory): replace `**data.json`** (or `**AIE1902_DATA_JSON**`), or `**resolve_dynamic_train_test_windows**` / `**Phase0Input**` After the default value is changed, you should rerun the script and update this section accordingly. (Heat map row and column sorting, missing keys, `nan` assembly and coordinate axis coloring are still responsible for `**fig_correlation_heatmap**`, `**_sort_syms_by_group`**, `**_sym_color`** in `**dash_app/figures.py**`.)

### 5.0 Phase2 shadow model selection premise (same origin as `Figure2.1-Res.md` §6.1)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

For complete **Model Selection Table / NVDA MSE / combined** see **`Figure2.1-Res.md` §6.2～§6.4**. Heatmap **does not rely** on `best_model_per_symbol`, this section **5.0** is only used for horizontal auditing.

### 5.1 Prerequisite (consistent with the pipeline Phase0 entrance)


| Project | Value (current warehouse snapshot) |
|-------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Market file | `**resolve_market_data_json_path()**` → `data.json` |
| `bundle.meta["source"]` | `akshare` |
| `bundle.meta["generated_at"]` | `2026-04-16T11:18:47.221640Z` |
| Dynamic analysis training window | `resolve_dynamic_train_test_windows(...)` is consistent with the start and end dates of `**Phase0Input**` written before calling `**run_phase0**` with `**research.pipeline.run_pipeline**` |
| Post-parsing training window (ISO day) | `**2024-01-02**`~`**2026-01-30**` |
| Test window (printed together with the script, not used for heat map) | `**2026-02-02**`～`**2026-04-15**` |


### 5.2 Object variables (Python)

- `**close**`: `load_bundle(...).close_universe.sort_index()`
- `**rets**`: `daily_returns(close[syms]).dropna(how="all")` (same as `**close[cols].pct_change()**` in `**run_phase0**` for simple daily returns)
- `**train_rets**`: `rets.loc[(rets.index >= train_start) & (rets.index <= train_end)]` → Number of rows **521**
- `**corr`**: `run_phase0(close, phase0_input_resolved)["environment_report"]["train_corr_preview"]`

### 5.3 Off-diagonal example element ρ (NVDA × MSFT)

1. **Correlation coefficient in dictionary** (consistent with `**train_rets.corr()`**):
  `**corr["NVDA"]["MSFT"]`** = **0.5433401994876633**
2. **Paired valid samples**: There are **503** training days with no missing items in both columns (recorded as vectors **x**, **y**, that is, the complete rows of `**train_rets`** on NVDA and MSFT).
3. **Sample covariance and sample standard deviation** (n=503, divisor n-1):
  \hat\sigma_{xy}= **0.00019320962078640073**
   \hat\sigma_x= **0.027796760463003504**, \hat\sigma_y= **0.012792715029779663**
   \hat\rho_{xy}=\hat\sigma_{xy}/(\hat\sigma_x\hat\sigma_y)= **0.5433401994876643** (Same as `**corr["NVDA"]["MSFT"]`** in machine precision)
4. **Pairing returns for the first three valid trading days** (first few rows on the intersection index):


| `date` | `train_rets["NVDA"]` | `train_rets["MSFT"]` |
| ---------- | ------------------ | ------------------ |
| 2024-01-02 | −0.02738784 | −0.01402414 |
| 2024-01-03 | −0.01245737 | −0.00074282 |
| 2024-01-04 | 0.00903443 | −0.00732359 |


### 5.4 Heat map cell text (star)

- `**cross_threshold`** = **0.3** (consistent with `**dash_app/app.py`** passing in `**fig_correlation_heatmap`**).  
- **NVDA × MSFT**: **|ρ| > 0.3** → text `**0.54 *`** (`**f"{v:.2f}"`** + `**tag = " *"`**, see `**dash_app/figures.py`**).

---

## 6. Source code anchor (traceable)

**Correlation Matrix Generation (Core):**
```python
# research/phase0.py — within run_phase0
train_rets = rets.loc[rets.index.intersection(train.index)]
if not train_rets.empty and len(train_rets.columns) > 1:
    corr = train_rets.corr().to_dict()
else:
    corr = {}
```**Heatmap assembly (core):**

- `**dash_app/figures.py`**: `fig_correlation_heatmap(...)` — Constructed from nested dict **M**, **go.Heatmap**, axis labeling and star text rules.  
- `**dash_app/app.py`**: Take `**train_corr_preview**` from `**p0["environment_report"]`** and pass in `**fig_correlation_heatmap(..., cross_threshold=0.3, figure_title="Figure0.2")**`.

---

## 7. Consistency check

1. Read the current snapshot `**snap_json["phase0"]["environment_report"]["train_corr_preview"]**` (nested dict).
2. Use the same `**close**`, training window intersection and column set as `**run_phase0**` to get `**train_rets**`, and calculate `**C = train_rets.corr()**` (`pandas` defaults to Pearson).
3. Assemble the snapshot dict into a matrix `**M_snap**` according to the object order of `**fig_correlation_heatmap**` (including `**_sort_syms_by_group**`), and rearrange the `**C**` into a same-order matrix `**M_recalc**`.
4. Element-by-element test for all finite elements of the two matrices **|M_{\mathrm{snap},ij}-M_{\mathrm{recalc},ij}| < \varepsilon**, take **\varepsilon = 10^{-9}**.
5. For non-diagonal element **i\neq j**: If **|\rho_{ij}| > \texttt{crossthreshold}**, then the corresponding cell text of `**fig_correlation_heatmap`** must contain the character `***`**; otherwise it must not contain `*****`.

---

## 8. Orthogonality early warning and downstream narrative (simplified)

- **Inter-group correlation pre-check** (technology vs risk aversion maximum |ρ|) see `**AssetManager.pre_check_correlation`**, the result is written into `**environment_report["orthogonality_check"]`**; About area `**analysis_engine.about_phase0_logic**` can switch the conclusion copy by the card next to the heat map.  
- **Structural Entropy FigX.2** and so on use the **Covariance/Eigenspectrum** perspective in subsequent phases; this figure is the **original Pearson correlation panel**, complementary to it rather than repeating the same formula.

---

**Placeholder**: `**{train_start}`** · `**{train_end}`** · `**{cross_threshold}`** · `**{n_symbols}`**