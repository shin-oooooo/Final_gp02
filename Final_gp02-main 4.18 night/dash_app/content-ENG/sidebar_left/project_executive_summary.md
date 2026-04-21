## 0. Project overview (Executive Summary)

### 0.1 Background and core questions

#### 0.1.1 Background: why do models fail together?

**Asset dimension:**
Normally assets A and B are low-correlation hedges. In panic, liquidity squeezes make everything fall together.
Optimization built on historical correlations (Markowitz or clustering) loses meaning when the covariance matrix jumps.

**Market dimension:**
Numeric models (Naive / LightGBM / Kronos) are **historical empiricists**: they assume **stationarity**—past
statistics predict the future. External shocks (e.g. April 2026 geopolitical stress) push markets into **non-
stationarity** where moments stop forecasting. Predictive models then enter a shared **logic-break** window.

#### 0.1.2 Research question: how do we detect numeric-model failure—and does defensive policy help?

#### 0.1.3 Approach

Failure is usually preceded by **signal conflict**: disagreement across numeric paradigms, and divergence between
numeric forecasts and live-event semantics.

**Axis A: endogenous disagreement (among numeric models)**

> **Hypothesis**: inter-model disagreement (entropy) correlates with future volatility. Severe “infighting” means
> statistical regularities are fracturing.

When Naive, ARIMA, LightGBM, and Kronos assign very different predictive PDFs (large KL divergence), paradigms no
longer agree on the market.

**Axis B: exogenous divergence (numeric vs. semantics)**

> **Hypothesis**: unstructured news often moves faster than mean-reverting prices.

When numeric models collectively lean bullish yet Crawl4AI sentiment is sharply negative (“sanctions,” “blockade”),
we flag **cross-dimensional logic-break**.

Both imply models **cannot forecast**—“we don’t understand.” The prudent response is admit ignorance and optimize
for survival: objective shifts from **maximize return** to **minimize loss**.

### 0.2 Logical chain: sensing → defense

Instead of chasing a universal model, we build a **self-doubting** defense stack in three stages:

1. **Asset-boundary diagnostics (Phase 1)**: structural entropy tracks correlation collapse across buckets—hedging
   logic fails before naive diversification trust.
2. **Paradigm-conflict monitoring (Phase 2)**: compare Naive / ARIMA / LightGBM / Kronos distributions; when KL
   divergence breaches thresholds **and** Crawl4AI semantics diverge, declare logic-break and trigger red circuit.
3. **Robust defensive response (Phase 3)**: during circuit events the objective switches from expected-return max to
   extreme-loss min; jump-diffusion Monte Carlo incorporates semantic risk into worst-case paths for survivability.
