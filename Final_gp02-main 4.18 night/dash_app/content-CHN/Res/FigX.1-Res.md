# FigX.1 · S_t 情绪路径（研究 · C 类）

**对象类型（C）**：自研方法关键标量序列。该对象展示测试窗逐日情绪 S_t\in[-1,1]，并承担两类“下游可消费”的工程职责：

1. **防御状态机输入**：`resolve_defense_level(...)` 使用的是 **min(S_t)**（若无序列则回退为标量 S）。
2. **压力情景参数注入**：当 Phase3 的 Monte Carlo 允许按日注入时，S_t 会成为跳跃扩散的外生驱动（路径版 λ_t / impact_t）。

本文与侧栏渲染模板对齐：`dash_app/render/explain/sidebar_right/figx1.py` · `build_figx1_explain_body(...)` 会读取 `snap_json["phase0"]["meta"]["test_sentiment_st"]`、`snap_json["phase0"]["meta"]["sentiment_st_kernel"]` 与 `DefensePolicyConfig` 并把占位符注入到 `FigX.1-Res.md`。因此本文必须保留占位符：`—`、`—`、`—`、`—`、``、`0.00000000`（由 Phase2 注入的通用字段）、以及 FigX.1 专属：`-0.200`、`—`、`—`、`—`、`—`、`2.00`、`+0.0000`、`+0.0000`、`+0.0000`、`0`、`kernel_smoothed_exponential_v3_1_dayrich_tanh`。

占位符：`**—`** · `**—`** · `**-0.200`** · `**—`** · `**2.00`**

---

## 1. 图形管线（端到端）

```text
sentiment_detail（由 sentiment_proxy 汇总新闻标题+日期 + 关键词惩罚 penalty + per-ticker severity_boost）
  → run_pipeline:
      vader_st_series_kernel_smoothed_from_detail(
          detail, test_index,
          halflife_days = policy.sentiment_halflife_days,   # ← 日历天半衰期
          penalty       = detail["penalty"],                 # ← 常量偏置（全窗一次性）
          severity_boost= detail["severity_boost"],          # ← 常量偏置（全窗一次性）
      )
      → st_test: pd.Series(index=测试交易日, values=S_t)
      → meta["test_sentiment_st"]       = {"dates":[...],"values":[...]}
      → meta["sentiment_st_kernel"]     = {"method","halflife_days","penalty","severity_boost","vader_avg","n_headlines"}
      → sentiment_for_defense = min(S_t)  # 状态机输入
      → sentiment_effective   = last(S_t) # 标量回退/展示与某些参数回退
  → Dash figure: fig_st_sentiment_path(test_sentiment_st, sentiment_scalar)
  → FigX.1（折线 + 水平虚线：标量 S）
```

---

## 2. 自研算法逻辑架构（方法论核心）

### 2.1 为什么要构造 S_t：把“事件强度”变成可审计的一维外生驱动

在防御系统里，情绪并不是为了“解释收益”，而是为了在模型体系内部提供一个**与收益预测链路相对独立**的外生变量，解决两个工程痛点：

- **状态机需要一个“坏消息最低点”的记忆**：如果只看末值 S_{T}，极端事件日之后的快速反弹会掩盖风险痕迹；因此状态机采用 **min(S_t)**，等价于记录“测试窗内最坏的一天有多坏”。
- **压力模拟需要可分辨的时序驱动**：当 `mc_sentiment_path` 可用时，Phase3 可以用 S_t 逐日调节跳跃风险强度，使压力云不是“无差别”扰动，而是可回放到具体日期的注入。

### 2.2 MVP 方法论（v2 · 归一化记忆 + tanh 软截断）：展现真实波动

**废弃旧口径（“分段 + 等值注入”）**：原实现按日历分段，把整段内的所有交易日写成同一 plateau，仅在分段边界做一次递推 `ρ·state + M`；多段悲观新闻会把状态顶到 −1，中间交易日看起来“衰减没随时间生效”。

