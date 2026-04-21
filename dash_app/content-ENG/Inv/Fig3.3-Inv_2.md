### Figure 3.2 · Dual-track Monte Carlo

A stress-testing model that combines a “normal baseline track” with a “pressure track” that embeds jump risk. Each path is generated with jump diffusion (log-space Euler discretization):

---

#### 1. Classical Monte Carlo (normal volatility term)

Prices are assumed to follow geometric Brownian motion—a smooth continuous process capturing routine, small random moves. GBM is determined by portfolio daily return, portfolio daily volatility, and time.

---

#### 2. Jump term

Models extreme events (e.g., policy shocks, earnings surprises). Such moves are discrete and large, making the return path “jump.”

1. **Jump intensity λ**: Expected jumps per year. Larger λ means a less stable environment and higher odds of “black swan” events.
2. **Jump size J**: When a jump hits at time t, price jumps to J times its previous level; J is often modeled as lognormal.
3. **λ and J are driven in real time by sentiment score S.**
4. **Jump probability P**: Poisson with parameter λ × t; larger λ or t raises P.

---

#### 3. Baseline vs. pressure tracks

- **Baseline track (no jump)**: Jump term off; pure Gaussian random walk.
- **Pressure track (with jump)**: Each step may trigger a log jump with probability P; jump parameters are injected from sentiment S.

---

#### Chart elements

| Element | Meaning |
|:---|:---|
| **Baseline cloud** (40 sampled baseline paths) | The “probability fan” of normal volatility—paths without extreme events. |
| **Stress cloud** (40 sampled pressure paths) | Distribution after a geopolitical shock—shifted down with higher dispersion. |
| **Conservative track** (stepwise median of 10,000 no-jump paths) | The most likely baseline scenario—expected return under normal conditions. |
| **Pressure track** (single path at the 5th percentile among 10,000 pressure paths) | At each time in the stress environment, sort 10,000 paths by return and take the path through the ~95th percentile point. “Worst reasonable scenario”—with 95% probability, losses stay above this red line. |
| **Worst terminal-value path inside cloud** (lowest terminal among 40 sampled pressure paths) | Worst realized path in the visible sample—helps judge whether tail risk is underestimated. |
| **Risk zone** | Region between the no-jump median track and the P5 pressure track. |

---

##### Flowchart

```
  μ_p = w* @ μ   (portfolio daily return)
  σ_p = √(w*@Σ@w*) (portfolio daily volatility)
        │
       ▼
  Jump-diffusion Monte Carlo (10,000 paths)
  → baseline track (no jump)
  → pressure track (with jump; jump params from sentiment S)
```

---
