# Figure 4.2 · Defense-strategy effectiveness test (Research · Class C)

**Object type (Class C)** — custom "defense-strategy effectiveness" test.
Figure 4.2 compares, on **the same test-window return matrix**, the realized
cumulative return and maximum drawdown (MDD) of **three fixed weighting
rules**, so that we can decide whether the Adaptive Optimizer achieves its
design goal of **"trading an acceptable amount of return for a meaningful
compression of tail risk."**

- **Blue line** — Level 0 · Max-Sharpe baseline weights
  (`test_equity_max_sharpe`, `color=#42a5f5`).
- **Grey dashed line** — custom weights from the Phase 0 pie chart
  (`test_equity_custom_weights`, `color=#78909c`).
- **Red line** — circuit-break CVaR weights produced by the Adaptive
  Optimizer (used in Level 1/2; `test_equity_cvar`, `color=#ef5350`).

> **Notation in this document**:
>
> - "**Highest drawdown**" means the **smallest `|test_mdd_pct_*|`** among the
>   three curves (i.e. the smallest absolute magnitude of MDD = the best
>   drawdown control).
> - "**Highest cumulative return**" means the largest `test_terminal_cumret_*`.
> - Under this convention, "highest drawdown + highest cumulative return"
>   means "compresses drawdown **and** preserves return," which matches the
>   Adaptive Optimizer design goal.

This document is aligned with the sidebar template
`dash_app/render/explain/main_p4/fig42.py::build_fig42_body(...)`, which
injects the placeholders `{term_ms}` / `{term_cw}` / `{term_cv}` (cumulative
return), `{term_mdd_ms}` / `{term_mdd_cw}` / `{term_mdd_cv}` (MDD%),
`{mc_content}` (MC counterfactual block), `{mc_pass}` / `{mc_mdd_pass}` /
`{defense_pass}` (booleans).

Placeholders: `{defense_pass}` · `{mc_pass}` · `{mc_mdd_pass}`

---

## 1. Figure pipeline (end-to-end)

```text
Phase 3 · optimization (objective switches with defense_level):
  - Level 0 → Max-Sharpe (w_level0)
  - Level 1 → Max-Sharpe + λ · negative-sentiment penalty (w_level1)
  - Level 2 → Min CVaR (w_level2 = w_cvar)
  ⇒ actual holding weights w_actual = w_levelN (N = defense_level)

Phase 3 · realized test-window paths (same test_returns_daily × three weights):
  - w_max_sharpe   → test_equity_max_sharpe / test_terminal_cumret_max_sharpe / test_mdd_pct_max_sharpe
  - w_custom(=pie) → test_equity_custom_weights / ...
  - w_cvar         → test_equity_cvar / ...

Dash plotting:
  - fig_p3_triple_test_equity(dates, y_ms, y_cu, y_cv, tpl)
  - build_fig42_body(ui_mode, snap_json, dv) injects the explanatory text
```

---

## 2. Method core

### 2.1 Why "one return matrix × three weight rules" instead of "one strategy × different markets"

The Adaptive Optimizer's effectiveness must be compared against **reasonable
baselines** within a **fixed environment**. Figure 4.2 pins the three
weighting rules to the same `test_returns_daily`, so any difference in
drawdown / return is **purely attributable to weight choice** — this is the
causal-attribution stance on "did the strategy construction succeed?"

### 2.2 Why Max-Sharpe and custom weights serve as baselines

- **Max-Sharpe (blue)** — the canonical no-defense baseline representing
  "fully trust historical μ/Σ estimates for risk-adjusted optimality"; used
  to measure how the Adaptive Optimizer improves over or gives up relative
  to "blind Sharpe maximization."
- **Custom weights (grey dashed)** — an investor-prior baseline (equal-weight
  or hand-drawn pie); used to measure the Adaptive Optimizer's improvement
  over "naive priors."
- The three are compared on **the same out-of-sample path**, equivalent to a
  conditionally-independent three-arm experiment.

### 2.3 Two-layer success verification

- **Layer 1 · realized test** (Figure 4.2 main chart): compare the three
  curves' MDD% and terminal cumulative return.
- **Layer 2 · counterfactual test** (`{mc_content}` block): Monte Carlo with
  the same RNG seed and identical jump / injection parameters, comparing
  "actual weights" vs. "counterfactual Level-0 weights" in terms of the
  **5-percentile terminal wealth with jumps** `{mc_pass}` and the
  **95-percentile MDD** `{mc_mdd_pass}`.
