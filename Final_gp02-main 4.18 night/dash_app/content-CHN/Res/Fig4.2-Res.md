# Figure4.2 · 防御策略有效性检验（研究 · C 类）

**对象类型（C）**：自研方法"防御策略有效性检验"。Figure 4.2 在同一测试窗收益矩阵上，对比**三种固定权重规则**的已实现累计收益与最大回撤（MDD），以判定 Adaptive Optimizer 是否达成"**以可接受的收益让步换取显著的尾部风险压缩**"之设计目标。

- **蓝线**：Level 0 · Max-Sharpe 基准权重（`test_equity_max_sharpe`，`color=#42a5f5`）
- **灰虚线**：自定义权重（来自 Phase 0 饼图；`test_equity_custom_weights`，`color=#78909c`）
- **红线**：Adaptive Optimizer 输出的熔断型 CVaR 权重（Level 1/2 实际使用；`test_equity_cvar`，`color=#ef5350`）

> **记号约定（本文档统一口径）**：
>
> - "**回撤率最高**" 指三条曲线中 `**|test_mdd_pct_*|` 绝对值最小**（= 最大回撤绝对幅度最小 = 回撤控制最优）。
> - "**累计收益率最高**" 指三条曲线中 `**test_terminal_cumret_`* 数值最大**。
> - 该口径下 "回撤率最高 + 累计收益率最高" 即"既控回撤又保收益"，与 Adaptive Optimizer 设计目标一致。

本文与侧栏渲染模板对齐：`dash_app/render/explain/main_p4/fig42.py` · `build_fig42_body(...)` 会注入占位符：`{term_ms}` / `{term_cw}` / `{term_cv}`（累计收益）、`{term_mdd_ms}` / `{term_mdd_cw}` / `{term_mdd_cv}`（MDD%）、`{mc_content}`（蒙卡反事实段落）、`{mc_pass}` / `{mc_mdd_pass}` / `{defense_pass}`（布尔判定）。

占位符：`**{defense_pass}`** · `**{mc_pass}`** · `**{mc_mdd_pass}`**

---

## 1. 图形管线（端到端）

```text
Phase3 · 优化求解（按 defense_level 切换目标函数）：
  - Level 0  → Max-Sharpe（w_level0）
  - Level 1  → Max-Sharpe + λ·负面语义惩罚（w_level1）
  - Level 2  → Min CVaR（w_level2 = w_cvar）
  ⇒ 实际持仓权重 w_actual = w_levelN（N = defense_level）

Phase3 · 测试窗已实现路径（同一 test_returns_daily 矩阵 × 三组权重）：
  - w_max_sharpe    → test_equity_max_sharpe / test_terminal_cumret_max_sharpe / test_mdd_pct_max_sharpe
  - w_custom(=pie)  → test_equity_custom_weights / ...
  - w_cvar          → test_equity_cvar / ...

Dash 绘图：
  - fig_p3_triple_test_equity(dates, y_ms, y_cu, y_cv, tpl)
  - build_fig42_body(ui_mode, snap_json, dv) 注入说明文本
```

---

## 2. 自研算法逻辑架构（方法论核心）

### 2.1 为什么用"同一收益矩阵 × 三套权重"而非"同一策略 × 不同市场"

Adaptive Optimizer 的有效性必须在**固定环境**下与**其它合理基准**比较。Figure 4.2 通过三权重共用 `test_returns_daily`，消除"市场择时"差异，使回撤/收益差距**仅来自权重选择**，这是对"策略构建是否成功"的**因果归因**。

### 2.2 为何取 Max-Sharpe 与自定义权重为基准

- **Max-Sharpe（蓝线）**：经典无防御基准，代表"完全信任历史 μ/Σ 估计"的最优风险调整收益；用于度量 Adaptive Optimizer 相对"无脑夏普化"的改进/让步。
- **自定义权重（灰虚线）**：反映投资者先验（等权或饼图手工）；用于检验 Adaptive Optimizer 相对"朴素先验"的改进。
- 三者在**同一样本外路径**上比较，等价于条件独立的"三被试实验"。

### 2.3 成功判定的双层验证

- **第一层 · 已实现检验（Figure 4.2 主图）**：比较三条曲线的 MDD% 与终端累计收益。
- **第二层 · 反事实检验（`{mc_content}` 段）**：蒙特卡洛在相同随机种子 + 相同跳跃/注入参数下，比较"实际权重"与"反事实 Level 0 权重"的**含跳 5% 分位终端财富** `{mc_pass}` 与 **MDD 95% 分位** `{mc_mdd_pass}`。
- **整体判定**：`defense_pass = mc_pass AND mc_mdd_pass = {defense_pass}`。

