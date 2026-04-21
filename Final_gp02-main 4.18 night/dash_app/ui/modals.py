from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.services.copy import get_app_label


def modal_add_asset() -> dbc.Modal:
    """Modal for adding a new asset to the portfolio."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(get_app_label("modal_add_asset_title", "新增资产"))),
            dbc.ModalBody(
                [
                    dbc.Label(get_app_label("modal_add_sym_label", "股票代码"), className="small"),
                    dbc.Input(
                        id="inp-add-sym",
                        type="text",
                        placeholder=get_app_label("modal_add_sym_placeholder", "如 NVDA"),
                        className="mb-2",
                    ),
                    dbc.Label(get_app_label("modal_add_weight_label", "初始权重（0–1）"), className="small"),
                    dbc.Input(id="inp-add-w", type="number", min=0, max=1, step=0.01, value=0.05, className="mb-2"),
                    dbc.Label(get_app_label("modal_add_cat_label", "归入资产类"), className="small"),
                    dcc.Dropdown(
                        id="dd-add-cat",
                        options=[
                            {"label": get_app_label("modal_add_cat_opt_tech", "科技股"), "value": "tech"},
                            {"label": get_app_label("modal_add_cat_opt_hedge", "对冲类"), "value": "hedge"},
                            {"label": get_app_label("modal_add_cat_opt_safe", "安全资产"), "value": "safe"},
                            {"label": get_app_label("modal_add_cat_opt_new", "新建类别…"), "value": "__new__"},
                        ],
                        value="tech",
                        clearable=False,
                        className="mb-2",
                    ),
                    dbc.Input(
                        id="inp-new-cat-name",
                        type="text",
                        placeholder=get_app_label("modal_add_new_cat_placeholder", "新类别名称（仅在选择「新建类别」时）"),
                        className="mb-2",
                    ),
                    html.P(
                        get_app_label(
                            "modal_add_reweight_hint",
                            "保存后其余标的权重按原比例缩放，使总和为 1−新资产权重。",
                        ),
                        className="small text-muted mb-0",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        get_app_label("modal_btn_cancel", "取消"),
                        id="btn-add-asset-cancel",
                        color="secondary",
                        className="me-2",
                        n_clicks=0,
                    ),
                    dbc.Button(
                        get_app_label("modal_btn_save", "保存"),
                        id="btn-add-asset-save",
                        color="primary",
                        n_clicks=0,
                    ),
                ]
            ),
        ],
        id="modal-add-asset",
        is_open=False,
        centered=True,
    )
