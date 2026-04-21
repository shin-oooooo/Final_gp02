# 情绪分与新闻序列模块：抓取与计分方法论（简版）

本文档对应 `research/sentiment_proxy.py`、`research/news_newapi.py`、`research/news_fetch_log.py` 及日历辅助 `research/sentiment_calendar.py` 中的实现，概述**新闻抓取 → 合并截断 → VADER → 综合分 S → 日度序列 S_t** 的流程、可调参数与核心公式。

---

## 1. 总体流程

1. **抓取**：多池并行拉取（英文 RSS、Google News Geo、可选 NewsAPI、可选 AKShare、Crawl4AI）。
2. **合并**：池顺序固定；跨池去重；丢弃无 `published` 日历日的条目。
3. **截断**：在测试窗内按策略保留至多 `max_headlines` 条（默认与上限见下）。
4. **计分**：对保留标题逐条 VADER；再叠加关键词惩罚与标的语境修正，得标量 S。
5. **序列**：由 `get_sentiment_detail` 返回的逐条 `compound` + `published` 构造按日历日或按分段的 S_t（见 §7）。

---

## 2. 数据源与池顺序（合并优先级）


| 池                           | 说明                              | 典型开关                                                                         |
| --------------------------- | ------------------------------- | ---------------------------------------------------------------------------- |
| **geo_rss**                 | Google News 等地缘种子 RSS           | `NEWS_GEO_RSS_CAP`                                                           |
| **rss_primary**             | 英文财经主 RSS（BBC/CNBC/Bloomberg 等） | RSS 相关 env                                                                   |
| **newapi**                  | NewsAPI.org 风格 `/v2/everything` | `NEWSAPI_KEY`, `NEWS_NEWAPI_ENABLED`, `NEWSAPI_FETCH_STRATEGY`               |
| **akshare_en / akshare_cn** | AKShare 全球线 / 中文门户              | `AKSHARE_NEWS_ENABLED`, `AKSHARE_EN_NEWS_ENABLED`, `AKSHARE_CN_NEWS_ENABLED` |
| **Crawl4AI**                | 配置 URL 爬取 Markdown → 标题候选       | `CRAWL4AI_ENABLED`, `CRAWL4AI_QUOTA_RATIO`, `CRAWL4AI_MAX_ITEMS` 等           |


**合并顺序**（先入池者优先在文本去重中保留）：  
`geo_rss → rss_primary → newapi → ak_en → ak_cn`，再与 **Crawl4AI** 结果拼接（Crawl 在 primary 合并之后单独去重配额）。

---

## 3. 关键参数与变量

### 3.1 规模与上限


| 符号 / 参数                               | 含义                                            | 默认或范围                                                                               |
| ------------------------------------- | --------------------------------------------- | ----------------------------------------------------------------------------------- |
| N_{\max}                              | `max_headlines`：用户/API 传入，管线内再夹紧              | [1,\texttt{MAXHEADLINESCAP}]，`MAX_HEADLINES_CAP=400`；默认 `DEFAULT_MAX_HEADLINES=120` |
| `NEWS_MAX_HEADLINES_PER_CALENDAR_DAY` | 同一日历日最多保留条数（合并后、VADER 前）                      | 默认 `80`                                                                             |
| `CRAWL4AI_QUOTA_RATIO`                | Crawl4AI 在最终集合中的目标占比（约）                       | 默认 `0.30`，夹紧到 [0,0.80]                                                              |
| `primary_quota`                       | \lfloor N_{\max}(1 - q_{\text{crawl}})\rfloor | 由 q_{\text{crawl}} 推出                                                               |
| `crawl_quota`                         | \lfloor N_{\max}\cdot q_{\text{crawl}}\rfloor | 同上                                                                                  |


### 3.2 合并策略


| 参数                         | 含义                                                                  |
| -------------------------- | ------------------------------------------------------------------- |
| `NEWS_UNIFORM_DAILY_MERGE` | `1`：按**日历日轮询**填充至上限（日内 `(source, text)` 排序）；`0`：按日期 oldest-first 截断 |


### 3.3 NewsAPI


