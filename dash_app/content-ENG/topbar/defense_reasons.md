# Defense Reasons — Defense-Tag copy master list

Central If/Then text for Defense-Tags. `load_defense_tag_text()` prefers `## Defense-Tag` sections inside each
`FigX.*-Inv.md` / `FigX.*-Res.md`; if missing, it falls back here.

success branches (Level 0) end with **`this variable does not directly change defense level`** for wording
consistency.

---

## Level 0 — Not elevated to Level 1/2 (success)

### FigX.1 — Test-window S_t semantic path

**Else**
`severity: success`
`FigX.1: st_min={st_min} ≥ τ_S_low={tau_s_low}; this variable does not directly change defense level`

### FigX.2 — Structural entropy

**Else**
`severity: success`
`FigX.2: H_struct={h_struct_short} ≥ τ_H1={tau_h1}; this variable does not directly change defense level`

### FigX.3 — Asset diagnostics (ADF + high vol + low AC1)

**Else**
`severity: success`
`FigX.3: no notable asset-level anomalies; this variable does not directly change defense level`

### FigX.4 — Credibility score

**Else**
`severity: success`
`FigX.4: credibility c={credibility} > τ_L1={tau_l1}; this variable does not directly change defense level`

### FigX.5 — Model–model stress (JSD)

**Else**
`severity: success`
`FigX.5: rolling triangle JSD mean ≤ τ={jsd_stress_dyn_thr}; this variable does not directly change defense level`

### FigX.6 — Model stress vs. market load direction

**Else**
`severity: success`
`FigX.6: semantic–numeric rolling cosine never negative; this variable does not directly change defense level`

---

## Level 1 — Elevate to Level 1 (warn)

### FigX.1 — Test-window S_t semantic path

**If** `c > τ_l1` and `s_min < τ_s_low`
**Then**
`severity: warn`
`FigX.1: min(S_t)={st_min} < τ_S_low={tau_s_low}, credibility c={credibility} > τ_L1={tau_l1} → elevate to Level 1`

### FigX.2 — Structural entropy

**If** `h_struct < τ_h1`
**Then**
`severity: warn`
`FigX.2: {figx2_trigger_line} → elevate to Level 1`

### FigX.3 — Asset diagnostics (ADF + high vol + low AC1)

**If** `adf_fail_assets` nonempty or `vol_assets` nonempty or `ac1_assets` nonempty
**Then**
`severity: warn`
`FigX.3: asset diagnostics flagged (see list) → elevate to Level 1`

> Runtime builds per-asset lines, e.g.  
> ADF: `{symbol} ADF failed (summary)`;  
> Vol: `{symbol} annualized vol {value} above threshold {tau_vol_melt}`;  
> AC1: `{symbol} first-order AC {value} below threshold {tau_return_ac1}`.

### FigX.4 — Credibility score

**Else If** `τ_l2 < c ≤ τ_l1`  
**Then**  
`severity: warn`  
`FigX.4: τ_L2 < c={credibility} ≤ τ_L1={tau_l1} → elevate to Level 1`

---

## Level 2 — Elevate to Level 2 (danger)

### FigX.4 — Credibility score

**If** `c ≤ τ_l2`
**Then**
`severity: danger`
`FigX.4: credibility c={credibility} ≤ τ_L2={tau_l2} → consensus collapse → elevate to Level 2`

### FigX.5 — Model–model stress

**If** `jsd_stress == yes`
**Then**
`severity: danger`
`FigX.5: on {jsd_alarm_date}, rolling triangle JSD mean={jsd_mean_at_breach} first exceeded τ={jsd_stress_dyn_thr} → first alert day {jsd_alarm_date}, elevate to Level 2`

### FigX.6 — Model stress vs. market load direction

**If** `logic_break_cos == yes`  
**Then**  
`severity: danger`  
`FigX.6: on {cos_alarm_date}, semantic–numeric rolling cosine={cos_at_breach} first negative → first alert day {cos_alarm_date}, elevate to Level 2`
