# All Labels · Topbar / Right-Sidebar / Main-Panel (P0–P4) Buttons & Scattered Copy

> **Single source of truth** for every static string rendered by the Dash application.
> Editing rule: **only touch the quoted value, never the key on the left** — keys are
> referenced by Python source and renaming them breaks the lookup. When adding keys,
> prefer existing prefixes (`btn_`, `tab_`, `modal_`, `p0_`, `p1_`, `p2_`, `p3_`, `p4_`,
> `aux_`, `overview_`, `diag_`, `level_status_`).
>
> Unified reader: `services/copy.py::get_topbar_label(key, default)` or its semantic
> alias `get_app_label(key, default)`. Fallback chain:
> `all_labels.md` → (legacy) `topbar_labels.md` → `assets/topbar_labels.json` → `default`.
> Language is driven by `?lang=chn|eng`; **Chinese and English bundles are separate files**
> (`content-CHN/all_labels.md` vs `content-ENG/all_labels.md`) — no silent cross-folder fallback.

---

## 0 · Long-Form Narratives & Explanations — Source-File Links (link only, do not inline)

The modules/files below emit **conditionally concatenated, business-logic-driven**
content or **long running prose** that is too placeholder-heavy to maintain in a
flat `key: "value"` store. To edit them, open the source file directly; keep the
`Inv/-Inv.md` and `Res/-Res.md` pair in sync (see `services/copy.py::get_md_text_by_mode`).

### Explanation Markdown (user-editable)

- Left-sidebar "Defense strategy & parameters" body · `[sidebar_left/sidebar_left.md](sidebar_left/sidebar_left.md)` / `[sidebar_left/sidebar_left_params_explanations.md](sidebar_left/sidebar_left_params_explanations.md)`
- P1 statistical methods (ADF / Ljung-Box / p-value meaning) · `[p1_stat_method.md](p1_stat_method.md)` *(add under `content-ENG/` when translated)*
- P2 shadow model-selection & pixel matrix · `[p2_pixel_shadow_intro.md](p2_pixel_shadow_intro.md)` · `[p2_fig21_intro.md](p2_fig21_intro.md)` *(optional long-form files)*
- P3 AdaptiveOptimizer prose · `[p3_adaptive_optimizer.md](p3_adaptive_optimizer.md)` · `[p3_dual_mc.md](p3_dual_mc.md)` *(optional)*
- Per-figure Invest briefs · `[Inv/Fig0.1-Inv.md](Inv/Fig0.1-Inv.md)` · `[Inv/Fig0.2-Inv.md](Inv/Fig0.2-Inv.md)` · `[Inv/Fig1.1-Inv.md](Inv/Fig1.1-Inv.md)` · `[Inv/Fig2.1-Inv.md](Inv/Fig2.1-Inv.md)` · `[Inv/Fig2.2-Inv.md](Inv/Fig2.2-Inv.md)` · `[Inv/Fig3.1-Inv.md](Inv/Fig3.1-Inv.md)` · `[Inv/Fig4.1-Inv.md](Inv/Fig4.1-Inv.md)` · `[Inv/FigX.1-Inv.md](Inv/FigX.1-Inv.md)` · `[Inv/FigX.2-Inv.md](Inv/FigX.2-Inv.md)` · `[Inv/FigX.3-Inv.md](Inv/FigX.3-Inv.md)` · `[Inv/FigX.4-Inv.md](Inv/FigX.4-Inv.md)` · `[Inv/FigX.6-Inv.md](Inv/FigX.6-Inv.md)`
- Per-figure Research (data / params / methodology details) · see `[Res/](Res/)` same-named `-Res.md` files
- Project introduction · `[project_intro.md](project_intro.md)`
- Phase introductions · `[phase1_intro.md](phase1_intro.md)` · `[phase2_intro.md](phase2_intro.md)` · `[phase3_intro.md](phase3_intro.md)` · `[phase4_intro.md](phase4_intro.md)` · `[phase0_tab_intro.md](phase0_tab_intro.md)`
- Topbar "usage tips" · `[hint_for_webapp.md](hint_for_webapp.md)`
- Topbar three-column defense intro · `[defense_intro.md](defense_intro.md)` · `[defense_reasons.md](defense_reasons.md)`
- Kronos weights status hints · `[kronos_hints.md](kronos_hints.md)`
- Figure titles / figure hints / status messages · `[figures_titles.md](figures_titles.md)` · `[figures_hints.md](figures_hints.md)` · `[status_messages.md](status_messages.md)`
- Methodology constraints · `[Methodology_constraints.md](Methodology_constraints.md)`

