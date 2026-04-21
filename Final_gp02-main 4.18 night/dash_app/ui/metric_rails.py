"""Metric rails for FigX.2 (structural entropy) and FigX.4 (credibility).

DOM structure — flat & deterministic:

  outer row           display:flex, width:100%, overflow:visible
  ├── left label col  fixed 130px, flex:0 0 130px
  └── track+anno col  flex:1 1 0, min-width:0, position:relative
        ├── rail      display:flex, width:100%, height:30px
        │             (**segments are DIRECT flex children**, not nested)
        │     ├── _seg  flex: 0 0 {p:.4f}%  ← **explicit flex-basis %**
        │     ├── _seg
        │     └── _seg (credibility only)
        ├── overlay_nodes (absolute: white + red vlines + caret)
        └── anno_node (tau labels)

Width invariant
---------------
Sum of segment flex-basis % values **equals 100.0000%** on both rails. The
percentages are derived from the **live** policy thresholds (τ_H1 / τ_L2 /
τ_L1) so they update immediately when the user moves a parameter slider.

To debug a misalignment, set ``DEBUG_RENDER=1`` and check server log for::

    [metric_rails] entropy p_tau=50.0000 yellow=50.0000 green=50.0000
    [metric_rails] credibility p_l2=45.0 p_l1=70.0 w2=45 w1=25 w0=30

Sum must equal 100 ± rounding.
"""

from __future__ import annotations

import logging
import os
from typing import List

from dash import html

