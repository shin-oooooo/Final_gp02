/**
 * Drag a single white boundary on a two-zone rail and update a hidden dcc.Slider.
 * Rails are rendered with:
 *  - root: .defense-single-rail-root (contains .defense-rgy-track)
 *  - handle: .defense-single-drag with data-target, data-min, data-max
 */
(function () {
  function clamp(x, lo, hi) {
    return Math.max(lo, Math.min(hi, x));
  }
  function round2(x) {
    return Math.round(x * 100) / 100;
  }
  function setVal(sliderId, v) {
    if (!window.dash_clientside || typeof window.dash_clientside.set_props !== "function") return;
    window.dash_clientside.set_props(sliderId, { value: v });
  }
  function setInput(inputId, v) {
    if (!inputId) return;
    if (!window.dash_clientside || typeof window.dash_clientside.set_props !== "function") return;
    window.dash_clientside.set_props(inputId, { value: v });
  }
  function rectOf(handle) {
    var wrap = handle && handle.closest && handle.closest(".defense-single-rail-root");
    var track = wrap && wrap.querySelector(".defense-rgy-track");
    if (!track) return null;
    return track.getBoundingClientRect();
  }
  function applyDom(handle, ratio) {
    var wrap = handle.closest(".defense-single-rail-root");
    if (!wrap) return;
    var track = wrap.querySelector(".defense-rgy-track");
    if (!track || track.children.length < 2) return;
    var lw = Math.max(ratio, 1e-6);
    var rw = Math.max(1 - ratio, 1e-6);
    track.children[0].style.flex = lw + " 1 0";
    track.children[1].style.flex = rw + " 1 0";
    handle.style.left = ratio * 100 + "%";
    handle.style.transform = "translateX(-50%)";
    // sync axis current number if exists
    var lbl = wrap.querySelector(".defense-axis-num--cur");
    var min = parseFloat(handle.getAttribute("data-min"));
    var max = parseFloat(handle.getAttribute("data-max"));
    if (lbl && isFinite(min) && isFinite(max)) {
      var v = round2(min + ratio * (max - min));
      lbl.textContent = v.toFixed(2);
      wrap.setAttribute("data-v", String(v));
    }
  }

  function boot() {
    document.addEventListener(
      "pointerdown",
      function (ev) {
        var h = ev.target && ev.target.closest && ev.target.closest(".defense-single-drag");
        if (!h) return;
        var sliderId = h.getAttribute("data-target");
        if (!sliderId) return;
        var min = parseFloat(h.getAttribute("data-min"));
        var max = parseFloat(h.getAttribute("data-max"));
        if (!isFinite(min) || !isFinite(max) || max <= min) return;
        var r = rectOf(h);
        if (!r || r.width <= 2) return;
        ev.preventDefault();
        try {
          h.setPointerCapture(ev.pointerId);
        } catch (e) {}

        function ratioFrom(e) {
          return clamp((e.clientX - r.left) / r.width, 0, 1);
        }
        var ratio = ratioFrom(ev);
        applyDom(h, ratio);

        function onMove(e) {
          ratio = ratioFrom(e);
          applyDom(h, ratio);
        }
        function onUp(e) {
          try {
            h.releasePointerCapture(e.pointerId);
          } catch (err) {}
          window.removeEventListener("pointermove", onMove);
          window.removeEventListener("pointerup", onUp);
          var v = round2(min + ratio * (max - min));
          setVal(sliderId, v);
          setInput(h.getAttribute("data-input"), v);
        }

        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
      },
      true
    );
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();

