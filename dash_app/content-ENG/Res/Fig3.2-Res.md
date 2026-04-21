# Figure3.2 · Weight comparison histogram (research · Category B)

**Object Type (B)**: Side-by-side histogram comparison of **base weights (gray)** versus `**phase3.weights` (blue)**. The blue bars are from `**research/phase3.py`** `**AdaptiveOptimizer**`'s **SLSQP** solution at a given `**DefenseLevel**`, **renormalized** by `**blocked_symbols`**. **The main axis of the methodology is §2** (defense level switching target + blocking redistribution); `**dash_app/figures.py`** `**fig_weights_compare`** is only responsible for two sets of bar mapping and optional custom comparison.

This article is aligned with the Phase 3 main column `**dcc.Graph(id="fig-p3-weights")**` (`**dash_app/ui/ids.py`** · `**IDS.P3_W`**, outsourced `**FIG.F3_2`** · `**Figure3.2**`); in the main callback `**fig_weights_compare(..., figure_title="Figure3.2")**` (`**dash_app/app.py**` / `**dash_app/services/pipeline_factories.py**`).

Placeholders: `**{n_symbols}**` · `**0**` · `**{objective_name}**` (can be injected aligned with snapshot `**snap_json["phase3"]**` / `**snap_json["defense_level"]**`). See `**Figure3.2-Inv.md**` for the investment narrative.

---

## 1. Graphics pipeline (end-to-end)
```text
data.json → run_pipeline → PipelineSnapshot.phase3.weights · meta.symbols_resolved · defense_level
  → Dash：fig_weights_compare(weights, symbols_resolved, tpl, figure_title="Figure3.2")
→ Side-by-side columns (grey: baseline branch; blue: phase3.weights)
```---

## 2. AdaptiveOptimizer and defense level (core methodology)

This section explains **Fig3.2 Blue column numerical meaning**: **Under the given marginal benefit vector μ, covariance Σ, sentiment dictionary and strategy parameters, press `DefenseLevel` to solve the combination weight**, and then apply **blocking set** **clearing and normalization**. The histogram itself is a **discrete weight vector** and **does not plot earnings trajectories**.

### 2.1 Purpose: Optimize weight vs columnar "benchmark" gray column


| Dimensions | Blue column (`**phase3.weights`**) | Gray column (`**fig_weights_compare`** first group) |
| ---------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Source** | `**run_phase3`** → `**AdaptiveOptimizer.optimize(level)`** → `**_apply_blocked_renorm**` | `**custom_weights**` Parameters: if yes **"Custom weights (pie chart)"**; **otherwise** **Equal weights `1/N`** |
| **With test window labels** | Optimize the use of **training windows μ, Σ** (and historical income subsamples of Level 2); **do not explicitly use the test window income to participate in the target** (the test window implementation is compared in fields such as `**defense_validation`**) | **Pure control**: current `**dash_app/app.py`** **not passed in** `**custom_weights`** → **always equal weights at runtime** |
| **Use** | **Capital Allocation Results** → Same day **Fig3.3** MC uses this `**w`** to generate the combined path | **Visual Anchor**: Observe the deviation of the optimization relative to **1/N (or pie chart vector to be accessed in the future)** |


An additional `**w_custom`** (from `**_custom_weights_for_symbols`** mapped `**Phase3Input.custom_portfolio_weights**`) is calculated in the pipeline and is used for comparison with the counterfactual trajectory in `**defense_validation**`; unless the downstream callback **explicitly passes** `**custom_weights`** to `**fig_weights_compare**`, otherwise **Fig3.2 The gray column does not display `w_custom`**.

### 2.2 `**DefenseLevel` → Objective function (implementation name → `phase3.objective_name`)**

`**research/defense_state.py`** `**DefenseLevel`**: STANDARD=0 · CAUTION=1 · MELTDOWN=2. `**resolve_defense_level`** (within `**run_pipeline`**) Diagnoses **resolve** `**level`** based on Phase1/2.

`**AdaptiveOptimizer.optimize`** (`**research/phase3.py`**):

