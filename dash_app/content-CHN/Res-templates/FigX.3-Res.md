# FigX.3 · 资产异常诊断（ADF / 波动 / AC1）（研究 · C 类）

**对象类型（C）**：自研方法“资产级证据集合”。FigX.3 的任务不是输出一个新的数值模型，而是把 Phase1 的逐资产诊断与阈值体系组织成可审计的证据，回答：

- 哪些资产在训练窗里就**不满足平稳性前提**（ADF 管线未过关）？
- 哪些资产存在**高波动**或**低 AC1** 这类“可能导致模型失真/权重不稳”的工程风险？

这些证据被状态机/策略用于 Level 1 的“资产级理由”，并在 Phase3 中可能进入 `blocked_symbols`（清零再归一化）。

本文与侧栏渲染模板对齐：`dash_app/render/explain/sidebar_right/figx3.py` · `build_figx3_explain_body(...)` 会注入占位符：`{h_struct_short}`、`{tau_h1}`、`{tau_vol_melt}`、`{tau_return_ac1}`，以及展开块 `{adf_fail_assets_md}` / `{vol_assets_md}` / `{ac1_assets_md}`。

占位符：`**{h_struct_short}**` · `**{tau_vol_melt}**` · `**{tau_return_ac1}**`

---

## 1. 图形管线（端到端）

```text
close_universe → daily_returns → returns
  → Phase1: run_phase1(...)
      → diagnostics[*]: ADF / 差分阶 / Ljung–Box / vol_ann / ac1 / basic_logic_failure / stationary_returns ...
  → Dash（侧栏研究块）：
      → diagnostic_failed_adf(d) 形成 ADF 失败列表
      → vol_ann > tau_vol_melt 形成高波动列表
      → ac1 < tau_return_ac1 形成低 AC1 列表
  → FigX.3：三张清单 + “综合判定”说明
```

---

## 2. 自研算法逻辑架构（方法论核心）

### 2.1 为什么要做“资产级证据集合”：状态机需要“可解释的微观理由”

仅依赖结构熵、JSD 或可信度等“宏观标量”会有一个工程缺口：当系统进入 Level 1 时，用户会追问“到底哪几个资产导致风险上升”。FigX.3 补足这一层解释，使防御等级变化可以追溯到：

- **统计前提失败**（ADF 未过关：模型在该资产上没有可靠前提）
- **风险形态异常**（高波动：权重/方差估计不稳定；低 AC1：收益结构更接近噪声或强均值回复，容易破坏线性假设）

### 2.2 三类证据的工程语义

- **ADF 未过关**：代表“训练窗收益不满足平稳性/逻辑闭环”，进入 Phase3 时更倾向被降权或剔除。
- **高波动**：代表“误差放大器”。在同样的模型分歧下，高波动资产更容易让组合尾部风险变厚。
- **低 AC1**：代表“短期结构不稳定/反转”。如果模型隐含趋势或惯性假设，AC1 过低会导致预测与现实方向错配。

---

## 3. 数据溯源与物理特征（Data Provenance & Physical Profile）

### 3.1 数据指纹

- 诊断来自：`snap_json["phase1"]["diagnostics"]`（逐资产 dict 列表）
- 阈值来自：`DefensePolicyConfig`（侧栏参数）
- 上下文标量：结构熵 `**{h_struct_short}**` 与阈值 `τ_h1=**{tau_h1}**`（用于说明“宏观环境是否已经偏向 Level1”）

### 3.2 变量映射

- **输入 X**：
  - `diagnostics[*].stationary_returns/basic_logic_failure/vol_ann/ac1`
  - `policy.tau_vol_melt={tau_vol_melt}`
  - `policy.tau_return_ac1={tau_return_ac1}`
- **输出 Y（侧栏展开块）**：
  - `{adf_fail_assets_md}`：ADF 未过关资产清单
  - `{vol_assets_md}`：高波动资产清单
  - `{ac1_assets_md}`：低 AC1 资产清单

---

## 4. 算法执行链（The Execution Chain）

