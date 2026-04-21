"""Defense-rails (tau) callbacks."""
from dash import Input, Output, ctx

from dash_app.ui.sidebar_left import (
    _defense_rgy_rail,
    _make_tau_ac1_rail,
    _make_tau_h1_rail,
    _make_tau_vol_rail,
    _unpack_tau_l2_l1,
)


def register_defense_rails_callbacks(app):
    @app.callback(
        Output("defense-rgy-rail-main", "children"),
        Input("sl-tau-l2-l1", "value"),
    )
    def _sync_defense_rails(tpair):
        a, b = _unpack_tau_l2_l1(tpair)
        return (_defense_rgy_rail(a, b),)

    @app.callback(
        Output("sl-tau-l2-l1", "value"),
        Output("inp-tau-l2", "value"),
        Output("inp-tau-l1", "value"),
        Input("sl-tau-l2-l1", "value"),
        Input("inp-tau-l2", "value"),
        Input("inp-tau-l1", "value"),
        prevent_initial_call=True,
    )
    def _sync_tau_pair_controls(tpair, l2_in, l1_in):
        trig = ctx.triggered_id
        if trig in ("inp-tau-l2", "inp-tau-l1"):
            a, b = _unpack_tau_l2_l1([l2_in, l1_in])
            return [a, b], a, b
        a, b = _unpack_tau_l2_l1(tpair)
        return [a, b], a, b

    @app.callback(
        Output("defense-rail-h1", "children"),
        Output("sl-tau-h1", "value"),
        Output("inp-tau-h1", "value"),
        Input("sl-tau-h1", "value"),
        Input("inp-tau-h1", "value"),
        prevent_initial_call=True,
    )
    def _sync_tau_h1(v, vin):
        trig = ctx.triggered_id
        val = vin if trig == "inp-tau-h1" else v
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = 0.5
        val = max(0.2, min(0.8, val))
        return [_make_tau_h1_rail(val)], val, val

    @app.callback(
        Output("defense-rail-vol", "children"),
        Output("sl-tau-vol", "value"),
        Output("inp-tau-vol", "value"),
        Input("sl-tau-vol", "value"),
        Input("inp-tau-vol", "value"),
        prevent_initial_call=True,
    )
    def _sync_tau_vol(v, vin):
        trig = ctx.triggered_id
        val = vin if trig == "inp-tau-vol" else v
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = 0.32
        val = max(0.10, min(0.70, val))
        return [_make_tau_vol_rail(val)], val, val

    @app.callback(
        Output("defense-rail-ac1", "children"),
        Output("sl-tau-ac1", "value"),
        Output("inp-tau-ac1", "value"),
        Input("sl-tau-ac1", "value"),
        Input("inp-tau-ac1", "value"),
        prevent_initial_call=True,
    )
    def _sync_tau_ac1(v, vin):
        trig = ctx.triggered_id
        val = vin if trig == "inp-tau-ac1" else v
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = -0.08
        val = max(-0.40, min(0.15, val))
        return [_make_tau_ac1_rail(val)], val, val