- **Level 0 (STANDARD)**: Minimize `**-(μ_port − r_f)/σ_port`** (`**r_f = RISK_FREE = 0`**), equivalent to **Maximize Sharpe**; return name `**max_sharpe`**, and give `**sharpe`**.
- **Level 1 (CAUTION)**: Minimize `**σ_port + λ_semantic · Σ_i w_i · neg_sent_i`**, where `**neg_sent_i = max(0, −sentiment(symbol_i))`**; return name `**caution_semantic**`.
- **Level 2 (MELTDOWN)**: Minimize **sample CVaRα** (`**policy.cvar_alpha`**) on **historical return matrix** `**R`**; `**R`** comes from `**hist_returns**`, truncated by `**subset_returns_for_cvar**`; if missing, use **RNG(0)** to synthesize the sample; return name `**min_cvar`**, and gives `**cvar`**.

Constraints: `**Σ w_i = 1**`, `**w_i ∈ [0,1]**`, **SLSQP** `**maxiter=500`**.

### 2.3 `**blocked_symbols` Renormalization**

Phase1 diagnostics `**weight_zero`** or `**basic_logic_failure`** targets into `**blocked_symbols**`. `**_apply_blocked_renorm**`: **Blocked positions are cleared**, **The remaining weights are normalized according to the sum**; if there is no allocated target, it will fall back to **Equal weight for surviving targets**.

### 2.4 **Customized weight mapping in pipeline (`_custom_weights_for_symbols`)**

Session/UI keys (such as `**TSMC`** → `**TSM`**, `**GLD**` → `**AU0**`) are merged into **non-negative vectors**, **simplex normalization**; fallback to **equal weight** when all zeros. The result is written to `**Phase3Input.custom_portfolio_weights`**, and `**w_custom**` (used for defense validation fields) is also obtained through `**_apply_blocked_renorm**` in `**run_phase3`**, and **has no forced binding** to the gray column of Fig3.2** (see §2.1).

---

## 3. Data Provenance


| Project | Description |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Blue column weights** | `**snap_json["phase3"]["weights"]`** |
| **Objective function label** | `**snap_json["phase3"]["objective_name"]`** ∈ `**max_sharpe`** / `**caution_semantic**` / `**min_cvar**` |
| **Defense Level (integer)** | `**snap_json["defense_level"]`** (consistent with the `**DefenseLevel`** enumeration) |
| **Column order / Universe** | `**snap_json["phase0"]["meta"]["symbols_resolved"]`** (column `**x`** aligned with the sequence, filtered `**s in weights**`) |
| **Margin μ** | `**pipeline` μ assembly**: `p2.model_mu.get(p2.best_model_per_symbol.get(s, "naive"), {}).get(s, float(hist_mu.get(s, 0.0)))` (extract), see `**research/pipeline.py`** |
| **Σ** | **Training window sample covariance**, diagonal **Lower bound 1e-10** |
| **Blocking Collection** | Phase1 `**diagnostics`** `**weight_zero` / `basic_logic_failure`** Aggregation |


---

## 4. Quick overview of formulas (corresponding to drawing and §2)

**Benchmark gray columns (without `custom_weights`)**: **1/N** each, **N=s\in symbols: s\in weights** (consistent with the `**fig_weights_compare`** implementation).

**Optional gray columns (passed in `custom_weights`)**: Same as investment view `**Figure3.2-Inv.md`** —
**\tilde w^{\mathrm{cust}}_i = \max(0,w^{\mathrm{cust}}_i) / \sum_j \max(0,w^{\mathrm{cust}}_j)**.

**Sharp Branch (Level 0)**:
**\mu_{p}=w^\top\mu**, **\sigma_{p}=\sqrt{w^\top\Sigma w}**, the objective is to minimize `**−(μ_p − r_f)/σ_p`** (`**r_f=0`**).

**Signal branch (Level 1)**: **\sigma_p + \lambda \sum_i w_i \cdot \max(0,-S_i)** (`**S_i`** from `**inp.sentiments`**).

**Circuit branch (Level 2)**: **Minimize CVaRα** (left tail mean loss) on the historical sample path, see the source code `**_cvar_loss`**.

---

## 5. Calculation Chain


