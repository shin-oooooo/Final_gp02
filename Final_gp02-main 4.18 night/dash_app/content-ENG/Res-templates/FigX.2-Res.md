# FigX.2 · Structural Entropy (Research · Category A)

**Object Type (A)**: Basic statistics and structural diagrams. This object compresses the "return covariance spectrum structure of the end window of the training period" into a scalar H_{\mathrm{struct}}\in[0,1], which is used to characterize whether cross-sectional risks are converging (whether diversification is failing). This amount will be directly consumed by the defense state machine `resolve_defense_level(...)` and is one of the important trigger factors of Level 1/2.

This document is the **text source of truth** (mainly source code) of the "Explanation Cards in Research Mode", which is semantically consistent with the graphical display (rail/gauge) of the sidebar FigX.2.

Placeholders (recommended to align with snapshots/injectors): `**{train_start}`** · `**{train_end}`** · `**{entropy_window}**` · `**{h_struct}**` · `**{tau_h1}**` · `**{tau_h_gamma}**` · `**{gamma_multiplier}**`

---

## 1. Graphics pipeline (end-to-end)
```text
data.json → load_bundle.close_universe
  → daily_returns(close[symbols]) = rets
  → resolve_dynamic_train_test_windows(...) → train_mask
  → Phase1: run_phase1(rets.loc[train_mask], Phase1Input, DefensePolicyConfig, close_train)
→ h_struct (structural entropy)
→ gamma_multiplier (γ multiplier: 3 when h_struct < τ_h_gamma, 1 otherwise)
→ UI (sidebar FigX.2 rail / or main bar gauge): display h_struct and threshold τ_h1
  → Defense state machine：resolve_defense_level(..., h_struct=h_struct, ...)
```---

## 2. Data Provenance


| Project | Description |
| ---------- | ------------------------------------------------------------------------------------------------ |
| **Returns panel** | `rets = daily_returns(close[symbols]).dropna(how="all")` (simple daily returns); Structural entropy uses the training window `rets.loc[train_mask]`. |
| **Row Complete Alignment** | Use `sub = rets.dropna(how="any")` before calculating the structural entropy, that is, if **any target lacks a return, the entire row will be eliminated** (ensure that the covariance matrix can be calculated).                           |
| **Last window length** | `entropy_window` (default 21), read from `Phase1Input.entropy_window`.                                       |
| **Output fields** | `snap_json["phase1"]["h_struct"]` and `snap_json["phase1"]["gamma_multiplier"]`.                   |


---

## 3. Methodology and mathematical objects

### 3.1 From covariance spectrum to "structural entropy"

The aligned last window return matrix is recorded as R\in\mathbb{R}^{W\times n} (W=\texttt{entropywindow}, n=number of assets), and the covariance matrix is:

\mathbf{C}=\mathrm{Cov}(R)\in\mathbb{R}^{n\times n}.

Perform eigendecomposition on \mathbf{C} to obtain eigenvalues \lambda_1,\ldots,\lambda_n, and perform lower bound protection:

- \lambda_k \leftarrow \max(\lambda_k, \varepsilon), where \varepsilon=10^{-18};
- p_k = \lambda_k / \sum_j \lambda_j;

Define original entropy and normalized structural entropy:

H_{\mathrm{raw}}=-\sum_{k=1}^{n} p_k\ln p_k,\qquad
H_{\mathrm{struct}}=\frac{H_{\mathrm{raw}}}{\ln n}\ (n\ge 2).

**Explanation**:

- H_{\mathrm{struct}}\to 1: The spectrum is more uniform (multi-factor dispersion), and the cross-sectional structure is more "rich";
- H_{\mathrm{struct}}\to 0: The spectrum is more concentrated (common factors dominate), asset returns are more consistent, and diversification is more fragile.

Implementation: `research/phase1.py:structural_entropy`.

### 3.2 Rollback for insufficient samples

If `len(sub) < entropy_window`, Phase1 will directly fall back `h_struct` to `1.0` (to avoid misjudgment on small sample covariance), see `research/phase1.py:run_phase1`.

---

