# FigX.3 · Asset Anomaly Diagnosis (ADF / Volatility / AC1) (Research · Category C)

**Object type (C)**: Self-developed method "asset-level evidence collection". The task of FigX.3 is not to output a new numerical model, but to organize the asset-by-asset diagnosis and threshold system of Phase 1 into auditable evidence, answering:

- Which assets do not meet the stability prerequisite in the training window (ADF pipeline has not passed the test)?
- Which assets have **high volatility** or **low AC1** engineering risks that may lead to model distortion/weight instability?

These evidences are used by state machines/policies for "asset-level justification" in Level 1, and may go into `blocked_symbols` (zeroed and normalized) in Phase 3.

This article is aligned with the sidebar rendering template: `dash_app/render/explain/sidebar_right/figx3.py` · `build_figx3_explain_body(...)` will inject placeholders: `{h_struct_short}`, `{tau_h1}`, `{tau_vol_melt}`, `{tau_return_ac1}`, and expand block `{adf_fail_assets_md}` / `{vol_assets_md}` / `{ac1_assets_md}`.

Placeholder: `**{h_struct_short}**` · `**{tau_vol_melt}**` · `**{tau_return_ac1}**`

---

## 1. Graphics pipeline (end-to-end)
```text
close_universe → daily_returns → returns
  → Phase1: run_phase1(...)
→ diagnostics[*]: ADF / differential order / Ljung–Box / vol_ann / ac1 / basic_logic_failure / stationary_returns ...
→ Dash (sidebar research block):
→ diagnostic_failed_adf(d) forms ADF failed list
→ vol_ann > tau_vol_melt forms a high volatility list
→ ac1 < tau_return_ac1 forms low AC1 list
→ FigX.3: Three lists + “comprehensive judgment” description
```---

## 2. Self-developed algorithm logic architecture (core methodology)

### 2.1 Why do we need “asset-level evidence collection”: State machines need “explainable micro reasons”

Relying only on "macro scalars" such as structural entropy, JSD or credibility will have an engineering gap: when the system enters Level 1, users will ask "which assets are causing the increased risk?" FigX.3 complements this layer of explanation so that changes in defense level can be traced back to:

- **Statistical premise failed** (ADF failed: the model has no reliable premise on this asset)
- **Abnormal risk pattern** (high volatility: weight/variance estimates are unstable; low AC1: return structure is closer to noise or strong mean reversion, easily violating the linearity assumption)

### 2.2 Engineering semantics of three types of evidence

- **ADF has not passed**: It means "the training window income does not meet the stability/logical closed loop", and it is more likely to be downgraded or eliminated when entering Phase 3.
- **High Fluctuation**: stands for "Error Amplifier". Under the same model divergence, highly volatile assets are more likely to thicken the tail risk of the portfolio.
- **Low AC1**: represents "short-term structural instability/reversal". If the model implicitly assumes trend or inertia, AC1 that is too low can lead to a mismatch between predictions and realistic directions.

---

## 3. Data Provenance & Physical Profile

### 3.1 Data fingerprint

- Diagnostics from: `snap_json["phase1"]["diagnostics"]` (per-asset dict list)
- Threshold value comes from: `DefensePolicyConfig` (sidebar parameter)
- Context scalar: structural entropy `**{h_struct_short}**` and threshold `τ_h1=**{tau_h1}**` (used to illustrate "whether the macro environment has been biased towards Level1")

### 3.2 Variable mapping

- **Enter X**:
  - `diagnostics[*].stationary_returns/basic_logic_failure/vol_ann/ac1`
  - `policy.tau_vol_melt={tau_vol_melt}`
  - `policy.tau_return_ac1={tau_return_ac1}`
- **Output Y (sidebar expander)**:
  - `{adf_fail_assets_md}`: ADF uncleared asset list
  - `{vol_assets_md}`: List of highly volatile assets
  - `{ac1_assets_md}`: Low AC1 asset list

---

## 4. The Execution Chain

