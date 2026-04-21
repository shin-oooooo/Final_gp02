# FigX.1 · S_t Sentiment Path (Research · Category C)

**Object type (C)**: Self-developed method key scalar sequence. This object displays the daily sentiment of the test window S_t\in[-1,1], and assumes two types of "downstream consumable" engineering responsibilities:

1. **Defense state machine input**: `resolve_defense_level(...)` uses **min(S_t)** (if there is no sequence, it falls back to scalar S).
2. **Pressure Scenario Parameter Injection**: When Phase3’s Monte Carlo allows daily injection, S_t becomes the exogenous driver of jump diffusion (path version λ_t / impact_t).

This article is aligned with the sidebar rendering template: `dash_app/render/explain/sidebar_right/figx1.py` · `build_figx1_explain_body(...)` will read `snap_json["phase0"]["meta"]["test_sentiment_st"]`, `snap_json["phase0"]["meta"]["sentiment_st_kernel"]` with `DefensePolicyConfig` and inject the placeholder into `FigX.1-Res.md`. Therefore this article must retain placeholders: `{train_start}`, `{train_end}`, `{test_start}`, `{test_end}`, `{p0_symbols_csv}`, `{credibility}` (generic fields injected by Phase2), and FigX.1 Exclusive: `{tau_s_low}`, `{st_min}`, `{st_max}`, `{st_last}`, `{st_news_days}`, `⟦PH1 1⟧`, `{sentiment_penalty}`, `{sentiment_severity_boost}`, `{sentiment_vader_avg}`, `{sentiment_n_headlines}`, `{sentiment_kernel_method}`.

Placeholders: `**{st_min}`** · `**{st_last}`** · `**{tau_s_low}`** · `**{st_news_days}`** · `**{sentiment_halflife_days}`**

---

## 1. Graphics pipeline (end-to-end)
```text
sentiment_detail (aggregated by sentiment_proxy news title + date + keyword penalty penalty + per-ticker severity_boost)
  → run_pipeline:
      vader_st_series_kernel_smoothed_from_detail(
          detail, test_index,
halflife_days = policy.sentiment_halflife_days, # ← Calendar day half-life
penalty = detail["penalty"], # ← constant offset (one time for the whole window)
severity_boost= detail["severity_boost"], # ← constant offset (one time for the whole window)
      )
→ st_test: pd.Series(index=test trading day, values=S_t)
      → meta["test_sentiment_st"]       = {"dates":[...],"values":[...]}
      → meta["sentiment_st_kernel"]     = {"method","halflife_days","penalty","severity_boost","vader_avg","n_headlines"}
→ sentiment_for_defense = min(S_t) # State machine input
→ sentiment_effective = last(S_t) # Scalar fallback/display and fallback of certain parameters
  → Dash figure: fig_st_sentiment_path(test_sentiment_st, sentiment_scalar)
→ FigX.1 (polyline + horizontal dashed line: scalar S)
```---

## 2. Self-developed algorithm logic architecture (core methodology)

### 2.1 Why construct S_t: Turn "event intensity" into an auditable one-dimensional exogenous driver

In the defense system, emotions are not meant to "explain benefits", but to provide an exogenous variable within the model system that is relatively independent of the benefit prediction link and solve two engineering pain points:

- **The state machine needs a memory of the "lowest point of bad news"**: If you only look at the final value S_{T}, the rapid rebound after the extreme event day will cover up traces of risk; therefore, the state machine uses **min(S_t)**, which is equivalent to recording "how bad the worst day is within the test window."
- **Pressure simulation requires resolvable timing driver**: When `mc_sentiment_path` is available, Phase3 can use S_t to adjust the jump risk intensity on a day-by-day basis, so that the pressure cloud is not an "indifferent" perturbation, but an injection that can be played back to a specific date.

### 2.2 MVP methodology (v2 · Normalized memory + tanh soft truncation): Show real fluctuations

**Abandon the old caliber ("segmentation + equal value injection")**: The original implementation is segmented by calendar, writing all trading days in the entire segment as the same plateau, and only doing a recursion `ρ·state + M` at the segment boundary; multiple segments of pessimistic news will push the state to −1, and the intermediate trading days appear to be "attenuated over time".

**Side effects of v1 exponential kernel (unnormalized)**: For the window of "almost all negative news", `H_t` monotonically accumulates to −1 with the news density; then superimpose the two negative constants of `penalty + severity_boost` for the entire window, S_t is easily hard clipped in the narrow band of [−1, −0.9], and no fluctuation is visually visible.

**v2 caliber (current version · normalization + damping + soft truncation)** — for each test trading day t (corresponding to calendar day `t_cal`):

