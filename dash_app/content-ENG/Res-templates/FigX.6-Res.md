# FigX.6 · Semantics – Numerical Rolling Cosine (Research · Class C)

**Object type (C)**: Self-developed method key scalar sequence. This object performs rolling cosine similarity between the semantic path S_t in the test window and the "shadow optimal" prediction mean sequence \bar{\mu}^{}_t on the numerical side to answer an engineering question:

> **Is there a "directional opposition" between semantic narrative (news sentiment) and numerical narrative (shadow optimal prediction mean)? **

When the rolling cosine appears to have a negative value, the system regards it as a "semantic-numeric logic break" and can directly trigger Level 2 (fuse).

This article is aligned with the sidebar rendering template: `dash_app/render/explain/sidebar_right/figx6.py` · `build_figx6_explain_body(...)` Placeholders will be injected: `{cos_w}`, `{cosine}`, `{lb_cos}`, `{sem_cos_computed}`, `{train_return_ac1}`, `{tau_ac1}`, `{logic_break_ac1}`, `{logic_break_total}`, `{st_path_tail_md}`, and general fields `{train_start}`, `{train_end}`, `{test_start}`, `{test_end}`, `{p0_symbols_csv}`, `{credibility}`.

Placeholders: `**{cosine}`** · `**{cos_w}**` · `**{lb_cos}**` · `**{logic_break_total}**`

---

## 1. Graphics pipeline (end-to-end)
```text
FigX.1: meta.test_sentiment_st → Align to get S_t
Phase2 strict OOS: daily μ_{m,s,t} / σ_{m,s,t}
→ Shadow model selection best_model_per_symbol[s]
→ Daily shadow optimal cross-sectional mean μ̄*_t = mean_s μ_{best(s),s,t}
→ rolling cosine (window W=semantic_cosine_window):
      cos_t = <S_{t-W+1:t}, μ̄*_{t-W+1:t}> / (||·|| ||·||)
→ any cos_t < 0 ⇒ logic_break_semantic_cosine_negative=True
→ Dash: fig_defense_semantic_cosine (display S_t, μ̄*_t, cos_t, and mark the first time cos<0)
```---

## 2. Self-developed algorithm logic architecture (core methodology)

### 2.1 Why use "rolling cosine": turning two heterogeneous sequences into "directional consistency" of the same scale

The semantic sequence S_t and the numerical sequence \bar{\mu}^{}_t have different dimensions and amplitudes, and it is meaningless to compare them directly. Cosine similarity only cares about "directional consistency":

- cos > 0: The semantics of the last W days are in the same direction as the overall value (good news is accompanied by a positive mean/bad news is accompanied by a negative mean).
- cos < 0: In recent W days, the semantics and numerical values ​​have been in the opposite direction (bad news has been continuously judged as a positive mean by the numerical side, or vice versa). This is regarded as a "narrative conflict" and requires system defense.

### 2.2 Why use “shadow optimal” \bar{\mu}^{}_t instead of fixed model

Fixed selection of a model will turn "cosine divergence" into "model selection bias". Phase2 first selects the optimal model for each asset based on the training tail shadow holdout, and then summarizes the daily optimal μ of the test window as \bar{\mu}^{}_t, so that the numerical side represents "the current most credible set of prediction narratives".

---

## 3. Data Provenance & Physical Profile

### 3.1 Data fingerprint

- Semantics: `phase0.meta.test_sentiment_st` (dates/values)
- Value: `phase2.test_daily_best_model_mu_mean` (length aligned with `phase2.test_forecast_dates`)
- Parameter: `policy.semantic_cosine_window = {cos_w}`

### 3.2 Variable mapping (runtime injection)

| Variable | Field | Inject value |
| ---------- | ----------------------------------------------- | -------------------------- |
| latest cosine | `phase2.cosine_semantic_numeric` | `**{cosine}**` |
| Whether the calculation is successful | `phase2.semantic_numeric_cosine_computed` | `**{sem_cos_computed}**` |
| Logic break (cosine) | `phase2.logic_break_semantic_cosine_negative` | `**{lb_cos}**` |
| Logic break (total) | `phase2.logic_break` | `**{logic_break_total}**` |
| S_t tail segment (audit) | `meta.test_sentiment_st` | `{st_path_tail_md}` |

---

## 4. The Execution Chain

