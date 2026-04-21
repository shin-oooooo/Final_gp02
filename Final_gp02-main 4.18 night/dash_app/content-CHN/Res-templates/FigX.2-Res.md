# FigX.2 · 结构熵（Structural Entropy）（研究 · A 类）

**对象类型（A）**：基础统计与结构图示。本对象把“训练期末窗的收益协方差谱结构”压缩成一个标量 H_{\mathrm{struct}}\in[0,1]，用于刻画**横截面风险是否趋同**（分散化是否正在失效）。该量会被防御状态机 `resolve_defense_level(...)` 直接消费，是 Level 1/2 的重要触发因子之一。

本文件是“研究模式下讲解卡片”的**文字真理源**（以源码为主），与侧栏 FigX.2 的图形展示（rail / gauge）语义一致。

占位符（建议与快照/注入器对齐）：`**{train_start}`** · `**{train_end}`** · `**{entropy_window}**` · `**{h_struct}**` · `**{tau_h1}**` · `**{tau_h_gamma}**` · `**{gamma_multiplier}**`

---

## 1. 图形管线（端到端）

```text
data.json → load_bundle.close_universe
  → daily_returns(close[symbols]) = rets
  → resolve_dynamic_train_test_windows(...) → train_mask
  → Phase1: run_phase1(rets.loc[train_mask], Phase1Input, DefensePolicyConfig, close_train)
      → h_struct（结构熵）
      → gamma_multiplier（γ 倍增：h_struct < τ_h_gamma 时为 3，否则为 1）
  → UI（侧栏 FigX.2 rail / 或主栏 gauge）：展示 h_struct 与阈值 τ_h1
  → Defense state machine：resolve_defense_level(..., h_struct=h_struct, ...)
```

---

## 2. 数据溯源（Data Provenance）


| 项目        | 说明                                                                                               |
| --------- | ------------------------------------------------------------------------------------------------ |
| **收益面板**  | `rets = daily_returns(close[symbols]).dropna(how="all")`（简单日收益）；结构熵使用训练窗 `rets.loc[train_mask]`。 |
| **行完备对齐** | 结构熵计算前使用 `sub = rets.dropna(how="any")`，即**任一标的缺收益则整行剔除**（确保协方差矩阵可计算）。                           |
| **末窗长度**  | `entropy_window`（默认 21），从 `Phase1Input.entropy_window` 读取。                                       |
| **输出字段**  | `snap_json["phase1"]["h_struct"]` 与 `snap_json["phase1"]["gamma_multiplier"]`。                   |


---

## 3. 方法论与数学对象

### 3.1 从协方差谱到“结构熵”

对齐后的末窗收益矩阵记为 R\in\mathbb{R}^{W\times n}（W=\texttt{entropywindow}，n=资产数），协方差矩阵为：

\mathbf{C}=\mathrm{Cov}(R)\in\mathbb{R}^{n\times n}.

对 \mathbf{C} 做特征分解得到特征值 \lambda_1,\ldots,\lambda_n，并做下界保护：

- \lambda_k \leftarrow \max(\lambda_k, \varepsilon)，其中 \varepsilon=10^{-18}；
- p_k = \lambda_k / \sum_j \lambda_j；

定义原始熵与归一化结构熵：

H_{\mathrm{raw}}=-\sum_{k=1}^{n} p_k\ln p_k,\qquad
H_{\mathrm{struct}}=\frac{H_{\mathrm{raw}}}{\ln n}\ (n\ge 2).

**解释**：

- H_{\mathrm{struct}}\to 1：谱更均匀（多因子分散），横截面结构更“丰富”；
- H_{\mathrm{struct}}\to 0：谱更集中（共同因子主导），资产收益更趋同，分散化更脆弱。

实现：`research/phase1.py:structural_entropy`。

### 3.2 样本不足的回退

若 `len(sub) < entropy_window`，Phase1 将 `h_struct` 直接回退为 `1.0`（避免在小样本协方差上误判），见 `research/phase1.py:run_phase1`。

---

## 4. 计算过程链（Calculation Chain）


