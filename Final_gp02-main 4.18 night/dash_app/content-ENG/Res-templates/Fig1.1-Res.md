# Figure1.1 · Group diagnosis and failure precursor identification (research)

**Object Type (A)**: Basic statistics and structural diagrams. This "picture" appears as two pieces of content on the UI:

- Left: Grid of asset-by-asset diagnostic cards (ADF/Ljung–Box/Differential Order/Logical Failure Label).
- Right side: "Asset-by-asset analysis + overall conclusion" (Markdown) automatically generated based on the diagnosis results.

They serve one purpose together: **Before entering Phase 2 (probability layer OOS and model confrontation), first clarify the "statistical premise that data can be modeled"** and provide a chain of evidence for targets that may need to be excluded from the universe.

This article aligns the `fig_label="Figure1.1"` block of the main column `dash_app/ui/main_p1.py` (output id: `p1-asset-cards`, `p1-group-analysis`).

Placeholder (optional): `**{train_start}`** · `**{train_end}**` · `**{n_symbols}**`

---

## 1. Graphics/text pipeline (end-to-end)
```text
data.json → load_bundle.close_universe
→ daily_returns(close[symbols]) = returns (simple returns)
  → resolve_dynamic_train_test_windows(...) → train_mask
  → Phase1: run_phase1(returns.loc[train_mask], Phase1Input, DefensePolicyConfig, close_train)
→ diagnostics: List[AssetDiagnostic](asset-by-asset ADF/LB/Differential/Failure Flag)
→ h_struct, gamma_multiplier (structural entropy and gamma multiplier, for sidebar FigX.2 / Defense state machine)
→ Dash main callback: render_dashboard_outputs(...)
→ p1-asset-cards (card grid)
→ p1-group-analysis (narrative_p1_group_analysis generates Markdown)
```---

## 2. Data Provenance


| Project | Description |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Raw data** | Daily closing price wide table `close: pd.DataFrame` (from `ass1_core.load_bundle`).                                                                 |
| **Training window return** | `rets = daily_returns(close[symbols]).dropna(how="all")`, and then take `rets.loc[train_mask]` as Phase1 input (see `research/pipeline.py`). |
| **Logarithmic returns (for ADF/LB)** | Prioritize the calculation of \ln(P_t/P_{t-1}) using the closing price of the training window `close_train`; otherwise fall back to \ln(1+r_t) (see `research/phase1.py:_log_returns`).                          |
| **Diagnostic output** | `snap_json["phase1"]["diagnostics"]`: A dictionary for each object, with fields from `AssetDiagnostic` (see `research/schemas.py`).                             |


---

## 3. Methodology and mathematical objects

### 3.1 Stationarity: ADF + differential pipeline (up to second order)

For each target's logarithmic return sequence x_t, perform the ADF test to obtain the p value:

- If p < \texttt{adf_p_threshold}: It is considered that the unit root can be rejected (stationary), enter Ljung–Box;
- Otherwise, do the difference \Delta x_t on x_t, and then do the ADF;
- Up to second difference \Delta^2 x_t. If the second order is still unstable, mark `basic_logic_failure=True` and set `weight_zero=True` on the optimization side.

Implementation: `research/phase1.py:_adf_diff_pipeline`.

### 3.2 Regularity/predictability: Ljung–Box (whether autocorrelation is significant)

Do Ljung–Box on the final sequence used for testing (default lags=10):

- `ljung_box_p > 0.05`: Do not reject "no autocorrelation", mark `white_noise=True` / `low_predictive_value=True` on the project, **only prompt, not eliminate**;
- `ljung_box_p ≤ 0.05`: The white noise hypothesis is rejected and it is believed that there is still a residual law that can be structured.

Implementation: `research/phase1.py:_ljung_box_p` and `wn` determination in `run_phase1`.

---

## 4. Calculation Chain


