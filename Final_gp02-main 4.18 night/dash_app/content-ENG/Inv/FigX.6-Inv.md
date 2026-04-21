## Load vs. semantic–numeric divergence

In physics, **load** is the external force that deforms a body and builds stress. In quant finance, load is live market sentiment; under violent swings, large external load warps model geometry. When load points opposite to model-implied stress, **market logic breaks structurally.**

## Champion models and the expectation series

Each symbol has a best (“champion”) model. We equally average their predicted return expectations over symbols to form a mean-expectation time series.

Champions anchor the best internal **stress** forecast; sentiment is the true external **load**. Opposing directions (cosine < 0) imply structural failure.

## Rolling cosine and failure day

At time **t**, slide a length-**w** window; take **w** points of mean expected return vs. sentiment and compute cosine similarity. The **first** time cosine drops below **0**, semantic and numeric trends diverge—we take that as the onset of logical failure, analogous to model–model stress logic and reasonable for this study design.
