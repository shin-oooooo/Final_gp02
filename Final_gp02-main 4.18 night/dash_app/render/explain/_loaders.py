"""FigX.*.md / Fig4.*.md 模板加载 + 占位符替换 + Defense-Tag 段解析。

加载根目录：``dash_app/content-{CHN,ENG}/{Inv,Res-templates}/``：

* ``mode == "research"`` → ``content-{LANG}/Res-templates/Fig{...}-Res.md``
  （**研究模式以 ``Res-templates`` 为唯一事实源**；``Res/`` 为
  ``scripts/md_sync.py --write-md`` 的快照产物，不被运行时读取。）
* 否则 → ``content-{LANG}/Inv/Fig{...}-Inv.md``

不再跨模式回退（旧版 ``-Res`` ↔ ``-Inv`` 互救机制已移除），以便按任务 2 的约定：
Invest 模式下若 ``Fig{...}-Inv.md`` 不存在，**严格显示**「目前未在仓库根目录
找到 Fig{...}-Inv.md。」；Research 模式严格保留 ``-Res.md`` 作为唯一事实来源。

英文文件夹 ``content-ENG/`` 缺失时会回退到 ``content-CHN/``（渐进式翻译友好）。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


# 缓存键：(prefix, fig, suffix, lang)。语言切换不共享缓存；prefix（FigX/Fig4/Fig0…）
# 必须出现在键里，否则 ``load_main_template(1, 1)`` 与 ``load_main_template(2, 1)``
# 会因为 sub 都为 "1" 而误命中同一个 entry。
_FIGX_TEMPLATE_CACHE: Dict[Tuple[str, str, str, str], str] = {}
_FIG4_TEMPLATE_CACHE: Dict[Tuple[str, str, str, str], str] = {}

# defense_reasons.md 解析缓存：lang → {fig_id: {branch_key: (body, severity)}}
_DEFENSE_REASONS_CACHE: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {}

# Defense-Tag 分支匹配：同时适配 per-FigX 与 defense_reasons.md 两种写法。
_DEFENSE_BLOCK_RE = re.compile(
    r'\*\*(If|Else If|Else)\*\*(.*?)\n'
    r'((?:[ \t]*`[^`]+`[ \t]*\n?)+)',
    re.DOTALL | re.IGNORECASE,
)


def _dash_app_root() -> Path:
    """返回 ``dash_app/`` 目录（`_loaders.py` 的祖父目录再上一层）。"""
    return Path(__file__).resolve().parents[2]


def _lang_content_root(lang: str) -> Path:
    """返回语言对应的 content 根目录。"""
    suffix = "CHN" if (lang or "chn").lower() == "chn" else "ENG"
    return _dash_app_root() / f"content-{suffix}"


def _current_lang() -> str:
    """读取 services/copy 中的当前语言（避免 import 时循环依赖）。"""
    try:
        from dash_app.services.copy import get_language

        return get_language()
    except Exception:
        return "chn"


def _substitute_md(template: str, vm: Dict[str, Any]) -> str:
    """``{key}`` → ``vm[key]`` 逐个替换。长 key 优先以防前缀冲突。"""
    out = template
    for k in sorted(vm.keys(), key=len, reverse=True):
        key = "{" + k + "}"
        if key in out:
            out = out.replace(key, str(vm[k]))
    return out


def _load_mode_template(
    cache: Dict[Tuple[str, str, str, str], str],
    fig: str,
    ui_mode: Optional[str],
    prefix: str,
) -> str:
    """加载 ``content-{LANG}/{Inv|Res}/{prefix}.{fig}{-Inv|-Res}.md``。

    * 按 ui_mode 决定 suffix；**不**跨模式回退（Invest 不会借 Res、反之亦然）；
    * 当前语言缺失时回退到 CHN；
    * 两者都缺失时返回占位提示 ``*目前未在仓库根目录找到 `Fig{...}`。*``，
      与任务 2 的用户可见文案严格一致。
    """
    m = (ui_mode or "invest").lower()
    suffix = "-Res.md" if m == "research" else "-Inv.md"
    # Research 模式从 ``Res-templates/`` 读取（包含占位符 + 模板文本）；
    # ``Res/`` 是 ``--write-md`` 输出的「定值快照」，仅用于离线分发。
    subdir = "Res-templates" if suffix == "-Res.md" else "Inv"
    lang = _current_lang()

    cache_key = (prefix, fig, suffix, lang)
    if cache_key in cache:
        return cache[cache_key]

    name = f"{prefix}.{fig}{suffix}"

    # 搜索顺序：当前语言 → （若为 eng）回退到 chn。
    search_langs = [lang]
    if lang == "eng":
        search_langs.append("chn")

    for lg in search_langs:
        p = _lang_content_root(lg) / subdir / name
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            cache[cache_key] = text
            return text

    # 均缺失：保持与用户可见文案严格一致（任务 2 约定）。
    msg = f"*目前未在仓库根目录找到 `{name}`。*\n"
    cache[cache_key] = msg
    return msg


def load_figx_template(fig: str, ui_mode: Optional[str]) -> str:
    """加载 ``content-{LANG}/{Inv|Res}/FigX.<fig>{-Inv,-Res}.md``。"""
    return _load_mode_template(_FIGX_TEMPLATE_CACHE, fig, ui_mode, "FigX")


def load_fig4_template(fig: str, ui_mode: Optional[str]) -> str:
    """加载 ``content-{LANG}/{Inv|Res}/Fig4.<fig>{-Inv,-Res}.md``。"""
    return _load_mode_template(_FIG4_TEMPLATE_CACHE, fig, ui_mode, "Fig4")


# Fig{phase}.{sub} 通用加载缓存（P0/P1/P2/P3 主栏讲解卡共用；按 prefix=Fig{phase} 区分）。
_FIG_MAIN_TEMPLATE_CACHE: Dict[Tuple[str, str, str, str], str] = {}


def load_main_template(phase: int | str, sub: int | str, ui_mode: Optional[str]) -> str:
    """加载 ``content-{LANG}/{Inv|Res-templates}/Fig{phase}.{sub}{-Inv,-Res}.md``。

    与 :func:`load_fig4_template` / :func:`load_figx_template` 同源；
    主栏 P0/P1/P2/P3 的讲解卡用本接口，与侧栏 FigX/主栏 P4 共享同一约定，
    避免再分散到 ``content/{basename}-Inv.md`` 这一旧入口。
    """
    p = int(str(phase).strip())
    s = int(str(sub).strip())
    # ``_load_mode_template`` 的命名格式为 ``f"{prefix}.{fig}{suffix}"``；
    # 把整个 ``Fig{phase}`` 当作 prefix、``{sub}`` 当作 fig，最终落到
    # ``Fig{phase}.{sub}-{Inv|Res}.md``，与 Inv/Res-templates 现有命名严格对齐。
    return _load_mode_template(_FIG_MAIN_TEMPLATE_CACHE, str(s), ui_mode, f"Fig{p}")


def _parse_block_content(content: str) -> Tuple[str, str]:
    """把一段由反引号行组成的分支内容解析为 ``(body, severity)``。"""
    body_lines: list[str] = []
    severity = "success"
    for line in content.strip().splitlines():
        line = line.strip()
        m_body = re.match(r'^`(.+)`$', line)
        if not m_body:
            continue
        inner = m_body.group(1).strip()
        if inner.startswith("severity:"):
            severity = inner.split(":", 1)[1].strip()
        else:
            body_lines.append(inner)
    return "\n".join(body_lines), severity


def _parse_defense_section(section: str) -> Dict[str, Tuple[str, str]]:
    """从一段包含 If/Else If/Else 分支的 Markdown 文本里，解出 ``{branch_key: (body, sev)}``。"""
    branches: Dict[str, Tuple[str, str]] = {}
    elif_counter = 0
    for keyword, _, content in _DEFENSE_BLOCK_RE.findall(section):
        key = keyword.lower().replace(" ", "_")
        if key == "else_if":
            key = f"elif_{elif_counter}"
            elif_counter += 1
        if key not in branches:
            branches[key] = _parse_block_content(content)
    return branches


def _fig_id_for_reasons(fig_num: str) -> str:
    """把 ``fig_num``（"1" / "P0-Agg" / "4.1"）映射为 defense_reasons.md 的 ### 标题 id。"""
    s = str(fig_num).strip()
    if s.upper() == "P0-AGG":
        return "P0-Agg"
    if "." in s:
        return f"Fig{s}"
    return f"FigX.{s}"


