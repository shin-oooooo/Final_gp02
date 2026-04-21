# Figure0.3 · Dynamic Beta (Steady State vs Fracture) (Research)

This article is aligned with the Phase 0 main column beta bar chart: `figure_title="Figure0.3"` (`dash_app/app.py` calls `fig_beta_regime_compare`). Placeholders `**{benchmark}**` · `**{train_start}**` · `**{train_end}**` · `**{test_start}**` · `**{test_end}**` can be injected by Caption/`_fmt_vars` or snapshot parsing.

---

## 1. Graphics pipeline (end-to-end)
```text
data.json → load_bundle.close_universe
→ research.pipeline.run_pipeline (parsing dynamic window) → research.phase0.run_phase0
  → phase0.beta_steady / phase0.beta_stress（Dict[str,float]）
  → Dash：fig_beta_regime_compare(beta_steady, beta_stress, symbols, benchmark, tpl)
→ Figure0.3 (Plotly grouped column)
```**Naming description**: The second parameter of `fig_beta_regime_compare` is named `**beta_break`** in the source code; the snapshot field written by the pipeline is `**beta_stress`** (`research/schemas.py` · `**Phase0Output**`). `environment_report["beta_break"]` points to the same set of break window estimates as `**beta_stress**` (see `**research/phase0.py**` · `**run_phase0**`).

---

## 2. Data Provenance


| Project | Description |
|------------- |------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Original data** | Daily frequency price wide table `**close: pd.DataFrame`** (column = underlying closing price; index is the trading day). Loading path: `**resolve_market_data_json_path()`** → Default warehouse root directory `**data.json**` (or environment variable `**AIE1902_DATA_JSON**`). |
| **Return sequence** | `**rets = close[cols].pct_change().dropna(how="all")`** within `**run_phase0`**, that is, each column **simple daily return**.                                                              |
| **Benchmark** | `**Phase0Input.benchmark`** (default `**SPY`**), must appear in the `**close**` column, otherwise `**Dynamic_Beta_Tracker**` returns an empty dictionary.                                                      |
| **Steady-state window (training)** | The trading day `**rets.index`** falls into the row of `**train.index`** (`**train.index`** is obtained by intersecting the start and end of training with `**Phase0Input**` and `**close**`).                                             |
| **Break window (test anchor)** | Defaults to the `**rets**` rows in the test window after intersecting with `**regime_break_start`**~`**regime_break_end`**; if the number of hit rows < 5, the fallback is to the `**rets**` rows in the entire test window (see `**research/phase0.py**`).             |
| **Sampling Frequency** | **Trading Day (Daily)**.                                                                                                                                         |


---

## 3. Methodology and mathematical objects

- **Definition (single asset i relative to benchmark b)**: On the selected time mask T, take the sub-table of `**rets`** `**sub = rets.loc[mask].dropna(how="any")`** (requires that **all columns** have returns on the day, otherwise the entire row is deleted).

\hat\beta_{i}=\frac{\widehat{\mathrm{Cov}}(r_b,r_i)}{\widehat{\mathrm{Var}}(r_ b)}=\frac{\mathrm{cov}*{\mathrm{sample}}(r_b,r_i)}{\mathrm{var}*{\mathrm{sample}}(r_b)}

The sample covariance/variance uses `**numpy`** / `**pandas`** with the default **ddof = 1** (consistent with `**np.cov(..., ddof=1)`**, `**np.var(..., ddof=1)`**). For implementation, see `**Dynamic_Beta_Tracker._beta_for_mask**`.

- **Financial meaning**: **\hat\beta_i** depicts the **linear sensitivity** of the underlying return relative to the benchmark return; the steady-state column is juxtaposed with the break column, used to observe the **shift** of the **geo/test anchoring window** internal sensitivity relative to the training period (not the buy and sell signal itself).
- **Illustration**: blue column = `**beta_steady`**, orange column = `**beta_stress`**; `**y=1**` refer to the dashed line (`**dash_app/figures.py**`).

---

## 4. Calculation Chain


| step | calculation object | input | output | logic/function |
| --- | ----------------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------- | -------------------------------------------------- |
| 1 | Column set `**cols**` | `**Phase0Input**` tech/hedge/safe + `**benchmark**` ∩ `**close.columns**` | List of sequence names | `**run_phase0**` |
| 2 | Full sample return `**rets**` | `**close[cols]**` | `**pct_change**` after deleting all rows missing | `**run_phase0**` |
| 3 | Steady state mask `**steady_mask**` | `**rets.index**` ∈ `**train.index**` | `**pd.Series(bool)**` | `**run_phase0**` |
| 4 | Break mask `**break_mask**` | Test ∩ `**regime_break_***`; fallback if less than 5 lines | `**pd.Series(bool)**` | `**run_phase0**` |
| 5 | `**beta_steady**`, `**beta_stress**` | `**rets**` + mask | `**Dict[str,float]**` | `**Dynamic_Beta_Tracker.steady_vs_break**` |
| 6 | Snapshot top-level fields | Same as above | `**phase0.beta_steady**` / `**phase0.beta_stress**` | `**Phase0Output**` |
| 7 | Bar height | two dictionaries + `**symbols**` (removal basis) | `**go.Bar**` `**y**` vector | `**fig_beta_regime_compare**` |


---

## 5. Key data calculation example

The numbers in this section are from the same source as the JSON printed by `**python research/figure03_res_key_example.py**` (executed in the warehouse root directory): after replacing `**data.json`**, dynamic window or `**regime_break_*`**, you should rerun the script and update this section accordingly.

