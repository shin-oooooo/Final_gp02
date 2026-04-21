# Figure3.1 · Best model return expectations and volatility predictions for each target (Research · Category B)

**Object type (B)**: Use a **three-line small table without vertical bars** to discretely display the **next day's return expectation μ̂** and **fluctuation forecast σ̂** for each target under the **Shadow Model Selection Winner**. The values ​​come from `**phase2.model_mu[best_model_per_symbol[s]][s]`** and `**phase2.model_sigma[best_model_per_symbol[s]][s]`** - that is, the **(\mu,\sigma)** pair given by **Fig2.1 The grid model where the pixel matrix is ​​lit** is given at the end of the test window. This figure **does not draw the time series**, but only presents the **cross-sectional ruler**; the Phase 3 downstream `**AdaptiveOptimizer`** uses this **μ̂ vector** as the marginal benefit prior.

**Model selection methodology (holdout segmentation, MSE+JSD comprehensive score, \alpha, defeat rules) will not be repeated in this article**, please refer to `**Figure2.1-Res.md`** **§2–§6** (single source of truth). The focus of this article is on the generation path of μ̂/σ̂, the three-row semantics of the table, and the numerical consistency with Phase 3 μ vector assembly (`research/pipeline.py`).

Table layout (no vertical bars, row direction readings):


| Line number | Meaning |
| --- | ------------------------------------------------------------------------------- |
| Line 1 | **subject** `sym` (column order = `snap_json["phase0"]["meta"]["symbols_resolved"]`) |
| Row 2 | **Best model μ̂** (`model_mu[best_model_per_symbol[sym]][sym]`, unit: daily return) |
| Row 3 | **Best model σ̂** (`model_sigma[best_model_per_symbol[sym]][sym]`, unit: daily return standard deviation) |


Placeholder: `**{n_symbols}`** · `**0`** · `**{objective_name}`** · (If required to be linked with Phase 2 drop-down) `**{p2_selected_symbol}**`

---

## 1. Graphics pipeline (end-to-end)
```text
data.json → run_phase2 →
phase2.best_model_per_symbol (winner model key per bid)
phase2.model_mu (four models × target → μ̂, end of test window or mean)
phase2.model_sigma (four models × target → σ̂)
→ The main callback is indexed by sym best_model_per_symbol[sym] → Get the corresponding μ̂, σ̂
→ Assemble a three-row table (without mullions): [symbols; μ̂_best; σ̂_best]
→ Output to Phase 3 main column fig_label=Figure3.1
```| Concept | Description |
|------------- |-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Data truth source** | `**phase2.model_mu`**, `**phase2.model_sigma`**, `**phase2.best_model_per_symbol**` (`**research/phase2.py**` `**run_phase2`** aggregation; see Fig2.1-Res §3 for details) |
| **Column/object order** | `**snap_json["phase0"]["meta"]["symbols_resolved"]`** (consistent with the columnar horizontal axis of Fig3.2) |
| **Time positioning** | The value of each grid is the **one-step prediction μ̂/σ̂** of the **end of the test window**; if `**model_mu_test_ts`** / `**model_sigma_test_ts`** exists, take its end point, otherwise return the full sample scalar (similar to `**dash_app/ui/main_p2.py`** `**_p2_mu_sigma_table`** The value rules are consistent) |
| **Phase 3 side** | `build_p3_panel` (`dash_app/ui/main_p3.py`) mounts the three-row μ̂/σ̂ table and outsources `**fig_label=FIG.F3_1`** (`**Figure3.1`**) |
| **No vertical bars** | Dash/HTML `**dbc.Table(..., borderless=True)`** or CSS `**border-left:0; border-right:0`**; only row separators are retained, and readings are along the **column direction (three rows per column)** Complete |


**Responsibility boundaries with Fig2.1 pixel matrix**: Fig2.1 answers **"Which family of models to choose for each target"** (discrete key); Fig3.1 answers **"What are the μ̂ and σ̂ given by the selected family of models at this moment"** (continuous scalar). The two figures share `best_model_per_symbol`**, but the data dimensions are complementary.