### Business-Logic Copy (prose is snapshot-dynamic; edit Python)

- Phase-0 topbar aggregate line (which drivers triggered the current Level) · `[../render/explain/topbar/p0_aggregate_line.py](../render/explain/topbar/p0_aggregate_line.py)`
- Topbar per-diagnostic lines (ADF / H_struct / prob failure / JSD / cosine / S_t) · `[../render/explain/topbar/diagnosis.py](../render/explain/topbar/diagnosis.py)`
- Topbar three-column Level intro (Markdown builder) · `[../render/explain/topbar/defense_intro.py](../render/explain/topbar/defense_intro.py)`
- P0 narrative (category ordering / balance / asset-class share) · `[../render/explain/main_p0/narrative.py](../render/explain/main_p0/narrative.py)` · `[../render/explain/main_p0/card_titles.py](../render/explain/main_p0/card_titles.py)`
- P1 cohort analysis prose · `[../render/explain/main_p1/narrative.py](../render/explain/main_p1/narrative.py)`
- P4 Fig 4.1 / 4.2 experimental-stack prose · `[../render/explain/main_p4/fig41.py](../render/explain/main_p4/fig41.py)` · `[../render/explain/main_p4/fig42.py](../render/explain/main_p4/fig42.py)`
- FigX.3/4/6 right-sidebar conditional lines (high-vol asset list / traffic light / rolling cosine) · `[../render/explain/sidebar_right/figx3.py](../render/explain/sidebar_right/figx3.py)` · `[../render/explain/sidebar_right/figx4.py](../render/explain/sidebar_right/figx4.py)` · `[../render/explain/sidebar_right/figx6.py](../render/explain/sidebar_right/figx6.py)`
- Figure-caption bundle (below-graph small text with placeholders) · `[../render/explain/figure_captions.py](../render/explain/figure_captions.py)`

---

# ─── Topbar ───────────────────────────────────────────────────────────────────

app_title: "AIE1902 Defense Research"

btn_invest: "Invest"
btn_research: "Research"
btn_lang_chn: "中"
btn_lang_eng: "EN"
btn_lang_chn_title: "Switch to Chinese copy (loads content-CHN/)"
btn_lang_eng_title: "Switch to English copy (loads content-ENG/)"

btn_run: "Save & Run"
btn_run_icon: "fa-play"
btn_run_title_default: "Save config and execute the full pipeline (formerly Save & Run)"

btn_download_data_json: "Download data.json"
btn_kronos_pull_icon: "fa-download"

btn_toggle_hints_label: "Webapp runbook & usage tips"
btn_toggle_hints: "View usage tips"
btn_toggle_defense_reasons: "Expand to see each defense-condition summary"

defense_dashboard: "Defense Dashboard"
defense_status_prefix: "Current defense status: "
kronos_pull_fallback_warning: "Full Kronos weights not detected: after Save & Run, Phase 2 will fall back to return-distribution statistics for Kronos (non-Transformer). Pulling weights first is recommended."

# Tabs (5 main-panel tabs + tooltips)

tab_p0: "Assets & Prerequisites"
tab_p1: "Data Diagnostics"
tab_p2: "Signal Contest"
tab_p3: "Automatic Defense"
tab_p4: "Experiment Conclusions"

tab_p0_title: "Asset-universe customization & research prerequisites"
tab_p1_title: "Data diagnostics & failure-signal detection"
tab_p2_title: "Multi-paradigm signal contest & model-failure detection"
tab_p3_title: "Automatic defense response"
tab_p4_title: "Experiment conclusions"

