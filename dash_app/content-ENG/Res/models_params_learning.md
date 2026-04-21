# Model parameter learning: methodology and brief process

This article explains how to generate and use **multi-model + out-of-sample (OOS) related parameters in this project; it is mainly text and formula, and comes with source code index** (`.py`, line number range; line numbers will drift with the version, please refer to `grep`/IDE).

---

## 1. Overview: Where do the parameters come from?

**Adjustable policy parameters** directly related to "multi-model + out-of-sample" are concentrated in `DefensePolicyConfig`, defined in `**research/schemas.py`** in the `DefensePolicyConfig` class (from about **line 13** at the beginning of the file). The fields most relevant to this article include:

- `**oos_fit_steps`**: The number of sparse refitting steps in the test window;
- `**shadow_holdout_days**`: shadow holdout length within the training window (**training labels only**, default 40, range 5–120);
- `**alpha_model_select`**: Trade-off of MSE vs JSD in shadow model selection \alpha;
- `**semantic_cosine_window` / `k_jsd` / `jsd_baseline_eps**`: JSD stress and training baseline (rolling window W is shared with FigX.6 semantic – numerical cosine, default is 5 days; the original `n_jsd` has been merged).

The pipeline hands the training/test window, income table, `close`, and strategy object to Phase2. For the entrance, see the `run_phase2` call in `**research/pipeline.py**` (about **534–540** lines).

For the logic of writing policies such as `**oos_fit_steps`**, `**shadow_holdout_days**`, `**alpha_model_select**` in the sidebar, see the `_run_all_inner` structure of `DefensePolicyConfig` in `**dash_app/app.py**` (about **3720–3770** lines).

---

## 2. Strictly out-of-sample: information set I_{t-1}

The convention of Phase2 is: **To predict the day's return r_t on test day t, only the information set I_{t-1}** before t can be used (`run_phase2` document string is about **520–524** lines).

In implementation, for each test day t and the underlying `sym`, the return history is:


\text{hist} = r_\tau : \tau < t .


Corresponding code: `hist = returns.loc[returns.index < t, sym].dropna()` in `**research/phase2.py`** (about **603** lines).

Meaning: Truncate according to calendar **rolling** to avoid fitting with future data (different from "estimate the entire section and then pretend to be OOS").

---

## 3. (\hat\mu,\hat\sigma) of each model on I_{t-1}

Four routines (Naive/ARIMA/LightGBM/Kronos or statistical proxies) summarized by `**_mus_sigs_for_series`**: `**research/phase2.py**` about **171–194** lines.


| Component | Meaning | Source Code |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Naive | The previous period's return is used to predict the next period's mean value | About **101–102** rows (`_naive_mu`) |
| ARIMA | Fitting ARIMA(1,0,1) on `hist`, taking 1-step forecasts and residual fluctuations | About **105–121** rows (`_arima_mu`) |
| LightGBM | Use x_t=r_t to predict y_t=r_{t+1}, get \hat\mu on the end point
| Kronos | **Not** When `kronos_mu_override` is passed in: use `**_kronos_mu_sigma`** (about **147–152** lines) long window statistics \mu,\sigma as Gaussian layer; when the test main ring is passed in `close` and the weights are ready, use `**kronos_one_step_mu_from_close`** to override Kronos's \mu (about **611–627** lines); see `**kronos_predictor.py`** for implementation | |


**Scale \sigma**: Prefer `Phase2Input.validation_residuals_std[sym]`; otherwise use `**_validation_sigma`** (about **155–161** lines), and take `max(..., 1e-8)` in `**_mus_sigs_for_series`**.

Gaussian negative log-likelihood (identical to `**_gaussian_nll**`, approximately lines **326–329**):


\mathrm{NLL}(y;\mu,\sigma)=\tfrac12\Big(\ln(2\pi\sigma^2)+\big(\tfrac{y-\mu}{\sigma}\big)^2\Big).


**Kronos Contract Summary** (see root directory `**Models_constraints.md`** for details):

- When the weight is ready: `kronos_one_step_mu_from_close` **Must** successfully infer or throw an error, **not** silently fall back to the historical mean on failure;
- When the weight is not ready: this function can still be called for `len(c_hist)≥30`, and **mean rollback** is performed internally;
- **Training window rolling JSD baseline** (about **745–757** lines) In order to save computing power, `**_kronos_mu_sigma`** is still used for Kronos without adjusting Transformer.

---

## 4. OOS calculation budget: `oos_fit_steps` (emphasis)

When the test window length is T, if ARIMA/LGBM is refitted for each t, the cost increases roughly with T. The project is controlled with `**oos_fit_steps` (denoted as K)**:

- Take at most K subscripts **uniformly** over 0,\ldots,T-1, and **recompute" each model (\hat\mu,\hat\sigma) on these days;
- **The rest of the test days** are not refitted, but the previous level (\hat\mu,\hat\sigma) **forward-padded** (forward-pad).

Policy fields: `DefensePolicyConfig.oos_fit_steps` (`**research/schemas.py`**).  
Select the recalculation subscript: `**research/phase2.py**` about **582–589** lines (`np.linspace` + `set`).  
Recalculation vs padding: ~lines 601–637**.

**Popular understanding**:

- K=T: Daily refresh within the test window (the smallest, the slowest);
- K=1: Approximately "the set of parameters in the test window goes to the end" (fastest and roughest);
- Intermediate value: Use **sparse refit** for speed under the premise that the **information set is still strictly I_{t-1}**.

---

## 5. Out-of-sample probability layer: NLL, DM, coverage
On the daily \mu_{m,t},\sigma_{m,t} and implementation y_t=r_t, do Gaussian NLL and test on Naive and three-structure model. The main logic is in `**_probabilistic_oos_bundle`**: `**research/phase2.py**` starts at about **353** lines; in `**run_phase2`** about Lines **857–866** call and write `prob_*` and `model_traffic_light`.

Nominal 95% Gaussian band (coded using 1.96\sigma) is implemented in this bundle.

DM type statistics: `**_dm_hac_t_pvalue`**: about **332–350** lines (do HAC variance on the difference sequence, and then calculate t and two-sided p).

---

## 6. Shadow model selection (tail of training window): `alpha_model_select` and `shadow_holdout_days`

The "Which model to believe more" for each bid comes from a holdout at the end of the training window (**never uses the test window label**): `**_tail_holdout_scores`**, starting from about **223** lines in `**research/phase2.py**`; from `**run_phase2`** to about **891–913** lines calculated by the strategy `**shadow_holdout_days`** and the available length of each bid. Called after `n_tail_eff`.

Comprehensive score (within `_tail_holdout_scores`):


\text{Score}*m=\alpha\cdot \frac{\mathrm{MSE}m}{\max{m'}\mathrm{MSE}*{m'}}+(1-\alph a)\cdot\frac{\mathrm{JSD}*m}{\max*{m'}\mathrm{JSD}_{m'}},


\alpha= `**policy.alpha_model_select*`*.  
Take \arg\min_m \text{Score}_m for each bid: see `best_model_per_symbol` update logic in `**run_phase2**` (about **904–915** lines).

**Kronos and Shadow**: When the weights and tokenizer are ready and `close` is passed in, the MSE of Kronos in the shadow is calculated step by step by `**kronos_one_step_mu_from_close`**; otherwise, the Kronos slot uses the **5-day rolling mean proxy** (branch within `_tail_holdout_scores`).

---

## 7. Test window JSD and "stress" baseline

- When there is a test day: the cross-sectional average of the daily three-sided JSD, and then average the test window: `**research/phase2.py`** The triangle block in the main loop (about **638–675** rows).  
- Estimated "normal divergence" baseline `**jsd_baseline_mean`** over the training window: ~**745–760** rows (window `**policy.semantic_cosine_window`**, default 5 days; shares the same window as FigX.6 semantic – numerical rolling cosine. This ring uses the `**_mus_sigs_for_series` statistical layer** for Kronos, see Section 3).  
- Whether stress is triggered: `**_jsd_stress_rolling_breach`**: About **75–99** lines are defined, **762–769** lines are called (linked with `**policy.k_jsd`**).

---

## 8. String together one sentence

- **True OOS bottom line**: Predict r_t only with `**returns.index < t`** (about **603** lines).  
- **Calculable knobs**: `**oos_fit_steps`** (sparse refit) + `**shadow_holdout_days**` (shadow tail length, only within training) + other strategy fields in the sidebar.  
- **Probabilistic Conclusion**: Do NLL/DM/Coverage with OOS sequences (`**_probabilistic_oos_bundle`**).  
- **Who is the "main model" display**: training tail shadow + `**alpha_model_select`**; **test window** is solely responsible for the out-of-sample main narrative.

---

## 9. Key data calculation example (aligned with Fig2.1 §6)

This document describes the parameters and learning process; **Realized numerical examples** (§6.1 Prerequisite table, §6.2 Full-section model selection, §6.3 NVDA, §6.4 Shadow MSE) are uniformly maintained in **`Figure2.1-Res.md` §6** to avoid bifurcation with the abstract description of this document.

---

*For a more complete table of model constraints/weaknesses see `**Models_constraints.md`**. If the internal logic of Phase2 changes, please update the line numbers of this file accordingly. *