| Step | Calculation Object | Input | Output |
| --- | ------------------- | --------------------------------------------------- | --------------------------------------------------- |
| 1 | `**train`** income statement | `**returns**`, `**train_mask`** | **Row complete training samples** (consistent with Phase2 `**dropna(how="any")`**) |
| 2 | `**μ`**, `**Σ**` | `**run_phase2**` results, training gains | **margin vector + covariance matrix** |
| 3 | `**DefenseLevel`** | Phase1/2 Diagnostics + `**DefensePolicyConfig`** | `**level**` |
| 4 | `**w_raw**` | `**AdaptiveOptimizer.optimize(level)**` | **Dictionary weight + `objective_name`** |
| 5 | `**phase3.weights**` | `**w_raw**` + `**blocked_symbols**` | `**_apply_blocked_renorm**` |
| 6 | **Fig3.2 Figure object** | `**weights`**, `**symbols`**, `**custom_weights**` (optional) | `**go.Bar`×2 · `barmode=group**` |


---

## 6. Key data calculation example (important values)

The following **several examples** explain **ruler and image reading**; **specific blue column coordinates** change with `**data.json`**, defense analysis and blocking set, **based on the same pipeline snapshot**.

### 6.0 Prerequisite (Phase2 shadow model selection, same origin as Fig2.1 §6.1)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

**Model selection full table / NVDA MSE / combined / full sample shadow MSE** See **`Figure2.1-Res.md` §6.2～§6.4**.

### 6.1 **UI Baseline (Current Implementation)**

`**dash_app/app.py`** calls `**fig_weights_compare(weights, symbols, tpl, ...)`** **Not passed** `**custom_weights`** → **Gray column name** **"Equal weight basis"**, the height of each mark is **1/N**.

### 6.2 **Algebraic chart reading (consistent with Investment View §3)**

Assume **N=10**, no custom control: each gray column is **0.100**. If `**phase3.weights["AU0"]=0.283`** in the same run (example: Jinxianhu main company), then the **blue column column is 0.283**, which means that **under the circuit breaker/alert and other paths** optimization will allocate **more capital** to the target (relatively equal weight).

### 6.3 **Snapshot Verification**

1. `**sum(snap_json["phase3"]["weights"].values()) ≈ 1`** (within floating point error).
2. For `**weight_zero`/`basic_logic_failure**` target **k** in `**snap_json["phase1"]["diagnostics"]`**: `**weights[k]=0`**.
3. `**snap_json["phase3"]["objective_name"]`** is **semantically consistent** with `**snap_json["defense_level"]**` (**0↔max_sharpe**, **1↔caution_semantic**, **2↔min_cvar**, subject to the source code `**AdaptiveOptimizer.optimize`**).

---

## 7. Source code anchor (traceable)

**Optimization and blocking:**
```python
# research/phase3.py — AdaptiveOptimizer.optimize (excerpt)
if level == DefenseLevel.STANDARD:
    res = minimize(self._sharpe_obj, w0, method="SLSQP", ...)
    return {self.symbols[i]: float(w[i]) for i in range(n)}, "max_sharpe", sh, None
# ... CAUTION / MELTDOWN ...
w = _apply_blocked_renorm(w_raw, syms, blocked)
```**Histogram:**
```python
# dash_app/figures.py — fig_weights_compare (excerpt)
if custom_weights:
    w_cust = [max(0.0, float(custom_weights.get(s, 0.0))) for s in syms]
    t = sum(w_cust) or 1.0
    first_y = [v / t for v in w_cust]
else:
    first_y = [eq] * n   # eq = 1.0 / n
```---

## 8. Consistency check

1. Read `**snap_json["phase3"]["weights"]**` and `**symbols_resolved**` (in the same order).
2. Rerun `**run_pipeline`** (or source-level replay `**run_phase3`** input) using the same `**DefensePolicyConfig**`, returns `**returns**`, window mask and Phase1/2 **output**.
3. `**weights**` dictionary **Key-by-key numerical consistency** (tolerating machine precision).
4. **Manual random inspection**: The blocked target **weight is 0**; the non-blocked target **is non-negative and the sum is 1**.

---

## 9. With Fig3.3 / Phase 2 (Simplified)

- **Fig3.3** (Dual Track MC) generates combined price paths using **the same set of optimization weights** `**w`** (via `**_simulate_mc_paths`**); Fig3.2 is a **static cross-section** of that `**w**`.  
- **Fig3.1** / **Fig2.1** The pixel matrix determines the column selection of `model_mu` in the **μ prior** (see `**run_pipeline`** **μ assembly**); **Fig3.2** **Does not repeat** the model selection logic, only shows the **Phase 3 optimization results**.

---

**Placeholder**: `**{n_symbols}`** · `**0`** · `**{objective_name}`**