---

## 2. Shadow mold selection methodology (cross-reference)


| Topic | Description |
| ----------------------- | ------------------------------------------------------------------------------- |
| **Model selection definition and purpose** | See `**Figure2.1-Res.md`** **§2.1** (Model selection container vs strict OOS) |
| **Holdout segmentation** | `**Figure2.1-Res.md`** **§2.2** |
| **MSE + JSD + \alpha** | `**Figure2.1-Res.md`** **§2.3–§2.5** |
| **Implement variable and formula table** | `**Figure2.1-Res.md`** **§3–§4** |
| **Numerical reproduction script** | `**python research/figure21_res_key_example.py`** (same origin as Fig2.1 §6 **Same JSON**) |


If you only read this section **Fig3.1**: Remember - **The winner model is determined by the training tail shadow comprehensive score `argmin combined`** (Fig2.1); this article **directly takes the winner's (\mu,\sigma)** at the end of the test window as three lines of numbers, **without re-selecting the model**, and **without inferring any scores in the test window**.

---

## 3. Data Provenance


| Project | Description |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Winner Dictionary** | `**snap_json["phase2"]["best_model_per_symbol"]`** (consistent with Fig2.1 key by key) |
| **μ̂ (full dictionary)** | `**snap_json["phase2"]["model_mu"]`** · `**{model: {sym: μ̂}}`** (four models × target) |
| **σ̂ (full dictionary)** | `**snap_json["phase2"]["model_sigma"]`** · `**{model: {sym: σ̂}}`** |
| **μ̂(t) / σ̂(t) timing** | `**snap_json["phase2"]["model_mu_test_ts"]`** / `**["model_sigma_test_ts"]`** (`**{model: {sym: [..]}}`**; take the last element, which is the one-step prediction at the end of the test window, and `**_p2_mu_sigma_table`** consistent) |
| **Column order / target** | `**snap_json["phase0"]["meta"]["symbols_resolved"]`** (consistent with the investment view `**Figure3.1-Inv.md`** table) |
| **Downstream consumption (Phase 3)** | `**research/pipeline.py`** `**mu = [p2.model_mu[p2.best_model_per_symbol[s]][s] for s in symbols]`**; Fig3.1 line 2 is **element-wise equal** to this vector (floating point precision tolerated) |


---

## 4. Quick overview of formulas (corresponding to drawing and §2)

**Row 2 (best model μ̂)**:
**\hat\mu^{\star}_s=\mathrm{modelmu}[\mathrm{bestmodelpersymbol}[s]][s]**

**Row 3 (best model σ̂)**:
**\hat\sigma^{\star}_s=\mathrm{modelsigma}[\mathrm{bestmodelpersymbol}[s]][s]**

**Time positioning (if OOS timing is available)**:
**\hat\mu^{\star}_s = \mathrm{modelmutestts}[m^{\star}_s][s][-1]**, **\hat\sigma^{\star}_s = \mathrm{modelsigmatestts}[m^{\star}_s][s][-1]**, where **m^{\star}_s = \mathrm{bestmodelpersymbol}[s]**.
**Pipeline-level default fallback** (consistent with `**research/pipeline.py`** **μ assembly**):
If `**m^\star_s`** is missing a key in `**model_mu`** or returns `**None`**, fall back to **\hat\mu^{\star}_s \leftarrow \bar r_s^{\mathrm{train}}** (`**hist_mu.get(s, 0.0)`**); **\hat\sigma^{\star}_s** The corresponding unit in this picture is rendered as a placeholder **"—"** (on the premise that the upstream has not failed, this rollback is almost never triggered).

---

## 5. Calculation Chain


