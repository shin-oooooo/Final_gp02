"""前端所有可见文字的**统一查找入口**（底层基础服务；不归任何 UI 区域）。

加载优先级：``content/<name>.md`` → ``assets/<name>.json``
（MD 的 YAML frontmatter 优先；失败才回退到 JSON）。

对外最常用 API：

* :func:`get_figure_title` / :func:`get_figure_hint`  — 图表标题与提示
* :func:`get_topbar_label` / :func:`get_kronos_hint` — 顶栏按钮、Kronos 状态
* :func:`get_sidebar_left_title` / :func:`get_sidebar_left_label` / :func:`get_param_explanation`  — 左栏
* :func:`get_status_message`                                                                       — 运行时提示/占位
* :func:`get_phase_intro` / :func:`get_project_intro` / :func:`get_defense_intro`                  — 嵌套结构
* :func:`get_md_text`                                                                              — 加载完整 Markdown 正文
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict


# --------------------------------------------------------------------------- #
# 语言 & 缓存状态                                                              #
# --------------------------------------------------------------------------- #

# 运行期语言开关：``"chn"`` = content-CHN/；``"eng"`` = content-ENG/。
# 由 `app.py` 的 layout factory 读取 ``?lang=`` 查询串后调用 :func:`set_language` 初始化；
# 顶栏的 CHN/ENG 按钮点击后会触发整页 reload，layout factory 会再次设置。
# ``eng`` 不会回退读取 ``content-CHN/``（中英目录互不穿透）。
_LANG: str = "chn"

# 缓存全部以「语言 + 文件名」为键，避免语言切换后读到旧内容。
_text_cache: Dict[str, Any] = {}
_md_cache: Dict[str, Any] = {}


def get_language() -> str:
    """返回当前语言代号（``"chn"`` / ``"eng"``）。"""
    return _LANG


def set_language(lang: Any) -> None:
    """切换 content-CHN / content-ENG 源目录。

    仅影响后续 :func:`get_md_text` / :func:`_get_copy` 等调用的读取目标；
    切换时会**清空 md/JSON 缓存**，避免读到旧语言下的内容。
    """
    global _LANG, _text_cache, _md_cache
    lang_s = str(lang or "chn").strip().lower()
    if lang_s not in ("chn", "eng"):
        lang_s = "chn"
    if lang_s == _LANG:
        return
    _LANG = lang_s
    _text_cache = {}
    _md_cache = {}


def _assets_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets"


def _lang_content_dir(lang: str) -> Path:
    """语言对应的 content 根目录（``chn`` → ``content-CHN``，``eng`` → ``content-ENG``）。"""
    suffix = "CHN" if (lang or "chn").lower() == "chn" else "ENG"
    return Path(__file__).resolve().parents[1] / f"content-{suffix}"


def _content_dir() -> Path:
    """当前语言对应的 content 根目录（向后兼容旧签名）。"""
    return _lang_content_dir(_LANG)


def _text_json_path(filename: str) -> Path:
    return _assets_dir() / filename


def _load_text_json(filename: str) -> Dict[str, Any]:
    """Load a JSON text file from ``assets/`` with language-aware caching。"""
    global _text_cache
    cache_key = f"{_LANG}:{filename}"
    if cache_key in _text_cache:
        return _text_cache[cache_key]
    p = _text_json_path(filename)
    if not p.is_file():
        _text_cache[cache_key] = {}
        return {}
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    _text_cache[cache_key] = data if isinstance(data, dict) else {}
    return _text_cache[cache_key]


# --------------------------------------------------------------------------- #
# Markdown + YAML frontmatter 加载                                             #
# --------------------------------------------------------------------------- #


_KV_LINE_RE = re.compile(
    r'^\s*(?:#{1,6}\s+)?([A-Za-z_][A-Za-z0-9_\-\.]*)\s*:\s*(.*?)\s*$'
)


def _parse_yaml_frontmatter(text: str) -> Dict[str, str]:
    """Parse ``key: "value"`` pairs from the leading metadata block of a Markdown file.

    Tolerant to historical accidents:

    * opening ``---`` only, or **no** ``---`` fences at all
    * the first key being prefixed with ``##`` / ``###`` markdown heading syntax
    * blank lines in the middle of the block
    * single / double quotes around the value
    """
    assert isinstance(text, str), f"text must be str, got {type(text).__name__}"

    result: Dict[str, str] = {}
    if not text:
        return result

    body = text
    if body.startswith("---"):
        end = body.find("---", 3)
        if end != -1:
            body = body[3:end]
        else:
            body = body[3:]

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("-"):
            continue
        if stripped.startswith(">"):
            continue
        if stripped.startswith("#") and ":" not in stripped.split(" ", 1)[-1]:
            continue
        m = _KV_LINE_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip()
        val = m.group(2).strip()
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        result[key] = val

    return result


def _load_md_file(filename: str, default: str = "") -> str:
    """Load optional Markdown copy from ``content-{LANG}/<filename>``。

    加载优先级：
    1. **仅**当前语言目录（``content-CHN`` 或 ``content-ENG``）；中英切换互不穿透。
    2. 缺失时返回 ``default``。
    """
    global _md_cache
    cache_key = f"md:{_LANG}:{filename}"
    if cache_key in _md_cache:
        return _md_cache[cache_key]
    content = ""
    path = _lang_content_dir(_LANG) / filename
    try:
        with path.open(encoding="utf-8") as f:
            content = f.read().strip()
    except OSError:
        content = ""
    if not content:
        content = default
    _md_cache[cache_key] = content
    return content


def _load_md_frontmatter(filename: str) -> Dict[str, str]:
    """Load markdown file and return parsed YAML frontmatter dict。"""
    cache_key = f"fm:{_LANG}:{filename}"
    if cache_key in _md_cache:
        fm = _md_cache.get(cache_key)
        return fm if isinstance(fm, dict) else {}
    text = _load_md_file(filename, "")
    fm = _parse_yaml_frontmatter(text)
    _md_cache[cache_key] = fm
    return fm


def get_md_text(filename: str, default: str = "") -> str:
    """Return the body of a markdown file in ``content/`` (without YAML frontmatter)。"""
    text = _load_md_file(filename, default)
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            body = text[end + 3:].strip()
            return body if body else default
    return text if text else default


def get_md_text_by_mode(basename: str, ui_mode: str, default: str = "") -> str:
    """加载按 UI 模式切换的 Markdown。

    查找顺序：

    1. ``content/{basename}-{Res|Inv}.md`` — 模式专属版（研究 → Res；否则 Inv）
    2. ``content/{basename}.md`` — 共享基础版（两种模式都用）
    3. ``default`` 参数兜底

    约定：用户想区分两种模式时，**新建一份** ``content/{basename}-Res.md`` 或
    ``content/{basename}-Inv.md`` 即可；原 ``{basename}.md`` 仍有效，作为未覆盖情况下的回退。

    Args:
        basename: 不含扩展名的文件名，例如 ``"p0_heatmap_body"``。
        ui_mode: ``"invest"`` / ``"research"``；不区分大小写。
        default: 两类文件都不存在时返回的兜底文本。

    Returns:
        Markdown 正文字符串（已剥去 YAML frontmatter）。
    """
    assert isinstance(basename, str) and basename, "basename must be non-empty str"

    mode = (ui_mode or "invest").strip().lower()
    suffix = "Res" if mode == "research" else "Inv"

    # Try mode-specific variant first
    mode_text = get_md_text(f"{basename}-{suffix}.md", "")
    if mode_text:
        return mode_text

    # Fallback to shared base
    shared = get_md_text(f"{basename}.md", "")
    if shared:
        return shared

    return default


# --------------------------------------------------------------------------- #
# 统一查找器                                                                   #
# --------------------------------------------------------------------------- #


def _get_copy(basename: str, key: str, default: str = "") -> str:
    """Unified copy lookup: tries ``content/<basename>.md`` first, then ``assets/<basename>.json``。"""
    assert isinstance(basename, str) and basename, "basename must be non-empty str"
    assert isinstance(key, str) and key, "key must be non-empty str"

    fm = _load_md_frontmatter(f"{basename}.md")
    if key in fm:
        return fm[key]
    data = _load_text_json(f"{basename}.json")
    val = data.get(key)
    if isinstance(val, str) and val:
        return val
    return default


# --------------------------------------------------------------------------- #
# 扁平 key-value 查找（对外常用）                                               #
# --------------------------------------------------------------------------- #


def get_figure_title(key: str, default: str = "") -> str:
    """Figure title (md → json)。"""
    return _get_copy("figures_titles", key, default)


def get_figure_hint(key: str, default: str = "") -> str:
    """Figure hint / guidance text (md → json)。"""
    return _get_copy("figures_hints", key, default)


def get_topbar_label(key: str, default: str = "") -> str:
    """Topbar / sidebar / main-panel label text。

    历史签名保留；文案源从 ``topbar_labels.md`` 迁移至**全站统一字典**
    ``all_labels.md``，覆盖顶栏、Tab、主栏概览卡标题、Modal、侧栏按钮等
    所有静态字符串。为降低迁移成本仍保留 ``topbar_labels.md`` 作为回退。

    加载顺序：``all_labels.md`` → ``topbar_labels.md`` →
    ``assets/topbar_labels.json`` → ``default``。
    """
    fm = _load_md_frontmatter("all_labels.md")
    if key in fm:
        return fm[key]
    # 向后兼容：旧版 topbar_labels.md 或 json
    return _get_copy("topbar_labels", key, default)


def get_app_label(key: str, default: str = "") -> str:
    """``get_topbar_label`` 的语义别名 —— 推荐用于**非顶栏**的静态文案调用点。

    新代码访问 Modal、主栏概览卡、侧栏按钮等 ``all_labels.md`` 键时使用本名，
    阅读起来比「``get_topbar_label`` 取 Modal 文字」更诚实。
    """
    return get_topbar_label(key, default)


def _get_sidebar_left_merged(key: str, legacy_json_basename: str, default: str) -> str:
    """Lookup a sidebar-left copy key from the merged ``sidebar_left.md``.

    与历史两份文件（``sidebar_left_titles.md`` / ``sidebar_left_labels.md``）相比，
    层级合并后键仍保持扁平；本 helper 在合并文件未命中时回退到**该 getter 专属**
    的旧 JSON，保持 ``get_sidebar_left_title`` / ``get_sidebar_left_label`` 的
    外部语义与返回值不变。
    """
    fm = _load_md_frontmatter("sidebar_left/sidebar_left.md")
    if key in fm:
        return fm[key]
    data = _load_text_json(f"{legacy_json_basename}.json")
    val = data.get(key)
    if isinstance(val, str) and val:
        return val
    return default


def get_sidebar_left_title(key: str, default: str = "") -> str:
    """Sidebar left block title (merged md → legacy json)。

    内部来源已从 ``sidebar_left_titles.md`` 迁移至合并文件 ``sidebar_left.md``；
    外部签名、返回值、JSON fallback 行为均保持不变。
    """
    return _get_sidebar_left_merged(key, "sidebar_left_titles", default)


def get_sidebar_left_label(key: str, default: str = "") -> str:
    """Sidebar left auxiliary label (merged md → legacy json)。

    内部来源已从 ``sidebar_left_labels.md`` 迁移至合并文件 ``sidebar_left.md``；
    外部签名、返回值、JSON fallback 行为均保持不变。
    """
    return _get_sidebar_left_merged(key, "sidebar_left_labels", default)


def get_param_explanation(key: str, default: str = "") -> str:
    """Parameter explanation (md → json)。"""
    return _get_copy("sidebar_left/sidebar_left_params_explanations", key, default)


def get_kronos_hint(key: str, default: str = "") -> str:
    """Kronos hint text (md → json)。"""
    return _get_copy("kronos_hints", key, default)


def get_status_message(key: str, default: str = "") -> str:
    """Status / error / idle message (md → json)。"""
    return _get_copy("status_messages", key, default)


# --------------------------------------------------------------------------- #
# 嵌套结构查找（当扁平 kv 不够用时）                                             #
# --------------------------------------------------------------------------- #


def get_phase_intro(phase: str) -> Dict[str, Any]:
    """Load phase intro: title + body template。"""
    md_name = f"P{phase}_intro.md"
    fm = _load_md_frontmatter(md_name)
    body_md = get_md_text(md_name, "")
    if fm or body_md:
        return {
            "title": fm.get("title", fm.get("header", "")),
            "body": body_md,
            **{k: v for k, v in fm.items() if k not in ("title", "header")},
        }
    return _load_text_json(f"P{phase}_intro.json")


def get_project_intro() -> Dict[str, Any]:
    """Return project intro dict with title, overview, and phases (md → json)。"""
    fm = _load_md_frontmatter("project_intro.md")
    if fm:
        phases = {
            k[len("phase_"):]: fm[k]
            for k in fm
            if k.startswith("phase_")
        }
        return {
            "title": fm.get("title", ""),
            "overview": fm.get("overview", get_md_text("project_intro.md", "")),
            "phases": phases or fm.get("phases_raw", {}),
        }
    return _load_text_json("project_intro.json")


def get_defense_intro() -> Dict[str, Any]:
    """Return defense intro dict with level descriptions (md → json)。

    MD format: frontmatter keys ``level{0,1,2}_title`` / ``level{0,1,2}_pretext`` /
    ``level{0,1,2}_item_N``。
    """
    fm = _load_md_frontmatter("topbar/defense_intro.md")
    if fm:
        out: Dict[str, Any] = {}
        for lvl in ("level0", "level1", "level2"):
            spec: Dict[str, Any] = {
                "title": fm.get(f"{lvl}_title", ""),
                "pretext": fm.get(f"{lvl}_pretext", ""),
                "items": [
                    fm[k]
                    for k in sorted(fm.keys())
                    if k.startswith(f"{lvl}_item_") and fm[k]
                ],
            }
            out[lvl] = spec
        return out
    return _load_text_json("defense_intro.json")
