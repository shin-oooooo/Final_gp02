# Fig 4.1 · Final conclusion analysis (P4)

> This template covers four cases:
>
> * **Case A** · Both alerts succeed
> * **Case B** · Only “model–model” succeeds (lower informational value)
> * **Case C** · Only “model–market” succeeds
> * **Case D** · Both alerts fail (attribution)
>
> Placeholders `{mm_verdict}` / `{mv_verdict}` / `{mm_t0_date}` / `{mv_t0_date}` / `{final_t0_date}` /
> `{earliest_t0_date}` are substituted by the frontend from the current snapshot.

## Thesis

Collective impairment of asset-class diversification under stress can be detected **1–5 trading days ahead**
by **“model–model stress”** together with **“model-stress vs. market-load-direction”**.
Because (i) the test window is finite, and (ii) research events (e.g. geopolitical shocks) tend to be
exogenous and persistent, we treat **at most one** “market logic-break” episode within the test window.
When both independent checks fire, **prefer the model–market load-direction alert date as the final alert date**:
the model–market test directly measures **narrative / load direction vs. price path**, closer to real-market
non-stationarity; model–model stress (JSD) reflects predictive-distribution disagreement **without mapping
one-to-one to realized market-regime change**.

---

## Case A · Both alerts succeed (final choice: model–market)

- **Model–model**: `{mm_verdict}`, alert date `{mm_t0_date}`
- **Model–market**: `{mv_verdict}`, alert date `{mv_t0_date}`
- **Final alert date (model–market preferred)**: **`{final_t0_date}`**

**Conclusion**: The two checks corroborate each other; narrative and statistical lenses both point to structural
strain around **`{final_t0_date}`**. At the conclusion layer the system adopts **`{mv_t0_date}`** as the final
alert date; the model–model date **`{mm_t0_date}`** remains an internal consistency check.

---

## Case B · Only “model–model” succeeds (⚠ lower informational value)

- **Model–model**: `{mm_verdict}`, alert date `{mm_t0_date}`
- **Model–market**: `{mv_verdict}`

> ⚠ **Lower informational value**: Only inter-model disagreement (JSD) fires, while narrative / load direction
> has not diverged from the price path. This means **higher predictive uncertainty**, but **not** automatically
> **market-level structural failure**; when using **`{mm_t0_date}`** as a reference alert, report this notice.

**Conclusion**: Use **`{mm_t0_date}`** as a **reference** alert date. Large predictive-distribution disagreement
(JSD stress above baseline) shows the three structural models disagree materially about future returns; if the
rolling semantic–numeric cosine stays ≥ 0 in the same window, **narratives have not yet directionally diverged
from prices**. The signal **alone does not justify** a “market logic-break” verdict; treat conclusions cautiously
and label **lower informational value**.

### Follow-up checks (priority order)

1. **Per-model diagnostics**: Inspect Phase2’s `prob_nll_mean` / `prob_dm_pvalue_vs_naive` / `prob_coverage_95`
   for ARIMA / LightGBM / Kronos OOS behavior:
   - If **one** model shows sharply worse NLL and DM vs Naive, elevated JSD often reflects **parameter drift**;
     remedy with **retraining / adjusting `oos_fit_steps`**.
   - If **all three** worsen together, suspect **covariate shift**; revisit **train window**, **expand the pool**,
     or **strengthen regularization**.
2. **Train–test distribution alignment**: Run KS / Wasserstein on returns **20–40** trading days before
   **`{mm_t0_date}`**; if the same-distribution null is rejected, tighten `train_end` or retrain.
3. **Narrative coverage**: Compare S_t and news—events may occur before text features catch them. If keywords are
   missing (new policy / geopolitical vocabulary), extend `sentiment_proxy` keywords and re-run cosine before
   revising this case.
4. **Statistical discipline**: Do **not** lower `verify_std_quantile_pct` / `verify_crash_quantile_pct` /
   `verify_tail_quantile_pct` ad hoc to force the model–market check—this harms independence and reproducibility.

---

## Case C · Only “model–market” succeeds

- **Model–model**: `{mm_verdict}`
- **Model–market**: `{mv_verdict}`, alert date `{mv_t0_date}`

**Conclusion**: Use **`{mv_t0_date}`** as the final alert date. Persistent semantic-load divergence from numeric
paths (rolling cosine < 0) suggests **narratives lead price / volatility**—a strong market-level impairment signal.
JSD may still sit below baseline because:

- Structural models **have not yet disagreed enough** on the new signal (common early in exogenous shocks);
- Homogeneous covariance structure **suppresses** distributional disagreement.

### Operational notes

1. **Act on the market–load test**: In the **5** trading days after `{mv_t0_date}`, monitor crash / tail shares vs.
   training baseline; if sustained, re-evaluate Phase 3 defense level.
2. **Watch for delayed JSD**: Track JSD **3–10** days after `{mv_t0_date}`; a late baseline breach is **time-offset
   agreement** between channels—useful methodological evidence.
3. **Strengthen linkage evidence**: Check whether ``cosine_semantic_numeric`` falls monotonically around
   `{mv_t0_date}`; a steep drop with ≥ **2** negative days is strong corroboration.

---

## Case D · Both alerts fail (attribution)

- **Model–model**: `{mm_verdict}`
- **Model–market**: `{mv_verdict}`

**Conclusion**: Neither check fires within the **1–5** trading-day window. Investigate **methodology / data before
models / thresholds**:

### Likely causes (priority order)

1. **Test window misses the true break**: Length or sampling cannot capture the event; verify ``test_start`` /
   ``test_end`` cover the intended episode.
2. **Training-window contamination**: Structural breaks inside training inflate baselines so OOS anomalies never
   cross; reset training to a stationary segment and retrain.
3. **Thresholds too conservative**: High train-window quantiles (`verify_std_quantile_pct` / `verify_crash_quantile_pct` /
   `verify_tail_quantile_pct`) delay triggers.
4. **Model homogeneity → muted JSD**: Models react similarly; add complementary models to raise sensitivity.
5. **Semantic proxy mismatch**: Text features weakly linked to the shock; enrich ``sentiment_proxy`` vocabulary.

### Actions

- First reconcile **test span + train span + universe**—any mismatch suppresses both checks.
- Only after that, consider relaxing ``verify_*_quantile_pct``.
- If still null, ask whether a structural break **exists in data**; if not, interpret as **correct stability** for
  this window, not “failed warning.”
