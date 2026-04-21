# 模型约束、能力与局限（Models — constraints, strengths, weaknesses）

> 目的：说明本仓库 **Phase 2 多模型轨** 中各预测器如何工作、**在何处被误用会失效**，以及 **Kronos** 与 **影子验证** 的现行契约。阅读时应结合源码，而非仅依赖本文档行号（行号会随提交漂移）。

---

## 1. 共同设定：信息集与「预测对象」

- **样本外（测试窗）**：在测试日 t 上预测当日收益 r_t，仅允许使用 `**returns.index < t`** 的信息（严格 I_{t-1}）。实现主环：`research/phase2.py` 中 `run_phase2` 对 `test_dates` 的循环（约 **595–677** 行一带，`hist = returns.loc[returns.index < t, sym]`）。
- **稀疏重拟合**：`DefensePolicyConfig.oos_fit_steps` 在测试窗内均匀选取若干日重算 (\hat\mu,\hat\sigma)，其余日 **前向填充** 上一档参数，在保持 I_{t-1} 的前提下换算力（`phase2.py` 约 **579–634** 行）。
- **高斯层**：各模型输出标量 \mu 与 \sigma，用于两两 **Jensen–Shannon**、NLL、名义带覆盖率等；这是 **简化假设**，不等价于真实收益分布。

---

## 2. Naive


| 维度     | 内容                                                          |
| ------ | ----------------------------------------------------------- |
| **机制** | 用上一期收益作为下一期均值预测（见 `_naive_mu`，`phase2.py` 约 **101–102** 行）。 |
| **约束** | 对趋势/结构突变不敏感；波动尺度来自验证窗残差启发式，而非模型内生。                          |
| **优势** | 无估计风险、极快、稳定基准；DM/NLL 常以 Naive 为对照。                          |
| **劣势** | 预测经济含义弱；在动量或均值回复 regime 下可系统偏离。                             |


---

## 3. ARIMA(1,0,1)


| 维度     | 内容                                                                         |
| ------ | -------------------------------------------------------------------------- |
| **机制** | 在截断历史 `hist` 上拟合 `ARIMA(1,0,1)`，取一步预测均值与残差波动（`_arima_mu`，约 **105–121** 行）。 |
| **约束** | 短历史或病态序列时回退到 Naive 式均值/波动；`statsmodels` 收敛失败走异常分支。                         |
| **优势** | 经典、可解释；中等长度历史上常作「参数化时间序列」对照。                                               |
| **劣势** | 线性高斯假设；对杠杆、跳变、日内结构无显式建模；OOS 上阶固定不随体制切换。                                    |


---

## 4. LightGBM（单特征回归）


| 维度     | 内容                                                                                                                           |
| ------ | ---------------------------------------------------------------------------------------------------------------------------- |
| **机制** | 特征 x_t=r_t，目标 y_t=r_{t+1}，在 `hist` 上拟合 `LGBMRegressor`，在末点 x 上预测 \hat\mu，残差标准差作 \hat\sigma（`_lgb_mu_sigma`，约 **124–144** 行）。 |
| **约束** | 样本过少或拟合失败时回退 Naive；超参固定（非 AutoML）。                                                                                           |
| **优势** | 可捕捉非线性边际；计算快于深度序列模型。                                                                                                         |
| **劣势** | 单滞后特征信息集极窄；**无**显式不确定性的概率校准；极端行情外推风险。                                                                                        |


---

## 5. Kronos（时序 Transformer 一步收益）

### 5.1 何时启用「真推理」

- `**kronos_parameters_available()`**（`kronos_predictor.py`）：`kronos_model` 可导入 且 模型/分词器目录内存在 `**.safetensors`**（路径受 `KRONOS_WEIGHTS_DIR` 等环境变量约束）。
- **已就绪时**：`run_phase2` **必须**传入与收益对齐的 `**close`**，且每个标的列齐全；否则在入口 `**ValueError`**（`phase2.py` 约 **537–548** 行）。
- **一步预测**：`kronos_one_step_mu_from_close` 由收盘价构造 OHLCV（`prepare_ohlcv_from_close`），再调用 `KronosPredictor.predict` 得到下一交易日收盘，换算为简单收益 \mu（`kronos_predictor.py`；失败在权重就绪时 `**raise`**，**不再**静默回退历史均值）。
- **未就绪时**：同一函数返回 **历史收益均值** 且 `success=False`；Phase2 测试环在 `len(c_hist)≥30` 时仍会调用该路径，此时 Kronos 轨实为 **统计回退**（`phase2.py` 约 **623–627** 行分支）。

### 5.2 与「统计 Kronos 层」的区别

