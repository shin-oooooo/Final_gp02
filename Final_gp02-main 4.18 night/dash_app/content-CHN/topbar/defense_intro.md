# Defense · 防御策略介绍（顶栏三色横排）

> 展示在顶栏中格展开卡片的 **Level 0 / 1 / 2** 三列介绍。
> 每个 Level 有：`title`（大标题）、`pretext`（导语）、`item_N`（条目 1,2,3…）。
> 新增条目：按序号往后加，例如 `level2_item_4: "…"`；删除则直接删掉那一行。

title: "防御策略介绍"

level2_title: "Level 2（熔断）触发条件"
level2_pretext: "满足任一即进入 Level 2："
level2_item_1: "Phase 2 测得模型可信度过低（一致性 ≤ τ_L2）。"
level2_item_2: "语义–数值滚动余弦 < 0（预测与情绪方向背离）。"
level2_item_3: "JSD 动态应力触发（三模型分歧超过训练基线 × k 倍）。"

level1_title: "Level 1（警戒）触发条件"
level1_pretext: "满足任一则进入 Level 1："
level1_item_1: "Phase 1 检测到资产组合的结构熵偏低，抗风险能力较弱。"
level1_item_2: "Phase 1 检测到某资产为「伪平稳」资产，即资产年化波动率大，或收益率存在均值回归倾向。"
level1_item_3: "Phase 2 测得模型可信度较低。"
level1_item_4: "Phase 2 测得模型可信度高，但最低情绪分过低。"
level1_item_5: "Phase 2 检测到三个进阶模型在预测精确度上不如基线模型。"
level1_item_6: "Phase 2 检测到三个模型在某时间点的分歧过大。"

level0_title: "Level 0（基准）"
level0_pretext: "未满足 Level 1 任一触发条件时维持本等级；优化目标以常规夏普（或等价）为主。"