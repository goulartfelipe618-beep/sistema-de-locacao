/**
 * Builder visual de condições JSON para regras de automação (AUT-01).
 */
(function () {
  "use strict";

  var FIELDS = [
    { v: "dias_vencido", l: "Dias vencido (título)" },
    { v: "dias_para_vencer", l: "Dias para vencer (documento)" },
    { v: "valor", l: "Valor numérico" },
    { v: "status", l: "Status (texto)" },
  ];

  var OPS = [
    { v: "always", l: "Sempre executar" },
    { v: "eq", l: "Igual a" },
    { v: "neq", l: "Diferente de" },
    { v: "gte", l: "Maior ou igual a" },
    { v: "lte", l: "Menor ou igual a" },
    { v: "gt", l: "Maior que" },
    { v: "lt", l: "Menor que" },
    { v: "contains", l: "Contém texto" },
  ];

  function buildJson(op, field, value) {
    if (op === "always") return { op: "always" };
    var out = { op: op, field: field };
    if (/^\d+(\.\d+)?$/.test(String(value).trim())) out.value = Number(value);
    else out.value = value;
    return out;
  }

  function parseJson(raw) {
    try {
      var data = JSON.parse(raw || "{}");
      return data && typeof data === "object" ? data : {};
    } catch (_) {
      return {};
    }
  }

  function initBuilder(root) {
    if (root.dataset.erpAutomationInit) return;
    root.dataset.erpAutomationInit = "1";

    var target = root.querySelector('[name="condicao_json"]');
    var paramsTarget = root.querySelector('[name="acao_params_json"]');
    var msgInput = root.querySelector(".automation-msg");
    if (!target) return;

    var opSel = root.querySelector(".automation-op");
    var fieldSel = root.querySelector(".automation-field");
    var valueInput = root.querySelector(".automation-value");
    var advanced = root.querySelector(".automation-json-advanced");

    var initial = parseJson(target.value);
    if (opSel && initial.op) opSel.value = initial.op;
    if (fieldSel && initial.field) fieldSel.value = initial.field;
    if (valueInput && initial.value !== undefined) valueInput.value = initial.value;

    function sync() {
      if (!opSel) return;
      var needsValue = opSel.value !== "always";
      if (fieldSel) fieldSel.disabled = !needsValue;
      if (valueInput) valueInput.disabled = !needsValue;
      if (needsValue && fieldSel && valueInput) {
        target.value = JSON.stringify(buildJson(opSel.value, fieldSel.value, valueInput.value));
      } else {
        target.value = JSON.stringify({ op: "always" });
      }
      if (advanced) advanced.value = target.value;
    }

    [opSel, fieldSel, valueInput].forEach(function (el) {
      if (el) el.addEventListener("change", sync);
      if (el) el.addEventListener("input", sync);
    });

    if (advanced) {
      advanced.addEventListener("change", function () {
        target.value = advanced.value;
        var data = parseJson(advanced.value);
        if (opSel && data.op) opSel.value = data.op;
        if (fieldSel && data.field) fieldSel.value = data.field;
        if (valueInput && data.value !== undefined) valueInput.value = data.value;
      });
    }

    if (msgInput && paramsTarget) {
      msgInput.addEventListener("input", function () {
        paramsTarget.value = JSON.stringify({ mensagem: msgInput.value || "Alerta automático" });
      });
      if (!paramsTarget.value || paramsTarget.value === "{}") {
        paramsTarget.value = JSON.stringify({ mensagem: msgInput.value || "Alerta automático" });
      }
    }

    sync();
  }

  function initAll(scope) {
    (scope || document).querySelectorAll(".automation-builder").forEach(initBuilder);
  }

  document.addEventListener("DOMContentLoaded", function () { initAll(document); });
  document.addEventListener("htmx:afterSwap", function (ev) { initAll(ev.detail.target); });
})();