> **备注**：当 `defense_level = 0` 时，`comparison_active = False`，蒙卡两轨一致，反事实段退化为"无额外尾部对照"，判定转由第一层（三条曲线的结构关系）完成。

---

## 3. 数据溯源与变量映射（Data Provenance）

### 3.1 三条曲线的共源矩阵

三条曲线都用同一个 `test_returns_daily[T×N]`（`phase3.defense_validation` 写入前的原始矩阵），仅权重向量不同；因此**日度收益差 = 权重差的线性组合**。

### 3.2 运行时注入字段（核心摘要）


| 变量                      | 注入值                                                                 |
| ----------------------- | ------------------------------------------------------------------- |
| 三条累计收益终端                | Max-Sharpe `{term_ms}` 自定义 `{term_cw}` 熔断型 CVaR `{term_cv}`         |
| 三条 MDD%                 | Max-Sharpe `{term_mdd_ms}` 自定义 `{term_mdd_cw}` CVaR `{term_mdd_cv}` |
| MC 含跳 5% 分位（是否 ≥ 反事实）   | `**{mc_pass}`**                                                     |
| MC MDD 95% 分位（是否 ≤ 反事实） | `**{mc_mdd_pass}`**                                                 |
| 综合防御判定（AND）             | `**{defense_pass}`**                                                |


### 3.3 关键字段与代码锚点


| 快照字段                                                        | 产生点                                                                | 说明                 |
| ----------------------------------------------------------- | ------------------------------------------------------------------ | ------------------ |
| `test_equity_max_sharpe/custom_weights/cvar`                | `research/phase3.py :: run_phase3 _realized_equity_series_and_mdd` | 三条累计收益路径           |
| `test_terminal_cumret_`* / `test_mdd_pct_*`                 | 同上                                                                 | 终端与 MDD 标量         |
| `resolved_custom_weights`                                   | 同上                                                                 | 饼图权重拦截后归一的实际持仓     |
| `actual_stress_p5_terminal` / `baseline_stress_p5_terminal` | `_simulate_mc_paths`                                               | MC 含跳 5% 分位（双轨）    |
| `actual_mdd_p95_pct` / `baseline_mdd_p95_pct`               | 同上                                                                 | MC MDD 95% 分位（双轨）  |
| `comparison_active`                                         | `run_phase3` 按 `defense_level` 设定                                  | `True` ⇔ Level 1/2 |


---

## 4. 算法执行链（The Execution Chain）


| 序号  | 逻辑阶段             | 输入                                                   | 输出                                                        | 规则                                                   | 代码锚点                                                 |
| --- | ---------------- | ---------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| 1   | 防御等级决策           | `resolve_defense_level(state)`                       | `defense_level ∈ {0,1,2}`                                 | τ_L1/τ_L2、jsd_stress、logic_break、pseudo_melt 等触发条件   | `research/defense_state.py :: resolve_defense_level` |
| 2   | 权重求解             | μ, Σ, defense_level                                  | `w_max_sharpe / w_cvar`                                   | Level 0=max Sharpe；Level 2=min CVaR；Level 1 加 λ·语义惩罚 | `research/phase3.py :: run_phase3`                   |
| 3   | 已实现净值            | `test_returns_daily × w`                             | `test_equity_* / test_terminal_cumret_* / test_mdd_pct_*` | 简单复利；MDD = (peak−trough)/peak                        | `_realized_equity_series_and_mdd`                    |
| 4   | MC 反事实（若 active） | `inp.mc_sentiment_path / jump_p / jump_impact / rng` | `actual/baseline_stress_p5_terminal`、`*_mdd_p95_pct`      | 相同 rng 下并行流仿真，比较含跳 5% 分位与 MDD 95% 分位                 | `_simulate_mc_paths`                                 |
| 5   | 子图输出             | 三条曲线 + MC 摘要                                         | Fig4.2                                                    | 图内仅展示已实现曲线；MC 段进入 `{mc_content}` 文本                  | `dash_app/figures.py :: fig_p3_triple_test_equity`   |


---

## 5. 图形叠加层元素语义（必须与最新实现一致）

