# Figure3.3 · 双轨蒙特卡洛（研究 · B 类）

**对象类型（B）**：数值模型预测输出（风险情景模拟）。该图把 Phase 3 优化后的组合权重 \(w^\*\) 映射为组合层面的 \(\mu_p,\sigma_p\)，再在**同一随机源**下生成两组 Monte Carlo 路径：

- **基准轨（无跳）**：仅几何布朗扩散项（连续小波动）。
- **压力轨（含跳）**：在扩散项基础上叠加“泊松跳跃”（极端事件），且跳跃强度/幅度可由情绪 \(S\)（或 \(S_t\) 路径）注入。

图的核心叙事不是“预测收益”，而是给出 **尾部风险边界**：用“无跳中位轨”与“含跳 5% 分位轨”之间的**风险区**，以及云路径对比，解释 Level 1/2 防御为何必要、以及与 Level 0 反事实的差异。

本文对齐主栏 `dcc.Graph(id="fig-p3-mc")`，由 `dash_app/dashboard_face_render.py` 调用 `dash_app/figures.py:fig_mc_dual_track(..., figure_title="Figure3.3")` 生成；MC 数据来自 `snap_json["phase3"]`。

占位符（可选）：`**0**` · `**{objective_name}**` · `**{mc_horizon_days}**` · `**{jump_lambda}**` · `**{jump_log_impact}**`

---

## 1. 图形管线（端到端）

```text
Phase0/1/2 → 组装 μ、Σ、blocked_symbols、defense_level
  → Phase3: run_phase3(Phase3Input, DefensePolicyConfig, DefenseLevel)
      → 10,000 路径向量化 jump-diffusion MC（同 rng seed=7）
      → 下采样至 ≤200 点用于前端渲染（mc_times / mc_paths_*）
      → 输出代表轨：无跳中位轨 mc_path_median_nojump；含跳 P5 轨 mc_path_jump_p5
      → 输出尾部指标：mc_expected_max_drawdown_pct（代表性 MDD）、mc_mdd_p95（尾部分布 MDD）
  → Dash：fig_mc_dual_track(times, paths_baseline, paths_stress, worst_idx, ...)
  → Figure3.3（两云 + 两代表轨 + 风险区）
```

---

## 2. 数据溯源（Data Provenance）

| 项目 | 说明 |
|---|---|
| **组合权重** | `snap_json["phase3"]["weights"]`（已应用 `blocked_symbols` 清零与归一化）。 |
| **边际 μ、Σ** | `Phase3Input.mu_daily / cov_daily`（由管线从训练窗收益 + Phase2 择模 μ 组装，见 `research/pipeline.py`）。 |
| **跳跃参数（常数版）** | `Phase3Input.jump_p`（年化强度 λ∈[0,1]）、`Phase3Input.jump_impact`（对数跳幅 J∈[-0.3,0.3]）。 |
| **跳跃参数（路径版，可选）** | 若 `Phase3Input.mc_sentiment_path` 长度 ≥ `mc_horizon_days`：每步 λ_t 与 J_t 由 \(S_t\) 经 `sentiment_path_to_jump_schedules` 映射；否则回退为常数 λ、J。 |
| **时间轴** | `phase3.mc_times`（单位：年；步长约 1/252），以及 `phase3.mc_date_labels`（与测试窗交易日对齐的 ISO 日期标签，用于前端 x 轴显示）。 |
| **云路径（下采样）** | `phase3.mc_paths_baseline`、`phase3.mc_paths_stress`：每个是二维数组（行=路径，列=时间点），用于绘制“云”。 |
| **代表轨（下采样）** | `phase3.mc_path_median_nojump`（无跳中位轨）、`phase3.mc_path_jump_p5`（含跳 P5 轨）。 |

---

## 3. 模型与数学对象（实现一致）

### 3.1 组合层面的 \(\mu_p,\sigma_p\)

令权重向量为 \(w\)，边际收益向量为 \(\mu\)，协方差为 \(\Sigma\)，则：

\[
\mu_p = w^\top\mu,\qquad \sigma_p=\sqrt{w^\top\Sigma w}.
\]

实现：`research/phase3.py:_simulate_mc_paths`（`mu_p`/`sig_p`）。

> 工程下界：\(\sigma\) 会被夹紧到 `sig_b = max(sig_p, 0.014)`，避免近零波动导致路径不动（同函数内）。

### 3.2 对数空间 Euler 跳跃扩散（无跳 vs 含跳）

在单步 \(\Delta t = 1/252\) 上：

\[
\Delta\ln S = \mu_p\Delta t + \sigma\sqrt{\Delta t}\,Z + J\cdot \mathbb{I}\{\text{jump}\},
\]