| step | calculation object | input | output | logic |
| --- | ---------------------------------- | ---------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------ |
| 1 | `**model_mu` / `model_sigma`** | Test window `**returns`**, four-model OOS one-step prediction | `**{m: {sym: μ̂}}`**, `**{m: {sym: σ̂}}`** | `**research/phase2.py`** `**run_phase2`** Each model branch (with Fig2.2 Density plots share the same source) |
| 2 | `**best_model_per_symbol`** | Shadow holdout comprehensive score | `**{sym: model_key}`** | See `**Figure2.1-Res.md`** **§2, §4** |
| 3 | `**μ̂^★`** vector | Steps 1, 2 | **float vector of length N** | `**μ̂^★_s = model_mu[best_model_per_symbol[s]][s]`** (original from Phase3 μ assembly) |
| 4 | `**σ̂^★`** vector | Steps 1, 2 | **Float vector of length N** | Same as above, replace `**model_sigma`** |
| 5 | **Fig3.1 Table object** | Steps 3, 4 + `**symbols_resolved`** | **3×N table without mullions** | Dash `**dbc.Table(..., borderless=True, striped=False)`** or equivalent CSS |


---

## 6. Key data calculation example (important values)

The following example shows the winner table + μ̂/σ̂ values according to the same snapshot (`**data.json`**, `**shadow_holdout_days=40`**, `**alpha_model_select=0.5`**) of `**Figure2.1-Res.md`** **§6.1**. After updating the data and re-running `**python research/figure21_res_key_example.py`** (shared with Fig2.1 §6) synchronously, rewrite this section according to the actual printed JSON.

### 6.0 Prerequisite (same origin as Fig2.1 §6.1)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

### 6.1 `**best_model_per_symbol`** (same as Fig2.1 §6.2)


| Target | Winner Model `**m^★_s`** |
| ----- | ---------------- |
| NVDA | lightgbm |
| MSFT | arima |
| TSMC | lightgbm |
| GOOGL | lightgbm |
| AAPL | lightgbm |
| XLE | arima |
| GLD | arima |
| TLT | lightgbm |
| SPY | lightgbm |


### 6.2 Three-row table reading method (example placeholder `{sym}` column)


| sym | NVDA | MSFT | TSMC | GOOGL | AAPL | XLE | GLD | TLT | SPY |
| ------- | ----------- | ----------- | ---- | ----- | ---- | --- | --- | --- | --- |
| μ̂^★ (day) | `{μ̂_NVDA}` | `{μ̂_MSFT}` | … | … | … | … | … | … | … |
| σ̂^★ (day) | `{σ̂_NVDA}` | `{σ̂_MSFT}` | … | … | … | … | … | … | … |


The actual number changes with the snapshot, and is subject to `**snap_json["phase2"]["model_mu"]`** / `**["model_sigma"]`**; formatting recommendations are **6 decimal places, fixed-width font** (consistent with `**dash_app/ui/main_p2.py`** `**_p2_mu_sigma_table`**).

### 6.3 Numerical consistency proposition (Fig3.1 ↔ Phase 3 μ vector)

Under the premise of the same `**last-snap`** and without switching universes:

`**np.array([snap["phase2"]["model_mu"][snap["phase2"]["best_model_per_symbol"][s]][s] for s in snap["phase0"]["meta"]["symbols_resolved"]])**`

**Element-wise equals** `**research/pipeline.py`** assembled `**Phase3Input.mu_daily`** (`**snap_json["phase3"]["mu_daily"]`**, within floating point precision). Fig3.1 table row 2 is the cross-sectional visualization of the vector; row 3 is σ̂ under the same winner, which does not directly enter the AdaptiveOptimizer (the optimization uses the training window sample covariance `**Σ**`, see `**Figure3.2-Res.md`** **§2.1**), **but for the reader to understand the Fig3.2 blue column gives a synchronized "single asset fluctuation scale". **

---

## 7. Source code anchor (traceable)

