/* 侧栏参数：问号悬停 300ms 打开说明卡；卡片挂到 body 避免被侧栏裁切；定位在问号上方；点击弹层外关闭 */
(function () {
  var HOVER_MS = 300;

  function hideAll() {
    document.querySelectorAll(".param-help-card.is-visible").forEach(function (el) {
      el.classList.remove("is-visible");
      var w = el._phWrap;
      if (w && el.parentNode === document.body) {
        w.appendChild(el);
      }
    });
  }

  function placeCardHorizontal(trigger, card) {
    var r = trigger.getBoundingClientRect();
    var pad = 8;
    var left = Math.round(r.right + pad);
    var vw = window.innerWidth;
    var maxW = Math.min(380, Math.max(160, vw - left - 12));
    card.style.left = left + "px";
    card.style.maxWidth = maxW + "px";
  }

  /** 将卡片放在问号上方（视口内夹紧），避免落到「右侧栏」区域底部 */
  function finalizeAboveTrigger(trigger, card) {
    var r = trigger.getBoundingClientRect();
    var pad = 8;
    var h = card.offsetHeight || 44;
    var top = Math.round(r.top - h - pad);
    if (top < 4) top = 4;
    var maxT = window.innerHeight - h - 8;
    if (top > maxT) top = maxT;
    card.style.top = top + "px";
    var left = parseInt(card.style.left, 10) || 0;
    var cw = card.offsetWidth || 220;
    if (left + cw > window.innerWidth - 8) {
      card.style.left = Math.max(4, Math.round(window.innerWidth - cw - 8)) + "px";
    }
  }

  function onDocPointerDown(ev) {
    if (!ev.target || !ev.target.closest) return;
    if (ev.target.closest(".param-help-trigger")) return;
    if (ev.target.closest(".param-help-card.is-visible")) return;
    hideAll();
  }

  function bindWrap(wrap) {
    if (wrap.dataset.paramHelpBound) return;
    wrap.dataset.paramHelpBound = "1";
    var tr = wrap.querySelector(".param-help-trigger");
    var card = wrap.querySelector(".param-help-card");
    if (!tr || !card) return;
    card._phWrap = wrap;
    wrap._phCard = card;
    var tShow = null;
    tr.addEventListener("mouseenter", function () {
      clearTimeout(tShow);
      tShow = setTimeout(function () {
        tShow = null;
        hideAll();
        if (card.parentNode !== document.body) {
          document.body.appendChild(card);
        }
        placeCardHorizontal(tr, card);
        card.classList.add("is-visible");
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            finalizeAboveTrigger(tr, card);
          });
        });
      }, HOVER_MS);
    });
    tr.addEventListener("mouseleave", function () {
      if (tShow) {
        clearTimeout(tShow);
        tShow = null;
      }
    });
  }

  function bindAll() {
    document.querySelectorAll(".param-help-wrap").forEach(bindWrap);
  }

  function init() {
    bindAll();
    document.addEventListener("pointerdown", onDocPointerDown, true);
    var root = document.getElementById("react-entry-point");
    if (root && window.MutationObserver) {
      var t = null;
      var obs = new MutationObserver(function () {
        if (t) return;
        t = setTimeout(function () {
          t = null;
          bindAll();
        }, 50);
      });
      obs.observe(root, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
