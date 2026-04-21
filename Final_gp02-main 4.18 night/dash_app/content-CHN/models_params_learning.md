# 模型参数学习：方法论与简要过程

本文说明本项目中**多模型 + 样本外（OOS）相关参数如何产生与使用；以文字与公式为主，并附源码索引**（`.py`，行号范围；行号会随版本漂移，请以 `grep`/IDE 为准）。

---

## 1. 总览：参数从哪来？

与「多模型 + 样本外」直接相关的**可调政策参数**集中在 `DefensePolicyConfig`，定义见 `**research/schemas.py`** 中 `DefensePolicyConfig` 类（自文件开头约 **第 13** 行起）。与本文最相关的字段包括：

- `**oos_fit_steps`**：测试窗内稀疏重拟合步数；
- `**shadow_holdout_days**`：训练窗内影子 holdout 长度（**仅训练标签**，默认 40，范围 5–120）；
- `**alpha_model_select`**：影子择模时 MSE vs JSD 的权衡 \alpha；
- `**semantic_cosine_window` / `k_jsd` / `jsd_baseline_eps**`：JSD 应力与训练基线（滚动窗 W 与 FigX.6 语义–数值余弦共用，默认 5 日；原 `n_jsd` 已合并）。

管线将训练/测试窗、收益表、`close`、策略对象交给 Phase2，入口见 `**research/pipeline.py**` 中 `run_phase2` 调用（约 **534–540** 行）。

侧栏将 `**oos_fit_steps`**、`**shadow_holdout_days**`、`**alpha_model_select**` 等写入策略的逻辑见 `**dash_app/app.py**` 中 `_run_all_inner` 构造 `DefensePolicyConfig`（约 **3720–3770** 行一带）。

---

## 2. 严格样本外：信息集 I_{t-1}

Phase2 的约定是：**在测试日 t 上预测当日收益 r_t，只能用 t 之前的信息集 I_{t-1}**（`run_phase2` 文档字符串约 **520–524** 行）。

实现上，对每个测试日 t 与标的 `sym`，收益历史为：


\text{hist} =  r_\tau : \tau < t .


对应代码：`**research/phase2.py`** 中 `hist = returns.loc[returns.index < t, sym].dropna()`（约 **603** 行）。

含义：按日历**滚动**截断，避免用未来数据拟合（与「整段估一次再假装 OOS」不同）。

---

## 3. 各模型在 I_{t-1} 上的 (\hat\mu,\hat\sigma)

四套路（Naive / ARIMA / LightGBM / Kronos 或统计代理）由 `**_mus_sigs_for_series`** 汇总：`**research/phase2.py**` 约 **171–194** 行。


| 组件       | 含义                                                                                                                                                                                                                        | 源码                               |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| Naive    | 上一期收益作下一期均值预测                                                                                                                                                                                                             | 约 **101–102** 行（`_naive_mu`）     |
| ARIMA    | 在 `hist` 上拟合 ARIMA(1,0,1)，取 1 步预测与残差波动                                                                                                                                                                                    | 约 **105–121** 行（`_arima_mu`）     |
| LightGBM | 用 x_t=r_t 预测 y_t=r_{t+1}，在末点 x 上出 \hat\mu，残差标准差作 \hat\sigma                                                                                                                                                               | 约 **124–144** 行（`_lgb_mu_sigma`） |
| Kronos   | **未** 传入 `kronos_mu_override` 时：用 `**_kronos_mu_sigma`**（约 **147–152** 行）长窗统计 \mu,\sigma 作高斯层；测试主环在传入 `close` 且权重就绪时，用 `**kronos_one_step_mu_from_close`** 覆盖 Kronos 的 \mu（约 **611–627** 行）；实现见 `**kronos_predictor.py`** |                                  |


**尺度 \sigma**：优先 `Phase2Input.validation_residuals_std[sym]`；否则用 `**_validation_sigma`**（约 **155–161** 行），并在 `**_mus_sigs_for_series`** 中取 `max(..., 1e-8)`。

高斯负对数似然（与 `**_gaussian_nll**` 一致，约 **326–329** 行）：


\mathrm{NLL}(y;\mu,\sigma)=\tfrac12\Big(\ln(2\pi\sigma^2)+\big(\tfrac{y-\mu}{\sigma}\big)^2\Big).


**Kronos 契约摘要**（详见根目录 `**Models_constraints.md`**）：

- 权重就绪时：`kronos_one_step_mu_from_close` **必须**成功推理或抛错，**不**再对失败静默回退历史均值；
- 权重未就绪时：仍可对 `len(c_hist)≥30` 调用该函数，内部走 **均值回退**；
- **训练窗滚动 JSD 基线**（约 **745–757** 行）为节省算力，对 Kronos 仍用 `**_kronos_mu_sigma`**，不调 Transformer。

---

## 4. OOS 计算预算：`oos_fit_steps`（重点）

