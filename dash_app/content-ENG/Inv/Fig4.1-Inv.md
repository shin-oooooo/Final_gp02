# Figure 4.1 · Sidebar JSD stress & semantic cosine (main-panel replay)

> The main panel replays the same data as sidebar FigX.5/6 for screenshots and full-window comparison.

---

## JSD stress replay

1. **Triangular JSD mean (test window)**: `{jsd_triangle_mean}`
2. **Dynamic yield threshold τ**: `{jsd_stress_dyn_thr}` (`k_jsd`=`{k_jsd}` × max(train baseline `{jsd_baseline_mean}`, ε=`{jsd_baseline_eps}`))
3. **Stress triggered**: `{jsd_stress}`
4. **Rolling window W**: `{cos_w}` days (shared with FigX.6 semantic cosine via `semantic_cosine_window`)

---

## Semantic cosine replay

1. **Rolling window W**: `{cos_w}` days
2. **Last-window cosine scalar**: `{cosine}`
3. **Ever < 0 (semantic–numeric divergence)**: `{lb_cos}`
4. **Aggregate logic break**: `{logic_break_total}`

---

## Early-warning validity on stress day

**If** `at least one signal lead > 0 = {early_warning_valid}` **Then**

→ Early warning is effective: {early_warning_signals} fired before the stress day with leads:

{early_warning_leads_md}

**Else**

→ Early warning underperformed: signals did not trigger before the stress day, or all leads ≤ 0.

---

## Expectation check

**If** `JSD stress not triggered = {jsd_stress_no}` **and** `rolling cosine ≥ 0 = {cosine_ge_zero}` **Then**

→ Main-panel replay matches sidebar: no model split or semantic divergence signal.

**Else**

→ Main-panel replay shows stress or divergence, consistent with sidebar FigX.5/6 alerts.
