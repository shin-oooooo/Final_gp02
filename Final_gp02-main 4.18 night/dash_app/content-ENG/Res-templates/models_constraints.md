# Models — constraints, strengths, weaknesses

> Purpose: describe how each forecaster on the **Phase 2 multi-model track**
> actually works, **where it fails when misused**, and the current contracts
> for **Kronos** and the **shadow validation** procedure.  Always cross-read
> with source code — the line numbers drift between commits.

> **TODO — English translation pending.**  The authoritative text lives in
> `content-CHN/Res-templates/models_constraints.md`; until a dedicated English
> edit is authored, consult that file for detailed commentary.

---

## Key reference points

- **Out-of-sample (test window):** at test day `t`, the predicted return
  `r_t` may only use information strictly before `t`
  (`returns.index < t`).  Main loop: `run_phase2` in `research/phase2.py`.
- **Sparse re-fit:** `DefensePolicyConfig.oos_fit_steps` re-estimates
  `(μ̂, σ̂)` on a handful of evenly spaced days inside the test window;
  other days forward-fill the most recent snapshot.
- **Gaussian layer:** every model emits scalar `μ` and `σ` used for
  pairwise JSD, NLL, nominal coverage etc.  This is a **simplification**
  and does not equal the true return distribution.

Models in the Phase 2 track: **Naive**, **ARIMA(1,0,1)**,
**LightGBM** (single-feature regression), **Kronos** (time-series
Transformer, strict inference when weights are available and a
statistical fallback otherwise).  **Shadow validation** compares these on
the tail of the training window only — it must never leak into the test
window.