测试窗长度为 T 时，若每个 t 都重拟合 ARIMA/LGBM，成本大致随 T 增长。项目用 `**oos_fit_steps`（记为 K）** 控制：

- 在 0,\ldots,T-1 上**均匀**取至多 K 个下标，在这些日子**重新**算各模型 (\hat\mu,\hat\sigma)；
- **其余测试日**不重新拟合，而是把上一档的 (\hat\mu,\hat\sigma) **前向填充**（forward-pad）。

政策字段：`DefensePolicyConfig.oos_fit_steps`（`**research/schemas.py`**）。  
选取重算下标：`**research/phase2.py**` 约 **582–589** 行（`np.linspace` + `set`）。  
重算 vs 填充：约 **601–637** 行。

**通俗理解**：

- K=T：测试窗内每日刷新（最细、最慢）；
- K=1：近似「测试窗内一套参数走到底」（最快、最粗）；
- 中间值：在**信息集仍严格为 I_{t-1}** 的前提下，用**稀疏 refit**换速度。

---

## 5. 样本外概率层：NLL、DM、覆盖率

在逐日 \mu_{m,t},\sigma_{m,t} 与实现 y_t=r_t 上，对 Naive 与三结构模型做高斯 NLL 与检验，主逻辑在 `**_probabilistic_oos_bundle`**：`**research/phase2.py**` 约 **353** 行起；于 `**run_phase2`** 约 **857–866** 行调用并写入 `prob_*` 与 `model_traffic_light`。

名义 95% 高斯带（代码用 1.96\sigma）见该 bundle 内实现。

DM 型统计：`**_dm_hac_t_pvalue`**：约 **332–350** 行（对差分序列做 HAC 方差，再算 t 与双侧 p）。

---

## 6. 影子选模（训练窗尾部）：`alpha_model_select` 与 `shadow_holdout_days`

每标的「更信哪一模型」来自 **训练窗末尾** 一段 holdout（**从不使用测试窗标签**）：`**_tail_holdout_scores`**，`**research/phase2.py**` 约 **223** 行起；由 `**run_phase2`** 约 **891–913** 行按策略 `**shadow_holdout_days`** 与每标的可用长度计算 `n_tail_eff` 后调用。

综合分数（`_tail_holdout_scores` 内）：


\text{Score}*m=\alpha\cdot \frac{\mathrm{MSE}m}{\max{m'}\mathrm{MSE}*{m'}}+(1-\alpha)\cdot\frac{\mathrm{JSD}*m}{\max*{m'}\mathrm{JSD}_{m'}},


\alpha= `**policy.alpha_model_select*`*。  
每标的取 \arg\min_m \text{Score}_m：见 `**run_phase2**` 中 `best_model_per_symbol` 更新逻辑（约 **904–915** 行一带）。

**Kronos 与影子**：权重与分词器就绪且传入 `close` 时，影子中 Kronos 的 MSE 由 `**kronos_one_step_mu_from_close`** 逐步计算；否则 Kronos 槽位用 **5 日滚动均值代理**（`_tail_holdout_scores` 内分支）。

---

## 7. 测试窗 JSD 与「应力」基线

- 有测试日时：逐日三边 JSD 的截面均值，再对测试窗平均：`**research/phase2.py`** 主循环内三角块（约 **638–675** 行一带）。  
- 训练窗上估计「正常分歧」基线 `**jsd_baseline_mean`**：约 **745–760** 行（窗口 `**policy.semantic_cosine_window`**，默认 5 日；与 FigX.6 语义–数值滚动余弦共用同一窗口。该环对 Kronos 用 `**_mus_sigs_for_series` 统计层**，见第 3 节）。  
- 应力是否触发：`**_jsd_stress_rolling_breach`**：约 **75–99** 行定义，**762–769** 行调用（与 `**policy.k_jsd`** 联动）。

---

## 8. 一句话串起来

- **真 OOS 底线**：预测 r_t 只用 `**returns.index < t`**（约 **603** 行）。  
- **算得动的旋钮**：`**oos_fit_steps`**（稀疏 refit）+ `**shadow_holdout_days**`（影子尾长，仅训练内）+ 侧栏其它策略字段。  
- **概率结论**：用 OOS 序列做 NLL / DM / 覆盖率（`**_probabilistic_oos_bundle`**）。  
- **谁当「主模型」展示**：训练尾部影子 + `**alpha_model_select`**；**测试窗**单独承担样本外主叙事。

---

## 9. 关键数据计算示例（与 Fig2.1 §6 对齐）

本文件说明参数与学习流程；**已落地数值实例**（§6.1 前提表、§6.2 全截面择模、§6.3 NVDA、§6.4 影子 MSE）统一维护于 **`Figure2.1-Res.md` §6**，避免与本文件抽象描述分叉。

---

*更完整的模型约束/弱点表见 `**Models_constraints.md`**。若 Phase2 内部逻辑变更，请对照更新本文件行号。*