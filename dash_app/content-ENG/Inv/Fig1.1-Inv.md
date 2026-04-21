### ADF test

The ADF test checks for a unit root to decide whether a series is "stationary."

#### 1. Log transform: stabilize volatility

1. **Reduce heteroskedasticity**: Logs damp explosive variance swings toward a more stable variance.
2. **Linearize**: Turns exponential trends into roughly linear ones for easier modeling.

#### 2. Differencing: remove trend

1. **Remove trend (unit root)**: What ADF cares about most.
2. **First difference**: “Today minus yesterday” gives increments (growth rates); usually removes linear trend.
3. **Second difference**: If the first difference is still non-stationary, difference again to capture “acceleration of growth.”

---

### Ljung–Box test (LB)

LB is the standard way to test for white noise—i.e., no serial correlation.

---

### Interpreting p-values

| Condition | Decision | ADF meaning | LB meaning |
|:---|:---|:---|:---|
| $P > 0.05$ | Fail to reject | Non-stationary with a unit root—risk of "spurious regression." | Series is white noise—no exploitable structure. |
| $P < 0.05$ | Reject | Stationary without a unit root—usable in AR/ARMA models. | Not white noise—serial correlation and hidden structure. |