def _parse_defense_reasons(lang: str) -> Dict[str, Dict[str, Tuple[str, str]]]:
    """解析 ``content-{LANG}/defense_reasons.md``，按 FigX 聚合分支。缓存按语言键存。

    文档结构：顶层 ``## Level N`` 分区，下有 ``### FigX.<n> — 标题`` 小节；
    每个小节里是一个 If / Else If / Else 块（与 per-FigX 模板同格式）。
    同一个 FigX 会在多个 Level 小节出现（一次一种分支），这里按首次出现收敛。
    """
    if lang in _DEFENSE_REASONS_CACHE:
        return _DEFENSE_REASONS_CACHE[lang]
    # 历史上文件位于 ``content-{LANG}/defense_reasons.md``；自从顶栏文案归档重构后
    # 实际存放位置是 ``content-{LANG}/topbar/defense_reasons.md``。两路径都探测，
    # 以兼容旧布局和保证 FigX.2/X.4（无 per-FigX Defense-Tag 段的图）能读到总表。
    candidates = [
        _lang_content_root(lang) / "topbar" / "defense_reasons.md",
        _lang_content_root(lang) / "defense_reasons.md",
    ]
    if lang == "eng":
        candidates.extend([
            _lang_content_root("chn") / "topbar" / "defense_reasons.md",
            _lang_content_root("chn") / "defense_reasons.md",
        ])
    path: Optional[Path] = next((p for p in candidates if p.is_file()), None)
    if path is None:
        _DEFENSE_REASONS_CACHE[lang] = {}
        return {}

    text = path.read_text(encoding="utf-8")
    chunks = re.split(r'(?m)^###\s+', text)  # chunks[0] 为 "### " 之前的前言
    heading_re = re.compile(r'^(FigX\.\d+|Fig\d+\.\d+|P0-Agg)\b')

    result: Dict[str, Dict[str, Tuple[str, str]]] = {}
    elif_counters: Dict[str, int] = {}
    for chunk in chunks[1:]:
        nl = chunk.find('\n')
        if nl == -1:
            continue
        heading = chunk[:nl].strip()
        body = chunk[nl + 1:]
        m_id = heading_re.match(heading)
        if not m_id:
            continue
        fig_id = m_id.group(1)
        m_block = _DEFENSE_BLOCK_RE.search(body)
        if not m_block:
            continue
        keyword, _, content = m_block.groups()
        key = keyword.lower().replace(" ", "_")
        if key == "else_if":
            counter = elif_counters.get(fig_id, 0)
            key = f"elif_{counter}"
            elif_counters[fig_id] = counter + 1
        fig_branches = result.setdefault(fig_id, {})
        if key not in fig_branches:
            fig_branches[key] = _parse_block_content(content)
    _DEFENSE_REASONS_CACHE[lang] = result
    return result


