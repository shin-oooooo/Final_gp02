# Sidebar-Left · 子标题 + 小标题（合并层级）

> 左栏参数区所有**分组子标题**（原 `sidebar_left_titles.md`）与**小标题 / 辅助标签**
> （原 `sidebar_left_labels.md`）已合并至本文件，按 `子标题 → 小标题` 两级层级组织。
>
> - **键（左侧 `key:`）保持扁平、英文、蛇形命名**；解析器按行 key-value 匹配。
> - H2 `## …` 表示**一个分组子标题**，其下紧跟 `*_params: "..."` 是该分组在 UI 上显示的主标题。
> - H3 `### 小标题` 列出该分组内每个控件的小标题键；若按 Sidebars.md 规定
> 该分组「无小标题」（仅子标题带问号），本区写 `None` 作为占位（解析器忽略）。
> - H3 `### 辅助标签` 列出该分组使用的色条 / 轴数字 / 按钮文字等非"小标题"型标签。
>
> 系统通过 `get_sidebar_left_title(key)` / `get_sidebar_left_label(key)` 读取本文件；
> 两函数签名与返回值未变，仅内部把源文件指向 `sidebar_left.md`，旧的
> `sidebar_left_titles.json` / `sidebar_left_labels.json` 仍作为 fallback。

---

## 防御等级参数

defense_params: "防御等级参数"

### 小标题

help_tau_l2_l1: "τ_L2 / τ_L1 可信度阈值"
help_tau_h1: "τ_H1 结构熵阈值"
help_tau_vol: "τ_vol 年化波动阈值"
help_tau_ac1: "τ_AC1 一阶自相关系数阈值"

### 辅助标签（色条分区）

tau_rgy_l2: "L2"
tau_rgy_l1: "L1"
tau_rgy_l0: "L0"
tau_h1_left_lbl: "L1"
tau_h1_right_lbl: "L0"
tau_vol_left_lbl: "L0"
tau_vol_right_lbl: "L1"
tau_ac1_left_lbl: "L1"
tau_ac1_right_lbl: "L0"

---

## JSD应力参数

jsd_stress_params: "JSD应力参数"

### 小标题

help_k_jsd: "k_jsd 基线放大倍数"
help_eps: "ε 基线基准值"

---

## 可信度参数

credibility_params: "可信度参数"

### 小标题

help_alpha: "α 基准项系数"  
help_beta: "β 惩罚项系数"  
help_gamma_cap: "γ 惩罚上限"

cred_min: "可信度输出下界"  
cred_max: "可信度输出上界"

---

## 影子测试（择模）参数

shadow_params: "影子测试（择模）参数"

### 小标题

help_shadow_alpha_mse: "α 为 MSE 权重，1−α 为 JSD 权重"  
help_shadow_holdout: "Holdout 时间窗长度"

---

## 模型生成预测结果参数

model_predict_params: "模型生成预测结果参数"

### 小标题

help_oos_steps: "OOS 模型参数更新次数"

---

## Level 1 负面语义惩罚放大倍数λ

lambda_params: "Level 1 负面语义惩罚放大倍数λ"

### 小标题

None

---

## 双轨蒙特卡洛参数

mc_params: "双轨蒙特卡洛参数"

### 小标题

help_scenario_step: "自测试集起点，「黑天鹅事件」注入的第（）个交易日"
help_scenario_impact: "「黑天鹅事件」冲击幅度（对数收益率）。"

---

## 模型—市场载荷方向检验参数

load_test_params: "模型—市场载荷方向背离检验参数"

### 小标题

help_semantic_cos_window: "W 计算滚动窗口长度"

---

## 预警成功验证参数

verify_params: "预警成功验证参数"

### 小标题

verify_train_window: "训练窗（天；用于尾部池化与滚动基线）"
verify_crash_q: "大跌分位（%；从高到低排序）"
verify_std_q: "Std 分位（%）"
verify_tail_q: "厚尾分位（%）"

---

## 模型更新时间参数

model_update_params: "模型更新时间参数"

### 辅助标签

# 注：data_max_age / auto_refresh / refresh_now 随 R1.10 移除，控件与文案不再
# 在左栏渲染；保留键以便旧 snapshot / 外部文案索引不报 KeyError。
data_max_age: "（已移除）数据刷新门槛 · R1.10 后仅走缺失兜底"
auto_refresh: "（已移除）启动自动下载 · R1.10 后常驻关闭"
refresh_now: "（已移除）立即刷新 · R1.10 后由缺失兜底代替"
refresh_now_icon: "fa-cloud-arrow-down"

---

## 面板外（跨区域共享）

### 辅助标签

defense_intro_card_title: "防御策略介绍"