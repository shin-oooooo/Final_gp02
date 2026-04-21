# Figure2.2 · Time × revenue density heat map (test window strictly OOS)

**Object type (B′)**: On each trading day **t** in the **test window**, use the **(\hat\mu_{m,s,t},\hat\sigma_{m,s,t})** output from each model to construct the **Gaussian prediction density** **p_{m,s,t}(r)**, stacked on the time × next period return **r** plane as **Translucent Thermal Layer**; and overlay **μ_{m,s,t} Ridge** (Scatter) and (optional) **Realized Simple Return True Value Polyline**. Shared **`phase2.best_model_per_symbol`** and **`phase2`** snapshots with **Discrete pixel mode selection** of **Fig2.1/Fig3.1**, but **not responsible for mode selection**, only showing the dynamics of **probability layer strictly out-of-sample**.

This article is aligned: **`dcc.Graph(id="fig-p2-density")`** · `dash_app/ui/main_p2.py` **`fig_label="Figure2.2"`** · Graphic function **`dash_app/figures.py::fig_p2_density_heatmap`** (the historical number in the document string was written as Figure 2.3, **The outsourcing title begins with `figure_title="Figure2.2"` shall prevail**).

Placeholder: `{p2_selected_symbol}` · A one-dimensional sequence placeholder of the same length as `phase2.test_forecast_dates` (can be injected by template).

---

## 1. Graphics pipeline (end-to-end)
```text
data.json → run_pipeline → run_phase2
→ test_forecast_dates(length T)
→ model_mu_test_ts[m][sym], model_sigma_test_ts[m][sym] (each T-step OOS moment of each model and each target)
→ (optional) dash_app/figures._test_returns(json_path, sym, t0, t1) → test_vals (length T, aligned with dates)
  → fig_p2_density_heatmap(dates, mu_ts, sigma_ts, sym, tpl, test_vals=..., figure_title="Figure2.2")
  → Output("fig-p2-density", "figure")
```**Partial refresh**: `dash_app/callbacks/p2_symbol.py` uses the same snapshot to recalculate **`fig-p2-density`** (updated together with pixel images and traffic lights) when **`p2-symbol`** changes. Since R1.10 the theme toggle is gone and `theme-store` is pinned to `"dark"`; it is now read as `State` only and no longer triggers this callback.

---

## 2. Responsibility boundaries with Fig2.1 (must read)

| Dimension | Fig2.1 Pixel matrix | Fig2.2 Density heat map |
| --- | --- | --- |
| **Time Range** | **Training Window** End **`n_tail_eff`** Day shadow holdout | **Testing Window** Each calendar trading day **t** |
| **Information Set** | Stepwise fitting within holdout (see **`Figure2.1-Res.md`** §2 for definition) | **Strict OOS**: Stepwise prediction under the condition `**returns.index < t`** |
| **Output semantics** | Discrete **`best_model_per_symbol[s]`** (model selection label) | Continuous **Density layer + μ ridge** (**Do not output** new model selection results) |
| **Purpose** | Answer "Who wins" | Answer "How the winner's **probabilistic narrative** unfolds over time in the test window" |

The two **cannot be read together**: shadow holdout **does not consume the test window label**; Fig2.2 **consumes** **`model_mu_test_ts` / `model_sigma_test_ts`**, consistent with the **`Figure2.1-Res.md`** §2.1 comparison table.

---

## 3. Data Provenance

| Project | Description |
| --- | --- |
| **Test date axis** | `snap_json["phase2"]["test_forecast_dates"]` (length **T**) |
| **OOS μ/σ** | `snap_json["phase2"]["model_mu_test_ts"][model][symbol]`, `model_sigma_test_ts` (each **len = T** and aligned with dates; otherwise the model **does not participate** in the drawing of the target) |
| **Realize return overlay** | `fig_p2_density_heatmap(..., test_vals=...)`: `dash_app/figures._test_returns`**(**`json_path`, `sym`, **First and last** test days**)** Returns a simple return sequence with **`test_forecast_dates`** **unit-by-element alignment**; **If the length is not equal, there will be no colored truth line** |
| **Current target** | Drop-down **`p2-symbol`**; the initial value is parsed by `dash_app/render/main_p2.py::_resolve_p2_symbol_selection` |

---

## 4. Mathematical objects and drawing rules (consistent with `figures.py`)

1. **Density**: For each valid model **m**, each **t**, calculate the Gaussian **PDF** on the yield grid **r_centers**, then **`log1p`**, normalize by column **`z/zmax`** and **`clip^γ`** (**γ=1.75**) to enhance the low-density area contrast.
2. **y-axis range**: `**[min(μ)−4σ_max, max(μ)+4σ_max]**`, fallback **±0.05** when data is missing.
3. **Number of grid bins**: `**n_r_bins=120**` (default).
4. **Multiple models**: `**model="all"`** When **Naive / ARIMA / LightGBM / Kronos** four layers of Heatmap **semi-transparent overlay**; add corresponding **μ ridges** after each layer (**Kronos** solid lines are thickened, other dotted lines).
5. **Legend**: The heat map is consistent with the μ line **legendgroup**, making it easy to hide the density + ridges of the **same model** with one click.

---

## 5. Calculation Chain