$$
S_t = \operatorname{softclip}\bigl(\alpha\,V_t + \beta\,\mathcal{H}_t + \gamma(P+B)\bigr),\qquad \operatorname{softclip}(x)=\tanh(x)
$$

- **Today item V_t**: If there is a headline on the calendar day of trading day t, take the robust aggregation of VADER `compound` on that day (sample <5 median, ≥5 take 20% censored mean), and clip to [−1,+1]; otherwise it is 0.
- **Normalized historical memory item** (v2 key changes):
  $$
  \mathcal{H}_t = \frac{\sum_{i\in\mathcal{N}(t),\,i<t_{\mathrm{cal}}} 2^{-(t_{\mathrm{cal}}-i)/H}\cdot M_i}{\sum_{i\in\mathcal{N}(t),\,i<t_{\mathrm{cal}}} 2^{-(t_{\mathrm{cal}}-i)/H}}\;\in[-1,+1]
  $$
  After normalization, the dimension of `H_t` is consistent with `V_t`, and **does not accumulate monotonically with news density** - "more negative news" will only make `H_t` closer to the historical daily average, but will not peg S_t at −1.
- **Vibration damping constant offset γ(P+B)**: directly take the `penalty` (keyword risk ∈ [−0.35, +0.15]) and `severity_boost` (per-ticker context correction ∈ [−0.70, +0.25]) calculated in one time for the entire window in `sentiment_detail`, and multiply them by γ for compression to avoid individual contributions that directly push S_t out of the upper and lower bounds.
- **tanh soft truncation**: converge with S-shape asymptotically at ±1, avoiding plateau; `soft_clip="hard"` degenerates into the old hard clip.
- **Training-window warm-up (v3 key change)**: at headline-filtering time, push the lower bound forward by `warmup_days = max(60, 2·n_test_td, ⌈3·H⌉)` calendar days (computed in `research/pipeline.py::_resolve_test_sentiment_path` and passed in explicitly). Raising the floor from v2's bare `⌈3·H⌉` to **at least 60** feeds training-tail headlines into the `H_t` memory early enough to **eliminate** the cold-start constant prefix where `V_t=H_t=0 → S_t ≡ tanh(offset_const)`.
- **Default parameters (v3.1)**: α=**1.0**, β=**0.2**, γ=**0.10**, H=**2** calendar days; `normalize_kernel=True`, `soft_clip="tanh"`, `include_today_in_memory=False`. vs v3 (0.7/0.4/0.3/3) — only four scalar knobs turned, formula unchanged: α↑ (full weight on today), β↓ (historical low-pass halved), γ↓ (constant offset cut from −0.27 to −0.09 when penalty≈−0.3 + boost≈−0.6), H↓ (memory even shorter). Expected ptp lifts from ≈0.65 to ≈0.9~1.0 and mean(S_t) rises from ≈−0.63 to ≈−0.25.
- **Double-layer filtering gate (new in v2)**: The news crawling side is switched to the general **Seed thesaurus gate** `_headline_passes_seed_gate`:
  - Fragments with word count < 4 / length < 16 characters → reject;
  - hit `_HEADLINE_PAGE_NAV_JUNK_RE` ("penny stocks", "tax brackets", "budget & performance", "administrative law judge", "harmed investors", NewsAPI rate excess text, etc.) → reject;
  - Missed on any of the `CRAWL4AI_TITLE_SEED_TERMS` seed words → Reject.
  **Available for all sources** (RSS / NewsAPI / Google News Geo / AKShare / Crawl4AI), controlled by the environment variable `NEWS_SEED_GATE_ALL_POOLS=1` (enabled by default).

- **Three-layer constant-trap guards (introduced in v2, synthetic amplitudes scaled up 10× in v3.1)** — cover the three degenerate regimes "no headlines in the filter window", "all headlines land on a single day", and "`per_day` non-empty but `H_t` collapses to a constant". They guarantee **S_t never degenerates into a flat line** and stamp the firing branch into `sentiment_detail["_st_trace"]`, surfaced in the `[S_t]` console line and the FigX.1 diagnostic block:
  - **Guard #1 (extended look-back retry)**: if `per_day` is empty within `warm_start..test_end`, extend the look-back to `max(2·warmup_days, 90)` calendar days and re-aggregate — this lets distant training-tail headlines still build a **decaying but non-constant** `𝒢_t`.
  - **Guard #2 (no headlines → synthetic fallback)**: still empty after extension, bypass the main `V_t + H_t` loop entirely; emit `tanh(fallback + γ(P+B))` plus a deterministic **±0.30·sin(φ) + ±0.10·sin(3φ)** sine jitter (v3.1: amplitudes were 0.03/0.01 and got squashed by tanh's ≈0.64 derivative at |base|≈0.6 down to `ptp≈0.035`, which looked identical to a flat line). Tags `synthetic_reason="no_headlines_in_extended_warmup"`.
  - **Guard #3 (kernel near-constant → overlay jitter)**: main loop completed but `ptp < 5e-4` (typical cause: all headlines on the same calendar day, so `H_t` is constant from that day onward). Overlay **±0.20·sin(φ) + ±0.08·sin(3φ)** on top of `S_t`. Tags `synthetic_reason="kernel_output_near_constant"`.

