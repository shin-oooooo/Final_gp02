<!--
  "Project overview" card body inside the left sidebar's "Research project overview" tab.
  Loaded via `dash_app/app.py::_serve_layout` and
  `dash_app/callbacks/app_shell.py::_lang_rebuild_children`
  (`services.copy.get_md_text("project_executive_summary.md", …)`), then injected
  through `ui.layout.build_lang_aware_children` into the `_overview_card("project", …)`.
  The card is expanded by default (is_open_default=True) and stays pinned / open
  across main-tab switches.

  If this file is left empty (or contains only comments), the UI falls back to
  the `all_labels.md::project_intro_fallback` prompt asking the author to fill it in.
-->

## Project executive summary

TODO: fill in the research project's executive summary. Suggested sections:

- Research goal & motivation
- Core methodology (three-stage defense / Adaptive Optimizer / dual-track Monte Carlo, etc.)
- Key findings and defense-effectiveness verdict
- Data scope, time windows and asset universe overview