def load_defense_tag_text(
    fig_num: str,
    ui_mode: Optional[str],
    vm: Dict[str, Any],
    branch_key: str = "if",
) -> Tuple[str, str]:
    """解析 Defense-Tag 分支并返回 ``(body, severity)``。

    Args:
        fig_num: ``"1"``/``"2"``/.../``"P0-Agg"``。
        ui_mode: ``"invest"``/``"research"``。
        vm: 占位符字典。
        branch_key: ``"if"`` / ``"elif_0"`` / ``"elif_1"`` / ... / ``"else"``。

    查找顺序（与 ``defense_reasons.md`` 自述一致）：
        1. ``ui_mode`` 对应的 per-FigX 模板的 ``## Defense-Tag`` 段；
        2. 另一模式（Inv↔Res）的 per-FigX 模板（Inv 简介版通常不含此段时救援）；
        3. 中央总表 ``content-{LANG}/defense_reasons.md`` —— 作为最终回落源，
           也是唯一把所有 Defense-Tag 文案集中起来的事实库，
           保证 per-FigX 模板缺段时仍能得到一致文案。
    """
    def _extract_section(text: str) -> Optional[str]:
        idx = text.find("## Defense-Tag")
        return text[idx:] if idx != -1 else None

    tpl = load_figx_template(fig_num, ui_mode)
    text = _substitute_md(tpl, vm)
    section = _extract_section(text)
    if section is None:
        alt_mode = "research" if (ui_mode or "invest").lower() != "research" else "invest"
        tpl_alt = load_figx_template(fig_num, alt_mode)
        if tpl_alt:
            section = _extract_section(_substitute_md(tpl_alt, vm))

    if section is not None:
        branches = _parse_defense_section(section)
        if branches:
            return branches.get(branch_key, branches.get("else", ("分支未匹配", "success")))

    # 回落到 defense_reasons.md 中央总表。
    reasons = _parse_defense_reasons(_current_lang())
    fig_branches = reasons.get(_fig_id_for_reasons(fig_num)) or {}
    if not fig_branches:
        return "Defense-Tag 段落未找到", "success"
    body, severity = fig_branches.get(
        branch_key,
        fig_branches.get("else", ("分支未匹配", "success")),
    )
    return _substitute_md(body, vm), severity
