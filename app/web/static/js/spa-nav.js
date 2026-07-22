/**
 * Navegação SPA: troca o conteúdo principal sem recarregar a página inteira.
 * Sidebar permanece fixa; URL e título sincronizados via History API.
 */
(function () {
  var CONTENT = "#app-content";
  var NAVBAR_TITLE = ".page-title";
  var MAIN = ".main";
  var LOADER = "#spa-loader";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function appName() {
    return document.documentElement.getAttribute("data-app-name") || "ERP";
  }

  function loaderEl() {
    return document.querySelector(LOADER);
  }

  function showLoader() {
    var el = loaderEl();
    if (!el) return;
    el.hidden = false;
    el.setAttribute("aria-hidden", "false");
  }

  function hideLoader() {
    var el = loaderEl();
    if (!el) return;
    el.hidden = true;
    el.setAttribute("aria-hidden", "true");
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

  var pendingSpaUrl = null;
  var skipNextHistoryPush = false;

  function pushSpaUrl(url) {
    if (!url) return;
    try {
      var u = new URL(url, window.location.origin);
      var next = u.pathname + u.search;
      var cur = window.location.pathname + window.location.search;
      if (next !== cur) {
        history.pushState({ erpSpa: true }, "", next);
      }
    } catch (ignore) {}
  }

  function requestUrlFromDetail(detail) {
    if (pendingSpaUrl) return pendingSpaUrl;
    if (detail.pathInfo && detail.pathInfo.requestPath) {
      return detail.pathInfo.requestPath;
    }
    if (detail.xhr && detail.xhr.responseURL) {
      return detail.xhr.responseURL;
    }
    return null;
  }

  function spaAjax(url) {
    var targetEl = document.querySelector(CONTENT);
    if (targetEl && window.htmx) {
      window.htmx.trigger(targetEl, "htmx:abort");
    }
    showLoader();
    window.htmx.ajax("GET", url, {
      target: CONTENT,
      swap: "outerHTML",
      headers: { "X-CSRF-Token": csrfToken(), "X-ERP-SPA": "1" },
    });
  }

  function spaNavigate(url, options) {
    options = options || {};
    if (!window.htmx) {
      window.location.href = url;
      return;
    }
    if (options.fromHistory) {
      pendingSpaUrl = null;
      skipNextHistoryPush = true;
    } else {
      pendingSpaUrl = url;
    }
    spaAjax(url);
  }

  function buildGetUrl(form) {
    var action = form.getAttribute("action") || window.location.pathname;
    var params = new URLSearchParams();
    new FormData(form).forEach(function (value, key) {
      if (value !== null && String(value).trim() !== "") {
        params.append(key, value);
      }
    });
    var qs = params.toString();
    return qs ? action + "?" + qs : action;
  }

  function navPathMatches(path, href) {
    if (!href) return false;
    if (path === href) return true;
    if (href === "/") return false;
    return path.indexOf(href + "/") === 0;
  }

  function updateActiveNav(optPath) {
    var path = optPath || window.location.pathname;
    var links = Array.prototype.slice.call(
      document.querySelectorAll(".nav-sub-link, .nav-group-link")
    ).filter(function (el) {
      return !el.classList.contains("is-disabled");
    });

    var best = null;
    var bestLen = -1;
    links.forEach(function (el) {
      var href = el.getAttribute("href");
      if (!href || !navPathMatches(path, href)) return;
      if (href.length > bestLen) {
        best = el;
        bestLen = href.length;
      }
    });

    links.forEach(function (el) {
      var href = el.getAttribute("href");
      if (!href) {
        el.classList.remove("is-active");
        return;
      }
      var active = el === best;
      el.classList.toggle("is-active", active);
      if (active) {
        var group = el.closest("[data-nav-group]");
        if (group && group.__x && group.__x.$data) {
          group.__x.$data.open = true;
        }
      }
    });
  }

  function pageTitleFromContent(main) {
    if (!main) return null;
    var fromAttr = main.getAttribute("data-page-title");
    if (fromAttr && fromAttr.trim()) return fromAttr.trim();
    var crumb = main.querySelector(".breadcrumb strong");
    if (crumb && crumb.textContent) return crumb.textContent.trim();
    return null;
  }

  function syncChrome() {
    var main = document.querySelector(CONTENT);
    if (!main) return;
    var title = pageTitleFromContent(main) || "Painel";
    var titleEl = document.querySelector(NAVBAR_TITLE);
    if (titleEl) titleEl.textContent = title;
    document.title = title + " · " + appName();
    updateActiveNav();
  }

  function finishContentSwap(detail) {
    var url = requestUrlFromDetail(detail || {});
    if (url && !skipNextHistoryPush) {
      pushSpaUrl(url);
    }
    skipNextHistoryPush = false;
    pendingSpaUrl = null;
    syncChrome();
    hideLoader();
    window.scrollTo(0, 0);
  }

  function shouldSpaNavigate(link) {
    if (!isSpaLink(link)) return false;
    if (link.closest(".navbar, .profile-modal, .profile-modal-backdrop")) return false;
    return !!(link.closest(".sidebar") || link.closest(CONTENT) || link.closest(MAIN));
  }

  document.addEventListener("click", function (event) {
    var link = event.target.closest("a");
    if (!shouldSpaNavigate(link)) return;
    event.preventDefault();
    var href = link.getAttribute("href");
    if (window.erpLayout && window.erpLayout.closeSidebar) {
      window.erpLayout.closeSidebar();
    }
    try {
      updateActiveNav(new URL(href, window.location.origin).pathname);
    } catch (ignore) {}
    spaNavigate(href);
  });

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form || form.tagName !== "FORM") return;
    if (form.method.toLowerCase() !== "get") return;
    if (form.dataset.noSpa === "true") return;
    if (form.closest(".navbar, .profile-modal")) return;
    if (!form.closest(CONTENT) && !form.closest(".sidebar")) return;
    event.preventDefault();
    spaNavigate(buildGetUrl(form));
  });

  document.body.addEventListener("htmx:beforeSwap", function (event) {
    var target = event.detail.target;
    if (!target || target.id !== "app-content") return;
    var frag = event.detail.fragment;
    if (frag && frag.nodeType === 1 && frag.id === "app-content") {
      event.detail.swapStyle = "outerHTML";
    }
  });

  document.addEventListener("htmx:beforeRequest", function (event) {
    var target = event.detail.target;
    if (target && target.id === "app-content") {
      target.classList.add("is-loading");
      showLoader();
    }
  });

  document.addEventListener("htmx:afterRequest", function (event) {
    var target = event.detail.target;
    if (target && target.id === "app-content") {
      target.classList.remove("is-loading");
      hideLoader();
    }
  });

  document.addEventListener("htmx:responseError", function (event) {
    hideLoader();
    var target = document.querySelector(CONTENT);
    if (target) target.classList.remove("is-loading");
    var detail = event.detail;
    if (!detail || !detail.target || detail.target.id !== "app-content") return;
    var url =
      pendingSpaUrl ||
      (detail.pathInfo && (detail.pathInfo.requestPath || detail.pathInfo.path)) ||
      null;
    pendingSpaUrl = null;
    skipNextHistoryPush = false;
    if (url) window.location.href = url;
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    var target = event.detail.target;
    if (target && target.id === "app-content") {
      finishContentSwap(event.detail);
    }
  });

  window.addEventListener("popstate", function () {
    spaNavigate(window.location.pathname + window.location.search, { fromHistory: true });
  });

  document.body.addEventListener("htmx:configRequest", function (event) {
    event.detail.headers["X-CSRF-Token"] = csrfToken();
    var target = event.detail.target;
    if (target && target.id === "app-content") {
      event.detail.headers["X-ERP-SPA"] = "1";
    }
  });

  syncChrome();
})();
