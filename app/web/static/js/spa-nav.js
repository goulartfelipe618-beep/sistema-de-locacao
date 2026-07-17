/**
 * Navegação SPA: troca o conteúdo principal sem recarregar a página inteira.
 * Sidebar permanece fixa; URL atualizada via History API (HTMX push-url).
 */
(function () {
  var CONTENT = "#app-content";
  var NAVBAR_TITLE = ".page-title";
  var MAIN = ".main";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function appName() {
    return document.documentElement.getAttribute("data-app-name") || "ERP";
  }

  function isSpaLink(link) {
    if (!link || link.tagName !== "A") return false;
    var href = link.getAttribute("href");
    if (!href || href.charAt(0) !== "/" || href.charAt(1) === "/") return false;
    if (link.dataset.noSpa === "true") return false;
    if (link.target === "_blank" || link.hasAttribute("download")) return false;
    if (link.closest("form")) return false;
    if (href.indexOf("/logout") === 0) return false;
    return true;
  }

  function spaNavigate(url) {
    if (!window.htmx) {
      window.location.href = url;
      return;
    }
    window.htmx.ajax("GET", url, {
      target: CONTENT,
      select: CONTENT,
      swap: "innerHTML",
      pushUrl: true,
      headers: { "X-CSRF-Token": csrfToken() },
    });
  }

  function buildGetUrl(form) {
    var action = form.getAttribute("action") || window.location.pathname;
    var params = new URLSearchParams(new FormData(form));
    var qs = params.toString();
    return qs ? action + "?" + qs : action;
  }

  function updateActiveNav() {
    var path = window.location.pathname;
    document.querySelectorAll(".nav-sub-link, .nav-group-link").forEach(function (el) {
      if (el.classList.contains("is-disabled")) return;
      var href = el.getAttribute("href");
      if (!href) {
        el.classList.remove("is-active");
        return;
      }
      var active = path === href || (href !== "/" && path.indexOf(href + "/") === 0);
      el.classList.toggle("is-active", active);
      if (active) {
        var group = el.closest("[data-nav-group]");
        if (group && group.__x && group.__x.$data) {
          group.__x.$data.open = true;
        }
      }
    });
  }

  function syncChrome() {
    var main = document.querySelector(CONTENT);
    if (!main) return;
    var title = main.getAttribute("data-page-title") || "Painel";
    var titleEl = document.querySelector(NAVBAR_TITLE);
    if (titleEl) titleEl.textContent = title;
    document.title = title + " · " + appName();
    updateActiveNav();
  }

  function shouldSpaNavigate(link) {
    if (!isSpaLink(link)) return false;
    return !!(link.closest(".sidebar") || link.closest(CONTENT) || link.closest(MAIN));
  }

  document.addEventListener("click", function (event) {
    var link = event.target.closest("a");
    if (!shouldSpaNavigate(link)) return;
    event.preventDefault();
    spaNavigate(link.getAttribute("href"));
  });

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form || form.tagName !== "FORM") return;
    if (form.method.toLowerCase() !== "get") return;
    if (form.dataset.noSpa === "true") return;
    if (!form.closest(CONTENT) && !form.closest(".sidebar")) return;
    event.preventDefault();
    spaNavigate(buildGetUrl(form));
  });

  document.addEventListener("htmx:beforeRequest", function (event) {
    var target = event.detail.target;
    if (target && target.id === "app-content") {
      target.classList.add("is-loading");
    }
  });

  document.addEventListener("htmx:afterRequest", function (event) {
    var target = event.detail.target;
    if (target && target.id === "app-content") {
      target.classList.remove("is-loading");
    }
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target && event.detail.target.id === "app-content") {
      syncChrome();
      window.scrollTo(0, 0);
    }
  });

  document.addEventListener("htmx:afterRequest", function (event) {
    if (event.detail.successful && event.detail.target && event.detail.target.id === "app-content") {
      syncChrome();
    }
  });

  window.addEventListener("popstate", function () {
    spaNavigate(window.location.pathname + window.location.search);
  });

  document.body.addEventListener("htmx:configRequest", function (event) {
    event.detail.headers["X-CSRF-Token"] = csrfToken();
  });

  syncChrome();
})();
