# P4 · Final conclusion analysis (shared source for Fig 4.1 + Fig 4.2)

> **Namespace convention**: This file hosts both the Fig 4.1 and Fig 4.2
> conclusion sections. They are distinguished by a prefix in the H2 headings:
> `## Fig4.1 · Case X` / `## Fig4.2 · Case X`. The frontend indexes on the
> combined prefix + case letter, so the two figures never bleed into each other.
>
> **Placeholders**:
>
> - Fig 4.1: `{mm_verdict}` / `{mv_verdict}` / `{mm_t0_date}` / `{mv_t0_date}` /
>   `{final_t0_date}` / `{earliest_t0_date}`
> - Fig 4.2: `{term_ms}` / `{term_cw}` / `{term_cv}` / `{term_mdd_ms}` /
>   `{term_mdd_cw}` / `{term_mdd_cv}` / `{mc_pass}` / `{mc_mdd_pass}` /
>   `{defense_pass}`

---

## Fig4.1 · Thesis

Collective impairment of asset-class diversification under stress can be
detected **1–5 trading days ahead** by **"model–model stress test"** together
with **"model-stress × market-load direction test"**. Because (i) the test
window is finite and (ii) research events (e.g. geopolitical shocks) tend to
be exogenous and persistent, we treat **at most one** "market logic-break"
episode within the test window. When both independent checks fire, **prefer
the model–market alert date as the final alert**: the model–market test
directly measures **narrative / load-direction drift relative to the price
path**, closer to real non-stationary market behavior, whereas model–model
stress (JSD) reflects only predictive-distribution disagreement and does
**not** map one-to-one to realized market-regime change.

---

## Fig4.1 · Case A · Both alerts succeed (final choice: model–market)

- **Model–model**: `{mm_verdict}`, alert date `{mm_t0_date}`
- **Model–market**: `{mv_verdict}`, alert date `{mv_t0_date}`
- **Final alert date (model–market preferred)**: **`{final_t0_date}`**

**Conclusion**: The two independent checks corroborate each other; narrative
and statistical lenses both point to structural strain around
**`{final_t0_date}`**. At the conclusion layer the system adopts
**`{mv_t0_date}`** as the final alert date; the model–model date
**`{mm_t0_date}`** serves as an internal consistency check.

---

## Fig4.1 · Case B · Only "model–model" succeeds (⚠ lower informational value)

- **Model–model**: `{mm_verdict}`, alert date `{mm_t0_date}`
- **Model–market**: `{mv_verdict}`

> ⚠ **Lower informational value**: Only the inter-model disagreement (JSD) has
> fired while narrative / load direction has **not** diverged from the price
> path. This signals **elevated predictive uncertainty**, but **not**
> necessarily **market-level structural failure**; whenever **`{mm_t0_date}`**
> is used as a reference alert, this caveat must be reported alongside it.

**Conclusion**: Treat **`{mm_t0_date}`** as a **reference** alert date only.
Substantial predictive-distribution disagreement (JSD stress above baseline)
indicates the three structural models hold materially inconsistent views of
the forward return distribution; however, the rolling semantic–numeric
cosine stays ≥ 0 over the same window, showing **no directional divergence
between narrative and price yet**. The signal alone **does not justify** a
"market logic-break" verdict; conclusions must remain cautious and be tagged
"lower informational value."

### Follow-up diagnostics (priority order)

1. **Per-model diagnostics**: Inspect Phase 2's `prob_nll_mean` /
   `prob_dm_pvalue_vs_naive` / `prob_coverage_95` for ARIMA / LightGBM /
   Kronos OOS behavior:
   - If **a single model** exhibits markedly worse NLL and DM indicates it
     underperforms Naive, the elevated JSD most likely reflects that model's
     **parameter drift**; remedy by **triggering retraining or adjusting
     `oos_fit_steps`**.
   - If **all three** degrade in the same direction, a **covariate shift in
     the input features** is more likely; remedy by **revisiting the train
     window**, **expanding the training pool**, or **adding stronger
     regularization**.
2. **Train–test distribution alignment**: Run KS / Wasserstein tests over the
   20–40 trading days **prior** to **`{mm_t0_date}`** to quantify marginal
   distribution drift; if the same-distribution null is rejected, tighten
   `train_end` or retrain.
3. **Narrative-coverage audit**: Cross-reference S_t (sentiment) with the news
   feed to check whether the event *has* occurred but is not yet captured in
   the text dimension. If new-domain keywords (abrupt policy / geopolitical
   vocabulary) are missing, extend the `sentiment_proxy` keyword set and
   re-run the cosine test before revising the verdict.
