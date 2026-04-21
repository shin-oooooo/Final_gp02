# Figure2.1 · Shadow mode selection pixel matrix (research · Class B)

**Object type (B)**: Discrete display of the relative advantages and disadvantages of **Naive / ARIMA / LightGBM / Kronos** on the **shadow holdout** at the end of the training window; each object corresponds to the model label with the smallest comprehensive score**. **For the definition, purpose, time segmentation, MSE+JSD dual goals and \alpha meaning of shadow testing, see §2** (this section is the main methodological axis of the full text). The pixmap **does not draw continuous returns**, only maps `**best_model_per_symbol`** → four rows of discrete color patches.

This article is aligned with the Phase 2 panel `**fig-p2-best-pixels`** (sidebar `**Figure2.1`** cell, `dash_app/ui/ids.py` · `**FIG.F2_1**`). The `**figure_title**` parameter of `**fig_p2_best_model_pixels**` in the current callback is passed in `**"Figure3.1"**` in `**dash_app/app.py**` / `**callbacks/p2_symbol.py**`, and coexists with the outer layer `**Figure2.1**` tag; the text is subject to Figure2.1** displayed in the **side column.

Placeholder: `**{n_symbols}`** · `**{p2_selected_symbol}`** · Can be injected aligned with `**phase2.best_model_per_symbol`** in the snapshot.

---

## 1. Graphics pipeline (end-to-end)
```text
data.json → daily_returns(close[universe])
→ run_phase2(...): tail holdout → best_model_per_symbol (one model key per symbol)
  → Dash: fig_p2_best_model_pixels(best_model_per_symbol, symbols, selected_symbol, ...)
→ 4×N pixel matrix (columns = symbols, rows = models)
```---

## 2. Shadow testing methodology (core)

This section explains that **Fig2.1 only relies on the model selection logic**: **Shadow holdout** - artificially draw a section **outside the pseudo sample** tail window inside the **training window**, only use **realized income as a label**, compare the one-step prediction quality of the four models, and then independently select the default model key for **each target**. The pixel matrix is ​​just a visualization of this dictionary, and the methodological focus is on the shadow experimental design rather than the drawing itself.

### 2.1 Purpose: Mold selection container vs strict out-of-sample


| Dimensions | Shadow testing (source of this figure) | Test window prediction in Phase 2 main loop (Service Fig2.2 / Credibility, etc.) |
| -------- | --------------------------------------------------------------- | -------------------------------------------------- |
| **Time Range** | **Training Window** end `**n_tail_eff`** days only | **Testing Window** each trading day t |
| **Information set** | For each step prediction, use the history up to that step (see each model definition in `**_tail_holdout_scores`**) | **strict**: only use **I_{t-1}** (`**returns.index < t`**) |
| **label** | **Real next day return** on holdout segment (within training sample) | Test window **Real return** |
| **Purpose** | **Relative comparison between models** → `**best_model_per_symbol[sym]`** (discrete label) | Density, JSD, DM, coverage, etc. **Pipeline output** |


The two **cannot be mixed**: Shadow **does not consume test window labels**, thereby avoiding the optimistic bias of "using the same test set to both select models and report OOS performance"; the test window is reserved exclusively for **Fig2.2** and the credibility pipeline.

### 2.2 Holdout structure (training tail slice)

Return sequence `**s`** for each underlying (from self-completed `**train`**):

1. **Effective tail length** `**n_tail_eff`** = `**min(policy.shadow_holdout_days, max(5, n_train_pts − 30))`** (see `**research/phase2.py`**), sidebar `**shadow_holdout_days**` defaults to **40**, clamped **[5,120]**.
2. **Fitting segment** `**train_s = s.iloc[:-n_tail_eff]`**: ARIMA/LightGBM etc. estimate or roll on this segment; when the length is insufficient, `**_tail_holdout_scores`** directly returns an empty graph and falls back to `**naive**`.
3. **Evaluation section** `**val_s = s.iloc[-(n_tail_eff+1):]`**: Construct `**n_tail_eff`** on it **one-step prediction vs next day realization** comparison, and calculate the **shadow MSE** of each model.
4. **Kronos**: The `**close`** column (`**close_sym`**) must be provided with `**s`** **calendar alignment** when the weight is ready, otherwise the statistical agent will be thrown or taken away (see the source code branch).

### 2.3 Dual-objective synthesis: point prediction (MSE) and density alignment (JSD)

The shadow stage not only looks at point errors, but also incorporates the **Jensen–Shannon distance** of the **model-implied Gaussian** and the **holdout implementation** into the same scale:

- **MSE**: Whether the next period's income **point prediction** is close to realization (the prediction definition of each model is different, see `**_tail_holdout_scores`**).  
- **JSD**: Construct empirical moments **(\mu_{\mathrm{emp}},\sigma_{\mathrm{emp}})** on holdout, and calculate **symmetric JSD** (`**_js_divergence`**) with each model moment to reflect whether the **probability shape** is outrageous.

