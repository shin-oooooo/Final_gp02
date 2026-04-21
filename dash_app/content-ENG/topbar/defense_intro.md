# Defense · strategy overview (top bar, three columns)

> Expanded card in the top-center showing **Level 0 / 1 / 2**.
> Each level has `title`, `pretext`, and `item_N` bullets.
> Add items by incrementing indices, e.g. `level2_item_4: "…"`; delete lines to remove entries.

title: "Defense strategy overview"

level2_title: "Level 2 (circuit) triggers"
level2_pretext: "Enter Level 2 if any condition holds:"
level2_item_1: "Phase 2 credibility too low (consistency ≤ τ_L2)."
level2_item_2: "Semantic–numeric rolling cosine < 0 (forecasts vs. sentiment diverge)."
level2_item_3: "Dynamic JSD stress fires (three-model disagreement exceeds baseline × k)."

level1_title: "Level 1 (alert) triggers"
level1_pretext: "Enter Level 1 if any condition holds:"
level1_item_1: "Phase 1 structural entropy implies weak diversification."
level1_item_2: "Phase 1 flags a “pseudo-stationary” asset (high vol or mean-reverting returns)."
level1_item_3: "Phase 2 credibility is moderately low."
level1_item_4: "Phase 2 credibility is high but minimum sentiment is very low."
level1_item_5: "Phase 2 shows all advanced models worse than the baseline on accuracy."
level1_item_6: "Phase 2 sees excessive disagreement among models at some time."

level0_title: "Level 0 (baseline)"
level0_pretext: "Stay here when no Level 1 trigger applies; objectives default to conventional Sharpe-style goals."