4. **Statistical discipline**: Do **not** lower `verify_std_quantile_pct` /
   `verify_crash_quantile_pct` / `verify_tail_quantile_pct` ad-hoc to force
   the model–market check to pass; doing so invalidates the independence and
   reproducibility of the checks at the defense layer.

---

## Fig4.1 · Case C · Only "model–market" succeeds

- **Model–model**: `{mm_verdict}`
- **Model–market**: `{mv_verdict}`, alert date `{mv_t0_date}`

**Conclusion**: Use **`{mv_t0_date}`** as the final alert date. Persistent
divergence between semantic load direction and numeric trajectory (rolling
cosine < 0) indicates that **narrative has moved ahead of price / volatility
in reflecting structural change** — a strong market-level impairment signal
with high informational value. Model–model stress (JSD) may still sit below
baseline because:

- The three structural models **have not yet formed consensus disagreement**
  on the new signal (common in the early phase of exogenous events, where
  disagreement shows a lag);
- The models' covariance structure is too homogeneous, so distributional
  disagreement is under-measured.

### Operational notes

1. **Act on the model–market check**: In the five trading days after
   `{mv_t0_date}`, monitor whether the crash / tail share remains above the
   training baseline; if sustained, trigger a Phase 3 defense-level re-evaluation.
2. **Watch for a lagged JSD match**: Keep sampling the JSD series for 3–10
   trading days after `{mv_t0_date}`; if it eventually crosses the baseline,
   that is **time-offset agreement between the two channels** and can be
   reported as evidence of methodological stability.
3. **Strengthen linkage evidence**: Check whether Phase 2's
   `cosine_semantic_numeric` declines monotonically around `{mv_t0_date}`; a
   steep fall coupled with ≥ 2 consecutive negative days constitutes strong
   corroboration.

---

## Fig4.1 · Case D · Both alerts fail (attribution)

- **Model–model**: `{mm_verdict}`
- **Model–market**: `{mv_verdict}`

**Conclusion**: Neither check produced a valid alert within the 1–5
trading-day window. Attribute the miss in the order **"methodology / data
first, models / thresholds second"**:

### Likely causes (by priority)

1. **Test window does not cover the true break day**: the test window is too
   short, or the sampling cadence cannot capture the target event; audit
   whether `test_start` / `test_end` encompass the intended event window.
2. **Training-window contamination**: Structural breaks inside training (e.g.
   post-2024 H2) poison the baseline itself, widening the threshold so that
   any later out-of-sample anomaly cannot clear it. Reset the training window
   to a stable segment and retrain.
3. **Thresholds too conservative**: Train-window quantiles
   (`verify_std_quantile_pct` / `verify_crash_quantile_pct` /
   `verify_tail_quantile_pct`) are too high and suppress triggers that would
   otherwise fire before the event materializes.
4. **Model homogeneity → JSD degeneracy**: The three structural models react
   similarly to new signals, so disagreement is crushed; add a complementary
   model (e.g. an extra nonlinear kernel or a pure statistical model) to
   raise sensitivity.
5. **Semantic proxy mismatch**: Sentiment / load features are weakly linked
   to the target event (e.g. exogenous policy shocks not yet vectorized);
   audit the `sentiment_proxy` keyword set and expand the event-domain
   dictionary.

### Actions

- First reconcile **test span + train span + universe** — any misalignment
  across these three suppresses both checks.
- Only after that should you consider relaxing `verify_*_quantile_pct`.
- If still null, ask whether a structural break **actually exists** in the
  data; if not, interpret the result as **correct stability detection** for
  this window, not as a "failed warning."

---

---

## Fig4.2 · Case A · Level 0 and the blue/red curves overlap

`defense_level = 0` and `test_equity_cvar ≡ test_equity_max_sharpe`. The
Adaptive Optimizer is not active; its output coincides with Max-Sharpe, so
the red line perfectly overlays the blue line in the chart, and the MC
counterfactual block reduces to "no extra tail comparison." In this case
`defense_pass = {defense_pass}` is reported only as a baseline; no further
verification is required.

---

## Fig4.2 · Case B · Level 0 but blue/red curves disagree

`defense_level = 0` but `test_equity_cvar ≢ test_equity_max_sharpe`. This
should not happen under the pipeline contract and indicates a consistency
anomaly. Investigate in order:

1. Whether the `w_cvar` calculation path accidentally entered the Level 2
   branch;
