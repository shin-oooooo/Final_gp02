"""``md_sync`` —— Markdown 模板 ↔ 快照数据同步 CLI（Feedback R3.2）。

设计动机
========
研究模式下 ``content-{LANG}/Res-templates/Fig*.md`` 是事实模板，含
``{credibility}`` 等占位符；运行时由 ``render.explain._loaders._substitute_md``
逐个替换。但用户需要一份**离线、定值的 Markdown 快照**用于：

* GitHub README / 论文附件直接渲染（不暴露占位符）；
* 跨电脑、不跑 Dash app 时也能查看最近一次实验的实际数值。

为避免「直接覆写模板 → 占位符丢失」死循环（用户原始痛点），采用
**Option A：模板分离**：

* ``content-{LANG}/Res-templates/`` —— 模板（保留 ``{key}`` 占位）；
  **运行时唯一事实源**。
* ``content-{LANG}/Res/`` —— 由本 CLI ``--write-md`` 生成的定值快照；
  **不被运行时读取**，仅用于离线分发。

CLI 用法
========
::

    # 全量重建：用 dash_app/data.json 渲染所有 Res-templates 模板 → Res/
    python -m dash_app.utilities.md_sync --write-md

    # 指定数据源 / 指定语言子集
    python -m dash_app.utilities.md_sync --write-md --data path/to/snap.json --lang chn
    python -m dash_app.utilities.md_sync --write-md --lang both

    # 单文件预览（不写入 Res/）：渲染指定模板 → stdout / --out
    python -m dash_app.utilities.md_sync --read-md content-CHN/Res-templates/FigX.4-Res.md
    python -m dash_app.utilities.md_sync --read-md X.md --out filled.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# 路径解析                                                                     #
# --------------------------------------------------------------------------- #


def _dash_app_root() -> Path:
    """返回 ``dash_app/`` 目录（本文件的祖父目录）。"""
    return Path(__file__).resolve().parent.parent


def _content_root(lang: str) -> Path:
    """``content-CHN`` / ``content-ENG``。"""
    suffix = "CHN" if (lang or "chn").lower() == "chn" else "ENG"
    return _dash_app_root() / f"content-{suffix}"


def _templates_dir(lang: str) -> Path:
    return _content_root(lang) / "Res-templates"


def _snapshot_dir(lang: str) -> Path:
    return _content_root(lang) / "Res"


# --------------------------------------------------------------------------- #
# 占位符词典构造（vm dict）                                                     #
# --------------------------------------------------------------------------- #


def _snap_components(snap_json: Dict[str, Any]) -> Tuple[Any, Dict[str, Any], Dict[str, Any], List[str]]:
    """从 snap 解出 ``(pol, p2, meta, symbols)``，与运行时 state 构造保持一致。"""
    from research.schemas import DefensePolicyConfig

    pol = DefensePolicyConfig()
    p0 = (snap_json.get("phase0") or {}) if isinstance(snap_json, dict) else {}
    p2 = (snap_json.get("phase2") or {}) if isinstance(snap_json, dict) else {}
    meta = (p0.get("meta") or {}) if isinstance(p0, dict) else {}
    symbols: List[str] = []
    for key in ("tech_symbols", "hedge_symbols", "safe_symbols"):
        for s in (meta.get(key) or []) if isinstance(meta, dict) else []:
            if isinstance(s, str) and s and s not in symbols:
                symbols.append(s)
    return (pol,
            p2 if isinstance(p2, dict) else {},
            meta if isinstance(meta, dict) else {},
            symbols)


def _build_vm_from_snap(snap_json: Dict[str, Any]) -> Dict[str, Any]:
    """构造 *基础* 占位符字典（merge_base_vm 的输出）。

    用于非 FigX/Fig4 类模板（Fig0.x/Fig1.x/Fig2.x/Fig3.x、methodology…）。
    FigX/Fig4 类使用 :func:`_render_via_dispatch`，其会调用 per-figure builder。
    """
    from dash_app.render.explain._formatters import merge_base_vm

    pol, p2, meta, symbols = _snap_components(snap_json)
    return merge_base_vm(
        ui_mode="research",
        snap_json=snap_json,
        pol=pol,
        p2=p2,
        meta=meta,
        symbols=symbols,
    )


def _substitute(template: str, vm: Dict[str, Any]) -> str:
    """``{key}`` → ``vm[key]``；长 key 优先以防前缀冲突。

    与 ``render/explain/_loaders.py::_substitute_md`` 行为一致；这里复制一份是
    为了让本 CLI 在没装齐 Dash 依赖时也能跑（``_substitute_md`` 模块级导入太重）。
    """
    out = template
    for k in sorted(vm.keys(), key=len, reverse=True):
        key = "{" + k + "}"
        if key in out:
            out = out.replace(key, str(vm[k]))
    return out


# Dispatch table：filename stem → callable that returns rendered MD.
# 使用 lazy lookup 避免 import 时即触发整链路的 Dash 加载。
def _render_via_dispatch(
    filename: str,
    snap_json: Dict[str, Any],
    base_vm: Dict[str, Any],
    template: str,
) -> str:
    """对 FigX.{1..6}-Res.md / Fig4.{1,2}-Res.md 调用 per-figure builder；其余返回
    基础 vm 渲染结果。这样 ``--write-md`` 输出与 Dash app 内**完全一致**。"""
    name = filename
    pol, p2, meta, symbols = _snap_components(snap_json)
    json_path = ""

    try:
        if name == "FigX.1-Res.md":
            from dash_app.render.explain.sidebar_right.figx1 import build_figx1_explain_body
            return build_figx1_explain_body("research", snap_json, pol, p2, meta, symbols, json_path)
        if name == "FigX.2-Res.md":
            from dash_app.render.explain.sidebar_right.figx2 import build_figx2_explain_body
            return build_figx2_explain_body("research", snap_json, pol, p2, meta, symbols, json_path)
        if name == "FigX.3-Res.md":
            from dash_app.render.explain.sidebar_right.figx3 import build_figx3_explain_body
            return build_figx3_explain_body("research", snap_json, pol, p2, meta, symbols, json_path)
        if name == "FigX.4-Res.md":
            from dash_app.render.explain.sidebar_right.figx4 import build_figx4_explain_body
            return build_figx4_explain_body("research", snap_json, pol, p2, meta, symbols, json_path)
        if name == "FigX.5-Res.md":
            from dash_app.render.explain.sidebar_right.figx5 import build_figx5_explain_body
            return build_figx5_explain_body("research", snap_json, pol, p2, meta, symbols, json_path)
        if name == "FigX.6-Res.md":
            from dash_app.render.explain.sidebar_right.figx6 import build_figx6_explain_body
            return build_figx6_explain_body("research", snap_json, pol, p2, meta, symbols, json_path)
        if name == "Fig4.1-Res.md":
            from dash_app.render.explain.main_p4.fig41 import build_fig41_explain_body
            return build_fig41_explain_body("research", snap_json, pol, p2, meta, symbols)
        if name == "Fig4.2-Res.md":
            from dash_app.render.explain.main_p4.fig42 import build_fig42_explain_body
            return build_fig42_explain_body("research", snap_json, pol, p2, meta, symbols)
    except Exception as exc:  # noqa: BLE001 — CLI 兜底，避免单文件失败拖垮全量渲染
        print(f"  ! per-figure dispatch FAILED for {name} ({type(exc).__name__}: {exc})\n"
              f"    → fallback to base-vm substitution.", file=sys.stderr)

    # 默认路径：基础 vm 替换。
    return _substitute(template, base_vm)


# --------------------------------------------------------------------------- #
# 文件 I/O                                                                     #
# --------------------------------------------------------------------------- #


def _load_snapshot(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"snapshot data.json not found at: {path}\n"
            "提示：请先在 Dash app 内点 Save Run 生成 data.json，或用 --data 指定路径。"
        )
    with path.open("r", encoding="utf-8") as f:
        snap = json.load(f)
    if not isinstance(snap, dict):
        raise ValueError(f"snapshot must be JSON object, got {type(snap).__name__}")
    return snap


def _iter_template_files(lang: str) -> Iterable[Path]:
    root = _templates_dir(lang)
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob("*.md") if p.is_file())


def _write_out(dst: Path, content: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="\n") as f:
        f.write(content)


# --------------------------------------------------------------------------- #
# 命令实现                                                                     #
# --------------------------------------------------------------------------- #


def _set_runtime_lang(lang: str) -> None:
    """切换 ``services.copy`` 当前语言（让 per-figure builder 走对应语言的模板）。"""
    try:
        from dash_app.services.copy import set_language
        set_language(lang)
    except Exception:
        pass  # 兼容缺失分支；非致命


def cmd_write_md(snap_path: Path, langs: List[str]) -> int:
    snap = _load_snapshot(snap_path)
    base_vm = _build_vm_from_snap(snap)
    total_in = total_out = 0
    for lang in langs:
        src_dir = _templates_dir(lang)
        if not src_dir.is_dir():
            print(f"[skip] templates dir not found for lang={lang}: {src_dir}",
                  file=sys.stderr)
            continue
        dst_dir = _snapshot_dir(lang)
        templates = list(_iter_template_files(lang))
        total_in += len(templates)
        if not templates:
            print(f"[skip] no .md templates under {src_dir}", file=sys.stderr)
            continue
        print(f"[{lang}] {len(templates)} template(s) -> {dst_dir}")
        _set_runtime_lang(lang)
        for src in templates:
            try:
                tpl = src.read_text(encoding="utf-8")
            except OSError as exc:
                print(f"  ! read failed: {src.name} ({exc})", file=sys.stderr)
                continue
            filled = _render_via_dispatch(src.name, snap, base_vm, tpl)
            dst = dst_dir / src.name
            _write_out(dst, filled)
            total_out += 1
            print(f"  + {src.name}")
    print(f"\nDone. {total_out}/{total_in} files rendered.")
    return 0 if total_out == total_in and total_in > 0 else 1


def cmd_read_md(template_path: Path, snap_path: Path, out_path: Optional[Path]) -> int:
    if not template_path.is_file():
        print(f"template not found: {template_path}", file=sys.stderr)
        return 2
    snap = _load_snapshot(snap_path)
    base_vm = _build_vm_from_snap(snap)
    # 自动推断语言：路径含 ``content-ENG`` → eng；其余按 chn。
    lang = "eng" if "content-ENG" in template_path.as_posix() else "chn"
    _set_runtime_lang(lang)
    tpl = template_path.read_text(encoding="utf-8")
    filled = _render_via_dispatch(template_path.name, snap, base_vm, tpl)
    if out_path is None:
        sys.stdout.write(filled)
        if not filled.endswith("\n"):
            sys.stdout.write("\n")
    else:
        _write_out(out_path, filled)
        print(f"wrote {len(filled)} chars -> {out_path}")
    return 0


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="md_sync",
        description=(
            "同步 Markdown 模板（Res-templates/）与快照数据（data.json）。\n"
            "Option A：模板分离 — Res-templates/ 是事实源，Res/ 是 --write-md 的产物。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write-md", action="store_true",
        help="渲染所有 Res-templates/*.md → Res/*.md（覆盖产物快照）。",
    )
    mode.add_argument(
        "--read-md", metavar="TEMPLATE",
        help="渲染单个模板文件并输出到 stdout 或 --out（不写入 Res/）。",
    )
    parser.add_argument(
        "--data", metavar="PATH", default=None,
        help="data.json 路径；默认 dash_app/data.json。",
    )
    parser.add_argument(
        "--lang", choices=("chn", "eng", "both"), default="both",
        help="处理的语言；默认 both。",
    )
    parser.add_argument(
        "--out", metavar="PATH", default=None,
        help="（仅 --read-md）输出文件路径；省略则打印到 stdout。",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    snap_path = Path(args.data) if args.data else (_dash_app_root() / "data.json")
    langs: List[str] = ["chn", "eng"] if args.lang == "both" else [args.lang]

    if args.write_md:
        return cmd_write_md(snap_path, langs)
    out_path = Path(args.out) if args.out else None
    tpl_path = Path(args.read_md)
    return cmd_read_md(tpl_path, snap_path, out_path)


if __name__ == "__main__":
    sys.exit(main())
