# FigX.5 · Model–model stress test (JSD time-series) (Research · Category C)

**Object type (C)**: a key scalar series produced by in-house research. Within the test window this object compresses the "forecast-distribution divergence" among the three structural models (ARIMA / LightGBM / Kronos) into a per-day JSD (triangle-mean) series, and builds a dynamic threshold from a rolling train-window baseline, producing `jsd_stress` (trigger flag) and the displayed threshold `jsd_stress_dyn_thr`.

The question it answers is:

> **Is the model ensemble still speaking within "the same probabilistic world"?**  
> When the probability-density divergence between models keeps growing beyond the normal fluctuation range of the training window, we declare a "model–model stress" state, which can fire Level 2 (circuit-breaker).

This document is aligned with the sidebar render template: `dash_app/render/explain/sidebar_right/figx5.py` · `build_figx5_explain_body(...)` injects placeholders:  
`0.00000000`, `0.00000000`, `0.00000000`, `0.00000000`, `0.00000000`, `0.00000000`, `5`, `2.0000`, `1.0000e-09`, `0.00000000`, `0`, `—`, plus the common fields `—`, `—`, `—`, `—`, ``, `0.00000000`, `否` (from the phase2 snapshot).

> **Unified window policy**: starting from this revision the rolling window **W** used by the JSD-stress detector is shared with FigX.6's semantic-numeric rolling cosine through a single policy field `DefensePolicyConfig.semantic_cosine_window` (sidebar "W rolling-window length", default **5 trading days**). The same W drives both the training rolling baseline and the test-window alarm rolling mean. The white solid line labelled **rolling triangle mean (W=5, alarm calibration)** on the chart is the actual trigger series for the red "first breach" vertical line. The legacy parameter `n_jsd` has been retired.

Placeholders: `**0.00000000`** · `**0.00000000**` · `**否**`

---

## 1. Chart pipeline (end-to-end)

```text
Phase2 strict OOS: for each test day t, fit each model's μ/σ using only I_{t-1}
  → compute three pairwise JSDs per symbol (Kronos–ARIMA / Kronos–LGBM / LGBM–ARIMA)
  → cross-sectional mean (average across symbols) per day:
      daily_tri[t] = mean_s JSD_triangle(s,t)
  → rolling train-window baseline jsd_baseline_mean (window W = policy.semantic_cosine_window)
  → dynamic threshold τ = k_jsd × max(jsd_baseline_mean, eps)
  → stress trigger: any W-day rolling mean(daily_tri) > τ ⇒ jsd_stress=True
  → Dash: fig_defense_jsd_stress_timeseries (daily triangle + white rolling triangle mean (W=5) + threshold line + first-breach vertical line)
```

---

## 2. In-house algorithm architecture (methodology core)

### 2.1 Why JSD: turn "model divergence" into a comparable probabilistic distance

The output of every model is ultimately harmonised in Phase 2 into a Gaussian \mathcal{N}(\mu,\sigma^2) (per day, per asset). JSD has two useful properties:

- **Symmetric**: \mathrm{JSD}(P,Q)=\mathrm{JSD}(Q,P), well-suited for an undirected "model–model stress" distance.
- **Bounded**: unlike KL, it does not blow up in some configurations, making threshold engineering tractable.

### 2.2 Why the "triangle mean": three edges summarise the ensemble-level divergence of three structural models

Three structural models form three pairwise edges; using the triangle mean avoids the bias of "looking at only one pair of models" and better matches the semantics of "is the model set as a whole in agreement?".

---

## 3. Data provenance & physical profile

### 3.1 Data fingerprint

- Test-date series: `phase2.test_forecast_dates`
- Daily triangle-mean series: `phase2.test_daily_triangle_jsd_mean`
- Training baseline: `phase2.jsd_baseline_mean`
- Trigger flag: `phase2.jsd_stress`

### 3.2 Variable mapping (injected at runtime)


| Variable                       | Field                                 | Injected value                                               |
| ------------------------------ | ------------------------------------- | ------------------------------------------------------------ |
| Triangle mean (cross-day mean) | `phase2.jsd_triangle_mean`            | `**0.00000000`**                                    |
| Max-of-three-edges mean        | `phase2.jsd_triangle_max`             | `**0.00000000**`                                     |
| Dynamic threshold              | `k_jsd×max(baseline,eps)`             | `**0.00000000**`                                   |
| Triggered?                     | `phase2.jsd_stress`                   | `**否**`                                           |
| Daily tail (audit)             | `phase2.test_daily_triangle_jsd_mean` | `len=0`, tail=`—` |


---

## 4. Algorithm execution chain