**μ̂/σ̂ dictionary generation (same as Fig2.2 density):**
```python
# research/phase2.py — run_phase2 returns (excerpt)
return Phase2Output(
    ...
    model_mu={m: dict(mus[m]) for m in models},
    model_sigma={m: dict(sigs[m]) for m in models},
    best_model_per_symbol=best_model_per_symbol,
    test_daily_best_model_mu_mean=daily_best_mu,
    model_mu_test_ts={m: dict(mu_ts[m]) for m in models},
    model_sigma_test_ts={m: dict(sig_ts[m]) for m in models},
)
```**Pipeline side μ assembly (downstream consumer):**
```python
# research/pipeline.py (excerpt)
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
```**Table value rules (doomsday snapshot):**
```python
# dash_app/ui/main_p2.py — _p2_mu_sigma_table (excerpt; Fig3.1 takes the best row according to the same rules)
if model_mu_test_ts and model_sigma_test_ts:
    ts_m = (model_mu_test_ts.get(m) or {}).get(symbol) or []
    ts_s = (model_sigma_test_ts.get(m) or {}).get(symbol) or []
    if ts_m and ts_s:
        mu, sg = ts_m[-1], ts_s[-1]
if mu is None:
    mu = model_mu.get(m, {}).get(symbol)
    sg = model_sigma.get(m, {}).get(symbol)
```**Phase 3 mount (outsourced Figure3.1):**
```text
dash_app/ui/main_p3.py — build_p3_panel
Three-row μ̂/σ̂ table (borderless)
  fig_label = FIG.F3_1  → "Figure3.1"
```---

## 8. Consistency check

1. **Winner Alignment**: `**snap["phase2"]["best_model_per_symbol"][s]`** is consistent with the Fig2.1 pixel bright grid **subject-by-subject** (Fig2.1 §8).
2. **μ Alignment Phase 3**: For each `**s ∈ symbols_resolved`**,
  `**snap["phase2"]["model_mu"][best_model_per_symbol[s]][s]`** **≈** `**snap["phase3"]["mu_daily"][idx(s)]`** (tolerate machine accuracy; if inconsistent, check whether the Kronos branch has gone through the agent or `**hist_mu`** is rolled back).
3. **σ non-negative**: `**snap["phase2"]["model_sigma"][m^★_s][s] ≥ 0`**; if it is `**None`** or `**NaN**`, the corresponding unit of the table renders `"—"`, and 0 must not be filled in silently.
4. **Time series consistency**: If there is `**model_mu_test_ts`** / `**model_sigma_test_ts`**, the last element is consistent with the `**model_mu`** / `**model_sigma`** scalar (same source, the difference should come from the caliber description of "doomsday vs full sample mean"; subject to §4 rules).
5. **No mullion rendering**: DOM check table unit **No `**border-left`** / `**border-right**`**, only row separation is retained; visual continuity when reading in column direction.

---

## 9. Phase 3 reading order (Fig3.1 → Fig3.2 → Fig3.3)


| Sequence | Figure No. | Function |
| --- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 1 | **Fig3.1** (this article) | Shows the **shadow winner per bid** given as **(μ̂,σ̂)** at the end of the test window; the μ̂ vector of row 2 is the marginal benefit prior received by the `**AdaptiveOptimizer`** (see `**research/pipeline.py`** for details) |
| 2 | **Fig3.2** | Solving `**phase3.weights`** under the same μ̂ prior + training window Σ, compared with equal weight/custom gray column (`**Figure3.2-Res.md`**) |
| 3 | **Fig3.3** | Dual-track Monte Carlo, observed under the same random engine `**defense_level`** / Objective function and scenario differences |


Placeholder context: `**0`**, `**{objective_name}`** and `**objective-banner**` (optimization goal description) align the sidebar `**DefensePolicyConfig**`; this figure **only exposes the original values of μ̂/σ̂** and does not do any rescaling of the **objective function**.

---

**Placeholder**: `**{n_symbols}`** · `**0`** · `**{objective_name}`** · `**{p2_selected_symbol}**`