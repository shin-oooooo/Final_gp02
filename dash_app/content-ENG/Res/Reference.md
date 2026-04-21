# References & Resources

This document summarizes the **models, statistical methods, numerical libraries, engineering tools and external services** involved in this warehouse (AIE1902 Defense Research Dashboard) to facilitate references and traceable sources in papers or reports. Entries are consistent with `requirements.txt`, `README.md` and `research/`, `dash_app/` implementations.

---

## 1. Prediction and machine learning model


| Entries | Role in this project | Papers/Official publications | Code/Models Home |
| ------------ | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LightGBM** | Phase 2 revenue forecast (such as `LGBMRegressor`), compared with ARIMA, Kronos | Ke et al., *LightGBM: A Highly Efficient Gradient Boosting Decision Tree*, NeurIPS 2017. [PDF](https://papers.nips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree.pdf) | [microsoft/LightGBM](https://github.com/microsoft/LightGBM) |
| **Kronos** | K-line time series basic model; Phase 2 one-step forecast (strict inference when weights are ready, see `Models_constraints.md`) and JSD rails | Liu et al., *Kronos: A Foundation Model for the Language of Financial Markets*, arXiv:2508.02739. [arXiv](https://arxiv.org/abs/2508.02739) | [shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos) |
| **ARIMA** | Phase 2 conditional mean (such as ARIMA(1,0,1)), compared with LGBM and Kronos | Box & Jenkins time series analysis framework | Implemented by [statsmodels](https://github.com/statsmodels/statsmodels) |
| **Naive benchmark** | Comparisons other than shadow MSE, partial KL pairs | — | — |


---

## 2. Emotion and natural language processing


| Entry | Role in this project | Thesis | Implementation |
| ---------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **VADER** | News title `compound` points, item expansion vocabulary, `S_t` sentiment sequence (see `research/sentiment_proxy.py`) | Hutto & Gilbert, *VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text*, ICWSM 2014. [ACL Anthology](https://aclanthology.org/W14-2616/) | [cjhutto/vaderSentiment](https://github.com/cjhutto/vaderSentiment) |


---

## 3. Statistical testing, information theory and evaluation indicators


| Method | Description (concept corresponds to implementation) | Reference |
|-------------------------------- |------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **ADF unit root test** | `research/phase1.py` Stationarity diagnosis | Dickey & Fuller (1979/1981); [statsmodels: `adfuller](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html)` |
| **Ljung–Box autocorrelation test** | `research/phase1.py` | Ljung & Box (1978); [statsmodels: `acorr_ljungbox](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html)` |
| **Negative Log Likelihood of Gaussian (NLL)** | Phase 2 Probability Score | Standard Multivariate/Univariate Gaussian Density |
| **Kullback–Leibler divergence (Gaussian closed form)** | Phase 2 internal `_gaussian_kl_forward` | Kullback & Leibler (1951) |
| **Jensen–Shannon divergence** | Phase 2 `_js_divergence`, triangular comparison of model distributions | Lin (1991); see [Endres & Schindelin (2003)](https://arxiv.org/abs/cs/0201011) |
| **Diebold–Mariano class test** | Phase 2 `_dm_hac_t_pvalue` (HAC t / two-sided p) | Diebold & Mariano (1995), *Journal of Business & Economic Statistics*. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0169207000700429) |
| **Prediction interval coverage** | Phase 2 “traffic light” indicators | Probabilistic forecasting and calibration literature (e.g. Gneiting et al.) |


---

## 4. Optimization, risk and stochastic simulation


| Method | Description | References |
| ------------------ | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| **Sequential Quadratic Programming (SLSQP)** | `scipy.optimize.minimize(..., method="SLSQP")` for combining weights | Kraft (1988); [SciPy Documentation](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html) |
| **CVaR (Conditional Value at Risk)** | Phase 3 Defense Level 2 Objectives | Rockafellar & Uryasev (2000) et al |
| **Sharpe Ratio** | Phase 3 Level 0 Goals | Sharpe (1966, 1994) |
| **Jump Diffusion and Monte Carlo Paths** | Phase 3 vectorized paths; emotion-driven jump scheduling | Merton (1976) Jump Diffusion |


---

## 5. Core Python numerical and machine learning library


| Library | Suggested Quotes/Documentation | GitHub |
| ------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **NumPy** | Harris et al. (2020), *Nature*. [DOI](https://doi.org/10.1038/s41586-020-2649-2) | [numpy/numpy](https://github.com/numpy/numpy) |
| **pandas** | McKinney (2010), *SciPy* Conference Paper. [DOI](https://doi.org/10.25080/Majora-92bf1922-00a) | [pandas-dev/pandas](https://github.com/pandas-dev/pandas) |
| **SciPy** | Virtanen et al. (2020), *Nature Methods*. [DOI](https://doi.org/10.1038/s41592-019-0686-2) | [scipy/scipy](https://github.com/scipy/scipy) |
| **statsmodels** | Seabold & Perktold (2010), *SciPy* Conference | [statsmodels/statsmodels](https://github.com/statsmodels/statsmodels) |
| **scikit-learn** | Pedregosa et al. (2011), *JMLR*. [PDF](https://www.jmlr.org/papers/volume12/pedregosa11a/pedregosa11a.pdf) | [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) |
| **PyTorch** | Paszke et al. (2019), NeurIPS | [pytorch/pytorch](https://github.com/pytorch/pytorch) |
| **einops** | Rogozhnikov (2022), arXiv:2112.02662. [arXiv](https://arxiv.org/abs/2112.02662) | [arogozhnikov/einops](https://github.com/arogozhnikov/einops) |
| **safetensors** | Hugging Face tensor safe serialization instructions | [huggingface/safetensors](https://github.com/huggingface/safetensors) |
| **huggingface_hub** | Wolf et al. (2020), ACL. [ACL](https://aclanthology.org/2020.acl-demos.6/) | [huggingface/huggingface_hub](https://github.com/huggingface/huggingface_hub) |


---

## 6. Web, UI and data verification


| Tools | GitHub / Documentation |
|-------------------------------- |------------------------------------------------------------------------------------------------ |
| **FastAPI** | [tiangolo/fastapi](https://github.com/tiangolo/fastapi) |
| **Uvicorn** | [encode/uvicorn](https://github.com/encode/uvicorn) |
| **a2wsgi** | [abersheeran/a2wsgi](https://github.com/abersheeran/a2wsgi) |
| **Dash** | [plotly/dash](https://github.com/plotly/dash) |
| **dash-bootstrap-components** | [facultyai/dash-bootstrap-components](https://github.com/facultyai/dash-bootstrap-components) |
| **Plotly** | [plotly/plotly.py](https://github.com/plotly/plotly.py) |
| **Streamlit** | [streamlit/streamlit](https://github.com/streamlit/streamlit) |
| **Altair** | [altair-viz/altair](https://github.com/altair-viz/altair) |
| **Pydantic** | [pydantic/pydantic](https://github.com/pydantic/pydantic) |
| **requests** | [psf/requests](https://github.com/psf/requests) |
| **feedparser** | [kurtmckee/feedparser](https://github.com/kurtmckee/feedparser) |
| **tqdm** | [tqdm/tqdm](https://github.com/tqdm/tqdm) |


---

## 7. Market data, news and crawlers


| Tools | Description | Links |
| ----------------- | ------------------------------------------------ | ------------------------------------------------------------------ |
| **AkShare** | Market and other data interface | [akfamily/akshare](https://github.com/akfamily/akshare) |
| **Crawl4AI** | Optional web crawling | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) |
| **Playwright** | Optional browser automation | [microsoft/playwright](https://github.com/microsoft/playwright) |
| **NewsAPI** | HTTP News API (if `research/news_newapi.py` is enabled) | [NewsAPI Documentation](https://newsapi.org/docs) |


---

## 8. Key data calculation example (engineering cross-reference)

This article is a summary of literature and tools, **not including** the values filled in during runtime. The **Phase2 shadow model selection instance** (prerequisite, `best_model_per_symbol`, NVDA decomposition, shadow MSE) that is consistent with the **`data.json`** snapshot can be found in **`Figure2.1-Res.md` §6**.