| Serial number | Logical stage | Input variables | Output target | Core algorithm/rules | Code anchor |
| --- | ---- | ---------------------------------- | ---------------------------- | -------------------------- | -------------------------------------------------- |
| 1 | Semantic alignment | `test_st_series` + `test_dates` | `st_arr` | reindex + ffill/bfill | `research/phase2.py` |
| 2 | Shadow model selection | `train` + `close` | `best_model_per_symbol` | Shadow holdout scores (MSE/JSD combination) | `research/phase2.py:_tail_holdout_scores` |
| 3 | Numeric sequence | `model_mu_test_ts` + best model | `μ̄*_t` | Section mean | `research/phase2.py:test_daily_best_model_mu_mean` |
| 4 | Rolling cosine | `st_arr`, `μ̄*_t`, W | `roll_cos` | Cosine similarity | `research/pipeline.py:_rolling_cosine_series` |
| 5 | Trigger flag | `roll_cos` | `lb_cos`/`cosine` | any <0; valid value at end | `research/phase2.py` |
| 6 | Drawing | `p2/meta` | FigX.6 | Three-track same picture + first breach vertical line | `dash_app/figures.py:fig_defense_semantic_cosine` |

---

## 5. Key data calculation example (important values)

**μ̄*_t** depends on **`best_model_per_symbol`**; the following **§5.1** has the same origin as **`Figure2.1-Res.md` §6.1**, **§6.2～§6.4** For the full model selection table and NVDA decomposition, see **`Figure2.1-Res.md` §6.2～§6.4**.

### 5.1 Premise (same origin as Fig2.1 §6.1)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

### 5.2 Full model selection table and NVDA MSE/combined (cross-reference)

See **`Figure2.1-Res.md` §6.2～§6.3**. The structure of `\bar{\mu}^{}_t` is in the code **take the best model μ daily and then cross-sectional mean**. During the audit, you should first check that **`best_model_per_symbol`** is consistent** with the pixels of Fig2.1, and then check **`test_daily_best_model_mu_mean`**.

---

## 6. Relationship with other objects (responsibility boundaries)

- **With FigX.1**: FigX.1 gives S_t; FigX.6 takes it as one of the inputs, otherwise the cosine cannot be calculated.
- **With FigX.4 (Believability)**: Believability is "probabilistic consistency" and cosine is "narrative consistency". Both can trigger more conservative defenses, but have different meanings.
- **With FigX.5 (JSD stress)**: JSD is "model-model divergence"; cosine is "semantic-numeric conflict". They are tied hard triggers in Level 2.

---

## 7. Consistency check (reproducible verification steps)

1. Check that `len(test_forecast_dates)` is consistent with `len(test_daily_best_model_mu_mean)`; if insufficient, FigX.6 should not be drawn.
2. Use the same window W={cos_w} to recalculate the rolling cosine sequence:
- `cosine_semantic_numeric` is equal to the last valid window value;
  - There is any window < 0 ⇔ `lb_cos` is YES.
3. Check the total logic break: `logic_break_total` should at least contain the OR relationship between `lb_cos` and `logic_break_ac1` (Phase2 merge caliber).

---

## 8. Method limitations

- **Cosine only looks at direction, not cause and effect**: cos<0 only shows that "the two sequences in the last W days have opposite directions", but cannot prove that "semantics cause numerical errors" or "numeric values cause semantic errors", which is an engineering trigger signal.
- **Window sensitive**: If W is too short, it will be sensitive to noise and cross zero frequently; if W is too long, the alarm will be delayed. This parameter needs to be adjusted in combination with the test window length and news coverage density.
- **Shadow optimization introduces non-stationarity**: the best model is selected at the end of training, but the test window may have a structural mutation; at this time \bar{\mu}^{}_t bias will cause cosine false positives.
- **S_t timestamp error will amplify the divergence**: If the spikes of S_t are misaligned, it will introduce false direction conflicts within the window, thereby falsely triggering lb_cos.

---

## Defense-Tag (If-Then conditional expression)

**If** `Semantic departure trigger = {lb_cos}` **Then**
`FigX.6: On {cos_alarm_date}, semantics – numerical rolling cosine = {cos_at_breach} appears negative for the first time → {cos_alarm_date} is the first warning day, and the defense level switches to Level 2`
`severity: danger`

**Else**
`FigX.6: Semantics – No negative values appear in numerical rolling cosine (last value ={cosine}); the current variable has no direct impact on defense level switching`
`severity: success`

> The copywriting uses `content-CHN/defense_reasons.md` as the source of fact; if you need to modify it, please update the summary table simultaneously.