## Credibility score and defense levels

The credibility score gauges how trustworthy the four numerical models are together.

1. Between **τ_L2** and **τ_L1**, credibility is judged low → defense shifts to Level 1 (alert).
2. Below **τ_L2**, credibility is judged very low → defense shifts to Level 2 (circuit breaker).

**τ_L2** and **τ_L1** are editable in the “custom parameter panel.”

## Formula

Credibility score = baseline term − penalty term.

- **Baseline** = 1/(1 + α·JSD)
- **Penalty** = min(cap, β·JSD)

A higher baseline coefficient dulls sensitivity to model split; a higher penalty coefficient sensitizes you to calibration error.

## Naive benchmark & traffic lights

Three traffic lights summarize the Naive uplift test. Colors follow rules such as the DM test, sign of d̄, and whether coverage lies in **0.85–0.99**, covering (i) whether forecasts beat Naive significantly and (ii) whether they are over- or under-confident.

If a model’s light is **red**, its out-of-sample reliability is worse than Naive on those dimensions. A red light applies a credibility penalty sized by the penalty branch. **If all three lights are red, defense escalates to Lv1.**