| 参数                             | 含义                                                         |
| ------------------------------ | ---------------------------------------------------------- |
| `NEWSAPI_FETCH_STRATEGY`       | `rss_gap_sample`（默认）/ `full_range` / `interval_vader`（及别名） |
| `NEWSAPI_GAP_MIN_RSS_COUNT`    | RSS+Geo 某日计数低于此则视为「稀疏日」候选                                  |
| `NEWSAPI_GAP_SAMPLE_MAX_DAYS`  | 稀疏日中最多抽几天去调 API                                            |
| `NEWSAPI_RANDOM_SEED`          | 字符串种子，用于可复现抽样                                              |
| `NEWSAPI_LOOKBACK_DAYS`        | 回溯自然日宽度                                                    |
| `LREPORT_SENTIMENT_TEST_START` | `interval_vader` 模式下「第 d 天」起点                              |


### 3.4 Crawl4AI 与日历带补洞


| 参数                                 | 含义                                      |
| ---------------------------------- | --------------------------------------- |
| `NEWS_CRAWL_STAMP_OFFSET_DAYS`     | 无解析日期时的回退「盖章」：`today - offset`          |
| `CRAWL4AI_GAP_FILL_ENABLED`        | 是否启用默认窗 **2026-03-17～2026-04-01** 的补洞逻辑 |
| `CRAWL4AI_GAP_FILL_START` / `END`  | 补洞日历窗（ISO）                              |
| `CRAWL4AI_GAP_FILL_MIN_PER_DAY`    | 低于该计数视为当日稀疏                             |
| `CRAWL4AI_GAP_FILL_MIN_BAND_TOTAL` | 窗内总条数低于此亦触发                             |
| `CRAWL4AI_GAP_FILL_EXTRA_BUDGET`   | 触发时增加的 crawl 抓取上限                       |


### 3.5 综合分与标的


| 符号                | 含义                                                      |
| ----------------- | ------------------------------------------------------- |
| \text{compound}_i | 第 i 条标题的 VADER compound \in [-1,1]                      |
| `penalty`         | 地缘等风险词命中惩罚（§5.2）                                        |
| `severity_boost`  | 组合标的语境×方向修正（§5.3）                                       |
| `active_symbols`  | `get_sentiment_detail(..., active_symbols=...)` 传入的标的列表 |


---

## 4. 合并与去重（要点）

- **去重键**：标题文本规范化后前缀（约 120 字符级）等；跨池保留先出现池的条目（池顺序见 §2）。
- **无日期丢弃**：合并与截断阶段仅保留 `published` 为日历 `date` 的条目；统计 `dropped_undated_count`。
- **Crawl4AI 与 primary 拼接**：在 primary 经 `_merge_headline_lists(..., primary_quota)` 后，从 `crawl_pool` 中按序追加不与 primary 文本键冲突的条目，直至 `crawl_quota`。
- **最终截断**：`_finalize_headline_cap`（默认仍用「按日轮询」或历史带偏好，见 `NEWS_PREFER_HISTORY_BAND`）。

---

## 5. VADER 与综合标量 S

### 5.1 VADER 与 \text{vaderavg}

使用 `vaderSentiment.SentimentIntensityAnalyzer`，并注入项目内 **Iran–US 冲突扩展词表**（`_IRAN_US_LEXICON`）。对每条标题 t_i：

\text{compound}_i,\ \text{pos}_i,\ \text{neg}_i,\ \text{neu}_i = \mathrm{VADER}(t_i)

\text{vaderavg} = \frac{1}{n}\sum_{i=1}^{n} \text{compound}_i

（n 为有效标题条数。）

### 5.2 风险词惩罚 `penalty`

设 `neg_hits`、`pos_hits` 分别为负面/正面关键词在**全部标题拼接串**中的命中次数（关键词表为 `_RISK_KEYWORDS`、`_POSITIVE_KEYWORDS`）：

\text{penalty} = \mathrm{clip}\big(-0.04\cdot \text{neghits} + 0.02\cdot \text{poshits},\ -0.35,\ 0.15\big)

### 5.3  severity_boost（标的语境）

对每个标的 s：短语规则得分 + 语境×方向配对表 `_CONTEXT_DIRECTION_PAIRS` 的加权和，再按每标的 cap 夹紧；令全部标的得分为 \Delta_s，取最差值 \text{worst}=\min_s \Delta_s，负值集合均值 \overline{\text{neg}}：

