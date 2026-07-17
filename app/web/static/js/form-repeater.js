/**
 * Repeater dinâmico de linhas (T39) para tarifário, propostas, etc.
 */
(function () {
  "use strict";

  function syncKmLivre(row) {
    var hidden = row.querySelector(".km-livre-val");
    var cb = row.querySelector(".km-livre-cb");
    if (!hidden || !cb || cb.dataset.kmSync) return;
    cb.dataset.kmSync = "1";
    hidden.value = cb.checked ? "1" : "0";
    cb.addEventListener("change", function () {
      hidden.value = cb.checked ? "1" : "0";
    });
  }

  function initRepeater(container) {
    if (container.dataset.erpRepeaterInit) return;
    container.dataset.erpRepeaterInit = "1";

    var rowsEl = container.querySelector(".form-repeater-rows");
    var tpl = container.querySelector("template.form-repeater-template");
    var addBtn = container.querySelector(".form-repeater-add");
    if (!rowsEl || !tpl) return;

    var min = parseInt(container.getAttribute("data-repeater-min") || "0", 10);
    var form = container.closest("form");
    var keyName = container.getAttribute("data-repeater-key") || "";
    var errMsg = container.getAttribute("data-repeater-error") || "Preencha ao menos uma linha.";

    function rowCount() {
      return rowsEl.querySelectorAll(".form-repeater-row").length;
    }

    function updateRemoveButtons() {
      var count = rowCount();
      rowsEl.querySelectorAll(".form-repeater-remove").forEach(function (btn) {
        btn.disabled = count <= min;
      });
    }

    function bindRow(row) {
      syncKmLivre(row);
      var rm = row.querySelector(".form-repeater-remove");
      if (rm) {
        rm.addEventListener("click", function () {
          if (rowCount() <= min) return;
          row.remove();
          updateRemoveButtons();
        });
      }
      if (window.ErpForms && window.ErpForms.enhanceFields && form) {
        window.ErpForms.enhanceFields(row, form);
      }
    }

    function addRow() {
      var row = tpl.content.firstElementChild.cloneNode(true);
      rowsEl.appendChild(row);
      bindRow(row);
      updateRemoveButtons();
      return row;
    }

    rowsEl.querySelectorAll(".form-repeater-row").forEach(bindRow);
    while (rowCount() < min) addRow();
    updateRemoveButtons();

    if (addBtn) addBtn.addEventListener("click", addRow);

    if (form && container.hasAttribute("data-repeater-validate") && keyName) {
      form.addEventListener("submit", function (ev) {
        var ok = false;
        rowsEl.querySelectorAll(".form-repeater-row").forEach(function (row) {
          var inp = row.querySelector('[name="' + keyName + '"]');
          if (inp && String(inp.value || "").trim()) ok = true;
        });
        if (!ok) {
          ev.preventDefault();
          var first = rowsEl.querySelector('[name="' + keyName + '"]');
          if (first) first.focus();
          alert(errMsg);
        }
      }, true);
    }
  }

  function initAll(root) {
    (root || document).querySelectorAll(".form-repeater").forEach(initRepeater);
  }

  document.addEventListener("DOMContentLoaded", function () { initAll(document); });
  document.addEventListener("htmx:afterSwap", function (ev) { initAll(ev.detail.target); });
})();
