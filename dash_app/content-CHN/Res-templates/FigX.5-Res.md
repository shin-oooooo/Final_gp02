# FigX.5 · 模型—模型应力检验（JSD 时序）（研究 · C 类）

**对象类型（C）**：自研方法关键标量序列。该对象把测试窗中三结构模型（ARIMA / LightGBM / Kronos）的"预测分布分歧"压缩为逐日 JSD（三角均值）序列，并用训练窗滚动基线构造动态阈值，得到 `jsd_stress`（是否触发）与展示阈值 `jsd_stress_dyn_thr`。

它回答的问题是：

> **模型集是否仍在"同一个概率世界"里说话？**  
> 若模型之间的概率密度分歧持续增大到超过训练期正常波动范围，则认为进入"模型—模型应力"状态，可触发 Level 2（熔断）。

本文与侧栏渲染模板对齐：`dash_app/render/explain/sidebar_right/figx5.py` · `build_figx5_explain_body(...)` 会注入占位符：  
`{jsd_kronos_arima_mean}`、`{jsd_kronos_gbm_mean}`、`{jsd_gbm_arima_mean}`、`{jsd_triangle_mean}`、`{jsd_triangle_max}`、`{jsd_baseline_mean}`、`{cos_w}`、`{k_jsd}`、`{jsd_baseline_eps}`、`{jsd_stress_dyn_thr}`、`{test_daily_tri_len}`、`{test_daily_tri_tail_csv}`，以及通用字段 `{train_start}`、`{train_end}`、`{test_start}`、`{test_end}`、`{p0_symbols_csv}`、`{credibility}`、`{jsd_stress}`（来自快照 phase2）。

> **窗口口径统一**：从本版起，JSD 应力的滚动窗口 **W** 与 FigX.6 语义–数值滚动余弦共用同一策略参数 `DefensePolicyConfig.semantic_cosine_window`（侧栏「W 计算滚动窗口长度」，默认 **5 日**），并同时决定「训练滚动基线窗」与「测试窗告警滚动窗」。图上白实线 **滚动三角均值（W={cos_w}，告警口径）** 即红色首次越线竖线的真正触发序列；原先独立的 `n_jsd` 参数已废弃。

占位符：`**{jsd_triangle_mean}**` · `**{jsd_stress_dyn_thr}**` · `**{jsd_stress}**`

---

## 1. 图形管线（端到端）

```text
Phase2 strict OOS：对每个测试日 t，仅用 I_{t-1} 拟合各模型的 μ/σ
  → 对每个标的计算三对 JSD（Kronos–ARIMA / Kronos–LGBM / LGBM–ARIMA）
  → 对每一天做截面均值（跨标的平均）：
      daily_tri[t] = mean_s JSD_triangle(s,t)
  → 训练窗滚动基线 jsd_baseline_mean（窗口 W = policy.semantic_cosine_window）
  → 动态阈值 τ = k_jsd × max(jsd_baseline_mean, eps)
  → 应力触发：任一 W 日滚动均值(daily_tri) > τ ⇒ jsd_stress=True
  → Dash：fig_defense_jsd_stress_timeseries（日度三角 + 白色滚动三角均值（W={cos_w}）+ 阈值线 + 首次 breach 竖线）
```

---

## 2. 自研算法逻辑架构（方法论核心）

### 2.1 为什么用 JSD：把"模型分歧"变成可比较的概率距离

不同模型的预测输出最终在 Phase2 被统一成高斯 \(\mathcal{N}(\mu,\sigma^2)\)（逐日、逐资产）。JSD 的好处是：

- **对称**：\(\mathrm{JSD}(P,Q)=\mathrm{JSD}(Q,P)\)，适合做"模型—模型应力"的无方向距离。
- **有界**：不会像 KL 一样在某些配置下爆炸，便于阈值工程化。

### 2.2 为什么用"三角均值"：用三条边概括三结构模型的群体分歧

三结构模型两两构成三条边；用三角均值避免"只看某一对模型"造成的偏置，并且更符合"模型集整体是否一致"的语义。

---

## 3. 数据溯源与物理特征（Data Provenance & Physical Profile）

### 3.1 数据指纹

- 测试日序列：`phase2.test_forecast_dates`
- 日度三角序列：`phase2.test_daily_triangle_jsd_mean`
- 训练基线：`phase2.jsd_baseline_mean`
- 触发标记：`phase2.jsd_stress`

### 3.2 变量映射（运行时注入）

| 变量 | 字段 | 注入值 |
|---|---|---|
| 三角均值（跨日均） | `phase2.jsd_triangle_mean` | `**{jsd_triangle_mean}**` |
| 三边最大均值 | `phase2.jsd_triangle_max` | `**{jsd_triangle_max}**` |
| 动态阈值 | `k_jsd×max(baseline,eps)` | `**{jsd_stress_dyn_thr}**` |
| 是否触发 | `phase2.jsd_stress` | `**{jsd_stress}**` |
| 日度尾段（审计） | `phase2.test_daily_triangle_jsd_mean` | `len={test_daily_tri_len}`，tail=`{test_daily_tri_tail_csv}` |

---

## 4. 算法执行链（The Execution Chain）

