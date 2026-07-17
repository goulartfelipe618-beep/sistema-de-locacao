/**
 * Zona de drag-and-drop para upload/importação de XML (FIS-05).
 */
(function () {
  "use strict";

  function initDropzone(zone) {
    if (zone.dataset.erpUploadInit) return;
    zone.dataset.erpUploadInit = "1";

    var input = zone.querySelector('input[type="file"]');
    var target = zone.querySelector("textarea[name=conteudo_xml], textarea[data-upload-target]");
    var hint = zone.querySelector(".upload-hint");
    if (!input || !target) return;

    function setContent(text, filename) {
      target.value = text;
      target.dispatchEvent(new Event("input", { bubbles: true }));
      if (hint) hint.textContent = filename ? "Arquivo: " + filename : "XML carregado.";
      zone.classList.add("upload-zone--filled");
    }

    function readFile(file) {
      if (!file) return;
      if (!/\.xml$/i.test(file.name) && file.type && file.type.indexOf("xml") === -1) {
        alert("Selecione um arquivo XML válido.");
        return;
      }
      var reader = new FileReader();
      reader.onload = function () { setContent(String(reader.result || ""), file.name); };
      reader.readAsText(file);
    }

    zone.addEventListener("dragover", function (ev) {
      ev.preventDefault();
      zone.classList.add("upload-zone--hover");
    });
    zone.addEventListener("dragleave", function () {
      zone.classList.remove("upload-zone--hover");
    });
    zone.addEventListener("drop", function (ev) {
      ev.preventDefault();
      zone.classList.remove("upload-zone--hover");
      var file = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
      readFile(file);
    });

    input.addEventListener("change", function () {
      readFile(input.files && input.files[0]);
    });

    zone.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        input.click();
      }
    });
  }

  function initAll(root) {
    (root || document).querySelectorAll(".upload-zone").forEach(initDropzone);
  }

  document.addEventListener("DOMContentLoaded", function () { initAll(document); });
  document.addEventListener("htmx:afterSwap", function (ev) { initAll(ev.detail.target); });
})();