其中 \(Z\sim\mathcal{N}(0,1)\)，跳跃事件为伯努利，步内跳跃概率：

\[
p_{\text{step}} = 1-\exp(-\lambda\Delta t).
\]

- **无跳基准轨**：令 \(\lambda=0,J=0\)。
- **含跳压力轨**：用 \(\lambda,J\)（常数或随 \(S_t\) 变化）生成 jump_inc，并叠加到扩散增量。

实现：`research/phase3.py:jump_diffusion_paths_vectorized` 与 `annual_jump_intensity_to_step_prob`。

---

## 4. 图中元素语义（与前端一致）

| 元素 | 语义（源码口径） |
|---|---|
| **基准云** | `mc_paths_baseline`（抽样 40 条、下采样≤200点）绘制的无跳路径集合。 |
| **压力云** | `mc_paths_stress`（抽样 40 条 + 追加“全 10,000 中最差终值路径”）绘制的含跳路径集合。 |
| **保守轨（无跳中位数）** | `mc_path_median_nojump`：对 10,000 条无跳路径逐时刻取中位数，再下采样。 |
| **压力轨（含跳 P5）** | `mc_path_jump_p5`：在 10,000 条含跳路径中，按终端财富取 5% 分位对应的“代表路径”，再下采样。 |
| **云内最差终值路径** | 全部含跳路径中终端最小的一条，确保尾部极端被可视化（`worst_idx` 指向它）。 |
| **风险区** | “无跳中位轨”与“含跳 P5 轨”之间的填充区域，表示从常态到压力尾部的可解释落差带。 |

---

## 5. 关键派生指标（读图时必须同时报）

- `mc_expected_max_drawdown_pct`：沿 **含跳 P5 代表路径** 的最大回撤（%），作为 UI 注释用的代表性 MDD（`research/phase3.py:_simulate_mc_paths`）。
- `mc_mdd_p95`：在 **全部 10,000 条含跳路径** 上计算 MDD 后取 95 分位（%），代表“路径分布意义下的尾部回撤风险”（同函数）。

二者一个是“单条代表轨的回撤”，一个是“全分布回撤的尾分位”，用途不同，不能混读。

---

## 6. 关键数据计算示例（重要数值 · Phase2 前提栏）

### 6.1 前提（与 Fig2.1 §6.1 同源）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

**择模全表与 NVDA 分解**见 **`Figure2.1-Res.md` §6.2～§6.4**。双轨 MC 使用 Phase3 权重 **w**，与 Fig3.2 同源；**不改变** `best_model_per_symbol`。

---

## 7. 源码锚点（可追溯）

- **Phase3 MC 核心**：`research/phase3.py:_simulate_mc_paths`（10,000 路径、P5 代表轨、MDD 指标）
- **跳跃扩散实现**：`jump_diffusion_paths_vectorized` / `jump_diffusion_paths_vectorized_scheduled`
- **情绪→跳跃参数**：`sentiment_to_jump_params`、`sentiment_path_to_jump_schedules`
- **前端绘图**：`dash_app/figures.py:fig_mc_dual_track`（风险区、云路径、累计收益%映射、日期标签）
- **主栏挂载**：`dash_app/ui/main_p3.py`：`dcc.Graph(id="fig-p3-mc")` + `fig_label="Figure3.3"`
- **Dash 组装**：`dash_app/dashboard_face_render.py` 中调用 `fig_mc_dual_track(..., path_median_nojump, path_jump_p5, ...)`

---

## 8. 一致性检验

1. 读取 `snap_json["phase3"]` 中的 `mc_times / mc_paths_* / mc_path_* / mc_worst_stress_path_index`。
2. 核对维度：
   - `len(mc_times) == len(mc_path_median_nojump) == len(mc_path_jump_p5)`；
   - `mc_paths_baseline` 每行列数与 `mc_times` 一致；`mc_paths_stress` 同。
3. 抽样复跑（同一输入 `Phase3Input`、同 rng seed=7）：
   - 代表轨与 `mc_mdd_p95` 在机器精度容忍下应一致（随机数固定）。

---

## 9. 与 Phase 3 其它对象的关系（简）

- **与 Figure3.2（权重）**：Fig3.2 给出 \(w^\*\) 的横截面；Fig3.3 用同一 \(w^\*\) 把风险“沿时间轴展开”为路径分布与尾部边界。
- **与防御等级**：`defense_level` 与 `objective_name` 决定权重来源（Sharpe / 语义惩罚 / CVaR），从而改变 \(\mu_p,\sigma_p\) 与路径分布形态；跳跃强度/幅度又会随情绪 \(S\) 进一步放大压力尾部。

