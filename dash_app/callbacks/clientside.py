"""Clientside callbacks."""
from dash import Input, Output, State


def register_clientside_callbacks(app):
    app.clientside_callback(
        """
        function(n_clicks) {
            if (!n_clicks) return window.dash_clientside.no_update;
            var btn = document.getElementById("btn-download-data-json");
            if (btn) {
                btn.className = "btn btn-secondary btn-sm w-100 mt-1";
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>下载中';
            }
            setTimeout(function() {
                var btn2 = document.getElementById("btn-download-data-json");
                if (btn2) {
                    btn2.className = "btn btn-success btn-sm w-100 mt-1";
                    btn2.innerHTML = '<i class="fa fa-check me-1"></i>下载完毕';
                }
                setTimeout(function() {
                    var btn3 = document.getElementById("btn-download-data-json");
                    if (btn3) {
                        btn3.className = "btn btn-outline-secondary btn-sm w-100 mt-1";
                        btn3.innerHTML = '<i class="fa fa-download me-1"></i>下载 data.json';
                    }
                }, 3000);
            }, 2000);
            return window.dash_clientside.no_update;
        }
        """,
        Output("download-btn-state-store", "data"),
        Input("btn-download-data-json", "n_clicks"),
        prevent_initial_call=True,
    )

    # Save Run 加载态：点击瞬间 → 旋转 spinner + "运行中..." 文案；
    # 不改 btn-run 的尺寸/位置，避免顶栏布局抖动。
    # 同时挂一个 watchdog：180 秒后若 `last-snap` / `pipeline-render-ctx` 都还
    # 没更新（pipeline 异常或网络卡死），自动复原按钮，避免 UI 僵死。
    app.clientside_callback(
        """
        function(n_clicks) {
            if (!n_clicks) return window.dash_clientside.no_update;
            var btn = document.getElementById("btn-run");
            if (btn) {
                btn.dataset.runningOriginalHtml = btn.dataset.runningOriginalHtml || btn.innerHTML;
                btn.dataset.runningOriginalClass = btn.dataset.runningOriginalClass || btn.className;
                btn.disabled = true;
                btn.classList.add("disabled");
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>运行中…';
                if (btn.dataset.runningWatchdog) {
                    clearTimeout(parseInt(btn.dataset.runningWatchdog, 10));
                }
                var tid = setTimeout(function() {
                    var b3 = document.getElementById("btn-run");
                    if (!b3 || !b3.disabled) return;
                    if (b3.dataset.runningOriginalHtml) {
                        b3.innerHTML = b3.dataset.runningOriginalHtml;
                    }
                    if (b3.dataset.runningOriginalClass) {
                        b3.className = b3.dataset.runningOriginalClass;
                    }
                    b3.disabled = false;
                    b3.classList.remove("disabled");
                    // 最小可见告警（不弹 alert、不阻塞）：给按钮加一个警示 class。
                    b3.classList.add("app-btn-run-timeout");
                    setTimeout(function() {
                        var b4 = document.getElementById("btn-run");
                        if (b4) b4.classList.remove("app-btn-run-timeout");
                    }, 4000);
                }, 180 * 1000);
                btn.dataset.runningWatchdog = String(tid);
            }
            return Date.now();
        }
        """,
        Output("run-btn-state-store", "data"),
        Input("btn-run", "n_clicks"),
        prevent_initial_call=True,
    )

    # Pipeline 完成（last-snap 更新）→ "完成" 闪现 → 复原原始按钮 HTML/className。
    # 同时清掉前面那个 180s watchdog 以免被双重复原。
    app.clientside_callback(
        """
        function(snap, ctx) {
            var btn = document.getElementById("btn-run");
            if (!btn) return window.dash_clientside.no_update;
            // 仅当先前点过 Save Run（按钮处于 disabled 态）才需要复原。
            if (!btn.disabled) return window.dash_clientside.no_update;
            if (btn.dataset.runningWatchdog) {
                clearTimeout(parseInt(btn.dataset.runningWatchdog, 10));
                btn.dataset.runningWatchdog = "";
            }
            btn.innerHTML = '<i class="fa fa-check me-1"></i>完成';
            setTimeout(function() {
                var b2 = document.getElementById("btn-run");
                if (!b2) return;
                if (b2.dataset.runningOriginalHtml) {
                    b2.innerHTML = b2.dataset.runningOriginalHtml;
                }
                if (b2.dataset.runningOriginalClass) {
                    b2.className = b2.dataset.runningOriginalClass;
                }
                b2.disabled = false;
                b2.classList.remove("disabled");
            }, 1200);
            return Date.now();
        }
        """,
        Output("run-btn-state-store", "data", allow_duplicate=True),
        Input("last-snap", "data"),
        Input("pipeline-render-ctx", "data"),
        prevent_initial_call=True,
    )
