# Figure4.1 · Early Warning Effectiveness Test (Research · Category C)

**Object type (C)**: Self-developed method "advance validity" test. Figure4.1 consists of two sub-figures, and each sub-figure is superimposed with the same set of research verification annotation layers:

- **Figure 4.1a (JSD)**: Rolling triangle JSD stress time series + dynamic threshold + `t_ref/t_alarm` overlay;
- **Figure 4.1b (cosine)**: Semantics – numerical rolling cosine timing (with cos=0 line) + `t_ref/t_alarm` overlay.

The research caliber of this object is: select a "price instability reference day" t_{\mathrm{ref}} in the test window, and verify whether the alarm day t_{\mathrm{alarm}} satisfies the **lead amount** L=t_{\mathrm{ref}}-t_{\mathrm{alarm}}\in[1,5] (trading day). If satisfied, the "effective advance blue band" is drawn on the graph, and the "green observation window 1-5 days after the alarm" is drawn for posterior testing.

This article is aligned with the sidebar rendering template: `dash_app/render/explain/main_p4/fig41.py` · `build_fig41_explain_body(...)` will inject placeholders:
`0.00000000`, `0.00000000`, `否`, `是`, `0.00000000`, `2.0000`, `1.0000e-09`, `5`, `⟦PH12 ⟧`, `否`, `是`, `否`, `无`, `- 无有效提前量`, `否`, `价格不稳参照日`, and general fields `—`, `—`, `—`, `—`, ``, `0.00000000`.

> **Unified window size**: `5` = `DefensePolicyConfig.semantic_cosine_window` (default 5 days) simultaneously acts as the rolling window **W** of JSD stress (the original `n_jsd` is obsolete) and FigX.6 semantic – numerical rolling cosine window. The sidebar "W calculates the rolling window length" is the same strategy parameter.

Placeholder: `**否`** · `**无**` · `**价格不稳参照日**`

---

## 1. Graphics pipeline (end-to-end)
```text
Phase2 output (base image):
- FigX.5: test_daily_triangle_jsd_mean + τ_jsd → JSD timing
- FigX.6: rolling cosine(S_t, μ̄*) → cosine timing

Phase3.defense_validation (research validation field):
- fig41_ew_ref_test_row (t_ref row order)
- fig41_ew_jsd_alarm_row / fig41_ew_cos_alarm_row (t_alarm row order)
- fig41_ew_lead_effective_lo/hi (default 1..5)

Dash drawing:
- fig_fig41_jsd_early_warning = FigX.5 base image + apply_fig41_early_warning_overlay
- fig_fig41_cos_early_warning = FigX.6 base figure + apply_fig41_early_warning_overlay
```---

## 2. Self-developed algorithm logic architecture (core methodology)

### 2.1 Why do we need “validity testing”: early warning does not mean effectiveness

Many signals in the system can "issue alarms", but the research question is: **Does the alarm give the available lead time**? Figure4.1 Separates “alarm occurrence” from “whether the alarm occurs earlier than the price instability reference day”:

- **Alarm**: signal triggered (JSD breach or cos<0).
- **valid**: The alert occurred 1–5 trading days before t_{\mathrm{ref}}.

Only in this way can "the signal itself" be distinguished from "the signal's predictive value for actual risk".

### 2.2 Three core time points/intervals

- **t_{\mathrm{alarm}}**: First alarm date (one each for JSD and cosine).
- **t_{\mathrm{ref}}**: Price instability reference day (identified by pipeline research logic from realized returns and mapped to the test row sequence of Phase2).
- **Observation window**: t_{\mathrm{alarm}}+1 to t_{\mathrm{alarm}}+5 (fixed, for posterior metrics/visualization consistency).

---

## 3. Data Provenance and Variable Mapping (Data Provenance)

### 3.1 x-axis alignment aperture

The x-axis of the two subfigures comes from the test day series of Phase2, but because different series may have different lengths, the drawing function will truncate the alignment according to the shortest length (see `_p2_jsd_chart_dates/_p2_cos_chart_dates` in `dash_app/figures.py`).

### 3.2 Runtime injection fields (core summary)


| Variable | Inject value |
| --------- | ------------------------------------------ |
| Reference day definition | `**价格不稳参照日`** |
| Is there an effective lead time | `**否**` |
| Lead time summary | `**无**` |
| Detailed lead time | `- 无有效提前量` |
| JSD: Stress or not | `**否**` (or `是` if not) |
| Cosine: Whether to diverge | `**否**` (if not, you can see `是`) |


---

## 4. The Execution Chain


