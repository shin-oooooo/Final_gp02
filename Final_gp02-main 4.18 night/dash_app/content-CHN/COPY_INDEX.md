# Dash UI · 文案索引（单一事实来源）

> **原则**：所有前端可见文字都从本目录（或 `content-ENG/`）的 `.md` 读取；
> `dash_app/assets/*.json` 仅作历史兼容 fallback。
> 改文案只需改 `.md` 并**重启 Dash 进程**（有内存缓存）。
>
> **中英文切换**：顶栏左格「中 / EN」按钮 → `?lang=chn` / `?lang=eng` → `app.py`
> 的 layout factory 读取查询串调用 `dash_app/services/copy.py::set_language()`
> 切换源目录。英文缺失项自动回退到中文同名文件。

---

## 一、加载优先级

```
content-CHN/<name>.md  (当 lang=chn)
content-ENG/<name>.md  (当 lang=eng，缺失时回退 content-CHN/<name>.md)
    →  assets/<name>.json    (最终 JSON 兜底，不会主动维护)
```

所有 `get_*` 函数实现在 `dash_app/services/copy.py`；统一通过
`_get_copy(basename, key, default)` 读取，因此每一个 `.json` 都可以通过创建同名
`.md` 覆盖。

---

## 二、每个 .md 控制页面哪里


| `.md` 文件                                                            | 控制区域                                                  | 使用的 Python API                                                     |
| ------------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------ |
| `figures_titles.md`                                                 | **每张图表的标题**（图上方灰条）                                    | `get_figure_title(key)`                                            |
| `figures_hints.md`                                                  | **每张图表的下方提示小字**                                       | `get_figure_hint(key)`                                             |
| `all_labels.md`（原 `topbar_labels.md`）                            | **全站静态文案**：顶栏（标题 / 投研 / 中英 / Tab / 按钮）、主栏 P0–P4（类标签 / 诊断短语 / 表头 / 提示 / caption）、研究模式手风琴标题、Modal 对话框、左栏 `_aux_label` 辅助小字、概览卡标题；顶部列出**大篇幅文档的超链接**（如 `p0_aggregate_line.py` / `p1_stat_method.md`） | `get_topbar_label(key)` 或等价的 `get_app_label(key)`                  |
| `sidebar_left.md`                                                   | 左栏分组子标题 + 组内小标题 / 辅助标签（合并层级；H2 = 子标题，H3 = 小标题 / 辅助标签） | `get_sidebar_left_title(key)` · `get_sidebar_left_label(key)`      |
| `sidebar_left_params_explanations.md`                               | 左栏参数问号按钮展开后的解释                                        | `get_param_explanation(key)`                                       |
| `kronos_hints.md`                                                   | Kronos 权重状态提示                                         | `get_kronos_hint(key)`                                             |
| `status_messages.md`                                                | **散落的运行时提示、占位、按钮文字**（含 Fig4.1 的 4 部分小标题）              | `get_status_message(key)`                                          |
| `defense_intro.md`                                                  | 顶栏展开的三列 Level 0/1/2 介绍                                | `get_defense_intro()`                                              |
| `project_intro.md`                                                  | 「研究项目综述」正文                                            | `get_project_intro()`                                              |
| `phase0_tab_intro.md` / `phase1_intro.md` / ... / `phase4_intro.md` | 各 Phase 顶部导语                                          | `get_phase_intro(0..4)`                                            |
| `Res-templates/FigX.*-Res.md` / `Inv/FigX.*-Inv.md` / `Res-templates/Fig0.1-Res.md` ... | 单张图的**长讲解卡片**（含 `## Defense-Tag` 段）。Research 模式以 `Res-templates/` 为唯一事实源；`Res/` 是 `dash_app/utilities/md_sync.py --write-md` 的离线快照产物，不被运行时读取。 | `dash_app/render/explain/_loaders.py::load_figx_template` / `load_fig4_template` / `load_defense_tag_text`、`build_figxN_explain_body` |
| `defense_reasons.md`                                                | 防御条件汇总（总表）                                            | 顶栏展开区                                                              |
| `hint_for_webapp.md`                                                | 顶栏「Webapp 运行与使用提示」弹窗                                  | `get_md_text('hint_for_webapp.md')`                                |
| `Methodology_constraints.md`                                        | 方法论局限性块                                               | 对应页脚                                                               |