- **Parameter echo log (new in v3.1)**: `vader_st_series_kernel_smoothed_from_detail` prints `[S_t:params] alpha=... beta=... gamma=... H=... warmup=... P=... B=... offset_const=...` at entry. Seeing α=0.7 / β=0.4 / γ=0.3 / H=3 in the console means the process is still running **old v3 bytecode** — clear `__pycache__` and restart.

### 2.3 Scoring object and variable dictionary

- **Sequence**: S_t (test window day by day, range clip to [-1,1]).
- **State machine input**: S_{\min}=\min_t S_t.
- **Threshold**: \tau_{S,low}=\texttt{policy.tau_s_low}=**{tau_s_low}** (When the consistency is high enough, it is still required that the emotion is not lower than the threshold before entering Level 0).
- **Half-life**: H=\texttt{policy.sentimenthalflifedays}=**{sentiment_halflife_days}** calendar days.
- **Constant bias**: `penalty`=**{sentiment_penalty}**, `severity_boost`=**{sentiment_severity_boost}**; full-window VADER mean (reference value)=**{sentiment_vader_avg}**; pooled headline number=**{sentiment_n_headlines}**.

---

## 3. Data Provenance & Physical Profile

### 3.1 Data Fingerprint

- **Training**: `**{train_start}`**~`**{train_end}`**
- **Test**: `**{test_start}`**～`**{test_end}`**
- **universe**:`**{p0_symbols_csv}`**
- **Sequence truth source**: `snap_json["phase0"]["meta"]["test_sentiment_st"]` (`dates/values`)

### 3.2 Variable Mapping

- **Core input variables X**:
  - `meta.test_sentiment_st` → S_t
  - `policy.tau_s_low` → \tau_{S,low}
- **Target observation variable Y (runtime injection)**:
  - `S_t` summary: min=`**{st_min}`**, max=`**{st_max}`**, last=`**{st_last}**`
  - "Coverage days/caliber": `**{st_news_days}**` (see sidebar builder for specific caliber)

---

## 4. The Execution Chain


| Serial number | Logical stage | Input variable (Variable) | Output target (Target) | Core algorithm/rules | Code anchor (Function, File) |
| --- | ----------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 1 | News summary | `sentiment_detail` | dated headlines + `penalty` + `severity_boost` | Fetch/remove/capping/rule correction + keyword penalty + per-ticker correction | `research/sentiment_proxy.py` |
| 2 | Daily robust aggregation | `published` + `compound` of headlines | M_i,\ i\in \mathcal{N} | Daily: <5 takes the median, ≥5 takes the 20% censored mean, clip to [−1,+1] | `_robust_daily_compound`, `research/sentiment_proxy.py` |
| 3 | Exponential kernel convolution generates S_t | M_i + trading index + `halflife_days` + `penalty` + `severity_boost` | `st_test` | S_t=\tanh\bigl(\alpha V_t+\beta\mathcal{H}_t+\gamma(P+B)\bigr); kernel distances in calendar days; Guard#1/#2/#3 kick in on degenerate branches | `vader_st_series_kernel_smoothed_from_detail`, `research/pipeline.py` |
| 4 | Snapshot writing | `st_test` + kernel diagnostics | `meta.test_sentiment_st` + `meta.sentiment_st_kernel` | dates/values + {method, halflife_days, penalty, boost, vader_avg, n} | `research/pipeline.py` |
| 5 | State machine input | `st_test` | `sentiment_for_defense=min(S_t)` | Risk memory (worst day) | `research/defense_state.py:resolve_defense_level` |
| 6 | UI mapping | `meta.test_sentiment_st` | FigX.1 polyline + horizontal line | y-axis fixed [-1.05,1.05], fallback branch marked red | `dash_app/figures.py:fig_st_sentiment_path` |
| 7 | Research copywriting injection | `snap_json` + `policy` | Article placeholder replacement | String template replacement | `dash_app/render/explain/sidebar_right/figx1.py:build_figx1_explain_body` |


---

## 5. Key data calculation example (important values)

**FigX.1** only consumes **emotion sequence**, **does not** directly read `best_model_per_symbol`; in order to align with the full library **Phase2 shadow model selection** audit, the following **prerequisite table** has the same origin as **`Figure2.1-Res.md` §6.1**, **§6.2～§6.4** See **`Figure2.1-Res.md` for the model selection value §6.2～§6.4**.