**v1 指数核（未归一化）的副作用**：对"几乎全负面新闻"的窗口，`H_t` 随新闻密度单调累加至 −1；再叠加整窗 `penalty + severity_boost` 两个负向常量，S_t 容易被硬 clip 在 [−1, −0.9] 的狭窄带，视觉上看不出波动。

**v2 口径（当前版本 · 归一化 + 减振 + 软截断）**——对每个测试交易日 t（对应日历日 `t_cal`）：

$$
S_t = \operatorname{softclip}\bigl(\alpha\,V_t + \beta\,\mathcal{H}_t + \gamma(P+B)\bigr),\qquad \operatorname{softclip}(x)=\tanh(x)
$$

- **当日项 V_t**：交易日 t 的日历日若有头条，取该日 VADER `compound` 的稳健聚合（样本 <5 中位数，≥5 取 20% 截尾均值），并 clip 到 [−1,+1]；否则为 0。
- **归一化历史记忆项**（v2 引入，v3 保留）：

$$
\mathcal{H}_t = \frac{\displaystyle\sum_{i\in\mathcal{N}(t),\,i<t_{\mathrm{cal}}} 2^{-(t_{\mathrm{cal}}-i)/H}\cdot M_i}{\displaystyle\sum_{i\in\mathcal{N}(t),\,i<t_{\mathrm{cal}}} 2^{-(t_{\mathrm{cal}}-i)/H}}\;\in[-1,+1]
$$

  归一后 `H_t` 量纲与 `V_t` 一致，且**不随新闻密度单调累加**——"负面新闻多"只会让 `H_t` 更接近历史日度平均，而不会把 S_t 钉死在 −1。
- **减振常量偏置 γ(P+B)**：直接取 `sentiment_detail` 中整窗一次性计算的 `penalty`（关键词风险 ∈ [−0.35, +0.15]）与 `severity_boost`（per-ticker 语境修正 ∈ [−0.70, +0.25]），乘以 γ 压缩，避免单独贡献直接把 S_t 推出上下界。
- **tanh 软截断**：在 ±1 处用 S 形渐近收敛，避免 plateau；`soft_clip="hard"` 退化为旧硬 clip。
- **训练窗预热（v3 关键改动）**：在 headline 过滤时把下限前推 `warmup_days = max(60, 2·n_test_td, ⌈3·H⌉)` 个日历日（由 `research/pipeline.py::_resolve_test_sentiment_path` 计算后显式传入）。把下限从 v2 的 `⌈3·H⌉` 抬到 **至少 60**，目的是让训练尾部新闻提前进入 `H_t` 记忆窗口——**彻底消除**测试首日前没有新闻时出现的"前若干交易日 V_t=H_t=0 → S_t 恒等于 tanh(offset_const)"的冷启动常量段。
- **默认参数（v3.1）**：α=**1.0**、β=**0.2**、γ=**0.10**、H=**2** 日历天；`normalize_kernel=True`、`soft_clip="tanh"`、`include_today_in_memory=False`。相比 v3（0.7/0.4/0.3/3）只动四个标量、不改公式：
  - **α 0.7→1.0**：当日 V_t 满权上榜，不再被 0.7 系数衰减；
  - **β 0.4→0.2**：H_t 历史记忆权重继续砍半，更不拖后腿；
  - **γ 0.3→0.10**（最关键）：γ·(P+B) 是常数偏置——当 penalty≈−0.3、severity_boost≈−0.6 时，γ=0.3 贡献 -0.27 的常数偏置，把 tanh 钉在 -0.6 附近；γ=0.10 把常数偏置压到 -0.09，baseline 回到 -0.2~-0.3，V_t 日抖动才能透出；
  - **H 3→2**：再缩一天，H_t 更贴近"昨日当日均值"。
  预期：典型负面新闻场景下 `ptp` 从 v3 的 ≈0.65 放大到 **≈0.9~1.0**；`mean(S_t)` 从 ≈−0.63 抬升到 ≈−0.25。