| 序号 | 逻辑阶段 | 输入变量 | 输出目标 | 核心规则 | 代码锚点 |
| --- | --- | --- | --- | --- | --- |
| 1 | 对数收益与检验 | 训练窗 close/returns | per-asset diagnostics | ADF 差分管线 + Ljung–Box 等 | `research/phase1.py:run_phase1` |
| 2 | ADF 失败口径 | `diagnostics[*]` | ADF fail list | `not (stationary_returns and not basic_logic_failure)` | `research/defense_state.py:diagnostic_failed_adf` |
| 3 | 高波动口径 | `vol_ann`, `tau_vol_melt` | vol list | `vol_ann > tau_vol_melt` | `dash_app/render/explain/sidebar_right/figx3.py:build_figx3_explain_body` |
| 4 | 低 AC1 口径 | `ac1`, `tau_return_ac1` | ac1 list | `ac1 < tau_return_ac1` | 同上 |

---

## 5. 关键数据计算示例（重要数值 · Phase2 前提栏）

下列 **§5.1** 与 **`Figure2.1-Res.md` §6.1** 同源，便于与 **影子择模** 同一快照对齐；**§6.2～§6.4** 择模全表见 **`Figure2.1-Res.md` §6.2～§6.4**。随后 **§5.2～§5.4** 仍为 **FigX.3 运行时注入清单**（与上文不混读）。

### 5.1 前提（与 Fig2.1 §6.1 同源）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

### 5.2 择模全表与 NVDA 分解（交叉引用）

见 **`Figure2.1-Res.md` §6.2～§6.4**。

---

## 6. 关键数据计算示例（运行时注入 · FigX.3 清单）

### 6.1 未通过 ADF 检验的资产（训练窗）

{adf_fail_assets_md}

---

### 6.2 高波动资产（年化波动 > τ_vol_melt）

阈值：`τ_vol_melt = {tau_vol_melt}`

{vol_assets_md}

---

### 6.3 低自相关资产（AC1 < τ_return_ac1）

阈值：`τ_return_ac1 = {tau_return_ac1}`

{ac1_assets_md}

---

## 7. 源码锚点（可追溯）

- `research/phase1.py`：生成 `diagnostics`（`vol_ann`、`ac1`、`basic_logic_failure`、`stationary_returns`）
- `research/defense_state.py`：`diagnostic_failed_adf`（ADF 失败的统一口径）
- `dash_app/sidebar_figx_md.py`：`build_figx3_explain_body`（清单生成与占位符注入）

---

## 8. 一致性检验（可复现核对步骤）

1. 用相同训练窗数据运行 Phase1，核对 `diagnostics` 字段齐全且数值可解析。
2. 用 `diagnostic_failed_adf` 口径复算 ADF 失败资产清单，应与 `{adf_fail_assets_md}` 一致。
3. 用阈值复算高波动/低 AC1 清单，应与 `{vol_assets_md}`/`{ac1_assets_md}` 一致。

---

## 9. 与其它对象的关系（职责边界）

- **与 FigX.2（结构熵）**：结构熵提供“系统级环境”，FigX.3 提供“资产级根因”。当结构熵低且 ADF 失败资产多时，Level1 的解释最强。
- **与 Phase3 blocked_symbols**：ADF 失败与“逻辑闭环失败”会导致某些资产权重被清零再归一化；FigX.3 是该行为的证据来源。

---

## 10. 方法局限性

- **多重检验与阈值敏感**：ADF/LB/AC1 在多资产上同时使用时存在多重比较问题；本系统用的是工程阈值而非统计显著性校正，解释应以“风险提示”而非“严格统计结论”为主。
- **训练窗依赖**：所有诊断都只看训练窗；若训练窗结构与测试窗截然不同，诊断可能滞后或失真。
- **AC1 的非因果性**：低 AC1 只是一种形态指标，不等价于“必然失效”；它更像“模型假设可能被破坏”的先验风险。
- **年化波动的频率假设**：`vol_ann` 以 252 交易日年化，假设日频收益近似同分布；在波动聚集强的市场里，这个缩放只是近似。

---

## Defense-Tag（If-Then 条件式）

**If** `存在 ADF 未过关 或 高波动 或 低 AC1` **Then**
`FigX.3: 资产诊断发现异常（见清单）→作为 Level 1 的资产级理由来源`
`severity: warn`

**Else**
`FigX.3: 资产级诊断未发现显著异常；当前变量对防御等级切换无直接影响`
`severity: success`

> 文案以 `content-CHN/defense_reasons.md` 为事实源；如需修改请同步更新总表。