- `**_kronos_mu_sigma`**（约 **147–152** 行）：在 **未** 传入 `kronos_mu_override` 时，用最近约 120 日收益的 **均值/标准差** 作为 Kronos 高斯层的 (\mu,\sigma)，用于 **训练窗滚动 JSD 基线** 等（约 **745–757** 行 `_mus_sigs_for_series(ss, sig_v)` **无** `close`）。这是 **算力与可复现性** 的折中：**基线应力标定**不调用 Transformer。
- **影子 holdout 中 Kronos 的 MSE**：当权重就绪时，对训练尾每一天用 `**kronos_one_step_mu_from_close`** 在截至该日的收盘价序列上推理（`_tail_holdout_scores`，约 **223** 行起；由 `run_phase2` 传入 `close_sym`，约 **891–913** 行）。权重未就绪时仍用 **5 日滚动均值代理** 填 Kronos 槽位，以免择模完全缺项。

### 5.3 能力边界与弱点


| 维度       | 内容                                                                                                  |
| -------- | --------------------------------------------------------------------------------------------------- |
| **优势**   | 在大上下文 K 线上可做 **零样本式** 一步外推；与 ARIMA/LGBM 并列时丰富 **分歧几何**（JSD）。                                        |
| **约束**   | 至少 **30** 个有效收盘日；OHLCV 由收盘价 **合成**，非真实盘口；`pred_len=1` 的短视设定。                                        |
| **劣势**   | 权重/显存/依赖失败即中断（就绪模式下）；对 **合成 OHLCV** 敏感；与 VADER 情绪等 **无** 原生联合建模。                                    |
| **可重复性** | `prepare_ohlcv_from_close` 中成交量部分含 **伪随机** 成分（无真实量时），跨进程固定种子若未设则可能微差——结论性论文若要求比特级复现，需固定随机种子或改为常数体积。 |


---

## 6. 影子验证（仅训练窗；不调测试窗）


| 维度           | 内容                                                                                                                                                                                                 |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **目的**       | 在 **训练集末尾** 留出一段伪样本外，比较 Naive / ARIMA / LightGBM / Kronos 的一步误差与 JSD 到经验分布，按 `**alpha_model_select`** 加权得综合分，选 `**best_model_per_symbol`**（`_tail_holdout_scores` + `run_phase2` 约 **891–913** 行）。 |
| **长度**       | `**DefensePolicyConfig.shadow_holdout_days`**（默认 40，侧栏 **5–120**；`research/schemas.py` 策略定义）。每标的实际 `n_tail_eff = min(配置, max(5, n_train−30))` 以满足 `_tail_holdout_scores` 最少历史要求。                   |
| **严谨性**      | 影子 **只消费训练窗标签**；**不得**把影子 holdout 挪到测试窗上做择模再回头解释同一测试窗——否则信息泄漏。                                                                                                                                     |
| **与 OOS 分工** | **测试窗**承担「正式样本外预测 + JSD/可信度/概率检验」叙事；**影子**只解决「训练内择模 + 像素矩阵着色叙事」；算力紧张时应 **缩短 `shadow_holdout_days` 或减小 `oos_fit_steps`**，而不是默认取消测试窗。                                                                |


---

## 7. 与防御等级、FigX 系列的耦合（只列要点）

- **Level 2** 条件之一含 `**jsd_stress`**：滚动三角 JSD 与训练基线 `**k_jsd`** 比较（`phase2.py` `_jsd_stress_rolling_breach` 约 **75–99** 行；基线滚动约 **745–760** 行）。
- **语义–数值余弦**：用测试窗上 **影子最优模型** 的 OOS \mu 截面均值与 S_t 做滚动 Pearson 余弦（约 **964–987** 行）；与 EWMA 展示标量不同路径，见 `FigX.5研究.md`。
- **可信度 `credibility_score`** 与 UI 中 `**consistency_score**` 数值同源（约 **886–889** 行一带 clip 后赋值）。

---

## 8. 源码索引（维护时优先 grep）


| 主题                                             | 主文件                                                                                                                    |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 策略字段（含 `shadow_holdout_days`, `oos_fit_steps`） | `research/schemas.py` — `DefensePolicyConfig`                                                                          |
| Phase2 主逻辑                                     | `research/phase2.py` — `run_phase2`, `_tail_holdout_scores`, `_mus_sigs_for_series`, `_probabilistic_oos_bundle`       |
| Kronos 权重检测与一步推理                               | `kronos_predictor.py` — `kronos_parameters_available`, `kronos_one_step_mu_from_close`, `load_kronos_predictor_cached` |
| 管线调用 Phase2                                    | `research/pipeline.py` — `run_pipeline` 内 `run_phase2(..., close=close, ...)`                                          |
| 侧栏写入策略                                         | `dash_app/app.py` — `_run_all_inner` 构造 `DefensePolicyConfig`（约 **3745–3770** 行一带）                                     |


---

*若实现变更，请同步更新本文件与 `模型参数学习.md`、各 `FigX.*研究.md` 中的行号或段落说明。*