| #   | Logical stage          | Input                       | Output                                     | Core algorithm / rule                                                  | Code anchor                                                               |
| --- | ---------------------- | --------------------------- | ------------------------------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 1   | OOS μ/σ series         | `returns`, `test_dates`     | `model_mu_test_ts` / `model_sigma_test_ts` | strict I{t-1}                                                          | `research/phase2.py:run_phase2`                                           |
| 2   | Triangle JSD (daily)   | per-day μ/σ (cross-asset)   | `test_daily_triangle_jsd_mean`             | pairwise JSD → triangle mean → cross-section mean                      | `research/phase2.py:_js_divergence/_triangle_js`                          |
| 3   | Train rolling baseline | `train`                     | `jsd_baseline_mean`                        | rolling triangle mean over window `W = policy.semantic_cosine_window` (default 5), then take its mean | `research/phase2.py` (baseline section)                                   |
| 4   | Stress trigger         | `daily_tri`, `k_jsd`, `eps` | `jsd_stress`                               | any rolling-mean breach (fallback to full-window mean if insufficient) | `_jsd_stress_rolling_breach`, `research/phase2.py`                        |
| 5   | Plot                   | `p2`                        | FigX.5                                     | series + threshold line + first-breach vertical line                   | `dash_app/figures.py:fig_defense_jsd_stress_timeseries`                   |
| 6   | Text injection         | `snap_json` + `policy`      | placeholder substitution in this file      | template substitution                                                  | `dash_app/render/explain/sidebar_right/figx5.py:build_figx5_explain_body` |


---

## 5. Source-code anchors (traceable)

- `research/phase2.py`: `run_phase2` (`daily_tri`, `jsd_baseline_mean`, `jsd_stress`)
- `dash_app/figures.py`: `fig_defense_jsd_stress_timeseries` (threshold-line definition and breach annotation)
- `dash_app/figures.py`: `fig_fig41_jsd_early_warning` (overlays t_ref/t_alarm on the FigX.5 base plot; see Fig4.1)

---

## 6. Consistency check (reproducible verification steps)

1. Verify that `len(test_forecast_dates)` equals (or is truncated to align with) `len(test_daily_triangle_jsd_mean)`.
2. Re-compute the threshold by hand: \tau=k\cdot\max(baseline,\varepsilon), and check it matches `0.00000000`.
3. Re-compute the breach: if any rolling-window mean exceeds the threshold, `否` should be "Yes"; otherwise "No" (apply the fallback rule when samples are insufficient).

---

## 7. Relationship with other objects (responsibility boundaries)

- **vs FigX.4 (credibility)**: the two share `jsd_triangle_mean`; FigX.5 emphasises "stress triggered?" (boolean), whereas FigX.4 maps divergence to a "credibility score" (continuous scalar) with an additional coverage penalty.
- **vs Fig4.1 (warning effectiveness)**: Fig4.1a uses the FigX.5 series as its base plot, overlaying `t_ref/t_alarm` to test whether the "1–5 day ahead" claim holds.

---

## 8. Methodological limitations

- **Gaussianisation approximation**: here JSD compares \mathcal{N}(\mu,\sigma^2); when actual returns / forecast distributions are materially non-Gaussian (heavy-tail, skewed), JSD only reflects divergence under the "Gaussian projection".
- **Cross-sectional mean dilutes local extremes**: when divergence concentrates in a few assets / a few dates, both cross-asset and cross-day means dilute the peaks; to locate root causes, inspect `phase2.jsd_by_symbol` or the per-day three-edge series directly.
- **Threshold depends on training-window stability**: `jsd_baseline_mean` is estimated by a rolling window on the training set; if the training window itself contains structural breaks, the baseline becomes biased high (causing false negatives); if too quiet, the baseline becomes biased low (causing false positives).
- **Sensitive to rolling-window parameters**: `semantic_cosine_window` (W, shared with FigX.6) and `k_jsd` control sensitivity; aggressive values cause `jsd_stress` to flip frequently and hurt strategy stability. A short W (=5) is more sensitive to a first-day breach but also more easily lit up by single-day noise — inspect the white rolling-mean line on the chart together with the threshold.

---

## Defense-Tag (If-Then conditional)

**If** `rolling triangle-JSD stress trigger = 否` **Then**
`FigX.5: on {jsd_alarm_date}, rolling triangle-JSD mean = {jsd_mean_at_breach} first exceeded τ = 0.00000000 → {jsd_alarm_date} is the first alarm day; defense level switches to Level 2`
`severity: danger`

**Else**
`FigX.5: rolling triangle JSD does not exceed τ=0.00000000; this variable has no direct effect on defense-level transitions`
`severity: success`