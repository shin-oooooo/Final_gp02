# Figure 4.2 · Defense strategy effectiveness validation

Maximum drawdown measures the largest loss magnitude for a portfolio over a chosen period—from the historical peak net value to the lowest net value.

It reflects the worst-case scenario an investor may face and the asset’s downside risk.  
A smaller drawdown usually indicates stronger risk control.

This figure compares drawdown behavior and cumulative return paths over time for three weighting schemes on the real test set, to validate the practical effectiveness of Adaptive Optimizer in controlling drawdown:

1. **Level 0** weights that target maximum Sharpe ratio.
2. User-defined weights or equal weights.
3. Portfolio weights optimized by Adaptive Optimizer.

---

## Test-window terminal metrics (simple compounding)

1. **Cumulative return**: Max-Sharpe `{term_ms}`　custom `{term_cw}`　circuit-breaker CVaR `{term_cv}`
2. **Max drawdown %**: Max-Sh `{term_mdd_ms}`　custom `{term_mdd_cw}`　CVaR `{term_mdd_cv}`

---

## Monte Carlo counterfactual / effectiveness

{mc_content}

---

## Defense-strategy validation

**If** `jump-inclusive 5% quantile actual ≥ counterfactual = {mc_pass}` **and** `MDD 95% quantile actual ≤ counterfactual = {mc_mdd_pass}` **Then**

→ Defense validation passes: tail risk is compressed effectively.

**Else**

→ Defense validation fails: review weight-switching logic or Monte Carlo settings.

---

## Expectation check

**If** `Monte Carlo jump-inclusive 5% quantile actual ≥ counterfactual = {mc_pass}` **Then**

→ Defense meets expectations under stress (left tail does not worsen).

**Else**

→ Actual left tail is worse than counterfactual; review scenario injection or model setup.
