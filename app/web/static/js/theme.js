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

  function updateProfileChrome(detail) {
    if (!detail || !detail.full_name) return;
    document.querySelectorAll(".user-name").forEach(function (el) {
      el.textContent = detail.full_name;
    });
    document.querySelectorAll(".user-avatar").forEach(function (el) {
      el.textContent = detail.full_name.charAt(0).toUpperCase();
    });
    var input = document.getElementById("profile_full_name");
    if (input) input.value = detail.full_name;
  }

  document.body.addEventListener("profileSaved", function (event) {
    updateProfileChrome(event.detail || {});
    window.dispatchEvent(new CustomEvent("profile-saved"));
  });

  document.body.addEventListener("profileError", function (event) {
    var box = document.getElementById("profile-form-error");
    if (!box) return;
    box.textContent = (event.detail && event.detail.message) || "Não foi possível salvar.";
    box.style.display = "block";
  });

  initTheme();
  window.ErpTheme = {
    apply: applyTheme,
    get: function () {
      return document.documentElement.getAttribute("data-theme") || "hybrid";
    },
  };
})();
