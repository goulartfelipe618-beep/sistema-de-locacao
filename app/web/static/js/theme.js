/**
 * Temas do painel: claro, escuro e híbrido (sidebar escura + conteúdo claro).
 * Persistência em localStorage.
 */
(function () {
  var STORAGE_KEY = "erp-ui-theme";
  var VALID = { light: 1, dark: 1, hybrid: 1 };

  function applyTheme(name) {
    var theme = VALID[name] ? name : "hybrid";
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) { /* ignore */ }
    document.querySelectorAll("[data-theme-option]").forEach(function (btn) {
      var active = btn.getAttribute("data-theme-option") === theme;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function initTheme() {
    var saved = null;
    try {
      saved = localStorage.getItem(STORAGE_KEY);
    } catch (e) { /* ignore */ }
    applyTheme(saved || "hybrid");
  }

  document.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-theme-option]");
    if (!btn) return;
    event.preventDefault();
    applyTheme(btn.getAttribute("data-theme-option"));
  });

  initTheme();
  window.ErpTheme = { apply: applyTheme, get: function () {
    return document.documentElement.getAttribute("data-theme") || "hybrid";
  }};
})();