- **Overall verdict**: `defense_pass = mc_pass AND mc_mdd_pass = {defense_pass}`.

> **Note**: When `defense_level = 0`, `comparison_active = False`; the two
> MC tracks agree and the counterfactual block degenerates to "no extra tail
> comparison." The verdict then falls back to Layer 1 (the structural
> relationship of the three curves).

---

## 3. Data provenance

### 3.1 Shared-source matrix for the three curves

All three curves use the same `test_returns_daily[T×N]` (the raw matrix
written into `phase3.defense_validation`); only the weight vector differs.
Therefore **daily-return differences = linear combinations of weight
differences**.

### 3.2 Runtime-injected fields (core summary)

| Variable | Injected value |
| --- | --- |
| Three terminal cumulative returns | Max-Sharpe `{term_ms}`, custom `{term_cw}`, CVaR `{term_cv}` |
| Three MDD% | Max-Sharpe `{term_mdd_ms}`, custom `{term_mdd_cw}`, CVaR `{term_mdd_cv}` |
| MC 5-percentile with jumps (≥ counterfactual?) | `{mc_pass}` |
| MC 95-percentile MDD (≤ counterfactual?) | `{mc_mdd_pass}` |
| Overall defense verdict (AND) | `{defense_pass}` |

### 3.3 Key fields and code anchors

| Snapshot field | Producer | Description |
| --- | --- | --- |
| `test_equity_max_sharpe/custom_weights/cvar` | `research/phase3.py :: run_phase3 :: _realized_equity_series_and_mdd` | Three cumulative-return paths |
| `test_terminal_cumret_*` / `test_mdd_pct_*` | Same as above | Terminal & MDD scalars |
| `resolved_custom_weights` | Same as above | Normalized post-filter pie weights |
| `actual_stress_p5_terminal` / `baseline_stress_p5_terminal` | `_simulate_mc_paths` | MC 5-percentile with jumps (two tracks) |
| `actual_mdd_p95_pct` / `baseline_mdd_p95_pct` | Same as above | MC 95-percentile MDD (two tracks) |
| `comparison_active` | `run_phase3` based on `defense_level` | `True` ⇔ Level 1/2 |

---

## 4. Execution chain

| # | Stage | Input | Output | Rule | Code anchor |
| --- | --- | --- | --- | --- | --- |
| 1 | Defense-level decision | `resolve_defense_level(state)` | `defense_level ∈ {0,1,2}` | τ_L1 / τ_L2, `jsd_stress`, `logic_break`, `pseudo_melt`, … | `research/defense_state.py :: resolve_defense_level` |
| 2 | Weight optimization | μ, Σ, defense_level | `w_max_sharpe` / `w_cvar` | Level 0 = max Sharpe; Level 2 = min CVaR; Level 1 adds λ · sentiment penalty | `research/phase3.py :: run_phase3` |
| 3 | Realized equity | `test_returns_daily × w` | `test_equity_*` / `test_terminal_cumret_*` / `test_mdd_pct_*` | Simple compounding; MDD = (peak − trough) / peak | `_realized_equity_series_and_mdd` |
| 4 | MC counterfactual (if active) | `inp.mc_sentiment_path` / `jump_p` / `jump_impact` / `rng` | `actual/baseline_stress_p5_terminal`, `*_mdd_p95_pct` | Parallel streams with identical RNG; compare 5-pct with jumps and 95-pct MDD | `_simulate_mc_paths` |
| 5 | Sub-figure output | three curves + MC summary | Fig 4.2 | Chart shows realized curves only; MC summary goes into `{mc_content}` | `dash_app/figures.py :: fig_p3_triple_test_equity` |

---

## 5. Chart overlay semantics (must match current implementation)

- **Blue (`#42a5f5`, width = 2.2)** — `Level 0 · Max-Sharpe`.
- **Grey dashed (`#78909c`, dash = "dot", width = 2)** — `custom weights (pie)`.
- **Red (`#ef5350`, width = 2.2)** — `circuit-break weights (Level 2 · CVaR)`,
  i.e. the Adaptive Optimizer's actual output.
- **"Blue and red coincide"** — when `defense_level = 0`,
  `w_cvar ≡ w_max_sharpe`, so `test_equity_cvar ≡ test_equity_max_sharpe`.
  The red line is fully hidden behind the blue line and the chart appears
  to contain only one compound line plus the grey dashed line.