Comprehensive score
**\mathrm{combined}_m=\alpha\cdot \frac{\mathrm{MSE}_m}{\max_j \mathrm{MSE}_j}+(1-\alpha)\cdot \frac{\mathrm{JSD}_m}{\max_j \mathrm{JSD}_j}**,
Among them **\alpha=** `**DefensePolicyConfig.alpha_model_select`** (default 0.5): **\alpha\to 1** is more biased towards **point prediction ranking**; **\alpha\to 0** is more biased towards **distribution fitting**. This is an explicit knob that puts "point error" and "density deviation" into the same comparable scale in engineering.

### 2.4 Selection rules and pixel semantics

- **Independent** for each bid: **\arg\min_m \mathrm{combined}_m** → `**best_model_per_symbol[sym]`**; the average shadow MSE (`**phase2.mse_*`**) across bids is only used for sidebar narrative, and **does not participate** in single column lighting.  
- **Fig2.1**: Column = target, row = `**_P2_MODELS`** fixed order; **Bright grid = optimal model in this column**, vertical dotted line marks the current drop-down target (if applicable).

### 2.5 Adjustable parameters (consistent with sidebar)


| Parameters | Function |
|--------------------------|----------------------------------|
| `**shadow_holdout_days`** | The longer the tail window → the more stable the estimate and the higher the computing power; the shorter the tail window → the larger the variance and the faster |
| `**alpha_model_select`** | Continuous trade-off between pure MSE vs pure JSD |


---

## 3. Data Provenance


| Project | Description |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Quotes** | `**resolve_market_data_json_path()`** · `**load_bundle`** · `**close_universe`** |
| **Returns** | `**daily_returns`** (Same as `**run_phase2`** input `**returns**`): Simple daily returns |
| **Training subsample `train`** | `**returns.loc[train_mask].dropna(how="any")**`: **Remove the entire row of trading days with no profit for either party** (consistent with `**research/phase2.py`** `**run_phase2`**) |
| **Shadow length** | `**DefensePolicyConfig.shadow_holdout_days`** (default 40, clamped [5,120]); effective tail `**n_tail_eff = min(shadow_holdout_days, max(5, n_train_pts − 30))`** |
| **Model key space** | `**research/phase2.py`** · `**_MODELS`** = `**["naive","arima","lightgbm","kronos"]`** (same order as `**dash_app/figures.py`** · `**_P2_MODELS**`) |


---

## 4. Quick overview of scoring components and formulas (corresponding to §2)

