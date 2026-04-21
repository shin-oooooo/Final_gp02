# FigX.6 · 语义–数值滚动余弦（研究 · C 类）

**对象类型（C）**：自研方法关键标量序列。该对象把测试窗内的语义路径 S_t 与数值侧“影子最优”预测均值序列 \bar{\mu}^{}_t 做滚动余弦相似度，回答一个工程问题：

> **语义叙事（新闻情绪）与数值叙事（影子最优预测均值）是否出现“方向性对立”？**

当滚动余弦出现负值时，系统把它视作“语义–数值逻辑断裂”，并可直接触发 Level 2（熔断）。

本文与侧栏渲染模板对齐：`dash_app/render/explain/sidebar_right/figx6.py` · `build_figx6_explain_body(...)` 会注入占位符：`5`、`0.00000000`、`否`、`否`、`0.00000000`、`-0.0800`、`否`、`否`、`—`，以及通用字段 `—`、`—`、`—`、`—`、``、`0.00000000`。

占位符：`**0.00000000`** · `**5**` · `**否**` · `**否**`

---

## 1. 图形管线（端到端）

```text
FigX.1：meta.test_sentiment_st → 对齐得到 S_t
Phase2 strict OOS：逐日 μ_{m,s,t} / σ_{m,s,t}
  → 影子择模 best_model_per_symbol[s]
  → 逐日影子最优截面均值 μ̄*_t = mean_s μ_{best(s),s,t}
  → 滚动余弦（窗口 W=semantic_cosine_window）：
      cos_t = <S_{t-W+1:t}, μ̄*_{t-W+1:t}> / (||·|| ||·||)
  → 任一 cos_t < 0 ⇒ logic_break_semantic_cosine_negative=True
  → Dash：fig_defense_semantic_cosine（显示 S_t、μ̄*_t、cos_t，并标注首次 cos<0）
```

---

## 2. 自研算法逻辑架构（方法论核心）

### 2.1 为什么要用“滚动余弦”：把两条异质序列变成同尺度的“方向一致性”

语义序列 S_t 与数值序列 \bar{\mu}^{}_t 的量纲不同、幅度不同，直接比较大小没有意义。余弦相似度只关心“方向一致性”：

- cos > 0：最近 W 天语义与数值整体同向（好消息伴随正均值/坏消息伴随负均值）。
- cos < 0：最近 W 天语义与数值整体反向（坏消息却被数值侧持续判为正均值，或相反），这被视作“叙事冲突”，需要系统防守。

### 2.2 为什么用“影子最优” \bar{\mu}^{}_t 而不是固定模型

固定选一个模型会把“余弦背离”变成“模型选择偏差”。Phase2 先基于训练尾影子 holdout 为每个资产选择最优模型，再把测试窗逐日的最优 μ 汇总为 \bar{\mu}^{}_t，使数值侧代表“当前最可信的预测叙事集合”。

---

## 3. 数据溯源与物理特征（Data Provenance & Physical Profile）

### 3.1 数据指纹

- 语义：`phase0.meta.test_sentiment_st`（dates/values）
- 数值：`phase2.test_daily_best_model_mu_mean`（长度与 `phase2.test_forecast_dates` 对齐）
- 参数：`policy.semantic_cosine_window = 5`

### 3.2 变量映射（运行时注入）

| 变量         | 字段                                            | 注入值                       |
| ---------- | --------------------------------------------- | ------------------------- |
| 最新余弦       | `phase2.cosine_semantic_numeric`              | `**0.00000000**`            |
| 是否计算成功     | `phase2.semantic_numeric_cosine_computed`     | `**否**`  |
| 逻辑断裂（余弦）   | `phase2.logic_break_semantic_cosine_negative` | `**否**`            |
| 逻辑断裂（总）    | `phase2.logic_break`                          | `**否**` |
| S_t 尾段（审计） | `meta.test_sentiment_st`                      | `—`       |

---

## 4. 算法执行链（The Execution Chain）