---

## 6. Key-data example (important numbers)

The **Phase 2 shadow model-selection** full-library prerequisites and
selection table share the source of **`Figure2.1-Res.md` §6**. The scale of
`w_cvar` / `w_custom` is consistent with Phase 1's `blocked_symbols` filter
and Phase 0's pie-chart interception (both are normalized inside
`run_phase3` before being fed into `_realized_equity_series_and_mdd`).

### 6.1 Reading-boundary with Fig 4.1

The three curves in Fig 4.2 only reflect **the product of weights and the
realized return matrix**; they do **not** recompute the alert logic (t_ref /
t_alarm / lead time). The alert verdict is authoritative in **`Figure4.1-Res.md`**
alone. If Fig 4.1 declares "early-warning failed," the "defense successful"
in Fig 4.2 can only be attributed to **structural conservatism**, not to
**forward identification** — the two figures must be read in tandem.

### 6.2 Worked example for the three-value path

Assume the current period has `{term_ms}` = 1.0320, `{term_cw}` = 1.0180,
`{term_cv}` = 1.0285; `{term_mdd_ms}` = 8.60%, `{term_mdd_cw}` = 7.90%,
`{term_mdd_cv}` = 5.20%. Then:

- MDD ordering (smallest `|%|` → largest): CVaR (5.20%) < Custom (7.90%) <
  Max-Sharpe (8.60%); **CVaR has the highest drawdown (smallest MDD)** ✓
- Cumulative-return ordering: Max-Sharpe (1.0320) > CVaR (1.0285) >
  Custom (1.0180); **CVaR is not the highest**.
- ⇒ **Case D** (strategy construction successful; gives up 0.35 pp of return
  in exchange for 3.4 pp of MDD compression).

---

## 7. Consistency checks (reproducible verification)

1. Verify `len(test_equity_max_sharpe) == len(test_equity_custom_weights) ==
   len(test_equity_cvar) == len(shadow_index_labels)`.
2. Verify the difference between `test_terminal_cumret_*` and each curve's
   end-point `-1` is below numerical tolerance (≤ 1e-12).
3. If `defense_level = 0`, verify `test_equity_cvar - test_equity_max_sharpe`
   is pointwise below numerical tolerance (the two curves should coincide
   strictly); otherwise the state falls into Case B (anomaly).
4. Verify `comparison_active == (defense_level >= 1)`.
5. If `comparison_active = True`, verify `actual_stress_p5_terminal` /
   `baseline_stress_p5_terminal` / `actual_mdd_p95_pct` /
   `baseline_mdd_p95_pct` are non-null; otherwise the counterfactual block
   degenerates and the verdict should fall back to Layer 1.

---

## 8. Relationship with other objects (responsibility boundary)

- **Against Fig 4.1 (early-warning effectiveness)** — Fig 4.2 only performs
  post-hoc verification of an actual defense action; whether the alert was
  truly **ahead of time** is decided by Fig 4.1. In time, the two are
  **sequential but orthogonal**: Fig 4.1 verifies **timing**; Fig 4.2
  verifies **realized stress reduction**.
- **Against Phase 3 weight optimization** — Fig 4.2 depends entirely on the
  `test_equity_*` / `test_terminal_cumret_*` / `test_mdd_pct_*` that
  `run_phase3` writes; it does **not** recompute the weights or the
  cumulative-return curves.
- **Against Phase 1/2 filtering (`blocked_symbols`)** — the
  `test_returns_daily` used by Fig 4.2 already has filtered columns dropped
  at the Phase 3 input stage. If an "dominant single-asset" anomaly appears
  in the curves, the first thing to audit is whether the filter is actually
  applied.

---

## 9. Conclusion analysis

> The five-case judgement logic, the Case E attribution list, method
> limitations, and the overall verdict have been migrated into the shared
> source `content-{LANG}/p4_conclusion_analysis.md`
> (indexed by the `## Fig4.2 · Case X` namespace, shared between Fig 4.1
> and Fig 4.2). The "conclusion analysis card" below Fig 4.2 at runtime is
> produced by `build_fig42_conclusion_card`, which slices that shared source
> by the current case and substitutes the placeholders in real time. If you
> need to read all five cases offline, please refer to the shared document
> above.