| 序号 | 逻辑阶段 | 输入变量 | 输出目标 | 核心算法/规则 | 代码锚点 |
|---|---|---|---|---|---|
| 1 | OOS μ/σ 序列 | `returns`, `test_dates` | `model_mu_test_ts`/`model_sigma_test_ts` | 严格 I\_{t-1} | `research/phase2.py:run_phase2` |
| 2 | 三角 JSD（每日） | per-day μ/σ（跨资产） | `test_daily_triangle_jsd_mean` | 两两 JSD → 三角均值 → 截面均值 | `research/phase2.py:_js_divergence/_triangle_js` |
| 3 | 训练滚动基线 | `train` | `jsd_baseline_mean` | 窗口 `W=policy.semantic_cosine_window` 的滚动三角均值再取均值（默认 5 日） | `research/phase2.py`（baseline 段） |
| 4 | 应力触发 | `daily_tri`, `k_jsd`, `eps` | `jsd_stress` | 任一滚动均值 breach（不足则回退全窗） | `_jsd_stress_rolling_breach`, `research/phase2.py` |
| 5 | 绘图 | `p2` | FigX.5 | 序列+阈值线+首次 breach 竖线 | `dash_app/figures.py:fig_defense_jsd_stress_timeseries` |
| 6 | 文案注入 | `snap_json` + `policy` | 本文占位符替换 | 模板替换 | `dash_app/render/explain/sidebar_right/figx5.py:build_figx5_explain_body` |

---

## 5. 关键数据计算示例（重要数值）

**Phase2 影子择模** 前提与 **`best_model_per_symbol` / NVDA MSE / combined** 全表见 **`Figure2.1-Res.md` §6**；本节仅列与 **FigX.5 应力叙事** 同一快照下的 **§6.1 前提**（与 Fig2.1 §6.1 **同源**）。

### 5.1 前提（与 Fig2.1 §6.1 同源）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

### 5.2 择模全表与 NVDA 分解

见 **`Figure2.1-Res.md` §6.2～§6.4**。**FigX.5** 消费的 **`jsd_triangle_mean` / `jsd_stress`** 由 **`run_phase2`** 写入 **`phase2`**，与像素择模 **共用** 同一快照，但 **应力判定** 不反向修改 **`best_model_per_symbol`**。

---

## 6. 源码锚点（可追溯）

- `research/phase2.py`：`run_phase2`（`daily_tri`、`jsd_baseline_mean`、`jsd_stress`）
- `dash_app/figures.py`：`fig_defense_jsd_stress_timeseries`（阈值线定义与 breach 标注）
- `dash_app/figures.py`：`fig_fig41_jsd_early_warning`（在 FigX.5 基图上叠加 t_ref/t_alarm，见 Fig4.1）

---

## 7. 一致性检验（可复现核对步骤）

1. 核对 `len(test_forecast_dates)` 与 `len(test_daily_triangle_jsd_mean)` 一致或被截断对齐。
2. 手工复算阈值 \(\tau=k\cdot\max(baseline,\varepsilon)\)，与 `{jsd_stress_dyn_thr}` 一致。
3. 复算 breach：若存在任一窗口滚动均值超过阈值，则 `{jsd_stress}` 应为"是"；否则为"否"（样本不足时按回退判定）。

---

## 8. 与其它对象的关系（职责边界）

- **与 FigX.4（可信度）**：二者共享 `jsd_triangle_mean`；FigX.5 强调"是否触发应力"（布尔），FigX.4 将分歧映射为"可信度评分"（连续标量）并叠加覆盖惩罚。
- **与 Fig4.1（预警有效性）**：Fig4.1a 用 FigX.5 的时序作为底图，并叠加 `t_ref/t_alarm` 来检验"提前 1–5 日"是否成立。

---

## 9. 方法局限性

- **高斯化近似**：JSD 在这里是对 \(\mathcal{N}(\mu,\sigma^2)\) 的近似比较；当真实收益/预测分布显著非高斯（厚尾、偏态）时，JSD 只反映"高斯投影"的分歧。
- **截面均值会稀释局部极端**：分歧集中在少数资产/少数日期时，跨资产均值与跨日均值会稀释尖峰；如果要定位根因，应回看 `phase2.jsd_by_symbol` 或逐日三边序列。
- **阈值依赖训练窗稳定性**：`jsd_baseline_mean` 由训练窗滚动估计；若训练窗本身包含结构突变，基线会偏高，导致漏报；若训练窗过平静，基线偏低，导致误报。
- **滚动窗口参数敏感**：`semantic_cosine_window`（W，与 FigX.6 共用）与 `k_jsd` 控制灵敏度；参数过激会使 `jsd_stress` 频繁翻转，影响策略稳定性。短窗（W=5）对首日超线更敏感，但也更容易被单日噪声点亮，请结合图上白色滚动三角均值线一并审阅。

---

## Defense-Tag（If-Then 条件式）

**If** `滚动三角 JSD 应力触发 = {jsd_stress}` **Then**
`FigX.5: 于{jsd_alarm_date}，滚动三角JSD均值={jsd_mean_at_breach}第一次超过τ={jsd_stress_dyn_thr}→{jsd_alarm_date}为首次预警日，防御等级切换至 Level 2`
`severity: danger`

**Else**
`FigX.5: 滚动三角 JSD 未超过 τ={jsd_stress_dyn_thr}；当前变量对防御等级切换无直接影响`
`severity: success`

> 文案以 `content-CHN/defense_reasons.md` 为事实源；如需修改请同步更新总表。
