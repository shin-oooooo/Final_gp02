#### Description of method limitations

- **VADER Semantic Accumulation**: Sensitive to non-English news and social media texts, cross-language sentiment mapping may introduce systematic bias.
- **JSD Stress Test**: Assuming that the model output approximately obeys a Gaussian distribution, the actual tail divergence may lead to an optimistic threshold setting.
- **Monte Carlo scenario injection**: step size and shock amplitude are fixed, asymmetric jump and regime-switching situations are not covered.
- **Rolling window estimation**: Structural entropy and cosine similarity are sensitive to the selection of window width, and the convergence speed of statistics decreases under extreme market conditions.

> The above constraints are for reference in result interpretation; subsequent versions can be replaced with template injection mode.

---

## Appendix · Key data calculation example (aligned with Phase2 shadow mode selection)

This article is a method limitation item, **excluding** the numerical table filled in during operation. If you need **shadow holdout premise consistent with **`data.json`** snapshot, full-section `best_model_per_symbol`, NVDA one-step MSE/combined, full-sample shadow MSE**, use **`Figure2.1-Res.md` §6** as the single source of truth (§6.1~§6.4).