| Sequence number | Logical stage | Input | Output | Rules | Code anchor |
| --- | -------- | --------------------- | --------------------- | ---------------- | ------------------------------------------------------------- |
| 1 | Reference day identification | Test window realized returns | `t_ref` (mapped to test_row) | Price instability operationalization (see label) | `research/pipeline.py:_failure_identification_research` |
| 2 | Alarm day (JSD) | `daily_tri` + threshold | `t_alarm_jsd` | First rolling breach | Same as above |
| 3 | Alarm day (cosine) | `roll_cos` | `t_alarm_cos` | First time cos<0 | Same as above |
| 4 | Overlay drawing | `t_ref/t_alarm` + date list | Blue belt/green belt/vertical line | L∈[1,5] only draws blue belt | `dash_app/figures.py:apply_fig41_early_warning_overlay` |
| 5 | Subfigure output | FigX.5 / FigX.6 base map | Fig4.1a / 4.1b | The overlay does not change the base map value, only increases the shape | `dash_app/figures.py:fig_fig41_*_early_warning` |


---

## 5. Graphics overlay element semantics (must be consistent with the latest implementation)

- **t_ref vertical line (yellow)**: refer to the pressure day (row=`fig41_ew_ref_test_row`).
- **t_alarm vertical bar (pink)**: first alarm date (row=`fig41_ew_jsd_alarm_row` or `fig41_ew_cos_alarm_row`).
- **Blue band**: Appears when and only when the advance amount L\in[1,5], indicating the "early warning effective area".
- **Green Band**: The 1st to 5th trading days after the alarm (fixed posterior observation window).

---

## 6. Key data calculation example (important values)

**Phase2 shadow model selection** The premise and model selection table of the whole library have the same origin as **`Figure2.1-Res.md` §6**. The following table is consistent with **§6.1**; the complete content of **§6.2~§6.4** can be found in **`Figure2.1-Res.md` §6.2~§6.4** (must not conflict with the values ​​there).

### 6.1 Premise (same origin as Fig2.1 §6.1)

| Project | Value |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **`data.json` meta** | **`source`** = `akshare`, `**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **Post-parsing training window (ISO)** | **`2024-01-02`**～`**2026-01-30`** |
| **`shadow_holdout_days`** (cfg/effective **`n_tail_eff`**) | **40** / **40** |
| **`alpha_model_select`** | **0.5** |

### 6.2 Reading boundary with Fig4.1

Fig4.1 The superimposed **warning/reference date** is determined by the **Phase3 research field** and the **test window row number**, and the `best_model_per_symbol` will not be recalculated; the model selection number is still only based on **`Figure2.1-Res.md` §6**.

---

## 7. Consistency check (reproducible verification steps)

1. Check that the rows of `t_ref/t_alarm` are in legal test row order (0 ≤ row < len(test_dates)).
2. Recalculate the lead time L and check:
  - If L\in[1,5], a blue effective band should appear in the picture;
  - Otherwise, no blue band will appear, but there will still be vertical lines (if row is not empty).
3. Check the green band: always from alarm+1 to alarm+5 (truncated to the end of the test window).

---

## 8. Relationship with other objects (responsibility boundaries)

- **With FigX.5 / FigX.6**: Fig4.1 does not change the calculation of the base chart indicators, but only superimposes the "research verification time point" onto these time series diagrams.
- **With Phase3.defense_validation**: The core evidence of Fig4.1 comes from the research fields written by Phase3; without these fields, the figure can only show the base map at best and cannot test the "advance validity".

---

## 9. Method limitations

- **Fungibility of reference day definition**: `research_failure_ref_label` currently uses a "price instability operationalization" rule; changing the rule (e.g. MDD breakout, higher/lower volatility quantile) would change t_{\mathrm{ref}}, thus changing the validity conclusion.
- **The advance interval is an engineering choice**: [1,5] is the strategic operable window rather than the statistical optimum. Different trading frequencies/position periods may require different intervals.
- **Insufficient samples and truncation**: When the test window is very short or the sequence is missing resulting in truncation, the positioning of t_{\mathrm{alarm}} will become unstable, thus affecting the validity judgment.
- **"Effective" does not equal "sufficient"**: Even if the advance amount falls within [1,5], it does not guarantee that the defense strategy will be better than the counterfactual; it only proves that "the alarm occurred before the reference date", which needs to be further verified in combination with Fig4.2 or posterior indicators.

---

## Defense-Tag (If-Then conditional expression)

**If** `Alert valid = 否` **Then**
`Fig4.1: Early warning is valid (无), reference day definition: 价格不稳参照日`
`severity: success`

**Else**
`Fig4.1: No effective advance is observed (need to check the t_ref definition or whether the signal trigger is too late), refer to the day definition: 价格不稳参照日`
`severity: warn`