# AIE1902 Final Project — 研究管线 + Web 仪表盘

> **课程 / 项目**：AIE1902 — 多资产防御性投资研究框架（Phase 0–4）
> **WebApp（在线 Demo）**：[https://huggingface.co/spaces/shinopqxm/Final_gp02](https://huggingface.co/spaces/shinopqxm/Final_gp02)
> **GitHub**：[https://github.com/shin-oooooo/Final_gp02](https://github.com/shin-oooooo/Final_gp02)

本仓库是一个「**量化研究管线 + FastAPI 后端 + Plotly Dash 前端**」三位一体的 Python 单体应用，围绕 NVDA / MSFT / TSMC / GOOGL / AAPL / XLE / GLD / TLT / SPY / AU0 等多资产标的，完成从数据采集、平稳性诊断、模型比选（Naive / ARIMA / LightGBM / Kronos），到蒙特卡洛路径生成、防御策略（标准 / 警戒 / 熔毁三级）评估的端到端分析，并通过可交互 Web UI 呈现。

> **目录重命名**：源码根目录已统一为 `**Final_gp02`**（曾用文件夹名 `**Final_gp02-main 4.18 night**`）。下文中的 `cd`、相对路径均以 `**Final_gp02/**` 为仓库根；若你本地仍保留旧文件夹名，请自行替换为当前实际路径。

---

## 1. 快速开始

### 1.1 一键启动（Windows）

仓库根目录下已提供 `START_SERVER.bat`，双击即可启动 FastAPI + Dash：

```bat
START_SERVER.bat
```

等同于在 `**Final_gp02/**` 仓库根目录下运行：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

启动后打开：

- Dash 仪表盘：[http://localhost:8000/dash/](http://localhost:8000/dash/)
- FastAPI 文档：[http://localhost:8000/docs](http://localhost:8000/docs)
- 健康检查：[http://localhost:8000/api/health](http://localhost:8000/api/health)

### 1.2 手动启动（任何平台）

```bash
cd "Final_gp02"
pip install -r requirements.txt
# 首次运行，可选：下载 Kronos 预训练权重到 kronos_weights/
python download_kronos_weights.py
# 启动
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

> 如需 `crawl4ai` 的实时新闻抓取，另需执行 `python research/install_crawl4ai_browsers.py` 安装 Playwright 浏览器。

### 1.3 Docker / HuggingFace Space 部署

仓库已提供 `Dockerfile`（CPU-only PyTorch，便于 HF Spaces 免 GPU 运行）：

```bash
cd "Final_gp02"
docker build -t final-gp02 .
docker run -p 8000:8000 final-gp02
```

---

## 2. 目录结构

```
Final_gp02/                        
├── README.md
├── .gitignore
├── api/                           # FastAPI 后端
│   └── main.py                    #   /api/analyze, /api/monte-carlo, /api/health …
├── dash_app/                      # Plotly Dash 前端（UI / 回调 / 渲染 / 图表）
│   ├── app.py                     #   create_dash_app() 工厂
│   ├── ui/                        #   静态布局
│   ├── callbacks/                 #   交互回调（按区域拆分）
│   ├── render/                    #   快照 → Dash 组件
│   ├── figures.py / fig41/        #   Plotly 图表构建
│   ├── pipeline_exec/             #   滑块 → 管线调用（三级降级）
│   ├── content-CHN/, content-ENG/ #   中英双语文案（Markdown）
│   └── ARCHITECTURE.md            #   架构详细说明（132 个 .py 文件全覆盖）
├── research/                      # 量化管线 Phase 0–3 + 情绪子系统
│   ├── pipeline.py                #   端到端编排
│   ├── phase0.py                  #   资产宇宙 / 相关性 / Beta
│   ├── phase1.py                  #   平稳性 / LB / 分组
│   ├── phase2.py                  #   模型比选（Naive / ARIMA / LightGBM / Kronos）
│   ├── phase3.py                  #   Jump-Diffusion MC 路径
│   ├── schemas.py                 #   Pydantic 数据契约
│   ├── sentiment/                 #   情绪子系统（多模块）
│   ├── news_newapi.py             #   NewsAPI 客户端
│   └── defense_state.py           #   防御等级解析
├── kronos_model/                  # Kronos 深度学习预测器（BSQuantizer + 注意力）
├── kronos_predictor.py
├── kronos_weights/                # HuggingFace 下载的预训练权重（LFS）
├── scripts/                       # 启动脚本 / HF Space 入口
├── data.json                      # 核心行情数据（宽格式收盘价表）
├── news_fetch_log*.json           # 新闻抓取日志 + pre-merge 快照
├── fetch_data.py                  # 数据拉取 CLI（AKShare + yfinance）
├── download_kronos_weights.py
├── requirements.txt               # 通用依赖
├── requirements-hf.txt            # HF Spaces 精简依赖
└── Dockerfile
```

完整依赖图与 132 个 `.py` 文件职责解释，见 `[dash_app/ARCHITECTURE.md](dash_app/ARCHITECTURE.md)`。

---

## 3. 核心能力

### 3.1 研究管线（`research/`）


| Phase       | 内容                                                    | 关键输出                                   |
| ----------- | ----------------------------------------------------- | -------------------------------------- |
| **Phase 0** | 资产宇宙 / 相关性热图 / 滚动 Beta                                | `cov_matrix`, `beta_matrix`            |
| **Phase 1** | 平稳性（ADF）/ LB 自相关 / 分组分析                               | 资产诊断卡片                                 |
| **Phase 2** | 四模型比选（Naive / ARIMA / LightGBM / Kronos）+ 影子择模 + 密度热图 | `best_model_per_symbol`, μ/σ 表         |
| **Phase 3** | AdaptiveOptimizer + Jump-Diffusion 蒙特卡洛双轨（保守/压力）      | `conservative_median_end`, `stress_p5` |
| **Phase 4** | 预警有效性（Fig4.1）+ 防御策略对照（Fig4.2）                         | 标准 / 警戒 / 熔毁三级评估                       |


情绪子系统（`research/sentiment/`）提供 9 个独立模块：词典、核心打分、过滤、RSS/Crawl4AI 源、NewsAPI 集成、情绪日历、时间序列装配。

### 3.2 FastAPI 后端（`api/main.py`）


| Endpoint                              | 作用                              |
| ------------------------------------- | ------------------------------- |
| `GET /api/health`                     | 健康检查                            |
| `POST /api/analyze`                   | 运行完整 Phase 0–3 管线，返回 JSON 快照    |
| `POST /api/monte-carlo`               | 后台任务：跳跃扩散 20k 条路径               |
| `GET /api/monte-carlo/{key}`          | 取回后台任务结果                        |
| `GET /api/integrations`               | Crawl4AI / Ollama / 财经资讯 URL 配置 |
| `GET /api/integrations/ollama/health` | Ollama 可达性                      |
| `GET /api/news/newapi`                | NewsAPI 日期化头条（需 `NEWSAPI_KEY`）  |
| `GET /api/routes`, `/api/dash-status` | 调试端点                            |


根路径 `/` 自动重定向至 `/dash/`；若 Dash 挂载失败会回落为纯 HTML 错误页。

### 3.3 Dash 仪表盘（`dash_app/`）

- **三列布局**：左侧栏（项目综述 / 防御参数）· 中间主面板（P0–P4 Tab）· 右侧栏（FigX.1–6 可折叠讲解）。
- **双语**：URL 参数 `?lang=chn|eng` 即时切换，文案从 `content-CHN/` / `content-ENG/` 读取。
- **主题**：默认 CYBORG 深色主题 + FontAwesome 图标 + 全局 MathJax 公式渲染。
- **交互**：滑块 → `pipeline_exec` → `research.pipeline.run_pipeline`（或远程 `/api/analyze`）。

---

## 4. 依赖栈

见 `[requirements.txt](requirements.txt)`。核心栈：

- **Web**：`fastapi`, `uvicorn`, `dash`, `dash-bootstrap-components`, `a2wsgi`, `streamlit`
- **量化**：`numpy`, `pandas`, `scipy`, `statsmodels`, `scikit-learn`, `lightgbm`, `pydantic`
- **深度学习**：`torch`, `einops`, `safetensors`, `huggingface_hub`, `tqdm`
- **数据 / 情绪**：`akshare`, `requests`, `feedparser`, `vaderSentiment`, `crawl4ai`, `playwright`
- **可视化**：`plotly`, `altair<5`

Python ≥ 3.11 推荐。

---

## 5. 环境变量


| 变量                            | 默认      | 说明                         |
| ----------------------------- | ------- | -------------------------- |
| `NEWSAPI_KEY`                 | *(无)*   | `/api/news/newapi` 与情绪管线使用 |
| `CRAWL4AI_ENABLED`            | `1`     | 是否启用 Crawl4AI 历史新闻抓取       |
| `CRAWL4AI_PAGE_TIMEOUT_MS`    | `30000` | 单页超时（毫秒）                   |
| `CRAWL4AI_MAX_URLS`           | `5`     | 每次抓取并发 URL 上限              |
| `CRAWL4AI_PER_PAGE_HEADLINES` | `30`    | 单页头条上限                     |
| `LREPORT_FAST_NEWS`           | `1`     | 并行 RSS + 短超时（开发态推荐）        |
| `NEWS_RSS_HTTP_TIMEOUT`       | `10`    | RSS HTTP 超时（秒）             |
| `NEWS_RSS_PARALLEL`           | `1`     | RSS 并发开关                   |


---

## 6. 开发约定

- **单向依赖**：UI 层（`dash_app/`）只读研究层（`research/`）快照；研究层永不反向依赖 UI。
- **数据契约**：所有跨层传递对象经 `research/schemas.py` 的 Pydantic 模型冻结。
- **文案分层**：前端可见文字统一放在 `dash_app/content-{CHN,ENG}/*.md`，代码侧不嵌字面量。
- **图表**：Plotly Figure 全部通过 `dash_app/figures*.py` / `dash_app/fig41/` 构建，`render/` 仅负责快照 → 组件。
- **工作流规则**：`.cursor/rules/` 下有 `prefer-edit-over-create`、`modular-refactor`、`architecture-bootstrap`、`dash-layout-static-contract`、`blackbox-refactor` 等工程规约。

---

## 7. 参考文档

- 架构详解：`[dash_app/ARCHITECTURE.md](dash_app/ARCHITECTURE.md)`
- 情绪方法论：`[research/sentiment_news_methodology.md](research/sentiment_news_methodology.md)`
- 数据摘要：`[read.txt](read.txt)`（各标的按月 mean_close）
- 在线 Demo：[https://huggingface.co/spaces/shinopqxm/Final_gp02](https://huggingface.co/spaces/shinopqxm/Final_gp02)

---

## 8. 许可

课程作业项目，未声明开源许可；如需复用请先联系作者。