| Step | Calculation Object | Input | Output |
| --- | --- | --- | --- |
| 1 | Test window stepwise OOS moment | `run_phase2` inner strict mask | `model_mu_test_ts`, `model_sigma_test_ts` |
| 2 | Implementation sequence | `_test_returns` | `test_vals` or **None** |
| 3 | Plotly objects | `fig_p2_density_heatmap` | `go.Figure` → **`fig-p2-density`** |

---

## 6. Key data calculation example (important values)

The following values share the same **`data.json`** snapshot logic with **`Figure2.1-Res.md` §6**; the tables directly related to **Shadow Mode Selection** in **§6.1～§6.4** have the same origin as **`Figure2.1-Res.md` §6.1～§6.4**. **§6.5** Only serves Fig2.2 (test window tensor).

### 6.1 Prerequisite (current warehouse snapshot)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

### 6.2 Full section `best_model_per_symbol` (snapshot)

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

### 6.3 Example target NVDA - shadow holdout one-step MSE with combined (same as `argmin combined`)

**One-step MSE (shadow tail segment, four models):**

| Model | MSE |
| -------- | ----------------------- |
| naive | 7.288432628021102×10⁻⁴ |
| kronos | 1.0991749996076322×10⁻³ |
| arima | 6.198924012450381×10⁻⁴ |
| lightgbm | 3.777983970682029×10⁻⁴ |

**Normalized comprehensive score (the smaller, the better):**

| model | combined |
|--------|----------------------|
| naive | 0.8315410480871027 |
| arima | 0.3512274957669465 |
| lightgbm | **0.3086266433365771** |
| kronos | 0.5077540684324975 |

→ **`best_model_per_symbol["NVDA"] = "lightgbm"`** (consistent with Fig2.1 pixel column).

### 6.4 Full sample shadow MSE mean (sidebar narrative aid)
The pipeline also outputs the average shadow MSE across standards (`**phase2.mse_naive`** ...). Current snapshot (same as §6.1): **3.5476386523745484×10⁻⁴** / **2.4045472704104052×10⁻⁴** / **2.0083813547912×10⁻⁴** / **2.63723246389078×10⁻³**. **Fig2.2 The heat map does not directly read this set of scalars**, but it can be compared with the sidebar narrative.

### 6.5 Fig2.2 Exclusive - Test window OOS tensor (structure check)

Reading from the same snapshot (**path example**):

| Check items | Expectations |
| --- | --- |
| **`len(snap["phase2"]["test_forecast_dates"])`** | **T** (equal to **`len(model_mu_test_ts[m][NVDA])`** for any valid model) |
| **`snap["phase2"]["model_mu_test_ts"]["lightgbm"]["NVDA"]`** | List of floats of length **T** (**ridge y = this sequence**) |
| **`snap["phase2"]["model_sigma_test_ts"]["lightgbm"]["NVDA"]`** | Same length **T** (the σ of Gaussian for each column of the heat map) |
| **`_test_returns`** Alignment | If the length of the second returned item **= T**, then the pink **Realized Returns** track appears; otherwise only the model layer |

After replacing the data: **Do not hand-code** — Check from `**data.json**` or **`python research/figure21_res_key_example.py`** (if provided by the warehouse) with the **`run_phase2`** output.

---

## 7. Source code anchor (traceable)
```python
# dash_app/figures.py — fig_p2_density_heatmap (excerpt)
for m in models_valid:
    for t_idx in range(T):
        mu_t = mus_m[t_idx]
        sig_t = max(sigs_m[t_idx], 1e-8)
        density_grid[:, t_idx] = _gaussian_pdf(r_centers, mu_t, sig_t)
    fig.add_trace(go.Heatmap(x=dates, y=r_centers, z=z_norm, ...))
fig.add_trace(go.Scatter(x=dates, y=mus_m, mode="lines", ...)) # μ ridges
```
```python
# dash_app/render/main_p2.py — build_main_p2_components (excerpt)
fig_p2_dens = fig_p2_density_heatmap(
    state.test_forecast_dates,
    state.model_mu_test_ts or {},
    state.model_sigma_test_ts or {},
    val, state.tpl,
    test_vals=test_vals, figure_title="Figure2.2",
)
```---

## 8. Consistency check

1. **`len(test_forecast_dates) == len(model_mu_test_ts[m][sym]) == len(model_sigma_test_ts[m][sym])`** is true for each **m** participating in the drawing.
2. Switch **`p2-symbol`**: the heat map and ridge **symbol** are changed synchronously; and **`fig-p2-best-pixels`** highlight column **same target**.
3. **Truth Line**: Appears only when **`_test_returns`** is aligned with the date axis **day by day**; otherwise, the interface prompts for missing data **not considered as a Phase2 failure**.
4. **With Fig2.1**: **`best_model_per_symbol`** is **consistent** with the pixel matrix under the same snapshot (see **`Figure2.1-Res.md`** §8).

---

## 9. With Fig3.1 / Phase3 (Simplified)

- **Fig3.1** table shares **`model_mu` / `model_sigma` / `model_mu_test_ts`** and other homologous fields with **Fig2.2**; the difference lies in the **presentation form** (table vs spatio-temporal density).
- **Phase3** uses **`model_mu[best_model_per_symbol[s]][s]`** (training window margin) when assembling **`mu_daily`** (training window margin), **Fig2.2** shows the **test window daily** **μ̂_{m,s,t}**, the two have **different calibers**, and no mixing of values ​​is allowed.

---

**Placeholder**: `**{p2_selected_symbol}`** · **Test window length T**