logger = logging.getLogger("dash_app.ui.metric_rails")
_TRACE = os.environ.get("DEBUG_RENDER", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[metric_rails] {msg % args}" if args else f"[metric_rails] {msg}")
        except Exception:
            pass


_FILL = {
    "red":    "defense-rgy-fill-danger",
    "yellow": "defense-rgy-fill-warn",
    "green":  "defense-rgy-fill-success",
}

_RAIL_H = 30
_LEFT_W = 130
_CARET_H = 11


def _clamp(x: float, lo: float, hi: float) -> float:
    assert lo <= hi, f"_clamp: lo={lo} > hi={hi}"
    return max(lo, min(hi, float(x)))


def _pct(v: float) -> str:
    """Format a percentage with enough precision to avoid rounding drift."""
    return f"{float(v):.4f}%"


def _vline(left: str, color: str, z: int = 9, hidden: bool = False) -> html.Div:
    """Thin 3px vertical line **spanning exactly the rail body**.

    ``top: _CARET_H`` (= 11px) aligns the vline with the rail's upper edge
    (the rail itself starts at ``paddingTop: 11px`` inside ``_track_col``).
    ``height: _RAIL_H`` makes it reach the rail's lower edge. Both white
    (τ markers) and red (value marker) vlines share identical geometry —
    **same ``top``, same ``height``, same ``width``** — so they visually
    look like twin lines on the same horizontal baseline.
    """
    return html.Div(style={
        "position": "absolute",
        "left": left,
        "top": f"{_CARET_H}px",
        "height": f"{_RAIL_H}px",
        "width": "3px",
        "transform": "translateX(-50%)",
        "background": color,
        "zIndex": z,
        "pointerEvents": "none",
        "display": "none" if hidden else "block",
    })


_NEON_CYAN = "#00e5ff"
_NEON_GLOW = (
    "0 0 2px #00e5ff, "
    "0 0 6px rgba(0,229,255,0.85), "
    "0 0 12px rgba(0,229,255,0.55)"
)


def _value_marker(left: str, hidden: bool = False) -> html.Div:
    """**Neon-industrial gem pin** value marker.

    Anatomy (painted, top → bottom)::

        ◇     10 px rotated square — flat neon cyan, **sharp corners**,
              **no inset highlight**, **no white border**; only outer
              multi-layer glow for the classic neon-tube look.
        ║     2.5 px rectangular tail — flat neon cyan, sharp corners,
              same glow.

    Design notes:
      * Colour ``#00e5ff`` (neon cyan) stands out against every rail
        segment (red / yellow / green) without blending in.
      * Multi-stop ``box-shadow`` (2 px tight halo + 6 px mid + 12 px
        soft) mimics a glowing neon tube against dark backgrounds.
      * No ``border-radius`` anywhere — pure industrial geometry.
      * Geometry (positions) unchanged from the previous marker so the
        horizontal alignment with ``val_left`` and the tau whitelines
        remains pixel-identical.
    """
    GEM_SIZE = 10
    TAIL_WIDTH = 2.5
    GEM_HALF = GEM_SIZE // 2

    tail_top = _CARET_H + GEM_HALF
    tail_height = _RAIL_H - GEM_HALF

    return html.Div(
        [
            html.Div(style={
                "position": "absolute",
                "left": "0",
                "top": f"{tail_top}px",
                "width": f"{TAIL_WIDTH}px",
                "height": f"{tail_height}px",
                "transform": "translateX(-50%)",
                "background": _NEON_CYAN,
                "borderRadius": "0",
                "boxShadow": _NEON_GLOW,
                "pointerEvents": "none",
            }),
            html.Div(style={
                "position": "absolute",
                "left": "0",
                "top": f"{_CARET_H}px",
                "width": f"{GEM_SIZE}px",
                "height": f"{GEM_SIZE}px",
                "transform": "translate(-50%, -50%) rotate(45deg)",
                "background": _NEON_CYAN,
                "borderRadius": "0",
                "border": "0",
                "boxShadow": _NEON_GLOW,
                "pointerEvents": "none",
            }),
        ],
        style={
            "position": "absolute",
            "left": left,
            "top": "0",
            "width": "0",
            "height": f"{_CARET_H + _RAIL_H}px",
            "zIndex": 12,
            "pointerEvents": "none",
            "display": "none" if hidden else "block",
        },
    )


def _caret(left: str, hidden: bool = False) -> html.Div:
    """Deprecated — kept for backward compatibility. Use :func:`_value_marker`.

    The old sharp red triangle is replaced by the gem pin above the rail.
    This stub delegates so any lingering callers keep working.
    """
    return _value_marker(left, hidden=hidden)


def _seg(label: str, fill_cls: str, width_pct: float) -> html.Div:
    """Colour bar segment with **explicit flex-basis in %**.

    ``flex: 0 0 {p}%`` sets grow=0 / shrink=0 / basis=percentage directly —
    this is unambiguous for every browser and independent of the ``width``
    shorthand. ``min-width: 0`` defuses flex's default intrinsic-size floor.
    """
    assert 0.0 <= width_pct <= 100.0, f"width_pct out of range: {width_pct}"
    p = float(width_pct)
    return html.Div(
        [html.Span(label, className="defense-zone-mid")],
        className=f"defense-rgy-seg {fill_cls}",
        style={
            "flexGrow": 0,
            "flexShrink": 0,
            "flexBasis": f"{p:.4f}%",
            "minWidth": "0",
            "height": f"{_RAIL_H}px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "boxSizing": "border-box",
            "overflow": "hidden",
        },
        **{"data-seg-width": f"{p:.4f}%"},
    )


def _rail_row(segments: List[html.Div]) -> html.Div:
    """Top-level rail: a flat flex row whose children are the segments.

    No nested inner flex container; no inner ``width: 100%``. Width invariant
    is enforced at the caller by making the segment widths sum to exactly
    100.0000%.
    """
    assert isinstance(segments, list) and segments, "segments must be non-empty list"
    return html.Div(
        segments,
        className="defense-neon-track",
        style={
            "display": "flex",
            "flexWrap": "nowrap",
            "width": "100%",
            "height": f"{_RAIL_H}px",
            "boxSizing": "border-box",
            "overflow": "hidden",
        },
    )


def _label_col(children: list) -> html.Div:
    return html.Div(children, style={
        "flex": f"0 0 {_LEFT_W}px",
        "width": f"{_LEFT_W}px",
        "paddingRight": "8px",
        "boxSizing": "border-box",
    })


def _track_col(rail_node: html.Div, overlay_nodes: list, anno_node: html.Div) -> html.Div:
    """Relative container; paddingTop reserves 11px for the caret inside the box."""
    return html.Div(
        [rail_node] + overlay_nodes + [anno_node],
        style={
            "flex": "1 1 auto",
            "minWidth": "0",
            "position": "relative",
            "paddingTop": f"{_CARET_H}px",
            "boxSizing": "border-box",
            "overflow": "visible",
        },
    )


# ── public API ───────────────────────────────────────────────────────────


def structural_entropy_rail(
    h_struct: float,
    tau_h1: float,
    *,
    show_marker: bool = True,
) -> html.Div:
    """FigX.2 — structural entropy colour bar (range 0.20–0.80).

    Segment split **live** reflects the ``tau_h1`` passed in (which comes from
    the live sidebar slider via ``state.tau_h1`` → ``build_sidebar_right``).

    Yellow width  = (tau_h1 − 0.20) / 0.60 × 100%
    Green  width  = 100% − yellow
    """
    vmin, vmax = 0.20, 0.80
    span = vmax - vmin
    th = _clamp(tau_h1, vmin, vmax)
    v = _clamp(h_struct, vmin, vmax)

    p_tau = 100.0 * (th - vmin) / span
    p_val = 100.0 * (v - vmin) / span

    yellow_pct = max(0.0, min(100.0, p_tau))
    green_pct = max(0.0, 100.0 - yellow_pct)
    _trace("entropy h=%.4f tau=%.4f → yellow=%.4f green=%.4f (sum=%.4f)",
           h_struct, tau_h1, yellow_pct, green_pct, yellow_pct + green_pct)

    title_col = "#66bb6a" if float(h_struct) >= float(th) else "#ffa726"

    rail_node = _rail_row([
        _seg("L1", _FILL["yellow"], yellow_pct),
        _seg("L0", _FILL["green"],  green_pct),
    ])

    tau_left = _pct(p_tau)
    val_left = _pct(p_val)
    overlay_nodes = [
        _vline(tau_left, "rgba(255,255,255,0.92)", z=10),
        _value_marker(val_left, hidden=not show_marker),
    ]

    anno_node = html.Div(
        [
            html.Span(f"{vmin:.2f}", className="defense-tau-axis-0"),
            html.Span(f"{vmax:.2f}", className="defense-tau-axis-1"),
            html.Div(
                [html.Div(f"{th:.2f}", className="defense-tau-anno-num"),
                 html.Div("T_H1", className="defense-tau-anno-var")],
                className="defense-tau-anno",
                style={"left": tau_left},
            ),
        ],
        className="defense-tau-anno-layer",
    )

    label_col = _label_col([
        html.Div("Structural Entropy", className="metric-rail-title",
                 style={"color": title_col, "marginTop": f"{_CARET_H}px"}),
        html.Div(f"{float(h_struct):.3f}", className="metric-rail-score"),
    ])

    return html.Div(
        [label_col, _track_col(rail_node, overlay_nodes, anno_node)],
        className="metric-rail metric-rail--entropy metric-rail-neon",
        style={
            "display": "flex",
            "width": "100%",
            "alignItems": "flex-start",
            "gap": "0px",
            "boxSizing": "border-box",
            "overflow": "visible",
        },
        **{"data-tau-h1": f"{float(tau_h1):.4f}", "data-h-struct": f"{float(h_struct):.4f}"},
    )


def credibility_rail(
    credibility: float,
    tau_l2: float,
    tau_l1: float,
    *,
    show_marker: bool = True,
) -> html.Div:
    """FigX.4 — credibility colour bar (range 0.0–1.0).

    Segment split **live** reflects ``tau_l2`` / ``tau_l1`` from the sidebar.

    Red   width = tau_l2 × 100%
    Yellow width = (tau_l1 − tau_l2) × 100%
    Green width  = (1 − tau_l1) × 100%
    """
    vmin, vmax = 0.0, 1.0
    tl2 = _clamp(tau_l2, vmin, vmax)
    tl1 = _clamp(tau_l1, vmin, vmax)
    if tl1 <= tl2:
        tl1 = min(1.0, tl2 + 0.01)
    v = _clamp(credibility, vmin, vmax)

    p_l2 = 100.0 * tl2
    p_l1 = 100.0 * tl1
    p_val = 100.0 * v

    w2_pct = max(0.0, min(100.0, p_l2))
    w1_pct = max(0.0, min(100.0 - w2_pct, p_l1 - p_l2))
    w0_pct = max(0.0, 100.0 - w2_pct - w1_pct)
    _trace("credibility c=%.4f tau_l2=%.4f tau_l1=%.4f → red=%.4f yellow=%.4f green=%.4f (sum=%.4f)",
           credibility, tau_l2, tau_l1, w2_pct, w1_pct, w0_pct,
           w2_pct + w1_pct + w0_pct)

    l2_left = _pct(p_l2 - 0.8) if abs(p_val - p_l2) <= 0.8 else _pct(p_l2)
    l1_left = _pct(p_l1 + 0.8) if abs(p_val - p_l1) <= 0.8 else _pct(p_l1)
    val_left = _pct(p_val)

    zone_col = (
        "#ef5350" if float(credibility) <= tl2
        else ("#ffa726" if float(credibility) <= tl1 else "#66bb6a")
    )

    rail_node = _rail_row([
        _seg("L2", _FILL["red"],    w2_pct),
        _seg("L1", _FILL["yellow"], w1_pct),
        _seg("L0", _FILL["green"],  w0_pct),
    ])

    overlay_nodes = [
        _vline(l2_left, "rgba(255,255,255,0.92)", z=10),
        _vline(l1_left, "rgba(255,255,255,0.92)", z=10),
        _value_marker(val_left, hidden=not show_marker),
    ]

    anno_node = html.Div(
        [
            html.Span("0", className="defense-tau-axis-0"),
            html.Span("1", className="defense-tau-axis-1"),
            html.Div(
                [html.Div(f"{tl2:.2f}", className="defense-tau-anno-num"),
                 html.Div("T_L2", className="defense-tau-anno-var")],
                className="defense-tau-anno", style={"left": _pct(p_l2)},
            ),
            html.Div(
                [html.Div(f"{tl1:.2f}", className="defense-tau-anno-num"),
                 html.Div("T_L1", className="defense-tau-anno-var")],
                className="defense-tau-anno", style={"left": _pct(p_l1)},
            ),
        ],
        className="defense-tau-anno-layer",
    )

    label_col = _label_col([
        html.Div("Credibility", className="metric-rail-title",
                 style={"color": zone_col, "marginTop": f"{_CARET_H}px"}),
        html.Div(f"{float(credibility):.3f}", className="metric-rail-score"),
    ])

    return html.Div(
        [label_col, _track_col(rail_node, overlay_nodes, anno_node)],
        className="metric-rail metric-rail--cred metric-rail-neon",
        style={
            "display": "flex",
            "width": "100%",
            "alignItems": "flex-start",
            "gap": "0px",
            "boxSizing": "border-box",
            "overflow": "visible",
        },
        **{
            "data-tau-l2": f"{float(tau_l2):.4f}",
            "data-tau-l1": f"{float(tau_l1):.4f}",
            "data-cred":   f"{float(credibility):.4f}",
        },
    )
