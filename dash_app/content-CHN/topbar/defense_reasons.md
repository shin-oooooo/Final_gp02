# Defense Reasons — 防御条件标签文案总表

本文档集中维护所有 Defense-Tag 的 If-Then 分支文案。前端 `load_defense_tag_text()` 优先从各 `FigX.*-Inv.md` / `FigX.*-Res.md` 的 `## Defense-Tag` 段落读取；若对应段落缺失，则回退至本文档。

success 分支（Level 0）的结果句统一为 `**当前变量对防御等级切换无直接影响**`，避免各 FigX 各自写法（"无影响" / "不构成额外阻碍" / "不构成触发" 等）带来不一致。

---

## Level 0 — 未提升至 Level 1/2（success）

### FigX.1 — 测试窗 S_t 语义路径

**Else**
`severity: success`
`FigX.1: st_min={st_min} ≥ τ_S_low={tau_s_low}；当前变量对防御等级切换无直接影响`

### FigX.2 — 结构熵

**Else**
`severity: success`
`FigX.2: H_struct={h_struct_short} ≥ τ_H1={tau_h1}；当前变量对防御等级切换无直接影响`

### FigX.3 — 资产异常诊断（ADF + 高波动 + 低 AC1）

**Else**
`severity: success`
`FigX.3: 资产级诊断未发现显著异常；当前变量对防御等级切换无直接影响`

### FigX.4 — 可信度评分

**Else**
`severity: success`
`FigX.4: 可信度 c={credibility} > τ_L1={tau_l1}；当前变量对防御等级切换无直接影响`

### FigX.5 — 模型——模型应力检验（JSD）

**Else**
`severity: success`  
`FigX.5: 滚动三角 JSD 均值 未超过 τ={jsd_stress_dyn_thr}；当前变量对防御等级切换无直接影响`

### FigX.6 — 模型应力——市场载荷方向检验与预警

**Else**
`severity: success`
`FigX.6: 语义–数值滚动余弦未出现负值；当前变量对防御等级切换无直接影响`

---

## Level 1 — 防御等级切换至 Level 1（warn）

### FigX.1 — 测试窗 S_t 语义路径

**If** `c > τ_l1` 且 `s_min < τ_s_low`
**Then**
`severity: warn`
`FigX.1: min(S_t)={st_min} < τ_S_low={tau_s_low}，且可信度 c={credibility} > τ_L1={tau_l1} → 防御等级切换至 Level 1`

### FigX.2 — 结构熵

**If** `h_struct < τ_h1`
**Then**
`severity: warn`
`FigX.2: {figx2_trigger_line} → 防御等级切换至 Level 1`

### FigX.3 — 资产异常诊断（ADF + 高波动 + 低 AC1）

**If** `adf_fail_assets` 非空 或 `vol_assets` 非空 或 `ac1_assets` 非空
**Then**
`severity: warn`
`FigX.3: 资产诊断发现异常（见清单）→ 防御等级切换至 Level 1`

> 注：运行时由代码动态拼接 per-asset 明细，格式含
> ADF：`{symbol} ADF 检验未通过（摘要）`；
> 波动：`{symbol} 年化波动 {value} 高于阈值 {tau_vol_melt}`；
> AC1：`{symbol} 一阶自相关系数 {value} 低于阈值 {tau_return_ac1}`

### FigX.4 — 可信度评分

**Else If** `τ_l2 < c ≤ τ_l1`  
**Then**  
`severity: warn`  
`FigX.4: τ_L2 < c={credibility} ≤ τ_L1={tau_l1} → 防御等级切换至 Level 1`

---

## Level 2 — 防御等级切换至 Level 2（danger）

### FigX.4 — 可信度评分

**If** `c ≤ τ_l2`
**Then**
`severity: danger`
`FigX.4: 可信度 c={credibility} ≤ τ_L2={tau_l2} → 模型一致性崩溃，防御等级切换至 Level 2`

### FigX.5 — 模型——模型应力检验与预警

**If** `jsd_stress == 是`
**Then**
`severity: danger`
`FigX.5: 于{jsd_alarm_date}，滚动三角JSD均值={jsd_mean_at_breach}第一次超过τ={jsd_stress_dyn_thr}→{jsd_alarm_date}为首次预警日，防御等级切换至 Level 2`

### FigX.6 — 模型应力——市场载荷方向检验与预警

**If** `logic_break_cos == 是`  
**Then**  
`severity: danger`  
`FigX.6: 于{cos_alarm_date}，语义–数值滚动余弦={cos_at_breach}第一次出现负值→{cos_alarm_date}为首次预警日，防御等级切换至 Level 2`