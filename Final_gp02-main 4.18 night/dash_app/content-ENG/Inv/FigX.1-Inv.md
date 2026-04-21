## What this figure shows

Scalar **S** is the aggregate market sentiment score; series **S_t** is daily sentiment over time. Values nearer **1** are more bullish; nearer **−1**, more bearish.

## Data strategy

To mitigate limited headline coverage on some dates, the pipeline:

**News ingestion**: Prefer English finance headlines over the test window from RSS / Geo / NewsAPI; if the NewsAPI key is missing, fall back to RSS / Geo only—**S_t** still generates, with sources noted in logs.

## Scalar S

**S**: Cross-window aggregate. All headline VADER scores plus keyword risk penalties (`penalty`) and symbol-aware bumps (`severity_boost`) map into a composite score on **[−1, 1].**

## Series S_t

**S_t**: Daily sentiment. Calendar segments by headline dates; each segment’s mean VADER decays exponentially from prior segments so sparse-news days keep directional momentum instead of collapsing to zero or blunt forward-fill.

## Impact on defense

When defense rises to Level 1, the objective adds a semantic penalty—lower **S_t** raises the penalty and pushes weights away from negatively toned names.

## Impact on dual-track Monte Carlo

Lower **S_t** increases jump intensity and jump size on the pressure track.