| 步骤  | 计算对象   | 输入                         | 输出                        | 逻辑 / 函数                                  |
| --- | ------ | -------------------------- | ------------------------- | ---------------------------------------- |
| 1   | 训练窗收益表 | `rets.loc[train_mask]`     | `rets_train`              | `research/pipeline.py`                   |
| 2   | 行完备子表  | `rets_train`               | `sub = dropna(how="any")` | `run_phase1`                             |
| 3   | 末窗切片   | `sub`                      | `tail = sub.iloc[-W:]`    | `run_phase1`                             |
| 4   | 协方差    | `tail`                     | `cov = tail.cov()`        | pandas 默认 ddof=1                         |
| 5   | 结构熵    | `cov`                      | `h_struct`                | `structural_entropy(cov)`                |
| 6   | γ 倍增   | `h_struct` + `tau_h_gamma` | `gamma_multiplier`        | `3.0 if h_struct < tau_h_gamma else 1.0` |


---

## 5. 阈值语义（与防御逻辑对齐）

### 5.1 τ_H1（结构熵主阈值）

`tau_h1` 来自 `DefensePolicyConfig.tau_h1`（侧栏滑条）。当 H_{\mathrm{struct}}<\tau_{H1} 时，通常解释为“横截面结构趋同风险上升”，在 `resolve_defense_level` 中可参与 Level 1 触发（需与其它信号共同裁决）。

### 5.2 τ_Hγ 与 γ 倍增（工程增益）

`tau_h_gamma` 更偏工程：当 H_{\mathrm{struct}}<\tau_{H\gamma} 时，Phase1 输出 `gamma_multiplier=3.0`，用于后续某些惩罚项/阈值联动的“加速”（见 `research/phase1.py`）。

---

## 6. 关键数据计算示例（重要数值）

**FigX.2** 使用 **`phase1.h_struct`**，与 Phase2 择模 **独立**；下列 **§6.1** 仍与全库 **`Figure2.1-Res.md` §6.1** 对齐，便于同一 `data.json` 会话内对照 **影子 holdout 参数是否与管线一致**。择模数值表见 **`Figure2.1-Res.md` §6.2～§6.4**。

### 6.1 前提（与 Fig2.1 §6.1 同源）

| 项目                                                   | 取值                                                                          |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| **`data.json` meta**                                 | **`source`** = `akshare`，`**generated_at`** = `2026-04-16T11:18:47.221640Z` |
| **解析后训练窗（ISO）**                                      | **`2024-01-02`**～`**2026-01-30`**                                           |
| **`shadow_holdout_days`**（cfg / 生效 **`n_tail_eff`**） | **40** / **40**                                                             |
| **`alpha_model_select`**                             | **0.5**                                                                     |

### 6.2 交叉引用

择模 **MSE / combined / 全样本影子 MSE** 见 **`Figure2.1-Res.md` §6.2～§6.4**。

---

## 7. 源码锚点（可追溯）

- **结构熵实现**：`research/phase1.py:structural_entropy`
- **Phase1 输出写入**：`research/phase1.py:run_phase1`（`h_struct`、`gamma_multiplier`）
- **防御状态机消费**：`research/defense_state.py:resolve_defense_level(..., h_struct=...)`
- **管线入口**：`research/pipeline.py:run_pipeline`（构造 `Phase1Input` 并调用 `run_phase1`）
- **UI 展示**：
  - 侧栏 rail：`dash_app/ui/metric_rails.py`（结构熵条形 rail）
  - 主栏 gauge（若启用）：`dash_app/figures.py:fig_entropy_gauge`

---

## 8. 一致性检验

1. 取同一份 `data.json` 与解析后的训练窗起止日，得到 `rets_train = rets.loc[train_mask]`。
2. 复算 `sub = rets_train.dropna(how="any")`，若 `len(sub) ≥ W`：
  - `tail = sub.iloc[-W:]`
  - `cov = tail.cov().to_numpy()`
  - `h' = structural_entropy(cov)`
3. 核对 `h'` 与快照 `snap_json["phase1"]["h_struct"]` 一致（容忍机器精度）。
4. 核对 `gamma_multiplier == (3.0 if h_struct < tau_h_gamma else 1.0)`。

---

## 9. 与其它对象的关系（职责边界）

- **与 Figure0.2（相关性热力图）**：0.2 展示逐对 Pearson 相关；FigX.2 展示“协方差谱的整体集中度”，是更高层的结构压缩指标。
- **与 Phase 3**：当结构熵偏低时，分散化假设更脆弱；此时即使点预测仍可用，优化也可能更偏向鲁棒目标（与其它信号共同决定）。

