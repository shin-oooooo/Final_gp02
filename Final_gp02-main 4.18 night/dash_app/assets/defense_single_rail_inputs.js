/**
 * Sync numeric input boxes to hidden dcc.Slider and the two-zone rail DOM.
 * Input must have id: inp-*
 * Rail handle has .defense-single-drag with data-target (slider id), data-input (input id),
 * and data-min/data-max bounds.
 */
(function () {
  function clamp(x, lo, hi) {
    return Math.max(lo, Math.min(hi, x));
  }
  function round2(x) {
    return Math.round(x * 100) / 100;
  }
  function setProps(id, props) {
    if (!window.dash_clientside || typeof window.dash_clientside.set_props !== "function") return;
    window.dash_clientside.set_props(id, props);
  }
  function applyDom(handle, ratio, v) {
    var wrap = handle.closest(".defense-single-rail-root");
    if (!wrap) return;
    var track = wrap.querySelector(".defense-rgy-track");
    if (track && track.children.length >= 2) {
      var lw = Math.max(ratio, 1e-6);
      var rw = Math.max(1 - ratio, 1e-6);
      track.children[0].style.flex = lw + " 1 0";
      track.children[1].style.flex = rw + " 1 0";
    }
    handle.style.left = ratio * 100 + "%";
    var lbl = wrap.querySelector(".defense-axis-num--cur");
    if (lbl) lbl.textContent = v.toFixed(2);
    wrap.setAttribute("data-v", String(v));
  }

  document.addEventListener(
    "change",
    function (ev) {
      var inp = ev.target;
      if (!inp || !inp.id || !inp.id.startsWith("inp-tau-")) return;
      var v = parseFloat(inp.value);
      if (!isFinite(v)) return;

      // Find handle bound to this input
      var h = document.querySelector('.defense-single-drag[data-input=\"' + inp.id + '\"]');
      if (!h) return;
      var sliderId = h.getAttribute("data-target");
      var min = parseFloat(h.getAttribute("data-min"));
      var max = parseFloat(h.getAttribute("data-max"));
      if (!sliderId || !isFinite(min) || !isFinite(max) || max <= min) return;

      v = clamp(v, min, max);
      v = round2(v);
      var ratio = (v - min) / (max - min);
      ratio = clamp(ratio, 0, 1);
      applyDom(h, ratio, v);
      setProps(sliderId, { value: v });
      setProps(inp.id, { value: v });
    },
    true
  );
})();