\text{severityboost} = \mathrm{clip}\big(0.60\cdot \text{worst} + 0.40\cdot \overline{\text{neg}},\ -0.70,\ 0.25\big)

### 5.4 综合情绪分 S

S = \mathrm{clip}\big(\text{vaderavg} + \text{penalty} + \text{severityboost},\ -1,\ 1\big)

`get_sentiment_score()` 返回即 S；`get_sentiment_detail()` 另返回各分量与逐条 VADER 明细。

---

## 6. NewsAPI 三种抓取模式（摘要）

1. `**rss_gap_sample`（默认）**
  在 `[today-\text{LOOKBACK}, today]` 内找出 RSS+Geo 计数 `< \texttt{NEWSAPI\_GAP\_MIN\_RSS\_COUNT}` 的日期，随机抽至多 `NEWSAPI_GAP_SAMPLE_MAX_DAYS` 天；仅对这些天逐日请求（每自然日至多一页 `everything`）。
2. `**full_range` / `full` / `all_days`**
  对上述回溯窗内**每个日历日**各发请求（受 API 与 `NEWSAPI_MAX_RAW_ARTICLES` 等限制）。
3. `**interval_vader`**
  - 在测试起点至 `today` 的 **日索引 1..30** 上生成单调端点序列，相邻端点差 \in2,3,4，含 1 与 30。  
  - 每相邻端点对应该窗内一段 **连续日历子区间**，**每段一次** `everything`（`from`/`to` 覆盖该段）。  
  - 段内原始结果按 VADER **compound** 分 5 箱（阈值 -0.6,-0.2,0.2,0.6）**轮询抽取**，再全局去重截断。  
  - 详见 `research/news_newapi.py` 中 `fetch_newapi_headlines_interval_vader`。

---

## 7. 日度情绪序列 S_t（两种实现）

输入均为 `get_sentiment_detail` 的 `headlines`：每条含 `published`（ISO 日期）与 `compound`。

### 7.1 按日历日均值 + 对齐交易日（`vader_st_series_from_detail`）

对日历日 d，令当日所有 compound 集合为 \mathcal{C}_d：

S^{\text{daily}}_d = \mathrm{clip}\left(\frac{1}{|\mathcal{C}*d|}\sum*{c\in\mathcal{C}_d} c,\ -1,\ 1\right)

将 S^{\text{daily}}_d 对齐到交易日索引 `index`：有新闻的日直接赋值；缺失用 **前向填充 → 后向填充**，仍缺则用 `fallback`。

### 7.2 分段累积平台（`vader_st_series_partition_cumulative_from_detail`）

在测试窗 [\text{teststartcal},\text{testendcal}] 内，按新闻出现日将窗划为若干**日历段**（见 `_calendar_segments_partition_by_news_dates`）。对段 [a,b]：

M = \mathrm{clip}\left(\mathrm{mean}\text{compound} : \text{published}\in[a,b],\ -1,\ 1\right)

维护累积量 `carry`（初值 `fallback`）。对该段内每个交易日赋同一水平：

S_t = \mathrm{clip}(\text{carry} + M,\ -1,\ 1)

然后 \text{carry} \leftarrow \text{carry} + M 进入下一段（段内为**平台**，段间**跳跃累积**）。

---

## 8. 持久化与审计

- `**write_news_fetch_log`**：合并后写入 `news_fetch_log.json`（默认路径可由 `LREPORT_NEWS_FETCH_JSON` 覆盖）；合并前全文写入兄弟文件 `*_premerge.json`（`LREPORT_NEWS_PREMERGE_JSON`）。  
- `**fetch_meta`** 中含池规模、`newapi_fetch_strategy`、Crawl 补洞触发信息、`news_uniform_daily_merge` 等，便于方法披露与复现实验。

---

## 9. 依赖与注意

- **VADER**：`pip install vaderSentiment`  
- **Crawl4AI**：需 `crawl4ai` 与 Playwright 浏览器（见仓库说明）  
- **NewsAPI**：受账户配额限制；失败时 `newapi_n=0`，情绪仅来自其余池，应在分析中注明。

---

*文档版本：与仓库代码同步的简要说明；细节以源码为准。*