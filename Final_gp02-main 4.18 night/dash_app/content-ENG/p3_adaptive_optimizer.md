### Figure 3.1 AdaptiveOptimizer

The optimal weight vector is recorded as $w^{\ast}$ and is solved by AdaptiveOptimizer. The objective function automatically switches with the defense level:

**Goal**:

- **μ_p**: Average daily return of the portfolio
- **σ_p**: Portfolio daily volatility

#### Level 0 — Normal state: Maximize Sharpe ratio
```
minimize −(μ_p − r_f) / σ_p where r_f = 0
Constraints: Σwᵢ = 1, 0 ≤ wᵢ ≤ 1
```Pure mathematical optimality: under given returns and risks, find the weight combination with the highest return per unit risk.

#### Level 1 — Alert state: Sharp + semantic penalty
```
minimize  σ_p  +  λ × Σ(wᵢ × neg_sentiment_i)
```While controlling risks, an "allocation cost" is levied on assets with negative sentiment scores - the worse the sentiment of an asset, the more its weight will be reduced by the optimizer. The λ slider controls the intensity of the penalty.

#### Level 2 — Circuit Breaker: Minimize CVaR (Conditional Value at Risk)
```
R_cond = subset_returns_for_cvar(hist_returns)
minimize CVaR_α(w) = −E[portfolio return | falls at the bottom of the worst α%]
```Completely give up the pursuit of profits and have only one goal: to reduce losses in extreme situations (tail). The historical samples used are also deliberately selected only to historical periods similar to the current market state (high volatility, high correlation), making the CVaR calculation more consistent with actual risks.

##### Flow chart of this stage
```
Daily income data of each asset (training set)
        │
        ▼
μ vector + covariance matrix
        │
       ▼
  AdaptiveOptimizer
  ┌─ Level 0: Max Sharpe → w*
├─ Level 1: Min (σ + λ·Semantic penalty) → w*
└─ Level 2: Min CVaR (conditional sample) → w*
        │
        ▼
μ_p = w* @ μ (portfolio daily return)
σ_p = √(w*@Σ@w*) (daily fluctuation of portfolio)
```---