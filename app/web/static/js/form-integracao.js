/**
 * Teste de conexão assíncrono e toggle de secrets (INT-01).
 */
(function () {
  "use strict";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function initSecretToggle(input) {
    if (input.dataset.secretToggle || input.type !== "password") return;
    input.dataset.secretToggle = "1";
    var wrap = document.createElement("div");
    wrap.className = "secret-field-wrap";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-sm secret-toggle-btn";
    btn.textContent = "Mostrar";
    btn.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.textContent = show ? "Ocultar" : "Mostrar";
    });
    wrap.appendChild(btn);
  }

  async function runTest(btn) {
    var url = btn.getAttribute("data-integration-test");
    if (!url) return;
    var row = btn.closest("tr");
    var panel = row ? row.querySelector(".integration-test-result") : null;
    if (!panel) {
      panel = document.getElementById("integration-test-panel");
    }
    btn.disabled = true;
    var old = btn.textContent;
    btn.textContent = "Testando…";
    try {
      var fd = new FormData();
      fd.append("csrf_token", csrfToken());
      fd.append("tipo", btn.getAttribute("data-integration-tipo") || "pagamentos");
      var resp = await fetch(url, {
        method: "POST",
        headers: { Accept: "application/json" },
        body: fd,
        credentials: "same-origin",
      });
      var data = await resp.json();
      if (panel) {
        panel.hidden = false;
        panel.className = "integration-test-result " + (data.ok ? "is-ok" : "is-fail");
        panel.textContent = data.message || (data.ok ? "Conexão OK" : "Falha na conexão");
      }
    } catch (_) {
      if (panel) {
        panel.hidden = false;
        panel.className = "integration-test-result is-fail";
        panel.textContent = "Erro ao testar conexão.";
      }
    } finally {
      btn.disabled = false;
      btn.textContent = old;
    }
  }

  function initAll(root) {
    (root || document).querySelectorAll('[data-secret="1"]').forEach(initSecretToggle);
    (root || document).querySelectorAll("[data-integration-test]").forEach(function (btn) {
      if (btn.dataset.integrationInit) return;
      btn.dataset.integrationInit = "1";
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        runTest(btn);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () { initAll(document); });
  document.addEventListener("htmx:afterSwap", function (ev) { initAll(ev.detail.target); });
})();
