# Figures · English titles

> Per-figure page title (the grey bar above each chart).
> System uses this file as the single source of truth; only falls back to
> `assets/figures_titles.json` when a key is missing.
>
> **Interface contract** (aligned with `callbacks/research_panels.py::_caption_refresh_on_mode`):
>
> * `fig_*_explain`      — Invest-mode explanation card title ("Chart & method overview").
> * `fig_*_explain_res`  — Research-mode explanation card title ("Data, parameters & methodology detail").
>
> When a key is missing, research mode falls back to the invest-mode key;
> invest mode falls back to the code-level hard-coded default.

fig_0_1: "Figure 0.1 · Portfolio weight pie"
fig_0_2: "Figure 0.2 · Correlation heatmap"
fig_0_3: "Figure 0.3 · Beta distribution & regime comparison"

fig_1_1: "Figure 1.1 · Group diagnostics & failure-precursor identification"
fig_1_2: "Figure 1.2 · Statistical-method notes (ADF / Ljung-Box / p-value meaning)"

fig_2_1: "Figure 2.1 · Shadow model-selection & best-model pixel matrix"
fig_2_2: "Figure 2.2 · Per-asset predicted-return density"

fig_3_1: "Figure 3.1 · Per-asset best-model return expectation & volatility forecast"
fig_3_2: "Figure 3.2 · Optimized vs custom weight comparison"
fig_3_3: "Figure 3.3 · Dual-track Monte Carlo simulation"

fig_4_1: "Figure 4.1 · Early-warning effectiveness test"
fig_4_1_jsd: "Figure 4.1a · Model–model stress early-warning effectiveness test"
fig_4_1_cos: "Figure 4.1b · Model-stress × market-load early-warning effectiveness test"
fig_4_2: "Figure 4.2 · Defense-strategy effectiveness test (three-weight test-window comparison)"

fig_x_1: "FigX.1 · Real-time market-sentiment path"
fig_x_2: "FigX.2 · Portfolio structural entropy"
fig_x_3: 'FigX.3 · Asset "pseudo-stationarity" & "insufficient-structure" test'
fig_x_4: "FigX.4 · Model credibility score & Naive-improvement test"
fig_x_5: "FigX.5 · Model–model stress test & warning"
fig_x_6: "FigX.6 · Model-stress × market-load direction test & warning"

# ─────────────── Invest-mode explanation card titles (overview) ───────────────

fig_0_1_explain: "Figure 0.1 chart & method overview"
fig_0_2_explain: "Figure 0.2 chart & method overview"
fig_0_3_explain: "Figure 0.3 chart & method overview"

fig_1_1_explain: "Figure 1.1 chart & method overview"
fig_1_2_explain: "Figure 1.2 chart & method overview"

fig_2_1_explain: "Figure 2.1 chart & method overview"
fig_2_2_explain: "Figure 2.2 chart & method overview"

fig_3_1_explain: "Figure 3.1 chart & method overview"
fig_3_2_explain: "Figure 3.2 chart & method overview"
fig_3_3_explain: "Figure 3.3 chart & method overview"

fig_4_1_explain: "Figure 4.1 chart & method overview"
fig_4_1_jsd_explain: "Figure 4.1a chart & method overview"
fig_4_1_cos_explain: "Figure 4.1b chart & method overview"
fig_4_2_explain: "Figure 4.2 chart & method overview"

fig_x_1_explain: "FigX.1 chart & method overview"
fig_x_2_explain: "FigX.2 chart & method overview"
fig_x_3_explain: "FigX.3 chart & method overview"
fig_x_4_explain: "FigX.4 chart & method overview"
fig_x_5_explain: "FigX.5 chart & method overview"
fig_x_6_explain: "FigX.6 chart & method overview"

# ─────────────── Research-mode explanation card titles (detail) ───────────────

fig_0_1_explain_res: "Figure 0.1 data, parameters & methodology detail"
fig_0_2_explain_res: "Figure 0.2 data, parameters & methodology detail"
fig_0_3_explain_res: "Figure 0.3 data, parameters & methodology detail"

fig_1_1_explain_res: "Figure 1.1 data, parameters & methodology detail"
fig_1_2_explain_res: "Figure 1.2 data, parameters & methodology detail"

fig_2_1_explain_res: "Figure 2.1 data, parameters & methodology detail"
fig_2_2_explain_res: "Figure 2.2 data, parameters & methodology detail"

fig_3_1_explain_res: "Figure 3.1 data, parameters & methodology detail"
fig_3_2_explain_res: "Figure 3.2 data, parameters & methodology detail"
fig_3_3_explain_res: "Figure 3.3 data, parameters & methodology detail"

fig_4_1_explain_res: "Figure 4.1 data, parameters & methodology detail"
fig_4_1_jsd_explain_res: "Figure 4.1a data, parameters & methodology detail"
fig_4_1_cos_explain_res: "Figure 4.1b data, parameters & methodology detail"
fig_4_2_explain_res: "Figure 4.2 data, parameters & methodology detail"

fig_x_1_explain_res: "FigX.1 data, parameters & methodology detail"
fig_x_2_explain_res: "FigX.2 data, parameters & methodology detail"
fig_x_3_explain_res: "FigX.3 data, parameters & methodology detail"
fig_x_4_explain_res: "FigX.4 data, parameters & methodology detail"
fig_x_5_explain_res: "FigX.5 data, parameters & methodology detail"
fig_x_6_explain_res: "FigX.6 data, parameters & methodology detail"
