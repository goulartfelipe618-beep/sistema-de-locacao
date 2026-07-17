/**
 * Modais de confirmação com consulta de impacto entre entidades.
 */
(function () {
  "use strict";

  var modal, titleEl, bodyEl, detailsEl, confirmBtn, cancelBtn, pendingForm;

  function ensureModal() {
    if (modal) return;
    modal = document.getElementById("erp-impact-modal");
    if (!modal) return;
    titleEl = modal.querySelector(".impact-modal-title");
    bodyEl = modal.querySelector(".impact-modal-body");
    detailsEl = modal.querySelector(".impact-modal-details");
    confirmBtn = modal.querySelector(".impact-modal-confirm");
    cancelBtn = modal.querySelector(".impact-modal-cancel");
    modal.querySelector(".impact-modal-backdrop")?.addEventListener("click", closeModal);
    cancelBtn?.addEventListener("click", closeModal);
    confirmBtn?.addEventListener("click", function () {
      if (pendingForm) {
        pendingForm.dataset.impactConfirmed = "1";
        pendingForm.requestSubmit();
      }
      closeModal();
    });
  }

  function closeModal() {
    if (modal) modal.hidden = true;
    pendingForm = null;
  }

  function showModal(opts) {
    ensureModal();
    if (!modal) {
      if (window.confirm(opts.summary || opts.title)) {
        if (pendingForm) pendingForm.requestSubmit();
      }
      return;
    }
    titleEl.textContent = opts.title || "Confirmar ação";
    bodyEl.textContent = opts.summary || "";
    detailsEl.innerHTML = "";
    (opts.details || []).forEach(function (d) {
      if (!d.count) return;
      var row = document.createElement("div");
      row.className = "impact-detail-row";
      row.innerHTML = "<span>" + d.label + "</span><strong>" + d.count + "</strong>";
      detailsEl.appendChild(row);
    });
    confirmBtn.disabled = !!opts.blocked && opts.mode !== "warn";
    confirmBtn.textContent = opts.blocked && opts.mode !== "warn" ? "Bloqueado" : "Confirmar";
    confirmBtn.classList.toggle("btn-danger", opts.mode !== "warn");
    modal.hidden = false;
  }

  async function handleSubmit(ev) {
    var form = ev.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.dataset.impactConfirmed === "1") {
      delete form.dataset.impactConfirmed;
      return;
    }

    var impactUrl = form.getAttribute("data-impact-url");
    var confirmMsg = form.getAttribute("data-confirm");
    if (!impactUrl && !confirmMsg) return;

    ev.preventDefault();

    if (impactUrl) {
      try {
        var resp = await fetch(impactUrl, { headers: { Accept: "application/json" } });
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        var data = await resp.json();
        pendingForm = form;
        showModal({
          title: form.getAttribute("data-impact-title") || "Verificar impacto",
          summary: data.summary,
          details: data.details,
          blocked: data.blocked,
          mode: form.getAttribute("data-impact-mode") || "block",
        });
      } catch (_) {
        pendingForm = form;
        showModal({
          title: "Confirmar",
          summary: "Não foi possível verificar vínculos. Deseja continuar mesmo assim?",
          mode: "warn",
        });
      }
      return;
    }

    pendingForm = form;
    showModal({
      title: form.getAttribute("data-confirm-title") || "Confirmar",
      summary: confirmMsg,
      mode: "warn",
    });
  }

  document.addEventListener("submit", handleSubmit, true);
  document.addEventListener("DOMContentLoaded", ensureModal);
})();