**Holdout segmentation, division of labor with test window OOS, and the statistical meaning of \alpha are subject to §2**; the following table is a comparison of **implementation-level** variables for easy reading in comparison with `**_tail_holdout_scores`**.
| Weight | Meaning |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `**mse_scores[m]`** | Shadow of model `**m`** **MSE** (Naive uses the current day's return to predict the next day; ARIMA/LGB see source code; Kronos calls `**kronos_one_step_mu_from_close`** on the `**close`** sequence when the weights are ready, otherwise **5 daily average proxy**) |
| `**jsd_scores[m]`** | **Gaussian** moments vs **holding period empirical** returns of **JSD** for each model (via `**_js_divergence`**) |
| **Combined score (the smaller the better)** | `**combined[m] = α · norm(MSE_m) + (1−α) · norm(JSD_m)`**, where `**norm(x_m)=x_m / max_j x_j`** Across four models, `**α = policy.alpha_model_select**` (default **0.5**) |


**Winning Rules**: `**best_model_per_symbol[sym] = argmin_m combined[m]`**; if `**combined_map`** is empty then `**"naive"**`.

---

## 5. Calculation Chain


| step | calculation object | input | output | logic |
| --- | ---------------------------- | -------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------- |
| 1 | `**train**` | `**returns**`, `**train_mask**` | Row complete training table | `**dropna(how="any")**` |
| 2 | `**mse_map`/`combined_map**` | `**train[sym]**`, `**n_tail_eff**`, `**close**` | Per-model scalar | `**research/phase2.py**` · `**_tail_holdout_scores**` |
| 3 | `**best_model_per_symbol**` | `**combined**` for each `**sym**` | `**Dict[str, str]**` (target → model key) | `**run_phase2**` aggregation loop |
| 4 | `**phase2**` snapshot fields | Phase2Output | `**PipelineSnapshot.phase2.best_model_per_symbol**` | `**run_pipeline`/API** |
| 5 | Pixel coordinates | `**best_model_per_symbol`**, `**symbols`** | `**go.Scatter**` bright square | `**fig_p2_best_model_pixels**` |


---

## 6. Key data calculation example (important values)

The following values are **one instantiation** of **§2 Shadow Methodology** under the current snapshot of `**data.json`** (same source** as the JSON printed by `**python research/figure21_res_key_example.py`**; the script only ran to **Phase 2**, about **90s**, including Kronos). After replacing `**data.json`**, `**shadow_holdout_days`**, `**alpha_model_select**` or Kronos environment, you must rerun and check for updates.

### 6.1 Prerequisite (current warehouse snapshot)


| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `**data.json` meta** | `**source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | `**2024-01-02`**～`**2026-01-30`** |
| `**shadow_holdout_days**` (cfg/effective `**n_tail_eff**`) | **40** / **40** |
| `**alpha_model_select`** | **0.5** |


### 6.2 Full section `**best_model_per_symbol`** (snapshot)


| Target | Shadow optimal model |
| ----- | -------- |
| NVDA | lightgbm |
| MSFT | arima |
| TSMC | lightgbm |
| GOOGL | lightgbm |
| AAPL | lightgbm |
| XLE | arima |
| GLD | arima |
| TLT | lightgbm |
| SPY | lightgbm |


### 6.3 Example target NVDA (consistent with `**argmin combined`**)

**One-step MSE (shadow tail segment, four models):**


| Model | MSE |
| -------- | ----------------------- |
| naive | 7.288432628021102×10⁻⁴ |
| kronos | 1.0991749996076322×10⁻³ |
| arima | 6.198924012450381×10⁻⁴ |
| lightgbm | 3.777983970682029×10⁻⁴ |


**Normalized comprehensive score (the smaller, the better; first take max(MSE), max(JSD) of each model and then linearly combine): **


| model | combined |
|--------|----------------------|
| naive | 0.8315410480871027 |
| arima | 0.3512274957669465 |
| lightgbm | **0.3086266433365771** |
| kronos | 0.5077540684324975 |


→ `**best_model_per_symbol["NVDA"] = "lightgbm"`**; The pixel matrix is lit in the **NVDA** column and the **LightGBM** row (the row order from top to bottom corresponds to Naive→ARIMA→LightGBM→Kronos).

### 6.4 Full sample shadow MSE mean (side column narrative aid, not single cell lighting basis)

The pipeline also outputs the cross-standard average shadow MSE (`**phase2.mse_naive`**...), which has no direct one-to-one relationship with the **comprehensive score** of a single standard. Current snapshot (same as **§6.1** script): **3.5476386523745484×10⁻⁴** / **2.4045472704104052×10⁻⁴** / **2.0083813547912×10⁻⁴** / **2.63723246389078×10⁻³**. **Pixels are still determined only by the `argmin combined` of each object. **

---

## 7. Source code anchor (traceable)

**Comprehensive points and merit selection:**
```python
# research/phase2.py — _tail_holdout_scores (excerpt)
max_mse = max(mse_scores.values()) or 1.0
max_jsd = max(jsd_scores.values()) or 1.0
alpha = float(np.clip(alpha_mse, 0.0, 1.0))
combined = {
    m: alpha * (mse_scores.get(m, max_mse) / max_mse)
    + (1.0 - alpha) * (jsd_scores.get(m, max_jsd) / max_jsd)
    for m in _MODELS
}
```**Aggregation into Phase2:**
```python
# research/phase2.py — inside run_phase2 (excerpt)
best_sym = min(combined_map, key=combined_map.get)
best_model_per_symbol[sym] = best_sym
```**Pixel Drawing:**
```python
# dash_app/figures.py — fig_p2_best_model_pixels (excerpt)
row_of = {m: i for i, m in enumerate(_P2_MODELS)}
bm = str(best_model_per_symbol.get(sym) or "naive")
if bm not in row_of:
    bm = "naive"
mi = row_of[bm]
```---

## 8. Consistency check

1. Read the snapshot `**snap_json["phase2"]["best_model_per_symbol"]**`.
2. Use the same `**returns**`, `**train_mask**` / `**test_mask**`, `**DefensePolicyConfig**`, `**close**` to re-execute `**run_phase2**` (or run `**research/figure21_res_key_example.py**` within the `**_run_p2_only**` path).
3. For each target `**s**`: **String labels must be exactly the same**.
4. (Optional) Call `**_tail_holdout_scores`** on any `**s`** and check that `**argmin(combined)`** is consistent with the snapshot.

---

## 9. With Phase 3 / Fig2.2 (Simplified)

- `**Phase3Input**` gives priority to `**model_mu[best_model_per_symbol[s]][s]**` when assembling margin `**μ**` (see `**research/pipeline.py**` near the `**hist_mu`/`mu**` section).  
- **Fig2.2** The density map displays the full test window distribution of **each model** under the same `**symbols`** drop-down; this figure **only marks the model selection winner**, and both share the `**phase2`** snapshot.

---

**Placeholder**: `**{n_symbols}`** · `**{p2_selected_symbol}`**