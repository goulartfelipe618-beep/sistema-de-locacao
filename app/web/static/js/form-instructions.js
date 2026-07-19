(function () {
  "use strict";

  function closePanel(btn, panel) {
    panel.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  }

  function openPanel(btn, panel) {
    panel.hidden = false;
    btn.setAttribute("aria-expanded", "true");
    panel.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  function bindRoot(root) {
    var btn = root.querySelector(".form-instructions-btn");
    var panel = root.querySelector(".form-instructions-panel");
    if (!btn || !panel || btn.dataset.bound) return;
    btn.dataset.bound = "1";
    btn.addEventListener("click", function () {
      if (panel.hidden) openPanel(btn, panel);
      else closePanel(btn, panel);
    });
  }

  function initAll(scope) {
    (scope || document).querySelectorAll("[data-instructions-root]").forEach(bindRoot);
  }

  document.addEventListener("DOMContentLoaded", function () { initAll(document); });
  document.addEventListener("htmx:afterSwap", function (ev) { initAll(ev.detail.target); });

  document.addEventListener("click", function (ev) {
    document.querySelectorAll("[data-instructions-root]").forEach(function (root) {
      if (root.contains(ev.target)) return;
      var btn = root.querySelector(".form-instructions-btn");
      var panel = root.querySelector(".form-instructions-panel");
      if (btn && panel && !panel.hidden) closePanel(btn, panel);
    });
  });
})();
