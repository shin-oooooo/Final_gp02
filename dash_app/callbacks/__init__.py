"""Callbacks package."""

from dash_app.callbacks.sidebar_layout import register_sidebar_layout_callbacks
from dash_app.callbacks.defense_rails import register_defense_rails_callbacks
from dash_app.callbacks.sidebar2_visibility import register_sidebar2_visibility_callbacks
from dash_app.callbacks.app_shell import register_app_shell_callbacks
from dash_app.callbacks.p0_assets import register_p0_assets_callbacks
from dash_app.callbacks.p2_symbol import register_p2_symbol_callbacks
from dash_app.callbacks.research_panels import register_research_panels_callbacks
from dash_app.callbacks.clientside import register_clientside_callbacks
from dash_app.callbacks.dashboard_pipeline import register_dashboard_pipeline_callbacks

__all__ = [
    "register_sidebar_layout_callbacks",
    "register_defense_rails_callbacks",
    "register_sidebar2_visibility_callbacks",
    "register_app_shell_callbacks",
    "register_p0_assets_callbacks",
    "register_p2_symbol_callbacks",
    "register_research_panels_callbacks",
    "register_clientside_callbacks",
    "register_dashboard_pipeline_callbacks",
]