# Main-panel shared: Phase-level status strip & generic labels

fig_explain_title_fmt: "Figure {phase}.{sub} · Explanation · {caption}"

level_status_l2: "STATUS: Level 2 — Meltdown defense"
level_status_l1: "STATUS: Level 1 — Guarded defense"
level_status_l0: "STATUS: Level 0 — Standard defense"
phase_intro_card_header: "Introduction (MeToAI §2)"
loading_card_title: "Loading data & charts"
loading_text: "Computing…"
loading_md_fallback: "Computing the full pipeline — please hold on…"
project_intro_fallback: "(Please write the project introduction into `dash_app/content/project_intro.md`.)"
placeholder_compute_prompt: "Click “Apply & Recompute” on the left to start computing"
inactive_variable_note: "{fig_lbl}: pipeline not executed → current variable has no effect on defense level"

# Research-mode three-section accordion (Result→raw / Calculation / Source & params)

research_accordion_result_title: "Result → raw data"
research_accordion_calc_title: "Calculation"
research_accordion_source_title: "Source code & model parameters"
research_header_raw: "Raw data"
research_header_learning: "Learning process"
research_header_source: "Source-code excerpt"

# Main-panel overview cards (5 collapsible cards in the Research Project Overview tab)

overview_p0_title: "P0 · Assets & research prerequisites"
overview_p1_title: "P1 · Data diagnostics"
overview_p2_title: "P2 · Signal contest"
overview_p3_title: "P3 · Automatic defense"
overview_p4_title: "P4 · Experiment conclusions"

# Modal · Add asset dialog

modal_add_asset_title: "Add asset"
modal_add_sym_label: "Ticker"
modal_add_sym_placeholder: "e.g. NVDA"
modal_add_weight_label: "Initial weight (0–1)"
modal_add_cat_label: "Asset class"
modal_add_cat_opt_tech: "Tech stocks"
modal_add_cat_opt_hedge: "Hedge"
modal_add_cat_opt_safe: "Safe-haven"
modal_add_cat_opt_new: "New category…"
modal_add_new_cat_placeholder: "New category name (only when “New category” is selected)"
modal_add_reweight_hint: "After saving, remaining holdings are rescaled proportionally so total = 1 − new-asset weight."
modal_btn_cancel: "Cancel"
modal_btn_save: "Save"

# ─── Main · P0 (Assets & research prerequisites) ──────────────────────────────

cat_tech: "Tech stocks"
cat_hedge: "Hedge"
cat_safe: "Safe-haven"
cat_benchmark: "Benchmark"

diag_pending: "Pending diagnosis"
diag_nonstat_or_logic_fail: "Non-stationary or logic failure · unfit as a modeling premise"
diag_stable_structure: "Stationary · exhibits modelable structure (not pure noise)"
diag_stable_weak: "Stationary · residuals near white noise (weak regularity)"
diag_nonstat_needs_diff: "Non-stationary · requires differencing or further tests"

# ─── Main · P1 (Data diagnostics) ─────────────────────────────────────────────

p1_stat_method_caption: "Statistical methods (ADF / Ljung-Box / p-value semantics)"

# ─── Main · P2 (Signal contest) ───────────────────────────────────────────────

