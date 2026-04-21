/**
 * Drag white boundaries on the L2/L1/L0 rail to update hidden dcc.RangeSlider id=sl-tau-l2-l1.
 * Requires window.dash_clientside.set_props (Dash renderer).
 */
(function () {
  var MIN = 0.2;
  var MAX = 0.95;
  var GAP = 0.02;

  function clamp(x, lo, hi) {
    return Math.max(lo, Math.min(hi, x));
  }
  function round2(x) {
    return Math.round(x * 100) / 100;
  }

  function trackRect(main) {
    var track = main && main.querySelector(".defense-rgy-track");
    if (!track) return null;
    return track.getBoundingClientRect();
  }

  function readTau(main) {
    var root = main && main.querySelector(".defense-tau-rail-root");
    if (!root) return null;
    var a = parseFloat(root.getAttribute("data-l2"));
    var b = parseFloat(root.getAttribute("data-l1"));
    if (!isFinite(a) || !isFinite(b)) return null;
    return { a: a, b: b, root: root };
  }

  function setTauPair(a, b) {
    if (!window.dash_clientside || typeof window.dash_clientside.set_props !== "function") {
      return;
    }
    window.dash_clientside.set_props("sl-tau-l2-l1", { value: [a, b] });
  }

  function applyRailDom(mainEl, aa, bb) {
    var track = mainEl.querySelector(".defense-rgy-track");
    if (!track || track.children.length < 3) return;
    var rw = Math.max(aa, 1e-6);
    var yw = Math.max(bb - aa, 1e-6);
    var gw = Math.max(1 - bb, 1e-6);
    track.children[0].style.flex = rw + " 1 0";
    track.children[1].style.flex = yw + " 1 0";
    track.children[2].style.flex = gw + " 1 0";
    var hL2 = mainEl.querySelector(".defense-tau-drag-l2");
    var hL1 = mainEl.querySelector(".defense-tau-drag-l1");
    if (hL2) {
      hL2.style.left = aa * 100 + "%";
      hL2.style.transform = "translateX(-50%)";
    }
    if (hL1) {
      hL1.style.left = bb * 100 + "%";
      hL1.style.transform = "translateX(-50%)";
    }
    var root = mainEl.querySelector(".defense-tau-rail-root");
    if (root) {
      root.setAttribute("data-l2", String(round2(aa)));
      root.setAttribute("data-l1", String(round2(bb)));
    }
    var rect = track.getBoundingClientRect();
    var distPx = Math.abs(bb - aa) * (rect.width || 0);
    var off = distPx > 0 && distPx < 76 ? 11 : 0;
    var al2 = mainEl.querySelector(".defense-tau-anno--l2");
    var al1 = mainEl.querySelector(".defense-tau-anno--l1");
    if (al2) {
      al2.style.left = (aa * 100).toFixed(2) + "%";
      al2.style.transform = off ? "translateX(calc(-50% - " + off + "px))" : "translateX(-50%)";
      var n2 = al2.querySelector(".defense-tau-anno-num");
      if (n2) n2.textContent = round2(aa).toFixed(2);
    }
    if (al1) {
      al1.style.left = (bb * 100).toFixed(2) + "%";
      al1.style.transform = off ? "translateX(calc(-50% + " + off + "px))" : "translateX(-50%)";
      var n1 = al1.querySelector(".defense-tau-anno-num");
      if (n1) n1.textContent = round2(bb).toFixed(2);
    }
  }

  function installDelegation(main) {
    if (!main || main._defenseTauRailDeleg) return;
    main._defenseTauRailDeleg = true;

    main.addEventListener(
      "pointerdown",
      function (ev) {
        var el = ev.target && ev.target.closest && ev.target.closest(".defense-tau-drag");
        if (!el || !main.contains(el)) return;
        var edge = el.getAttribute("data-tau-edge");
        if (edge !== "l2" && edge !== "l1") return;
        ev.preventDefault();

        var parsed = readTau(main);
        if (!parsed) return;
        var a = parsed.a;
        var b = parsed.b;
        var rect = trackRect(main);
        if (!rect || rect.width <= 2) return;

        try {
          el.setPointerCapture(ev.pointerId);
        } catch (e) {}

        function ratioFromEvent(e) {
          var r = (e.clientX - rect.left) / rect.width;
          return clamp(r, 0, 1);
        }

        function onMove(e) {
          var t = round2(ratioFromEvent(e));
          t = clamp(t, MIN, MAX);
          if (edge === "l2") {
            a = clamp(t, MIN, b - GAP);
          } else {
            b = clamp(t, a + GAP, MAX);
          }
          a = round2(a);
          b = round2(b);
          applyRailDom(main, a, b);
        }

        function onUp(e) {
          setTauPair(a, b);
          try {
            el.releasePointerCapture(e.pointerId);
          } catch (err) {}
          window.removeEventListener("pointermove", onMove);
          window.removeEventListener("pointerup", onUp);
        }

        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
      },
      true
    );
  }

  function boot() {
    var main = document.getElementById("defense-rgy-rail-main");
    if (!main) return;
    installDelegation(main);
    var parsed = readTau(main);
    if (parsed) applyRailDom(main, parsed.a, parsed.b);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  /* Dash 动态布局可能晚于 DOMContentLoaded */
  setTimeout(boot, 800);
})();