| step | calculation object | input | output | logic/function |
| --- | ----------- | ------------------------ | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 1 | Log return series | `rets` + `close_train` | `lr` | `_log_returns` |
| 2 | ADF + differential | `lr` + `adf_p_threshold` | `diff_order, stationary_returns, basic_logic_failure, adf_p, adf_p_returns` | `_adf_diff_pipeline` |
| 3 | Ljung–Box | Final inspection sequence | `ljung_box_p` | `_ljung_box_p` |
| 4 | Card sorting (red/yellow/green) | `AssetDiagnostic` | headline/badge | `dash_app/dashboard_face_render.py` |
| 5 | Conclusion text within the group | `phase1.diagnostics` | Markdown | `dash_app/render/explain/main_p1/narrative.py:narrative_p1_group_analysis` |


---

## 5. UI semantics (card colors and fields)

Color grouping of main column cards (`dash_app/dashboard_face_render.py`):

- **red (danger)**: `basic_logic_failure=True` or `stationary_returns=False` → "non-stationary or logic failure · not modelable"
- **Amber (warning)**: `stationary_returns=True` and `low_predictive_value=True` → “Stationary · Residuals are near white noise (weak regularity)”
- **Green (success)**: `stationary_returns=True` and `low_predictive_value=False` → "stationary · modelable structure exists (rejects pure noise)"

Three p-values/fields shown in the card:

- `ADF log return p`: `adf_p`
- `Differential order / ADF(final) p`: `diff_order` and `adf_p_returns`
- `Ljung–Box p`: `ljung_box_p`

---

## 6. Key data calculation example (important values)

The following columns are organized in the same way as **`Figure2.1-Res.md` §6** to facilitate horizontal auditing: The full table values of **Phase2 Shadow Model Selection** are based on **`Figure2.1-Res.md` §6.2～§6.4** as a single source of truth; this section only reiterates the **premise** and marks the **reading boundary with this figure (Phase1)**.

### 6.1 Prerequisite (Phase2 shadow model selection, same origin as Fig2.1 §6.1)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

### 6.2～6.4 Model selection full section, NVDA decomposition, full sample shadow MSE

For complete tables and descriptions, see **`Figure2.1-Res.md` §6.2～§6.4** (the same `data.json` snapshot must not be contradicted here).

### 6.5 Comparative reading of this picture (Phase1)

**Figure1.1** The cards in the left column come from **`snap_json["phase1"]["diagnostics"]`** (ADF / Ljung–Box / Differential Stage / Logic Failure Label), ** and the shadow MSE table of NVDA in §6.3 belong to different objects**: the former is **training window statistical test**, the latter is **training tail holdout model selection score**, **it is forbidden to mix the same p value or number in the same column**.

---

## 7. Source code anchor (traceable)

- **Phase1 calculation**: `research/phase1.py:run_phase1`
- **ADF/Ljung–Box**: `_adf_pvalue`, `_ljung_box_p`, `_adf_diff_pipeline`
- **Logarithmic return construction**: `_log_returns` (close_train takes precedence)
- **Main column rendering**: `dash_app/dashboard_face_render.py` (`p1_grid` / `p1_group_analysis`)
- **Narrative generation within the group**: `dash_app/render/explain/main_p1/narrative.py:narrative_p1_group_analysis`
- **Method description document (supplementary)**: `dash_app/content/p1_stat_method.md` (shown as Figure1.2 in the UI)

---

## 8. Consistency check

1. Fix the same `data.json` and the parsed start and end dates of the training window, and rerun `research.pipeline.run_pipeline`.
2. Extract `snap_json["phase1"]["diagnostics"]` and manually recalculate any target:
  - Logarithmic returns (prefer `close_train`);
  - ADF(p) and differential order;
  -Ljung–Box(p).
3. Check:
  - `basic_logic_failure` is consistent with the second-order differential failure condition;
  - `low_predictive_value` is consistent with `ljung_box_p > 0.05` (when `ljung_box_p` is non-empty).

---

## 9. And downstream narrative (Simplified)

- **With Phase 3 blocked set**: `basic_logic_failure=True` or `weight_zero=True` objects will enter `blocked_symbols` and their weights will be cleared and normalized during optimization (see `research/pipeline.py` and `research/phase3.py`).
- **With FigX.2 (Structural Entropy)**: Phase1 outputs `h_struct` at the same time, which is the direct input of the defense state machine and the sidebar structural entropy card; the diagnostic explanation of Figure1.1 is "single asset premise", and FigX.2 explains "cross-sectional structural pressure".