### 5.1 Prerequisite (current warehouse snapshot)


| Project | Value |
|-------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Quote file | `**data.json**` (`**bundle.meta["source"]**` = `akshare`, `**generated_at**` = `2026-04-16T11:18:47.221640Z`) |
| **Benchmark`** | `**SPY**` |
| Training window after parsing | `**2024-01-02**`～`**2026-01-30**` |
| Test window after parsing | `**2026-02-02**`～`**2026-04-15**` |
| `**regime_break_start**`~`**regime_break_end**` (`**Phase0Input` default factory**) | `**2026-03-30`**~`**2026-04-20`** |
| Mask `**break_mask.sum()**` (original number of hit lines before rollback) | **12** |


### 5.2 Example target NVDA (`**beta_steady` / `beta_stress`**)

1. **Dictionary output (consistent with the height of the blue/orange column in the picture)**
  - `**beta_steady["NVDA"]`** = **2.159458126680862**
  - `**beta_stress["NVDA"]`** = **1.3660776160597603**
  - **\Delta\beta** = **−0.7933805106211018**
2. **Hand calculation verification (same formula as `Dynamic_Beta_Tracker`)**
  - **Steady-state subtable** (after masking `**dropna(how="any")`**) valid number of rows **457**;
   \widehat{\mathrm{Var}}(r_{SPY})= **5.85924852109553×10⁻⁵**,
   \widehat{\mathrm{Cov}}(r_{SPY},r_{NVDA})= **1.2652801835122564×10⁻⁴**
   → **\hat\beta=** **1.2652801835122564×10⁻⁴ / 5.85924852109553×10⁻⁵** = **2.159458126680862** (consistent with the dictionary).  
  - **Broken subtable**The number of valid rows is **11**;
  \widehat{\mathrm{Var}}(r_{SPY})= **1.0954990434886374×10⁻⁴**,
  \widehat{\mathrm{Cov}}(r_{SPY},r_{NVDA})= **1.4965367217247054×10⁻⁴**
  → **\hat\beta=** **1.3660776160597603** (consistent with dictionary).
3. **Simple returns for the first three rows of the steady-state window (within `sub`, columns SPY/NVDA)**


| `date` | `r_SPY` | `r_NVDA` |
| ---------- | --------- | ---------- |
| 2024-01-02 | −0.005793 | −0.027388 |
| 2024-01-03 | −0.008456 | −0.012457 |
| 2024-01-04 | −0.003336 | 0.009034 |


1. **Simple returns for the first three rows of the break window (within `sub`)**


| `date` | `r_SPY` | `r_NVDA` |
| ---------- | --------- | ---------- |
| 2026-03-30 | −0.003343 | −0.014028 |
| 2026-03-31 | 0.029068 | 0.055882 |
| 2026-04-01 | 0.007535 | 0.007741 |


### 5.3 Phase2 shadow model selection prerequisite (aligned with `Figure2.1-Res.md` §6)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

**Full model selection table and NVDA decomposition** see **`Figure2.1-Res.md` §6.2～§6.4**. In this figure, there is no direct identical formula between **Beta regime** and model selection**. This section only serves the audit of the whole database **same snapshot**.

---

## 6. Source code anchor (traceable)

**Beta Estimate (Core):**
```python
# research/phase0.py — Dynamic_Beta_Tracker._beta_for_mask
sub = self.returns.loc[mask].dropna(how="any")
yb = sub[self.benchmark].to_numpy(dtype=float)
vx = float(np.var(yb, ddof=1)) or 1e-12
# ...
out[c] = float(np.cov(yb, y, ddof=1)[0, 1] / vx)
```**Bar Chart Assembly (Core):**

- `**dash_app/figures.py`** · `**fig_beta_regime_compare`**: `syms` culling `**benchmark`**, `**b0`/`b1**` assembled by `**dict.get(..., nan)**`.  
- `**dash_app/app.py**`: `**fig_beta_regime_compare(dict(p0["beta_steady"]), dict(p0["beta_stress"]), ...)**`, `**figure_title="Figure0.3"**`.

---

## 7. Consistency check

1. Read snapshots `**snap_json["phase0"]["beta_steady"]**`, `**snap_json["phase0"]["beta_stress"]**`.
2. Use the same `**close**` and the same `**Phase0Input**` (including the parsed training/test window and `**regime_break_***`) to re-execute `**run_phase0**` and get `**beta_steady'**` and `**beta_stress'**`.
3. For each key `**s**` (union of two dictionaries): If both sides of `**snap**` and `**'**` are finite floating point, then test **|\beta_s-\beta'_s| < \varepsilon**, take **\varepsilon = 10^{-9}**.
4. For the `**symbols`** order used in `**fig_beta_regime_compare`**, check whether the `**y`** bar value is equal to `**float(beta_*.get(s))**` (missing is **NaN**, there is no bar in the figure).

---

## 8. And downstream narrative (simplified)

- **Figure0.2** gives the linear correlation structure of the training period; this figure compares the baseline sensitivity **region on the same `**rets`** slice** and is often read together with `**orthogonality_check`** and the sidebar `**about_phase0_logic`**.  
- When `**defense_level**` is higher, the Beta area card title can be switched by `**analysis_engine.p0_beta_card_title**` (aligned with the investment view Copy).

---

**Placeholder**: `**{benchmark}`** · `**{train_start}`** · `**{train_end}`** · `**{test_start}`** · `**{test_end}**`