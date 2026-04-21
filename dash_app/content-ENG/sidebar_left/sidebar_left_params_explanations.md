# Sidebar-Left · “?” expanded explanations

> Detailed text behind each parameter **?** affordance.
>
> `tau_*` keys attach to individual **micro-labels** (four defense τ).
> `block_*` keys attach to **group titles** (JSD stress / credibility / shadow / prediction / Level 1 λ / dual MC).

# ── Micro-label level (four defense τ) ──

tau_h1: "Higher τ_H1 makes the “weak diversification” verdict stricter. When structural entropy falls below τ_H1, the book is treated as relatively homogeneous / weak defense → Level 1 (alert)."

tau_l2_l1: "Credibility scores aggregate four numeric models. Smaller τ_L2 and τ_L1 mean stricter “collective failure.” Between τ_L2 and τ_L1 ⇒ low credibility ⇒ Level 1; below τ_L2 ⇒ very low credibility ⇒ Level 2 (circuit)."

tau_vol: "Smaller τ_vol makes the “pseudo-stationary asset” verdict stricter. Annualized vol below τ_vol flags pseudo-stationarity—likely violent moves after regime change ⇒ Level 1."

tau_ac1: "Larger τ_AC1 makes the “insufficient predictive structure” verdict stricter. First-order autocorrelation above τ_AC1 suggests strategy logic may break ⇒ Level 1."

# ── Group-title level (batch tooltips) ──

block_jsd_stress: "JSD measures model disagreement; rolling triangle JSD vs. baseline flags collective stress. k_JSD scales the baseline—higher k ⇒ stricter disagreement test. ε floors the baseline away from zero to avoid unstable triggers."

block_credibility: "Credibility = baseline − penalties. Higher α dulls sensitivity to disagreement; higher β raises sensitivity to forecast error; γ caps excessive penalties."

block_shadow: "Shadow testing picks the best per-symbol model. α near 1 emphasizes point forecasts (MSE); near 0 emphasizes distributional fit (JSD). A tail segment of the training window acts as pseudo-OOS to score MSE/JSD—shorter windows are faster but noisier."

block_model_predict: "How many times models refit on information strictly before each test date inside the official test window. More refits cost time; fewer refits mean coarser adaptation."

block_lambda: "At Level 1, AdaptiveOptimizer minimizes annualized volatility plus a penalty on negative semantic exposure. Larger λ weighs negativity more in the objective."

block_mc: "Dual-track Monte Carlo evaluates the optimized portfolio in normal vs. stressed paths; optional black-swan injection simulates logic-break shocks."
