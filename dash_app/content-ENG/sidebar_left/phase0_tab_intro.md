**1. Research prerequisites**

Hedging works in normal regimes. The market is undergoing a **structural break**, not ordinary noise.

**2. Asset universe**

Guided by “hedging works in normal times but may fail in a break,” the pool is split into four observation tiers.
These tiers are **not** preset conclusions—they provide comparable cohorts for Phase 1–3 correlation diagnostics,
paradigm conflict monitoring, and defense switching.


| Category | Tickers | Role in this project |
| -------- | ------- | -------------------- |
| **Core tech (high beta)** | **NVDA, MSFT, TSMC, GOOGL, AAPL** | High-volatility samples to watch correlation convergence and covariance-structure collapse in stress. |
| **Energy (geo-sensitive)** | **XLE (energy ETF) or USO (oil)** | Instruments tied to geopolitical news; tests whether **Crawl4AI** semantics lead numeric models on price shocks. |
| **Safe-haven (low-correlation boundary)** | **GLD (gold), TLT (long bonds)** | Historical low correlation to equities; observe capital migration and rebalancing under CVaR minimization after “red” triggers. |
| **Market benchmark** | **SPY (S&P 500)** | Alpha benchmark and regression anchor for **Dynamic Beta Tracker**. |


**3. Model roster**

We deliberately pick four non-overlapping paradigms so **inter-model disagreement (entropy)** is statistically
comparable. Failure of any single model is not the thesis; **collective impairment** requires irreconcilable JSD
divergence across all four paradigms.


| Model | Paradigm | Strengths | Weaknesses | Role |
| ----- | -------- | --------- | ---------- | ---- |
| **Naive** | Random-walk baseline | No parameters, no overfit, fully reproducible lower bound | Ignores signals—no trends, seasonality, or events | Benchmark; if complex models lose to Naive in a break, their stationarity assumption is falsified. |
| **ARIMA** | Linear time-series stats | Mean-reversion & short inertia; interpretable params/residuals | Needs stationarity; blind to breaks and heavy tails | “Classical statistics” view; residual spikes flag instability early. |
| **LightGBM** | Tree / feature-driven | Nonlinear interactions, fast training, cross-asset features | Still historical mapping—poor extrapolation OOS | “Feature-engineering” view vs ARIMA’s linear lens. |
| **Kronos** | Foundation time-series / deep inference | Pretrained structure, outputs distributions not points | Black box, compute cost, history prior may persist in breaks | “Deep learning” ceiling; if Kronos diverges from all others, trigger logic tripwire. |