## 4. Calculation Chain


| step | calculation object | input | output | logic/function |
| --- | ------ | -------------------------- | ------------------------ | ---------------------------------------- |
| 1 | Training window income table | `rets.loc[train_mask]` | `rets_train` | `research/pipeline.py` |
| 2 | Row complete subtable | `rets_train` | `sub = dropna(how="any")` | `run_phase1` |
| 3 | Last window slice | `sub` | `tail = sub.iloc[-W:]` | `run_phase1` |
| 4 | Covariance | `tail` | `cov = tail.cov()` | pandas default ddof=1 |
| 5 | Structural entropy | `cov` | `h_struct` | `structural_entropy(cov)` |
| 6 | γ multiplier | `h_struct` + `tau_h_gamma` | `gamma_multiplier` | `3.0 if h_struct < tau_h_gamma else 1.0` |


---

## 5. Threshold semantics (aligned with defense logic)

### 5.1 τ_H1 (main threshold of structural entropy)

`tau_h1` comes from `DefensePolicyConfig.tau_h1` (sidebar slider). When H_{\mathrm{struct}}<\tau_{H1}, it is usually interpreted as "increased risk of cross-sectional structural convergence" and can participate in Level 1 triggering in `resolve_defense_level` (needs to be adjudicated together with other signals).

### 5.2 τ_Hγ and γ multiplication (engineering gain)

`tau_h_gamma` is more engineering-oriented: when H_{\mathrm{struct}}<\tau_{H\gamma}, Phase1 outputs `gamma_multiplier=3.0`, which is used to "accelerate" certain subsequent penalty/threshold linkages (see `research/phase1.py`).

---

## 6. Key data calculation example (important values)

**FigX.2** uses **`phase1.h_struct`** and is **independent** from Phase2 mode selection; the following **§6.1** is still aligned with the full library **`Figure2.1-Res.md` §6.1** to facilitate intra-session comparison of the same `data.json` **Whether the shadow holdout parameters are consistent with the pipeline**. See **`Figure2.1-Res.md` §6.2～§6.4** for the numerical table of modulus selection.

### 6.1 Premise (same origin as Fig2.1 §6.1)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

### 6.2 Cross-reference

Model selection **MSE / combined / full sample shadow MSE** See **`Figure2.1-Res.md` §6.2～§6.4**.

---

## 7. Source code anchor (traceable)

- **Structural entropy implementation**: `research/phase1.py:structural_entropy`
- **Phase1 output writing**: `research/phase1.py:run_phase1` (`h_struct`, `gamma_multiplier`)
- **Defense state machine consumption**: `research/defense_state.py:resolve_defense_level(..., h_struct=...)`
- **Pipeline entry**: `research/pipeline.py:run_pipeline` (construct `Phase1Input` and call `run_phase1`)
- **UI display**:
  - Sidebar rail: `dash_app/ui/metric_rails.py` (structural entropy bar rail)
  - Main column gauge (if enabled): `dash_app/figures.py:fig_entropy_gauge`

---

## 8. Consistency check

1. Take the same `data.json` and the parsed start and end dates of the training window, and get `rets_train = rets.loc[train_mask]`.
2. Compound calculation `sub = rets_train.dropna(how="any")`, if `len(sub) ≥ W`:
  - `tail = sub.iloc[-W:]`
  - `cov = tail.cov().to_numpy()`
  - `h' = structural_entropy(cov)`
3. Check that `h'` is consistent with the snapshot `snap_json["phase1"]["h_struct"]` (machine precision is tolerated).
4. Check `gamma_multiplier == (3.0 if h_struct < tau_h_gamma else 1.0)`.

---

## 9. Relationship with other objects (responsibility boundaries)

- **With Figure0.2 (correlation heat map)**: 0.2 shows the pairwise Pearson correlation; FigX.2 shows the "overall concentration of the covariance spectrum", which is a higher-level structural compression indicator.
- **and Phase 3**: When structural entropy is low, the dispersion assumption is weaker; even if point predictions are still available, the optimization may be more biased towards the robust goal (co-determined with other signals).