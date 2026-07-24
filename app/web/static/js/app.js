/**
 * Boot do painel administrativo.
 * - CSRF em formulários e HTMX
 * - Menu lateral mobile
 * - Scroll horizontal seguro em tabelas
 */
(function () {
  var MOBILE_BP = 1024;

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function isMobileLayout() {
    return window.matchMedia("(max-width: " + (MOBILE_BP - 1) + "px)").matches;
  }

  function sidebarOpen() {
    return document.body.classList.contains("sidebar-open");
  }

  function setSidebarOpen(open) {
    var toggle = document.getElementById("nav-toggle");
    var backdrop = document.getElementById("sidebar-backdrop");
    document.body.classList.toggle("sidebar-open", open);
    if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (backdrop) backdrop.setAttribute("aria-hidden", open ? "false" : "true");
  }

  function closeSidebar() {
    if (sidebarOpen()) setSidebarOpen(false);
  }

  function openSidebar() {
    if (isMobileLayout()) setSidebarOpen(true);
  }

  function toggleSidebar() {
    setSidebarOpen(!sidebarOpen());
  }

  function bindSidebarControls() {
    var toggle = document.getElementById("nav-toggle");
    var closeBtn = document.getElementById("sidebar-close");
    var backdrop = document.getElementById("sidebar-backdrop");
    if (toggle && !toggle.dataset.bound) {
      toggle.dataset.bound = "1";
      toggle.addEventListener("click", function () {
        toggleSidebar();
      });
    }
    if (closeBtn && !closeBtn.dataset.bound) {
      closeBtn.dataset.bound = "1";
      closeBtn.addEventListener("click", closeSidebar);
    }
    if (backdrop && !backdrop.dataset.bound) {
      backdrop.dataset.bound = "1";
      backdrop.addEventListener("click", closeSidebar);
    }
    document.querySelectorAll(".sidebar .nav-sub-link, .sidebar .nav-group-link").forEach(function (link) {
      if (link.dataset.sidebarBound) return;
      link.dataset.sidebarBound = "1";
      link.addEventListener("click", function () {
        if (isMobileLayout()) closeSidebar();
      });
    });
  }

  function wrapTables(root) {
    var scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll("table.table").forEach(function (table) {
      if (table.closest(".table-scroll")) return;
      var wrap = document.createElement("div");
      wrap.className = "table-scroll";
      wrap.setAttribute("role", "region");
      wrap.setAttribute("aria-label", "Tabela com rolagem horizontal");
      wrap.setAttribute("tabindex", "0");
      if (table.parentNode) {
        table.parentNode.insertBefore(wrap, table);
        wrap.appendChild(table);
      }
    });
  }

  function normalizeCardWidths(root) {
    var scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll('.card[style*="max-width"]').forEach(function (card) {
      var style = card.getAttribute("style") || "";
      var match = style.match(/max-width:\s*([^;]+)/i);
      if (match) {
        card.style.setProperty("--inline-card-max", match[1].trim());
        card.style.maxWidth = "min(" + match[1].trim() + ", 100%)";
      }
    });
  }

  function initLayout(root) {
    wrapTables(root);
    normalizeCardWidths(root);
    bindSidebarControls();
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if ((form.getAttribute("method") || "get").toUpperCase() === "GET") return;
    var input = form.querySelector('input[name="csrf_token"]');
    if (!input) {
      input = document.createElement("input");
      input.type = "hidden";
      input.name = "csrf_token";
      form.appendChild(input);
    }
    input.value = csrfToken();
  });

  document.addEventListener("htmx:configRequest", function (event) {
    event.detail.headers["X-CSRF-Token"] = csrfToken();
  });

  document.addEventListener("DOMContentLoaded", function () {
    initLayout(document);
    refreshNotificationBadge();
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target) initLayout(event.detail.target);
    refreshNotificationBadge();
  });

  window.addEventListener("resize", function () {
    if (!isMobileLayout()) closeSidebar();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeSidebar();
  });

  function refreshNotificationBadge() {
    var badges = document.querySelectorAll(".js-notificacoes-badge");
    if (!badges.length) return;
    fetch("/notificacoes/badge-count", { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) return null;
        return response.json();
      })
      .then(function (data) {
        if (!data) return;
        var total = Number(data.total) || 0;
        badges.forEach(function (el) {
          if (!el) return;
          if (total > 0) {
            el.textContent = String(total);
            el.hidden = false;
            el.removeAttribute("hidden");
            el.classList.remove("nav-badge--hidden");
            el.setAttribute("aria-label", total + " não lidas");
          } else {
            el.textContent = "0";
            el.hidden = true;
            el.setAttribute("hidden", "");
            el.classList.add("nav-badge--hidden");
            el.removeAttribute("aria-label");
          }
        });
      })
      .catch(function () {});
  }

  window.erpLayout = {
    closeSidebar: closeSidebar,
    openSidebar: openSidebar,
    wrapTables: wrapTables,
    refreshNotificationBadge: refreshNotificationBadge,
  };
})();