2. Whether the `test_returns_daily` input matches what the solver received;
3. Whether `resolved_custom_weights` / `blocked_symbols` filtering is applied
   inside `run_phase3`.

**Conclusion**: Until the anomaly is resolved, the Fig 4.2 evidence on this
page is **not reliable** (`defense_pass = {defense_pass}`).

---

## Fig4.2 · Case C · Strategy construction successful (optimal)

`defense_level ≥ 1`, `|test_mdd_pct_cvar|` is the smallest of the three
curves, and `test_terminal_cumret_cvar` is also the highest. The Adaptive
Optimizer compresses drawdown while preserving cumulative return. This
verifies the **"logic circuit-breaker"** design — automatically switching to
a CVaR-minimizing strategy once the failure condition is detected — as the
mechanical inevitability for facing black-swan events: it trades off a small
excess return in calm periods for survival probability in the extreme.

---

## Fig4.2 · Case D · Strategy construction successful (primary objective met)

`defense_level ≥ 1`, `|test_mdd_pct_cvar|` is the smallest, but
`test_terminal_cumret_cvar` is **not** the highest. The Adaptive Optimizer
**trades cumulative return for the lowest MDD**, which is consistent with
the design goal "prioritize defense over return during circuit-break."

---

## Fig4.2 · Case E · Strategy construction failed

`defense_level ≥ 1` and `|test_mdd_pct_cvar|` is **not** the smallest. Even
if `test_terminal_cumret_cvar` turns out to be the highest in a sub-case,
the baseline objective "defense = tail-risk compression" is not met.

### E-1 · `|MDD_cvar|` not the smallest AND `cumret_cvar` is the highest

Equivalent to "the Adaptive Optimizer has become **more aggressive** under
stress":

1. **CVaR estimate sample insufficient**: The test window contains too few
   left-tail samples; the empirical CVaR is therefore overly optimistic and
   the `w_cvar` obtained by the optimizer is "overestimated in effectiveness."
   Check whether `cvar_alpha` (default 0.05) is too wide, or extend
   `mc_horizon_days`.
2. **Covariance estimate degradation**: If Phase 0's Σ is dominated by a few
   outlier days, Min-CVaR will concentrate weight into names that appear
   "historically safe but have heavy tails in practice."
3. **Defense-level escalated by mistake**: `resolve_defense_level` should not
   have escalated to Level 2 in the current period; audit `jsd_stress`,
   `pseudo_melt`, and `prob_full_pipeline_failure` for false positives.

### E-2 · `|MDD_cvar|` not the smallest AND `cumret_cvar` is not the highest

The most severe sub-case — the Adaptive Optimizer **fails to protect drawdown
and fails to preserve return**:

1. **Structural break between training and test windows**: Phase 0's Σ is no
   longer valid in the test window; `w_cvar` underperforms both benchmarks
   out-of-sample. Remedy by resetting `train_end`, retraining, or using a
   shorter estimation window + recursive update.
2. **`blocked_symbols` filter is too aggressive**: Phase 1 has rejected too
   many names (e.g. an ADF threshold that is too strict), so the investable
   universe collapses and the red line simultaneously worsens on both MDD
   and return as a result of the reduced diversification. Audit
   `pol.tau_vol_melt` / `pol.tau_return_ac1`.
3. **Semantic prior points in the wrong direction**: Under Level 1 the
   λ-weighted negative-sentiment penalty, if its sign is inverted relative to
   the actual narrative (sentiment polarity flipped), drives weights in the
   wrong direction. Audit the sign of the S_t output from
   `vader_st_series_partition_cumulative_from_detail` against the news feed.
4. **Objective and constraints are incompatible**: If `w_cvar` hits an upper
   or lower weight bound, the result is a **constraint solution** rather than
   an optimization solution, and the Adaptive Optimizer has no real degree
   of freedom in the current window.

### Fig 4.2 methodological limitations

- **Test-window length**: The shorter the test window, the greater the MDD's
  random variation; the ordering of `|MDD%|` can be flipped by one or two
  extreme days. Prefer the `comparison_active=True` MC counterfactual as the
  primary criterion.
- **"Construction successful" ≠ "long-run robustness"**: Fig 4.2 can only
  show that the Adaptive Optimizer compresses realized MDD **within this
  particular test window**; cross-window robustness requires an additional
  rolling back-test and is out of scope for this page.
- **Seed dependence of the MC counterfactual**: Even with the same random
  seed, the quantile of the counterfactual remains sensibly biased across
  different jump intensities / scenario injections; focus on trend-level
  conclusions rather than single-percentage-point differences.
