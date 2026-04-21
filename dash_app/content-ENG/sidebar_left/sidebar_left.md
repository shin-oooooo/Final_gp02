# Sidebar-Left · Section titles + micro-labels (merged)

> All **group titles** (formerly `sidebar_left_titles.md`) and **micro-labels / auxiliary tags**
> (formerly `sidebar_left_labels.md`) live in this file, organized as `section → micro-label` hierarchy.
>
> - **Keys** stay flat, English, snake_case; the parser matches line-by-line key-value pairs.
> - H2 `## …` marks a **group title**; the following `*_params: "..."` is the visible group heading in the UI.
> - H3 `### Micro-labels` lists per-control labels inside the group; if a group has **no micro-labels**
>   per Sidebars.md rules, write `None` as placeholder (ignored by parser).
> - H3 `### Auxiliary labels` lists color-band text, axis ticks, button labels, etc.
>
> `get_sidebar_left_title(key)` / `get_sidebar_left_label(key)` read this file; signatures unchanged—legacy
> `sidebar_left_titles.json` / `sidebar_left_labels.json` remain fallbacks.

---

## Defense-level parameters

defense_params: "Defense-level parameters"

### Micro-labels

help_tau_l2_l1: "τ_L2 / τ_L1 credibility thresholds"
help_tau_h1: "τ_H1 structural-entropy threshold"
help_tau_vol: "τ_vol annualized volatility threshold"
help_tau_ac1: "τ_AC1 first-order autocorrelation threshold"

### Auxiliary labels (color bands)

tau_rgy_l2: "L2"
tau_rgy_l1: "L1"
tau_rgy_l0: "L0"
tau_h1_left_lbl: "L1"
tau_h1_right_lbl: "L0"
tau_vol_left_lbl: "L0"
tau_vol_right_lbl: "L1"
tau_ac1_left_lbl: "L1"
tau_ac1_right_lbl: "L0"

---

## JSD stress parameters

jsd_stress_params: "JSD stress parameters"

### Micro-labels

help_k_jsd: "k_jsd baseline scale factor"
help_eps: "ε baseline floor"

---

## Credibility parameters

credibility_params: "Credibility parameters"

### Micro-labels

help_alpha: "α baseline term weight"
help_beta: "β penalty weight"
help_gamma_cap: "γ penalty cap"

cred_min: "Credibility output lower bound"
cred_max: "Credibility output upper bound"

---

## Shadow test (model selection) parameters

shadow_params: "Shadow test (model selection) parameters"

### Micro-labels

help_shadow_alpha_mse: "α weights MSE; 1−α weights JSD"
help_shadow_holdout: "Holdout window length"

---

## Model prediction rollout parameters

model_predict_params: "Model prediction rollout parameters"

### Micro-labels

help_oos_steps: "OOS parameter refresh count"

---

## Level 1 negative-semantics penalty multiplier λ

lambda_params: "Level 1 negative-semantics penalty multiplier λ"

### Micro-labels

None

---

## Dual-track Monte Carlo parameters

mc_params: "Dual-track Monte Carlo parameters"

### Micro-labels

help_scenario_step: "Trading days from test-window start when the “black swan” shock is injected"
help_scenario_impact: "“Black swan” shock size (log return)."

---

## Model–market load-direction test parameters

load_test_params: "Model–market load-direction divergence parameters"

### Micro-labels

help_semantic_cos_window: "W rolling window length"

---

## Warning-success verification parameters

verify_params: "Warning-success verification parameters"

### Micro-labels

verify_train_window: "Training window (days; tail pooling & rolling baseline)"
verify_crash_q: "Crash quantile (%; high-to-low sort)"
verify_std_q: "Std quantile (%)"
verify_tail_q: "Tail quantile (%)"

---

## Model refresh timing parameters

model_update_params: "Model refresh timing parameters"

### Auxiliary labels

# Note: data_max_age / auto_refresh / refresh_now were removed in R1.10; no UI
# control renders them anymore. Keys kept so legacy snapshots / external copy
# indexes do not KeyError.
data_max_age: "(removed) data-freshness threshold — R1.10 falls back to missing-file only"
auto_refresh: "(removed) auto-download on boot — R1.10 always off"
refresh_now: "(removed) manual refresh — R1.10 replaced by missing-file fallback"
refresh_now_icon: "fa-cloud-arrow-down"

---

## Cross-panel shared

### Auxiliary labels

defense_intro_card_title: "Defense strategy overview"