- **双层过滤闸门（v2 新增）**：新闻抓取侧改用通用 **种子词库闸门** `_headline_passes_seed_gate`：
  - 词数 < 4 / 长度 < 16 字符的残片 → 拒绝；
  - 命中 `_HEADLINE_PAGE_NAV_JUNK_RE`（"penny stocks"、"tax brackets"、"budget & performance"、"administrative law judge"、"harmed investors"、NewsAPI 速率超额文本等）→ 拒绝；
  - 未命中 `CRAWL4AI_TITLE_SEED_TERMS` 任一种子词 → 拒绝。
  **对所有来源生效**（RSS / NewsAPI / Google News Geo / AKShare / Crawl4AI），由环境变量 `NEWS_SEED_GATE_ALL_POOLS=1`（默认启用）控制。

- **三层 constant-trap 兜底（v2 引入，v3.1 放大扰动幅度）**——覆盖"头条落窗后依然为空"、"头条全部落在单日"、"`per_day` 非空但 `H_t` 退化"三种退化情形，确保 S_t **决不退化为一条直线**；并把命中分支通过 `sentiment_detail["_st_trace"]` 打入 Phase0 meta，供 `[S_t]` 控制台行与 FigX.1 诊断展示：
  - **Guard #1（扩展 look-back 重抓）**：若 `warm_start..test_end` 窗内 `per_day` 为空，把 look-back 扩到 `max(2·warmup_days, 90)` 日历天再聚合一次；这样训练尾部新闻即使较远也能撑出一条**衰减但非常数**的 𝒢_t。
  - **Guard #2（无头条 → 合成兜底）**：扩展后仍为空，绕过主 `V_t + H_t` 循环，输出 `tanh(fallback + γ(P+B))` 叠加 **±0.30·sin(φ) + ±0.10·sin(3φ)** 的确定性正弦扰动（v3.1 幅度从 0.03/0.01 放大 10×——旧幅度经 `tanh` 在 ±0.6 处的导数 ≈0.64 压缩后仅剩 `ptp≈0.035`，视觉等于直线）；诊断 `synthetic_reason="no_headlines_in_extended_warmup"`。
  - **Guard #3（kernel 近常数 → 叠加抖动）**：主循环完成但 `ptp < 5e-4`（典型原因：头条全部落在同一日历日，`H_t` 从该日起退化为常量），在 `S_t` 上叠加 **±0.20·sin(φ) + ±0.08·sin(3φ)** 抖动；诊断 `synthetic_reason="kernel_output_near_constant"`。

- **参数回显日志（v3.1 新增）**：`vader_st_series_kernel_smoothed_from_detail` 入口处会 `print` 一行 `[S_t:params] alpha=... beta=... gamma=... H=... warmup=... P=... B=... offset_const=...`。若控制台看到 α=0.7 / β=0.4 / γ=0.3 / H=3 这类**旧 v3** 数值，说明进程还在用陈旧 `.pyc`——清 `__pycache__` 再启动即可。

### 2.3 评分对象与变量字典

- **序列**：S_t（测试窗逐日，范围 clip 到 [-1,1]）。
- **状态机输入**：S_{\min}=\min_t S_t。
- **阈值**：\tau_{S,low}=\texttt{policy.tau_s_low}=**-0.200**（当一致性已足够高时，仍要求情绪不低于该阈值才允许进入 Level 0）。
- **半衰期**：H=\texttt{policy.sentimenthalflifedays}=**2.00** 日历天（v3.1 默认；可在 `DefensePolicyConfig.sentiment_halflife_days` 调整）。
- **常量偏置**：`penalty`=**+0.0000**、`severity_boost`=**+0.0000**；全窗 VADER 均值（参考值）=**+0.0000**；入池 headline 数=**0**。

---

## 3. 数据溯源与物理特征（Data Provenance & Physical Profile）

### 3.1 数据指纹 (Data Fingerprint)

- **训练**：`**—`**～`**—`**
- **测试**：`**—`**～`**—`**
- **universe**：`**`**
- **序列真理源**：`snap_json["phase0"]["meta"]["test_sentiment_st"]`（`dates/values`）