- **蓝线（`#42a5f5`，width=2.2）**：`Level 0 · Max-Sharpe`。
- **灰虚线（`#78909c`，dash="dot"，width=2）**：`自定义权重（饼图）`。
- **红线（`#ef5350`，width=2.2）**：`熔断权重（Level 2 · CVaR）`，即 Adaptive Optimizer 的实际输出。
- **"蓝线与红线重合"**：当 `defense_level = 0` 时，`w_cvar ≡ w_max_sharpe`，故 `test_equity_cvar ≡ test_equity_max_sharpe`。此时红线完全盖在蓝线上（肉眼不可分），图中以"单条叠合线 + 灰虚线"的两条线形式呈现。

---

## 6. 关键数据计算示例（重要数值）

**Phase2 影子择模** 全库前提与 `**Figure2.1-Res.md` §6** 同源。`w_cvar` / `w_custom` 的规模与 Phase 1 的 `blocked_symbols` 过滤、Phase 0 的饼图拦截一致（两者都在 `run_phase3` 内被归一化再进入 `_realized_equity_series_and_mdd`）。

### 6.1 与 Fig4.1 的读法边界

Fig4.2 的三条曲线只反映**权重与已实现收益矩阵之积**；**不**再重算预警（`t_ref/t_alarm` / 提前量），预警判定只以 `**Figure4.1-Res.md`** 为准。若 Fig4.1 判定"预警失败"，则 Fig4.2 的"防御成功"只能归因为 **结构性保守性** 而非 **事前识别**，两者须同批阅读。

### 6.2 示例三值推演（便于核算）

假设当期 `{term_ms}` = 1.0320、`{term_cw}` = 1.0180、`{term_cv}` = 1.0285；`{term_mdd_ms}` = 8.60%、`{term_mdd_cw}` = 7.90%、`{term_mdd_cv}` = 5.20%。则：

- MDD 排名（`|%|` 最小 → 最大）：CVaR (5.20%) < Custom (7.90%) < Max-Sharpe (8.60%)；**CVaR 回撤率最高** ✓
- 累计收益排名：Max-Sharpe (1.0320) > CVaR (1.0285) > Custom (1.0180)；**CVaR 非最高**
- ⇒ **情形 D**（策略构建成功；以 0.35 pp 的收益让步换取 3.4 pp 的 MDD 压缩）。

---

## 7. 一致性检验（可复现核对步骤）

1. 核对 `len(test_equity_max_sharpe) == len(test_equity_custom_weights) == len(test_equity_cvar) == len(shadow_index_labels)`。
2. 核对 `test_terminal_cumret`_* 与各曲线末端 `-1` 点之差 ≤ 数值误差（≤ 1e-12）。
3. 若 `defense_level = 0`，核对 `test_equity_cvar - test_equity_max_sharpe` 逐点差 ≤ 数值误差（应严格重合）；否则落入情形 B（异常）。
4. 核对 `comparison_active == (defense_level >= 1)`。
5. 若 `comparison_active = True`，核对 `actual_stress_p5_terminal / baseline_stress_p5_terminal / actual_mdd_p95_pct / baseline_mdd_p95_pct` 非空；否则反事实段退化，结论应以第一层为准。

---

## 8. 与其它对象的关系（职责边界）

- **与 Fig 4.1 （预警有效性）**：Fig 4.2 只对"已发生的防御动作"进行事后检验；预警是否"提前"由 Fig 4.1 决定。两者时序上**串联但正交**：Fig 4.1 验证 **timing**，Fig 4.2 验证 **realized stress reduction**。
- **与 Phase 3 权重求解**：Fig 4.2 完全依赖 `run_phase3` 写入的 `test_equity`_* / `test_terminal_cumret`_* / `test_mdd_pct_`*，自身**不重算**权重或收益曲线。
- **与 Phase 1/2 拦截（`blocked_symbols`）**：Fig 4.2 的 `test_returns_daily` 已在 Phase 3 入参阶段按拦截规则剔除对应列；若出现"单资产主导"的异常曲线，应首先检查拦截是否失效。

---

## 9. 结论分析

> 五类情形判定逻辑、E 情形归因、方法局限性、综合研判等说明文案已统一迁移至
> ``content-CHN/p4_conclusion_analysis.md``（Fig 4.1 / Fig 4.2 共用源，按
> ``## Fig4.2 · 情形 X`` 命名空间索引）。前端 Fig 4.2 下方的"结论分析独立卡片"
> 由 ``build_fig42_conclusion_card`` 从该共用源按当期情形实时切片并注入占位符；
> 若需离线查阅完整 5 情形叙述，请参见上述文档。