| 序号  | 逻辑阶段 | 输入变量                            | 输出目标                    | 核心算法/规则                   | 代码锚点                                               |
| --- | ---- | ------------------------------- | ----------------------- | ------------------------- | -------------------------------------------------- |
| 1   | 语义对齐 | `test_st_series` + `test_dates` | `st_arr`                | reindex + ffill/bfill     | `research/phase2.py`                               |
| 2   | 影子择模 | `train` + `close`               | `best_model_per_symbol` | 影子 holdout 评分（MSE/JSD 组合） | `research/phase2.py:_tail_holdout_scores`          |
| 3   | 数值序列 | `model_mu_test_ts` + best model | `μ̄*_t`                 | 截面均值                      | `research/phase2.py:test_daily_best_model_mu_mean` |
| 4   | 滚动余弦 | `st_arr`, `μ̄*_t`, W            | `roll_cos`              | 余弦相似度                     | `research/pipeline.py:_rolling_cosine_series`      |
| 5   | 触发标记 | `roll_cos`                      | `lb_cos`/`cosine`       | 任一 <0；末端有效值               | `research/phase2.py`                               |
| 6   | 绘图   | `p2/meta`                       | FigX.6                  | 三轨同图 + 首次 breach 竖线       | `dash_app/figures.py:fig_defense_semantic_cosine`  |

---

## 5. 关键数据计算示例（重要数值）

**μ̄*_t** 依赖 **`best_model_per_symbol`**；下列 **§5.1** 与 **`Figure2.1-Res.md` §6.1** 同源，**§6.2～§6.4** 择模全表与 NVDA 分解见 **`Figure2.1-Res.md` §6.2～§6.4**。

### 5.1 前提（与 Fig2.1 §6.1 同源）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

### 5.2 择模全表与 NVDA MSE/combined（交叉引用）

见 **`Figure2.1-Res.md` §6.2～§6.3**。`\bar{\mu}^{}_t` 的构造在代码中 **逐日取 best 模型 μ 再截面均值**，审计时应先核对 **`best_model_per_symbol`** 与 Fig2.1 像素 **一致**，再核对 **`test_daily_best_model_mu_mean`**。

---

## 6. 与其它对象的关系（职责边界）

- **与 FigX.1**：FigX.1 给出 S_t；FigX.6 以它为输入之一，否则无法计算余弦。
- **与 FigX.4（可信度）**：可信度是“概率一致性”，余弦是“叙事一致性”。两者都可触发更保守的防御，但含义不同。
- **与 FigX.5（JSD 应力）**：JSD 是“模型—模型分歧”；余弦是“语义—数值冲突”。它们在 Level 2 中是并列硬触发项。

---

## 7. 一致性检验（可复现核对步骤）

1. 核对 `len(test_forecast_dates)` 与 `len(test_daily_best_model_mu_mean)` 一致；不足则 FigX.6 不应绘制。
2. 用同一窗口 W=5 复算滚动余弦序列：
  - `cosine_semantic_numeric` 等于最后一个有效窗口值；
  - 存在任一窗口 < 0 ⇔ `lb_cos` 为“是”。
3. 核对总逻辑断裂：`logic_break_total` 至少应包含 `lb_cos` 与 `logic_break_ac1` 的 OR 关系（Phase2 合并口径）。

---

## 8. 方法局限性

- **余弦只看方向，不看因果**：cos<0 只说明“最近 W 天两条序列方向相反”，不能证明“语义导致数值错”或“数值导致语义错”，属于工程触发信号。
- **窗口敏感**：W 太短会对噪声敏感、频繁穿零；W 太长会延迟告警。该参数需要结合测试窗长度与新闻覆盖密度调整。
- **影子最优引入了非平稳性**：best model 在训练尾选择，但测试窗可能结构突变；此时 \bar{\mu}^{}_t 偏置会导致余弦误报。
- **S_t 时间戳误差会放大背离**：若 S_t 的尖峰错位，会在窗口内引入虚假的方向冲突，从而误触发 lb_cos。

---

## Defense-Tag（If-Then 条件式）

**If** `语义背离触发 = 否` **Then**
`FigX.6: 于{cos_alarm_date}，语义–数值滚动余弦={cos_at_breach}第一次出现负值→{cos_alarm_date}为首次预警日，防御等级切换至 Level 2`
`severity: danger`

**Else**
`FigX.6: 语义–数值滚动余弦未出现负值（最后值=0.00000000）；当前变量对防御等级切换无直接影响`
`severity: success`

> 文案以 `content-CHN/defense_reasons.md` 为事实源；如需修改请同步更新总表。