| Sequence number | Logic stage | Input variables | Output target | Core rules | Code anchor |
| --- | --- | --- | --- | --- | --- |
| 1 | Logarithmic returns and tests | Training windows close/returns | per-asset diagnostics | ADF differential pipeline + Ljung–Box et al | `research/phase1.py:run_phase1` |
| 2 | ADF failure caliber | `diagnostics[*]` | ADF fail list | `not (stationary_returns and not basic_logic_failure)` | `research/defense_state.py:diagnostic_failed_adf` |
| 3 | High volatility caliber | `vol_ann`, `tau_vol_melt` | vol list | `vol_ann > tau_vol_melt` | `dash_app/render/explain/sidebar_right/figx3.py:build_figx3_explain_body` |
| 4 | Low AC1 caliber | `ac1`, `tau_return_ac1` | ac1 list | `ac1 < tau_return_ac1` | Same as above |

---

## 5. Key data calculation example (important values · Phase2 prerequisite column)

The following **§5.1** has the same origin as **`Figure2.1-Res.md` §6.1**, making it easy to align with the same snapshot of **Shadow mode selection**; **§6.2～§6.4** For the full list of mode selection, see **`Figure2.1-Res.md` §6.2～§6.4**. Subsequently **§5.2～§5.4** are still **FigX.3 runtime injection list** (not to be confused with the above).

### 5.1 Premise (same origin as Fig2.1 §6.1)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

### 5.2 Full model selection table and NVDA decomposition (cross-reference)

See **`Figure2.1-Res.md` §6.2～§6.4**.

---

## 6. Key data calculation example (runtime injection · FigX.3 list)

### 6.1 Assets that failed ADF inspection (training window)

{adf_fail_assets_md}

---

### 6.2 High Volatility Assets (Annualized Volatility > τ_vol_melt)

Threshold: `τ_vol_melt = {tau_vol_melt}`

{vol_assets_md}

---

### 6.3 Low autocorrelation assets (AC1 < τ_return_ac1)

Threshold: `τ_return_ac1 = {tau_return_ac1}`

{ac1_assets_md}

---

## 7. Source code anchor (traceable)

- `research/phase1.py`: generate `diagnostics` (`vol_ann`, `ac1`, `basic_logic_failure`, `stationary_returns`)
- `research/defense_state.py`: `diagnostic_failed_adf` (unified caliber of ADF failure)
- `dash_app/sidebar_figx_md.py`: `build_figx3_explain_body` (manifest generation and placeholder injection)

---

## 8. Consistency check (reproducible verification steps)

1. Run Phase1 with the same training window data and check that the `diagnostics` fields are complete and the values can be parsed.
2. Use the `diagnostic_failed_adf` caliber to recalculate the ADF failed asset list, which should be consistent with `{adf_fail_assets_md}`.
3. Recalculate the high volatility/low AC1 list with thresholds, which should be consistent with `{vol_assets_md}`/`{ac1_assets_md}`.

---

## 9. Relationship with other objects (responsibility boundaries)

- **With FigX.2 (Structural Entropy)**: Structural Entropy provides "system-level context" and FigX.3 provides "asset-level root causes". Level1 has the strongest explanation when structural entropy is low and ADF failure assets are high.
- **and Phase3 blocked_symbols**: ADF failure and "logical closed loop failure" will cause some asset weights to be cleared and normalized; FigX.3 is the source of evidence for this behavior.

---

## 10. Method limitations

- **Multiple testing and threshold sensitivity**: ADF/LB/AC1 has multiple comparison problems when used simultaneously on multiple assets; this system uses engineering thresholds instead of statistical significance correction, and the explanation should be based on "risk tips" rather than "strict statistical conclusions".
- **Training window dependence**: All diagnoses only look at the training window; if the training window structure is completely different from the test window, the diagnosis may lag or be distorted.
- **Acausality of AC1**: Low AC1 is just a morphological indicator, not equivalent to "certain failure"; it is more like a priori risk that "model assumptions may be violated".
- **Frequency assumption of annualized fluctuations**: `vol_ann` is annualized with 252 trading days, assuming that daily frequency returns are approximately the same distribution; in markets with strong volatility aggregation, this scaling is only approximate.

---

## Defense-Tag (If-Then conditional expression)

**If** `There is ADF failed or high volatility or low AC1` **Then**
`FigX.3: Asset diagnostics found anomalies (see list) → Source of asset-level justification as Level 1`
`severity: warn`

**Else**
`FigX.3: No significant anomalies were found in asset-level diagnosis; current variables have no direct impact on defense level switching`
`severity: success`

> The copywriting uses `content-CHN/defense_reasons.md` as the source of fact; if you need to modify it, please update the summary table simultaneously.