---

## 三、MD 格式规则（只此一份，不要再变）

简单 key-value（大多数文件用这种）：

```md
# 随意加说明注释（系统忽略）
> 引用块也会被忽略

key_name: "一段可带空格与标点的中文文案"
another_key: "值"
```

**允许**：

- 文件头部加任意 `#` 标题 / `>` 引用块做注释
- `key: value` 中间插空行
- 不写 `---` 围栏（旧版残留的单个 `---` 也能兼容）
- 值用双引号 `"…"`、单引号 `'…'` 或不加引号

**不允许**：

- 在 key 前面加 `##` （这是历史坑，最新解析器会**自动剥掉**，但请别新写）
- key 用中文（必须是 `[A-Za-z_][A-Za-z0-9_\-\.]`*）

嵌套结构（`defense_intro.md` 这种）：用下划线扁平化 key，例如 `level2_title` / `level2_item_1`。

---

## 四、修改流程（最小可运行案例）

1. 打开对应的 `.md`，改引号内文字即可。
2. 保存。
3. **重启 Dash 进程**（有进程内缓存 `_md_cache`）。
4. 浏览器硬刷新（Ctrl+F5）。

快速本地验证某个键有没有被读到（不用启动 Dash）：

```bash
cd "Final_gp02-main 4.18 night"
python -c "from dash_app.figure_caption_service import get_status_message; print(get_status_message('fig41_section2_title'))"
```

---

## 五、Fig4.1 / FigX.2 / FigX.4 bug 说明

### Fig4.1 不显示

现行设计是**四部分面板**（详见 `dashboard_face_render.py::_p4_experiments_stack_block` 与本目录 `Fig4.1-Res.md`），依赖 `phase3.defense_validation.fig41_verify` 字段。

- 若现有 `data.json` 是旧版本：**必须重跑一次管线**（点击侧栏「保存运行」或 `/api/refresh`）。
- 若新版管线跑过但仍空：检查 `research/post_alarm_realized_metrics.py::build_fig41_verify_bundle` 的返回，可能 `test_st_series` 为空或参照日映射失败。

图表区"无可用日收益"/"无数据"的占位文字现在**全部来自 `status_messages.md`**：

- `fig41_empty_daily_returns`
- `fig41_empty_std_by_k`

### FigX.2 结构熵 / FigX.4 可信度 样式问题

`metric_rails.py` 生成的 DOM 结构健康，CSS 在 `assets/custom.css`。如果发现样式异常，请提供**截图**并指出是：

- 色块宽度错 → `defense-rgy-seg` 的 flex 分配问题
- 标注位置错 → `defense-tau-anno` 的 `left` 百分比
- 文字颜色错 → `metric-rail-title` 的深色模式颜色变量

### 标题不随 .md 更新

**这个问题已经修掉了**。根因：解析器要求 `---` 首尾围栏，旧 `figures_titles.md` 只有开头。新解析器容忍任意格式，并且**优先**读 `.md`。

---

## 六、弃用的 JSON 文件

下列文件仍保留在 `assets/`，作为 fallback，**不要**再编辑它们（改了不生效）：

- `figures_titles.json`
- `figures_hints.json`
- `topbar_labels.json`（`.md` 已更名为 `all_labels.md`；本 JSON 保留只作最后兜底）
- `sidebar_left_titles.json`
- `sidebar_left_labels.json`
- `sidebar_left_params_explanations.json`
- `kronos_hints.json`
- `status_messages.json`
- `defense_intro.json`
- `project_intro.json`
- `P{0..4}_intro.json`
- `figure_captions.json`（**例外**：仍在使用，结构复杂不适合 md，暂不迁移）

