/**
 * Temas do painel: claro, escuro e intermediário (hybrid).
 * Persistência: localStorage + cookie (servidor via POST /configuracoes/tema).
 */
(function () {
  var STORAGE_KEY = "erp-ui-theme";
  var VALID = { light: 1, dark: 1, hybrid: 1 };

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function persistCookie(theme) {
    try {
      document.cookie =
        STORAGE_KEY +
        "=" +
        encodeURIComponent(theme) +
        "; path=/; max-age=31536000; SameSite=Lax";
    } catch (e) { /* ignore */ }
  }

  function persistServer(theme) {
    if (!window.fetch) return;
    var token = csrfToken();
    if (!token) return;
    try {
      fetch("/configuracoes/tema", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRF-Token": token,
        },
        body: "csrf_token=" + encodeURIComponent(token) + "&theme=" + encodeURIComponent(theme),
        credentials: "same-origin",
      }).catch(function () { /* ignore */ });
    } catch (e) { /* ignore */ }
  }

  function syncButtons(theme) {
    document.querySelectorAll("[data-theme-option]").forEach(function (btn) {
      var active = btn.getAttribute("data-theme-option") === theme;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function applyTheme(name, options) {
    var opts = options || {};
    var theme = VALID[name] ? name : "hybrid";
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) { /* ignore */ }
    persistCookie(theme);
    syncButtons(theme);
    if (opts.persistServer !== false) {
      persistServer(theme);
    }
    window.dispatchEvent(new CustomEvent("erp-theme-change", { detail: { theme: theme } }));
  }

  function initTheme() {
    var root = document.documentElement;
    var current = root.getAttribute("data-theme");
    if (!current || !VALID[current]) {
      try {
        current = localStorage.getItem(STORAGE_KEY);
      } catch (e) { /* ignore */ }
    }
    applyTheme(current || "hybrid", { persistServer: false });
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

  document.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-theme-option]");
    if (!btn) return;
    event.preventDefault();
    event.stopPropagation();
    applyTheme(btn.getAttribute("data-theme-option"));
  });

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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTheme);
  } else {
    initTheme();
  }

  window.ErpTheme = {
    apply: applyTheme,
    get: function () {
      return document.documentElement.getAttribute("data-theme") || "hybrid";
    },
  };
})();