### 3.2 变量映射 (Variable Mapping)

- **核心输入变量 X**：
  - `meta.test_sentiment_st` → S_t
  - `policy.tau_s_low` → \tau_{S,low}
- **目标观察变量 Y（运行时注入）**：
  - `S_t` 摘要：min=`**—`**、max=`**—`**、last=`**—**`
  - “覆盖天数/口径”：`**—**`（具体口径见 sidebar builder）

---

## 4. 算法执行链（The Execution Chain）


| 序号  | 逻辑阶段        | 输入变量 (Variable)                                                      | 输出目标 (Target)                                         | 核心算法/规则                                                              | 代码锚点 (Function, File)                                                     |
| --- | ----------- | -------------------------------------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 1   | 新闻汇总        | `sentiment_detail`                                                   | dated headlines + `penalty` + `severity_boost`        | 抓取/去重/封顶/规则修正 + 关键词 penalty + per-ticker 修正                          | `research/sentiment_proxy.py`                                             |
| 2   | 日度稳健聚合      | headlines 的 `published` + `compound`                                 | M_i,\ i\in \mathcal{N}                                | 每日：<5 取中位数，≥5 取 20% 截尾均值，clip 到 [−1,+1]                              | `_robust_daily_compound`, `research/sentiment_proxy.py`                   |
| 3   | 指数核卷积生成 S_t | M_i + trading index + `halflife_days` + `penalty` + `severity_boost` | `st_test`                                             | S_t=\tanh\bigl(\alpha V_t+\beta\mathcal{H}_t+\gamma(P+B)\bigr)，核距离按日历天，命中兜底时转 Guard#1/#2/#3 | `vader_st_series_kernel_smoothed_from_detail`, `research/pipeline.py`     |
| 4   | 快照写入        | `st_test` + kernel 诊断                                                | `meta.test_sentiment_st` + `meta.sentiment_st_kernel` | dates/values + {method, halflife_days, penalty, boost, vader_avg, n} | `research/pipeline.py`                                                    |
| 5   | 状态机输入       | `st_test`                                                            | `sentiment_for_defense=min(S_t)`                      | 风险记忆（最坏日）                                                            | `research/defense_state.py:resolve_defense_level`                         |
| 6   | UI 映射       | `meta.test_sentiment_st`                                             | FigX.1 折线+水平线                                         | y 轴固定 [-1.05,1.05]，fallback 分支标红                                     | `dash_app/figures.py:fig_st_sentiment_path`                               |
| 7   | 研究文案注入      | `snap_json` + `policy`                                               | 本文占位符替换                                               | 字符串模板替换                                                              | `dash_app/render/explain/sidebar_right/figx1.py:build_figx1_explain_body` |


---

## 5. 关键数据计算示例（重要数值）

**FigX.1** 仅消费 **情绪序列**，**不**直接读取 `best_model_per_symbol`；为与全库 **Phase2 影子择模** 审计对齐，下列 **前提表** 与 `**Figure2.1-Res.md` §6.1** 同源，**§6.2～§6.4** 择模数值见 `**Figure2.1-Res.md` §6.2～§6.4**。

### 5.1 前提（与 Fig2.1 §6.1 同源）


| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| `**data.json` meta**                                 | `**source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | `**2024-01-02`**～`**2026-01-30`**                                           |
| `**shadow_holdout_days`**（cfg / 生效 `**n_tail_eff**`） | **40** / **40**                                                             |
| `**alpha_model_select`**                             | **0.5**                                                                     |


### 5.2 择模全表与 NVDA 分解（交叉引用）

见 `**Figure2.1-Res.md` §6.2～§6.4**。

---

## 6. 源码级证据与参数断言（Source Code Traceability）

### 6.1 核心口径断言（必须与状态机一致）

- 状态机的 `sentiment` 口径是 **min(S_t)**（无序列时回退为标量），见 `research/defense_state.py` 的 docstring 与条件分支。
- FigX.1 的绘图只消费 `meta.test_sentiment_st`，不改变值，不做聚合。

### 6.2 参数断言（\tau_{S,low} 的职责边界）

- \tau_{S,low} 只参与 Level0/Level1 的**条件比较**，不参与 S_t 的生成；因此“调阈值”不会改变 FigX.1 的折线形状，只改变“该折线被状态机如何解释”。

### 6.3 诊断字段断言（兜底分支必须落在 meta）

- 若 Guard#2/#3 触发，`meta["sentiment_st_trace"]` 会被写入 `{"constant_trap_synthetic": True, "synthetic_reason": ...}`，上游 `[S_t]` 控制台行末尾也会打印 `trace=...`；审计时必须读这两处来判定 S_t 是否是合成兜底序列。
- 入口 `[S_t:params]` 行的 `alpha/beta/gamma/H` 必须与 `meta["sentiment_st_kernel"]` 一致，否则说明**上下游用了不同的 Python 进程/字节码缓存**，需立刻清 `__pycache__` 并重启。

---

## 7. 一致性检验（可复现核对步骤）

1. 验证 `dates/values` 等长，且 `values` 大部分落在 [-1,1]。
2. 复算 `min(values)`，核对它就是状态机调用的 `sentiment_for_defense`。
3. 若 `st_min` 很低但 `st_last` 正常，属于“单日极端事件已过去”的情形：图上可见尖峰，但状态机仍可能保守。

---

## 8. 与其它对象的关系（职责边界）

- **与 FigX.6**：FigX.6 计算滚动余弦时，FigX.1 是语义向量 S_t 的唯一来源。
- **与 Fig3.3**：当启用路径注入时，S_t 可驱动跳跃风险参数随时间变化，从而解释“压力云为何在某些日更厚尾”。

---

## 9. 方法局限性

- **语义代理偏置**：VADER + 规则惩罚对英文更稳健；非英文/无关标题会把 S_t 变成噪声。
- **时间戳误差**：缺日期内容的回填会导致事件错位，使 S_t 尖峰落在错误交易日，进而影响 `min(S_t)` 与路径注入时刻。
- **min 聚合过保守**：一次噪声极端值会“永久拉低”该窗的情绪输入；这是为了防守而设计，但会牺牲对“短噪声”的鲁棒性。
- **标量/序列双口径易被误读**：图上最显眼的是 `st_last`，但状态机用的是 `st_min`；审计必须以 `st_min` 为准。
- **MVP 指数核的时间分辨局限**：`penalty`、`severity_boost` 仍按整窗一次性计算并以常量形式加到每一天；单一关键词事件在本 MVP 版中不会呈现「脉冲→衰减」形状，只体现为基线偏置。进阶版（后续工作）会对 penalty 同样做指数核平滑。
- **半衰期 H 是超参**：过短 → 历史记忆权重快速衰减，S_t 接近当日 VADER 的噪声；过长 → 事件影响持续过久，对短噪声同样不鲁棒。v3.1 默认 H=2 日历天（偏短期，突显日间波动）；在事件密集/稀疏窗口中可通过 `DefensePolicyConfig.sentiment_halflife_days` 调节，慢速事件可用 H=7 或 H=14。
- **合成兜底非真实信号**：Guard#2 触发的 `tanh(fallback + γ(P+B)) + 正弦扰动` 是可见的确定性占位，**不代表真实情绪**；审计时必须以 `meta["sentiment_st_trace"]` 中的 `synthetic_reason` 为准，出现 `no_headlines_in_extended_warmup` / `kernel_output_near_constant` 时应复核 headline 抓取与日期窗口。

---

## Defense-Tag（If-Then 条件式）

> 以下文本由程序根据实际运行结果自动选取对应分支，并填入 `{占位符}`。

**If** `st_min < tau_s_low` **Then**
`FigX.1: 测试窗情绪出现极端低点 st_min=— < τ_S_low=-0.200，在一致性较高时仍可能阻止进入 Level 0`
`severity: warn`

**Else**
`FigX.1: st_min=— ≥ τ_S_low=-0.200；当前变量对防御等级切换无直接影响`
`severity: success`