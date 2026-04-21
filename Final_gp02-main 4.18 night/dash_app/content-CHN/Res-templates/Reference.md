# References & Resources

本文档汇总本仓库（AIE1902 防御研究看板）涉及的**模型、统计方法、数值库、工程工具与外部服务**，便于论文或报告中的参考文献与可追溯来源。条目与 `requirements.txt`、`README.md` 及 `research/`、`dash_app/` 实现保持一致。

---

## 1. 预测与机器学习模型


| 条目           | 在本项目中的角色                                          | 论文 / 正式出版物                                                                                                                                                                                        | 代码 / 模型主页                                                      |
| ------------ | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **LightGBM** | Phase 2 收益预测（如 `LGBMRegressor`），与 ARIMA、Kronos 对比 | Ke et al., *LightGBM: A Highly Efficient Gradient Boosting Decision Tree*, NeurIPS 2017. [PDF](https://papers.nips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree.pdf) | [microsoft/LightGBM](https://github.com/microsoft/LightGBM)    |
| **Kronos**   | K 线时序基础模型；Phase 2 一步预测（权重就绪时严格推理，见 `Models_constraints.md`）与 JSD 轨 | Liu et al., *Kronos: A Foundation Model for the Language of Financial Markets*, arXiv:2508.02739. [arXiv](https://arxiv.org/abs/2508.02739)                                                       | [shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos)    |
| **ARIMA**    | Phase 2 条件均值（如 ARIMA(1,0,1)），与 LGBM、Kronos 对比     | Box & Jenkins 时间序列分析框架                                                                                                                                                                            | 经 [statsmodels](https://github.com/statsmodels/statsmodels) 实现 |
| **Naive 基准** | 影子 MSE、部分 KL 对之外的对照                               | —                                                                                                                                                                                                 | —                                                              |


---

## 2. 情绪与自然语言处理


| 条目        | 在本项目中的角色                                                             | 论文                                                                                                                                                                     | 实现                                                                  |
| --------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **VADER** | 新闻标题 `compound` 分、项目扩展词表、`S_t` 情绪序列（见 `research/sentiment_proxy.py`） | Hutto & Gilbert, *VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text*, ICWSM 2014. [ACL Anthology](https://aclanthology.org/W14-2616/) | [cjhutto/vaderSentiment](https://github.com/cjhutto/vaderSentiment) |


---

## 3. 统计检验、信息论与评估指标


| 方法                            | 说明（概念对应实现）                               | 参考                                                                                                                                                          |
| ----------------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ADF 单位根检验**                 | `research/phase1.py` 平稳性诊断               | Dickey & Fuller (1979/1981)；[statsmodels: `adfuller](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html)`                 |
| **Ljung–Box 自相关检验**           | `research/phase1.py`                     | Ljung & Box (1978)；[statsmodels: `acorr_ljungbox](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html)`           |
| **高斯负对数似然（NLL）**              | Phase 2 概率评分                             | 标准多元/一元高斯密度                                                                                                                                                 |
| **Kullback–Leibler 散度（高斯闭式）** | Phase 2 内部 `_gaussian_kl_forward`        | Kullback & Leibler (1951)                                                                                                                                   |
| **Jensen–Shannon 散度**         | Phase 2 `_js_divergence`、模型分布三角对比        | Lin (1991)；参见 [Endres & Schindelin (2003)](https://arxiv.org/abs/cs/0201011)                                                                                |
| **Diebold–Mariano 类检验**       | Phase 2 `_dm_hac_t_pvalue`（HAC t / 双侧 p） | Diebold & Mariano (1995), *Journal of Business & Economic Statistics*. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0169207000700429) |
| **预测区间覆盖率**                   | Phase 2 “交通灯”类指标                         | 概率预报与校准文献（如 Gneiting et al.）                                                                                                                                |


---

## 4. 优化、风险与随机模拟


| 方法                | 说明                                                    | 参考                                                                                               |
| ----------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| **序列二次规划（SLSQP）** | `scipy.optimize.minimize(..., method="SLSQP")` 用于组合权重 | Kraft (1988)；[SciPy 文档](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html) |
| **CVaR（条件风险价值）**  | Phase 3 防御 Level 2 目标                                 | Rockafellar & Uryasev (2000) 等                                                                   |
| **Sharpe 比率**     | Phase 3 Level 0 目标                                    | Sharpe (1966, 1994)                                                                              |
| **跳跃扩散与蒙特卡洛路径**   | Phase 3 向量化路径；情绪驱动跳跃调度                                | Merton (1976) 跳跃扩散                                                                               |


---

## 5. 核心 Python 数值与机器学习库


| 库                   | 建议引用 / 文档                                                                                                  | GitHub                                                                        |
| ------------------- | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| **NumPy**           | Harris et al. (2020), *Nature*. [DOI](https://doi.org/10.1038/s41586-020-2649-2)                           | [numpy/numpy](https://github.com/numpy/numpy)                                 |
| **pandas**          | McKinney (2010), *SciPy* 会议论文. [DOI](https://doi.org/10.25080/Majora-92bf1922-00a)                         | [pandas-dev/pandas](https://github.com/pandas-dev/pandas)                     |
| **SciPy**           | Virtanen et al. (2020), *Nature Methods*. [DOI](https://doi.org/10.1038/s41592-019-0686-2)                 | [scipy/scipy](https://github.com/scipy/scipy)                                 |
| **statsmodels**     | Seabold & Perktold (2010), *SciPy* 会议                                                                      | [statsmodels/statsmodels](https://github.com/statsmodels/statsmodels)         |
| **scikit-learn**    | Pedregosa et al. (2011), *JMLR*. [PDF](https://www.jmlr.org/papers/volume12/pedregosa11a/pedregosa11a.pdf) | [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn)     |
| **PyTorch**         | Paszke et al. (2019), NeurIPS                                                                              | [pytorch/pytorch](https://github.com/pytorch/pytorch)                         |
| **einops**          | Rogozhnikov (2022), arXiv:2112.02662. [arXiv](https://arxiv.org/abs/2112.02662)                            | [arogozhnikov/einops](https://github.com/arogozhnikov/einops)                 |
| **safetensors**     | Hugging Face 张量安全序列化说明                                                                                     | [huggingface/safetensors](https://github.com/huggingface/safetensors)         |
| **huggingface_hub** | Wolf et al. (2020), ACL. [ACL](https://aclanthology.org/2020.acl-demos.6/)                                 | [huggingface/huggingface_hub](https://github.com/huggingface/huggingface_hub) |


---

## 6. Web、UI 与数据校验


| 工具                            | GitHub / 文档                                                                                   |
| ----------------------------- | --------------------------------------------------------------------------------------------- |
| **FastAPI**                   | [tiangolo/fastapi](https://github.com/tiangolo/fastapi)                                       |
| **Uvicorn**                   | [encode/uvicorn](https://github.com/encode/uvicorn)                                           |
| **a2wsgi**                    | [abersheeran/a2wsgi](https://github.com/abersheeran/a2wsgi)                                   |
| **Dash**                      | [plotly/dash](https://github.com/plotly/dash)                                                 |
| **dash-bootstrap-components** | [facultyai/dash-bootstrap-components](https://github.com/facultyai/dash-bootstrap-components) |
| **Plotly**                    | [plotly/plotly.py](https://github.com/plotly/plotly.py)                                       |
| **Streamlit**                 | [streamlit/streamlit](https://github.com/streamlit/streamlit)                                 |
| **Altair**                    | [altair-viz/altair](https://github.com/altair-viz/altair)                                     |
| **Pydantic**                  | [pydantic/pydantic](https://github.com/pydantic/pydantic)                                     |
| **requests**                  | [psf/requests](https://github.com/psf/requests)                                               |
| **feedparser**                | [kurtmckee/feedparser](https://github.com/kurtmckee/feedparser)                               |
| **tqdm**                      | [tqdm/tqdm](https://github.com/tqdm/tqdm)                                                     |


---

## 7. 市场数据、新闻与爬虫


| 工具             | 说明                                         | 链接                                                              |
| -------------- | ------------------------------------------ | --------------------------------------------------------------- |
| **AkShare**    | 行情等数据接口                                    | [akfamily/akshare](https://github.com/akfamily/akshare)         |
| **Crawl4AI**   | 可选网页抓取                                     | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai)     |
| **Playwright** | 可选浏览器自动化                                   | [microsoft/playwright](https://github.com/microsoft/playwright) |
| **NewsAPI**    | HTTP 新闻 API（若启用 `research/news_newapi.py`） | [NewsAPI 文档](https://newsapi.org/docs)                          |


---

## 8. 关键数据计算示例（工程交叉引用）

本文为文献与工具汇总，**不包含**运行时填写的数值。与 **`data.json`** 快照一致的 **Phase2 影子择模实例**（前提、`best_model_per_symbol`、NVDA 分解、影子 MSE）统一见 **`Figure2.1-Res.md` §6**。