p2_mse_best_prefix: "Best mean MSE ≈ {mse}×10⁻⁴"
p2_shadow_mse_unavailable: "Full-sample shadow MSE unavailable"
p2_credibility_hint: "Credibility score = {score} (α·JSD base + coverage penalty; α/β adjustable in left sidebar)"
p2_table_header_model: "Model"
p2_table_header_mu: "μ̂ (OOS last day)"
p2_table_header_sigma: "σ̂"
p2_prob_caption: "Three-model probabilistic verification (OOS NLL + DM(HAC) vs Naive + interval coverage)"
p2_logic_break_header_prefix: "Logic-break notice"
p2_logic_ac1_line: "- Training-window market-return AC1={ac1} below τ_AC1 (logic break)."
p2_logic_cos_line_prefix: "- Rolling cosine between test-window S_t and numeric forecast μ (cross-sectional mean) = {cos}"
p2_logic_cos_break_suffix: "; semantic and numeric trends diverge (logic break)"
p2_symbol_search_label: "Symbol (searchable)"
p2_symbol_search_placeholder: "Search ticker…"
p2_density_hint: "Tip: high/low-density contrast is emphasized; click a legend entry to hide its density and μ ridgeline."
p2_caption_jsd_current: "*Edges and the **JSD triangle mean (current symbol)** are daily averages for **{sym}** over the test window; global-aggregate triangle mean = {g_tri}.*"
p2_caption_missing_sym: "*Edges and triangle mean are global aggregates (current symbol has no per-symbol cache — rerun the pipeline to populate `jsd_by_symbol`).*"
p2_caption_global: "*Edges and triangle mean are global aggregates.*"
p2_fig21_caption: "Shadow model selection & pixel matrix (MSE / shadow validation / composite score)"
p2_fig22_caption: "Time × return density (Y-axis · μ ridgeline · coloring)"

# ─── Main · P3 (Automatic defense) ────────────────────────────────────────────

p3_adaptive_header: "AdaptiveOptimizer & three-stage defense"
p3_st_reuse_note: "Test-window S_t is shared with right-sidebar FigX.1; shadow-selection results now appear at the top of Phase 2."
p3_fig33_caption: "Dual-track Monte Carlo"

# ─── Main · P4 (Experiment conclusions) ───────────────────────────────────────

p4_fig41_title: "Figure 4.1 · Warning-effectiveness check (fixed 5-day window)"
p4_fig411_title: "Figure 4.1.1 · Simple daily returns in the 5 days after a current-symbol alert"
p4_symbol_search_placeholder: "Search symbol (e.g. NVDA)"
p4_placeholder_daily_return: "Daily return"

# ─── Right Sidebar (Defense indicators) ───────────────────────────────────────

# Titles and placeholders in the right sidebar are sourced via `get_figure_title` /

# `get_status_message`. See `figures_titles.md` and `status_messages.md`. Key roster

# for convenience: fig_x_1..fig_x_6 (outer card titles), fig_x_1_explain..6 (Invest

# explanation-card titles), fig_x_1_explain_res..6_res (Research explanation-card

# titles), idle_placeholder (pre-run), placeholder_jsd / placeholder_cosine (chart

# skeletons), figx_run_prompt (pre-run prompt).

# ─── Left Sidebar · parameter block (auxiliary greys) ─────────────────────────

# Block titles and help tooltips live in `sidebar_left.md` +

# `sidebar_left_params_explanations.md`. This section only records the grey

# auxiliary labels produced directly by `_aux_label("...")`.

aux_k_jsd_scale: "k_jsd baseline scale"
aux_epsilon_floor: "ε baseline floor"
aux_alpha_base: "α baseline coefficient"
aux_beta_penalty: "β penalty coefficient"
aux_gamma_cap: "γ penalty cap"
aux_shadow_alpha_mse: "α is MSE weight, 1−α is JSD weight"
aux_shadow_holdout: "Shadow holdout length (training-window tail only)"
aux_oos_fit_steps: "OOS refit steps"
aux_oos_mark_fastest: "1 (fastest)"
aux_oos_mark_full: "Full"
aux_mc_scenario_step: "Nth trading day (from test-window start) when the “black-swan” shock is injected"
aux_mc_scenario_impact: "“Black-swan” shock magnitude (log return)"

# ─── Left Sidebar Tabs · self-check & feedback (Overview / Defense tabs) ──────

sidebar_tab_overview_label: "Research Project Overview"
sidebar_tab_params_label: "Defense Strategy & Parameters"
sidebar_thought_process_header: "System Thought Process"
sidebar_theme_dark_switch: "Dark theme"
sidebar_copy_report_btn: "Copy report + remarks"
sidebar_feedback_placeholder: "Optional: describe the symptom (e.g. “spinner keeps spinning after Recompute”)"
sidebar_collapse_toggle_label: "<<"