### 5.1 Premise (same origin as Fig2.1 §6.1)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

### 5.2 Full model selection table and NVDA decomposition (cross-reference)

See **`Figure2.1-Res.md` §6.2～§6.4**.

---

## 6. Source code level evidence and parameter assertion (Source Code Traceability)

### 6.1 Core caliber assertion (must be consistent with the state machine)

- The `sentiment` caliber of the state machine is **min(S_t)** (fallback to scalar when there is no sequence), see the docstring and conditional branches of `research/defense_state.py`.
- The drawing of FigX.1 only consumes `meta.test_sentiment_st`, does not change the value, and does not perform aggregation.

### 6.2 Parameter assertion (responsibility boundaries of \tau_{S,low})

- \tau_{S,low} only participates in the **conditional comparison** of Level0/Level1 and does not participate in the generation of S_t; therefore "adjusting the threshold" will not change the polyline shape of FigX.1, but only changes "how the polyline is interpreted by the state machine".

### 6.3 Diagnostic-field assertion (fallback branches must land in meta)

- When Guard #2 / #3 fires, `meta["sentiment_st_trace"]` is populated with `{"constant_trap_synthetic": True, "synthetic_reason": ...}`; the upstream `[S_t]` console line also prints `trace=...` at the tail. Audits **must** consult both to decide whether S_t is a synthetic fallback.
- The `alpha/beta/gamma/H` echoed by `[S_t:params]` at function entry must match `meta["sentiment_st_kernel"]`; any mismatch means the upstream and downstream ran **different Python processes / bytecode caches** — clear `__pycache__` and restart immediately.

---

## 7. Consistency check (reproducible verification steps)

1. Verify that `dates/values` are of equal length, and most of `values` fall within [-1,1].
2. Recalculate `min(values)` and check that it is the `sentiment_for_defense` called by the state machine.
3. If `st_min` is very low but `st_last` is normal, it is a "single-day extreme event has passed" situation: spikes are visible on the graph, but the state machine may still be conservative.

---

## 8. Relationship with other objects (responsibility boundaries)

- **With FigX.6**: When FigX.6 computes the rolling cosine, FigX.1 is the only source of the semantic vector S_t.
- **With Fig3.3**: When path injection is enabled, S_t can drive the jump risk parameter over time, thus explaining "why the pressure cloud is fatter-tailed on some days".

---

## 9. Method limitations

- **Semantic Agent Bias**: VADER + rule penalty is more robust to English; non-English/irrelevant titles turn S_t into noise.
- **Timestamp error**: Backfilling of missing date content will cause event misalignment, causing the S_t peak to fall on the wrong trading day, thus affecting `min(S_t)` and path injection time.
- **min aggregation is too conservative**: An extreme value of noise will "permanently pull down" the emotional input of the window; this is designed for defense, but will sacrifice the robustness to "short noise".
- **Scalar/sequential dual calibers are easily misunderstood**: The most conspicuous one on the picture is `st_last`, but the state machine uses `st_min`; audit must be based on `st_min`.
- **Time resolution limitations of MVP exponential kernel**: `penalty` and `severity_boost` are still calculated once for the entire window and added to each day in the form of a constant; single keyword events will not show a "pulse → decay" shape in this MVP version, and will only be reflected as a baseline offset. The advanced version (subsequent work) will also perform exponential kernel smoothing on penalty.
- **Half-life H is a hyperparameter**: too short → the historical memory weight decays rapidly, and S_t is close to the noise of VADER on the day; too long → the impact of the event lasts too long and is not robust to short noise. v3.1 defaults to H=2 calendar days (short-term, amplified daily volatility); adjust via `DefensePolicyConfig.sentiment_halflife_days`, use H=7 or H=14 for slower events.
- **Synthetic fallback is not real signal**: the `tanh(fallback + γ(P+B)) + sine jitter` emitted when Guard #2 fires is a visible deterministic placeholder and **does not represent actual sentiment**. Audits must check `meta["sentiment_st_trace"]["synthetic_reason"]`; any `no_headlines_in_extended_warmup` / `kernel_output_near_constant` value should trigger a review of headline ingestion and the date window.

---

## Defense-Tag (If-Then conditional expression)

> The following text is automatically selected by the program based on the actual running results and filled in with `{placeholder}`.
**If** `st_min < tau_s_low` **Then**
`FigX.1: The test window sentiment has an extreme low point st_min={st_min} < τ_S_low={tau_s_low}, which may still prevent entry to Level 0 when the consistency is high`
`severity: warn`

**Else**
`FigX.1: st_min={st_min} ≥ τ_S_low={tau_s_low}; the current variables have no direct impact on defense level switching`
`severity: success`