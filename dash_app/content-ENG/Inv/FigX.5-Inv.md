## Stress as an analogy

In physics, stress is the internal force within a material that resists external loads and deformation. When stress exceeds what the material can bear, it fractures or collapses. When the market regime shifts fundamentally (e.g., from chop to crash, or from fundamentals-driven to liquidity-driven logic), different algorithms respond with different sensitivities and their forecasts can “tear apart” sharply. That surge in disagreement among predictions is what we call “stress.”

## Model–model stress detection

“Model–model stress detection” quantifies how far numerical models disagree, judges whether they have collectively “failed,” and forecasts the onset of model divergence—i.e., structural breaks in the market.

## JSD and the triangular JSD mean

JSD measures how much two models disagree: larger JSD means larger disagreement. Three models yield three pairwise JSD values. In this chart, at each cross-section we equally weight each model’s predicted mean return and volatility across all symbols, then average pairwise JSDs from those equally weighted moments, and equally weight again to obtain the “triangular JSD mean” `jsd_triangle_mean` and its time series. On the training set, a sliding window of length `n_kl` produces a daily series `hist_jsd` with the same recipe; averaging that series gives a scalar `jsd_mean`.

## Stress buildup vs. failure

Rising stress does not imply immediate collapse; failure occurs only when stress exceeds the yield threshold.

## Logical assumption

`jsd_mean` acts as the structural “baseline capacity”; `k_jsd` is the safety factor. The first time `k_jsd × max(jsd_baseline_mean, ε)` triggers, inter-model disagreement has exceeded historical norms by several fold—meaning price action can no longer be explained by the existing narrative: the structure has “broken,” and we take that date as the start of logical market failure. Because the test window is short while the studied event (e.g., a geopolitical shock) lasts longer, we approximately treat one such “break” inside the test window—a reasonable qualitative assumption for forecasting purposes.
