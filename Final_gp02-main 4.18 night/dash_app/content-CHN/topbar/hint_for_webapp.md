## 使用提示

1. **首次使用**：点击左栏「立即刷新数据」获取最新行情，再点顶栏「保存运行」执行全链路。
2. **投资 / 研究模式**：投资模式显示讲解卡片；研究模式显示源码追踪、数据索引与完整方法论。切换研究模式后，侧栏讲解卡标题会从「图表与方法简介」切换为「数据、参数与方法论详情」。
3. **中英文切换**：顶栏左格投资/研究按钮的**下方**新增「中 / EN」分段按钮，点击后页面会附加 `?lang=chn` 或 `?lang=eng` 查询串并自动刷新。中文文案维护于 `dash_app/content-CHN/`、英文文案维护于 `dash_app/content-ENG/`；两个目录内部结构相同（含 `Inv/`、`Res/` 子文件夹，分别存 `-Inv.md` / `-Res.md`）。若英文文件缺失，系统会自动回退到中文同名文件，便于翻译渐进式补齐。页面上所有**按钮、Tab、Modal、主栏 P0–P4 诊断短语/表头/提示、研究模式手风琴标题、左栏辅助小字、概览卡标题**等静态文案集中维护在 `all_labels.md`（原 `topbar_labels.md`），并在该文件顶部通过**超链接**指向大篇幅叙述（如 `render/explain/topbar/p0_aggregate_line.py` 与 `p1_stat_method.md`），避免把长文塞进扁平 key-value。
4. **防御等级**：顶栏徽章显示当前 Level（0/1/2），点击右侧 ↓ 可展开查看各防御条件汇总。
5. **三栏布局**：左栏调参数，中栏看主图，右栏看防御指标。
6. **自定义资产**：左栏 P0 面板可增删标的、调整权重，点击「应用」后重算。
7. **Hugging Face Space 上的新闻情绪**：HF 容器内很难装 Crawl4AI（Chromium + Playwright 依赖链复杂且易触发 IP 反爬），所以 HF 部署默认**不现场爬新闻**，而是**回放仓库里已经提交的 `news_fetch_log.json` / `news_fetch_log_premerge.json`** 作为情绪分输入（由 `research/sentiment/sources_cache.py` 自动识别 HF 的 `SPACE_ID` 环境变量触发）。若想在本地强制走同样的回放：设 `LREPORT_NEWS_USE_CACHE=1`；想强制关闭回放：`LREPORT_NEWS_USE_CACHE=0`。更新情绪数据的流程是**本地跑一次全链路 → 提交更新后的两个 JSON → 推到 Space 仓库**。
