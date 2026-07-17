/**
 * ERP Form Engine — máscaras, validação, cascatas e UX global.
 * Inicializa automaticamente em formulários POST do painel.
 */
(function () {
  "use strict";

  var UFS_FALLBACK = [
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB",
    "PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
  ];

  var MASK_RULES = {
    cpf: { pattern: "###.###.###-##", max: 11 },
    cnpj: { pattern: "##.###.###/####-##", max: 14 },
    cep: { pattern: "#####-###", max: 8 },
    phone: { pattern: "(##) ####-####", max: 10 },
    mobile: { pattern: "(##) #####-####", max: 11 },
    placa: { pattern: "AAA#A##", max: 7, upper: true },
    renavam: { pattern: "###########", max: 11 },
    year: { pattern: "####", max: 4 },
    percent: { pattern: "##,##", max: 5, suffix: " %" },
  };

  var MONEY_NAMES = /valor|preco|preço|limite|desconto|comissao|comissão|total|caucao|caução|franquia|parcela|saldo|multa|taxa_valor/i;
  var PHONE_NAMES = /^telefone$|^fone$/i;
  var MOBILE_NAMES = /^celular$|^mobile$/i;

  function digits(value) {
    return (value || "").replace(/\D/g, "");
  }

  function applyPattern(raw, pattern, upper) {
    var d = digits(raw);
    var out = "";
    var di = 0;
    for (var i = 0; i < pattern.length && di < d.length; i++) {
      var ch = pattern[i];
      if (ch === "#") {
        out += d[di++];
      } else if (ch === "A") {
        var c = d[di++];
        out += upper ? String(c).toUpperCase() : c;
      } else {
        out += ch;
        if (d[di] === ch) di++;
      }
    }
    return out;
  }

  function formatMoneyBR(raw) {
    var d = digits(raw);
    if (!d) return "";
    var cents = parseInt(d, 10);
    var reais = (cents / 100).toFixed(2);
    var parts = reais.split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return "R$ " + parts[0] + "," + parts[1];
  }

  function detectMaskType(input) {
    var mask = input.getAttribute("data-mask");
    if (mask) return mask;
    var name = (input.name || input.id || "").toLowerCase();
    if (name === "cpf") return "cpf";
    if (name === "cnpj") return "cnpj";
    if (name === "cep") return "cep";
    if (name === "placa") return "placa";
    if (name === "renavam") return "renavam";
    if (name === "phone" || name === "telefone") return "phone";
    if (MOBILE_NAMES.test(name)) return "mobile";
    if (/ano_(fabricacao|modelo)|^ano$/.test(name)) return "year";
    if (/percentual|percent|aliquota|alíquota/.test(name)) return "percent";
    if (MONEY_NAMES.test(name) || input.getAttribute("data-money") != null) return "money";
    if (input.type === "date" || /vencimento|validade|data_/.test(name)) return "date";
    return null;
  }

  function bindMask(input, type) {
    if (input.dataset.erpMaskBound) return;
    input.dataset.erpMaskBound = "1";
    input.setAttribute("autocomplete", input.getAttribute("autocomplete") || "off");

    if (type === "money") {
      input.inputMode = "decimal";
      if (!input.placeholder) input.placeholder = "R$ 0,00";
      input.addEventListener("input", function () {
        var pos = input.selectionStart;
        var before = input.value.length;
        input.value = formatMoneyBR(input.value);
        var after = input.value.length;
        input.setSelectionRange(Math.max(0, pos + (after - before)), Math.max(0, pos + (after - before)));
      });
      return;
    }

    if (type === "date" && input.type !== "date" && input.type !== "datetime-local") {
      input.placeholder = input.placeholder || "dd/mm/aaaa";
      input.addEventListener("input", function () {
        input.value = applyPattern(input.value, "##/##/####");
      });
      return;
    }

    var rule = MASK_RULES[type];
    if (!rule) return;

    input.placeholder = input.placeholder || rule.pattern.replace(/#/g, "0").replace(/A/g, "A");
    input.addEventListener("input", function () {
      var d = digits(input.value).slice(0, rule.max);
      input.value = applyPattern(d, rule.pattern, rule.upper);
    });
    if (rule.suffix && !input.parentElement.classList.contains("input-suffix-wrap")) {
      /* percent shown inline */
    }
  }

  function markRequiredLabels(form) {
    form.querySelectorAll("[required]").forEach(function (el) {
      var id = el.id || el.name;
      if (!id) return;
      var label = form.querySelector('label[for="' + id + '"]');
      if (label && !label.classList.contains("form-label--required")) {
        label.classList.add("form-label--required");
      }
      var wrap = el.closest(".form-group");
      if (wrap) {
        var lbl = wrap.querySelector(".form-label");
        if (lbl && !lbl.classList.contains("form-label--required")) {
          lbl.classList.add("form-label--required");
        }
      }
    });
    if (!form.querySelector(".form-legend-required")) {
      var legend = document.createElement("p");
      legend.className = "form-legend-required";
      legend.textContent = "* Campos obrigatórios";
      var actions = form.querySelector(".form-actions");
      if (actions) form.insertBefore(legend, actions);
      else form.appendChild(legend);
    }
  }

  function setupPersonToggle(form) {
    var sel = form.querySelector("#person_type, [name=person_type]");
    if (!sel) return;

    var cpfGroup = form.querySelector("#cpf, [name=cpf]")?.closest(".form-group");
    var cnpjGroup = form.querySelector("#cnpj, [name=cnpj]")?.closest(".form-group");
    var fantasiaGroup = form.querySelector("#nome_fantasia, [name=nome_fantasia]")?.closest(".form-group");
    if (!cpfGroup && !cnpjGroup) return;

    function sync() {
      var isPf = sel.value === "pf";
      if (cpfGroup) {
        cpfGroup.style.display = isPf ? "" : "none";
        var cpfInput = cpfGroup.querySelector("input");
        if (cpfInput) cpfInput.required = isPf && !cpfInput.disabled;
      }
      if (cnpjGroup) {
        cnpjGroup.style.display = isPf ? "none" : "";
        var cnpjInput = cnpjGroup.querySelector("input");
        if (cnpjInput) cnpjInput.required = !isPf && !cnpjInput.disabled;
      }
      if (fantasiaGroup) fantasiaGroup.style.display = isPf ? "none" : "";
    }
    sel.addEventListener("change", sync);
    sync();
  }

  function setupVinculoMotorista(form) {
    var sel = form.querySelector("#vinculo, [name=vinculo]");
    var cpf = form.querySelector("#cpf, [name=cpf]");
    if (!sel || !cpf) return;
    function sync() {
      var isTerceiro = sel.value === "terceiro";
      cpf.required = isTerceiro && !cpf.disabled;
      var group = cpf.closest(".form-group");
      if (group) {
        var lbl = group.querySelector(".form-label");
        if (lbl) lbl.classList.toggle("form-label--required", isTerceiro);
      }
    }
    sel.addEventListener("change", sync);
    sync();
  }

  async function fetchJson(url) {
    var resp = await fetch(url, { headers: { Accept: "application/json" } });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    return resp.json();
  }

  function setupViaCep(form) {
    var cep = form.querySelector("#cep, [name=cep]");
    if (!cep || cep.dataset.erpCepBound) return;
    cep.dataset.erpCepBound = "1";

    cep.addEventListener("blur", async function () {
      var d = digits(cep.value);
      if (d.length !== 8) return;
      cep.classList.add("is-loading");
      try {
        var data = await fetchJson("/cadastros/cep/" + d);
        var set = function (id, val) {
          var el = form.querySelector("#" + id + ", [name=" + id + "]");
          if (el && val && !el.dataset.userEdited) el.value = val;
        };
        set("endereco", data.endereco);
        set("complemento", data.complemento);
        set("bairro", data.bairro);
        set("cidade", data.cidade);
        set("city", data.cidade);
        set("uf", data.uf);
        set("state", data.uf);
        var ufEl = form.querySelector("#uf, [name=uf], #state, [name=state]");
        if (ufEl && ufEl.tagName === "SELECT" && data.uf) {
          ufEl.value = data.uf;
          ufEl.dispatchEvent(new Event("change"));
        }
        var num = form.querySelector("#numero, [name=numero]");
        if (num) num.focus();
      } catch (_) { /* silencioso */ }
      finally { cep.classList.remove("is-loading"); }
    });
  }

  async function ensureUfSelect(form) {
    var ufEl = form.querySelector("#uf, [name=uf], #state, [name=state]");
    if (!ufEl || ufEl.tagName === "SELECT" || ufEl.dataset.erpUfConverted) return;
    ufEl.dataset.erpUfConverted = "1";
    var current = ufEl.value;
    var select = document.createElement("select");
    select.className = ufEl.className;
    select.id = ufEl.id;
    select.name = ufEl.name;
    select.innerHTML = '<option value="">Selecione a UF</option>';
    try {
      var ufs = await fetchJson("/cadastros/ibge/ufs");
      ufs.forEach(function (u) {
        var opt = document.createElement("option");
        opt.value = u.sigla;
        opt.textContent = u.sigla + " — " + u.nome;
        if (u.sigla === current.toUpperCase()) opt.selected = true;
        select.appendChild(opt);
      });
    } catch (_) {
      UFS_FALLBACK.forEach(function (sigla) {
        var opt = document.createElement("option");
        opt.value = sigla;
        opt.textContent = sigla;
        if (sigla === current.toUpperCase()) opt.selected = true;
        select.appendChild(opt);
      });
    }
    ufEl.replaceWith(select);
    return select;
  }

  async function setupIbgeCascade(form) {
    var ufEl = await ensureUfSelect(form);
    if (!ufEl) ufEl = form.querySelector("#uf, [name=uf]");
    var cidadeEl = form.querySelector("#cidade, [name=cidade], #city, [name=city]");
    if (!ufEl || !cidadeEl) return;

    var currentCity = cidadeEl.value;
    var isSelect = cidadeEl.tagName === "SELECT";

    async function loadCities() {
      var uf = ufEl.value;
      if (!uf) {
        if (isSelect) cidadeEl.innerHTML = '<option value="">Selecione a UF primeiro</option>';
        cidadeEl.disabled = true;
        return;
      }
      cidadeEl.disabled = true;
      if (!isSelect) {
        var sel = document.createElement("select");
        sel.className = cidadeEl.className;
        sel.id = cidadeEl.id;
        sel.name = cidadeEl.name;
        cidadeEl.replaceWith(sel);
        cidadeEl = sel;
        isSelect = true;
      }
      cidadeEl.innerHTML = '<option value="">Carregando...</option>';
      try {
        var cities = await fetchJson("/cadastros/ibge/municipios/" + encodeURIComponent(uf));
        cidadeEl.innerHTML = '<option value="">Selecione a cidade</option>';
        cities.forEach(function (c) {
          var opt = document.createElement("option");
          opt.value = c.nome;
          opt.textContent = c.nome;
          if (c.nome === currentCity) opt.selected = true;
          cidadeEl.appendChild(opt);
        });
        cidadeEl.disabled = false;
      } catch (_) {
        cidadeEl.innerHTML = '<option value="">Erro ao carregar cidades</option>';
      }
    }

    ufEl.addEventListener("change", loadCities);
    if (ufEl.value) loadCities();
    else if (isSelect) cidadeEl.disabled = true;
  }

  function setupMarcaModelo(form) {
    var marca = form.querySelector("#marca_id, [name=marca_id]");
    var modelo = form.querySelector("#modelo_id, [name=modelo_id]");
    if (!marca || !modelo) return;

    async function loadModelos() {
      var mid = marca.value;
      var selected = modelo.value;
      modelo.disabled = true;
      modelo.innerHTML = '<option value="">Carregando...</option>';
      if (!mid) {
        modelo.innerHTML = '<option value="">Selecione a marca primeiro</option>';
        return;
      }
      try {
        var items = await fetchJson("/frota/modelos/json?marca_id=" + encodeURIComponent(mid));
        modelo.innerHTML = '<option value="">Selecionar modelo</option>';
        items.forEach(function (m) {
          var opt = document.createElement("option");
          opt.value = m.id;
          opt.textContent = m.nome;
          if (m.id === selected) opt.selected = true;
          modelo.appendChild(opt);
        });
        modelo.disabled = false;
      } catch (_) {
        modelo.innerHTML = '<option value="">Erro ao carregar modelos</option>';
      }
    }

    marca.addEventListener("change", loadModelos);
    if (marca.value) loadModelos();
    else {
      modelo.disabled = true;
      modelo.innerHTML = '<option value="">Selecione a marca primeiro</option>';
    }
  }

  function setupFuelSlider(form) {
    var names = ["nivel_combustivel_atual", "combustivel_nivel", "combustivel_entrada", "combustivel_saida"];
    names.forEach(function (name) {
      var input = form.querySelector("#" + name + ", [name=" + name + "]");
      if (!input || input.type === "range") return;
    var group = input.closest(".form-group");
    if (!group || group.querySelector('input[type="range"]')) return;

    var range = document.createElement("input");
    range.type = "range";
    range.min = "0";
    range.max = "8";
    range.step = "1";
    range.value = input.value || "8";
    range.className = "form-range";
    range.style.marginTop = "6px";
    input.type = "number";
    input.min = "0";
    input.max = "8";
    input.style.maxWidth = "80px";

    range.addEventListener("input", function () { input.value = range.value; });
    input.addEventListener("input", function () { range.value = input.value; });
    group.appendChild(range);
    });
  }

  function setupPeriodoContrato(form) {
    var ini = form.querySelector("[name=retirada_prevista_em]");
    var fim = form.querySelector("[name=devolucao_prevista_em]");
    if (!ini || !fim) return;
    form.addEventListener("submit", function (ev) {
      if (ini.value && fim.value && new Date(fim.value) <= new Date(ini.value)) {
        ev.preventDefault();
        showFieldError(fim, "Devolução prevista deve ser posterior à retirada.");
        fim.focus();
      }
    }, true);
  }

  function setupPeriodoVigencia(form) {
    var ini = form.querySelector("[name=vigencia_inicio]");
    var fim = form.querySelector("[name=vigencia_fim]");
    if (!ini || !fim) return;
    form.addEventListener("submit", function (ev) {
      if (ini.value && fim.value && fim.value < ini.value) {
        ev.preventDefault();
        showFieldError(fim, "Vigência fim deve ser igual ou posterior ao início.");
        fim.focus();
      }
    }, true);
  }

  function setupTaxaCalculo(form) {
    var tipo = form.querySelector("#tipo_calculo, [name=tipo_calculo]");
    var valor = form.querySelector("#valor, [name=valor]");
    if (!tipo || !valor) return;
    function sync() {
      var t = tipo.value;
      if (t === "percentual") {
        valor.setAttribute("data-mask", "percent");
        valor.placeholder = "0,00 %";
      } else {
        valor.setAttribute("data-mask", "money");
        valor.setAttribute("data-money", "1");
        valor.placeholder = "R$ 0,00";
      }
      delete valor.dataset.erpMaskBound;
      bindMask(valor, t === "percentual" ? "percent" : "money");
    }
    tipo.addEventListener("change", sync);
    sync();
  }

  function validateCpf(cpf) {
    cpf = digits(cpf);
    if (cpf.length !== 11 || /^(\d)\1+$/.test(cpf)) return false;
    var sum = 0, i, rest;
    for (i = 0; i < 9; i++) sum += parseInt(cpf[i], 10) * (10 - i);
    rest = (sum * 10) % 11;
    if (rest === 10) rest = 0;
    if (rest !== parseInt(cpf[9], 10)) return false;
    sum = 0;
    for (i = 0; i < 10; i++) sum += parseInt(cpf[i], 10) * (11 - i);
    rest = (sum * 10) % 11;
    if (rest === 10) rest = 0;
    return rest === parseInt(cpf[10], 10);
  }

  function validateCnpj(cnpj) {
    cnpj = digits(cnpj);
    if (cnpj.length !== 14 || /^(\d)\1+$/.test(cnpj)) return false;
    var t = cnpj.length - 2;
    var d = cnpj.substring(t);
    var calc = function (x) {
      var n = cnpj.substring(0, x);
      var y = x - 7;
      var s = 0;
      for (var i = x; i >= 1; i--) {
        s += parseInt(n.charAt(x - i), 10) * y--;
        if (y < 2) y = 9;
      }
      return s % 11 < 2 ? 0 : 11 - (s % 11);
    };
    return calc(t) === parseInt(d.charAt(0), 10) && calc(t + 1) === parseInt(d.charAt(1), 10);
  }

  function showFieldError(input, msg) {
    input.classList.add("is-invalid");
    input.setAttribute("aria-invalid", "true");
    var errId = "err-" + (input.name || input.id || "field");
    var existing = document.getElementById(errId);
    if (!existing) {
      existing = document.createElement("div");
      existing.id = errId;
      existing.className = "form-error";
      existing.setAttribute("role", "alert");
      input.parentElement.appendChild(existing);
    }
    existing.textContent = msg;
  }

  function clearFieldError(input) {
    input.classList.remove("is-invalid");
    input.removeAttribute("aria-invalid");
    var errId = "err-" + (input.name || input.id || "field");
    var el = document.getElementById(errId);
    if (el) el.remove();
  }

  function validateForm(form) {
    var ok = true;
    form.querySelectorAll(".is-invalid").forEach(function (el) { clearFieldError(el); });

    form.querySelectorAll("[required]").forEach(function (el) {
      if (el.offsetParent === null) return;
      if (!el.value || !String(el.value).trim()) {
        showFieldError(el, "Campo obrigatório.");
        ok = false;
      }
    });

    var cpf = form.querySelector("#cpf, [name=cpf]");
    if (cpf && cpf.offsetParent !== null && digits(cpf.value).length >= 11 && !validateCpf(cpf.value)) {
      showFieldError(cpf, "CPF inválido.");
      ok = false;
    }
    var cnpj = form.querySelector("#cnpj, [name=cnpj]");
    if (cnpj && cnpj.offsetParent !== null && digits(cnpj.value).length >= 14 && !validateCnpj(cnpj.value)) {
      showFieldError(cnpj, "CNPJ inválido.");
      ok = false;
    }

    if (!ok) {
      var first = form.querySelector(".is-invalid");
      if (first) first.focus();
    }
    return ok;
  }

  function normalizeOnSubmit(form) {
    form.querySelectorAll("input, textarea").forEach(function (el) {
      var type = el.dataset.erpMaskType || detectMaskType(el);
      if (!type) return;
      if (type === "money") {
        var d = digits(el.value);
        el.value = d ? (parseInt(d, 10) / 100).toFixed(2).replace(".", ",") : "";
      } else if (type === "cpf" || type === "cnpj" || type === "cep" || type === "phone" || type === "mobile" || type === "renavam") {
        el.value = digits(el.value);
      } else if (type === "placa") {
        el.value = el.value.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
      }
    });
  }

  function setupDefaults(form) {
    var venc = form.querySelector('[name=vencimento], [name=validade_em]');
    if (venc && venc.type === "date" && !venc.value) {
      var d = new Date();
      d.setDate(d.getDate() + 30);
      venc.value = d.toISOString().slice(0, 10);
    }
    var placa = form.querySelector("#placa, [name=placa]");
    if (placa && !placa.value) placa.placeholder = "ABC1D23";
  }

  function setupFilialDevolucao(form) {
    var ret = form.querySelector("[name=filial_retirada_id]");
    var dev = form.querySelector("[name=filial_devolucao_id]");
    if (!ret || !dev) return;
    ret.addEventListener("change", function () {
      if (!dev.value && ret.value) dev.value = ret.value;
    });
  }

  function setupPeriodoReserva(form) {
    var ini = form.querySelector("[name=retirada_em]");
    var fim = form.querySelector("[name=devolucao_em]");
    if (!ini || !fim) return;
    form.addEventListener("submit", function (ev) {
      if (ini.value && fim.value && new Date(fim.value) <= new Date(ini.value)) {
        ev.preventDefault();
        showFieldError(fim, "Devolução deve ser posterior à retirada.");
        fim.focus();
      }
    }, true);
  }

  var COMBOBOX_URLS = {
    cliente: "/cadastros/clientes/json",
    fornecedor: "/cadastros/fornecedores/json",
    veiculo: "/frota/veiculos/json",
  };
  var COMBOBOX_NAMES = {
    cliente_id: "cliente",
    fornecedor_id: "fornecedor",
    veiculo_id: "veiculo",
  };

  function debounce(fn, ms) {
    var t;
    return function () {
      var args = arguments;
      var self = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(self, args); }, ms);
    };
  }

  function setupComboboxes(form) {
    form.querySelectorAll("select").forEach(function (sel) {
      if (sel.multiple || sel.dataset.erpCombobox) return;
      var type = sel.getAttribute("data-combobox") || COMBOBOX_NAMES[sel.name];
      if (!type || !COMBOBOX_URLS[type]) return;
      var force = sel.hasAttribute("data-combobox");
      if (!force && sel.options.length <= 12) return;

      sel.dataset.erpCombobox = "1";
      var wrap = document.createElement("div");
      wrap.className = "combobox-wrap";
      sel.parentNode.insertBefore(wrap, sel);
      wrap.appendChild(sel);

      var input = document.createElement("input");
      input.type = "text";
      input.className = "form-input combobox-input";
      input.placeholder = sel.options[0] ? sel.options[0].textContent.trim() : "Digite para buscar...";
      input.autocomplete = "off";
      wrap.insertBefore(input, sel);

      var list = document.createElement("div");
      list.className = "combobox-dropdown";
      list.hidden = true;
      wrap.appendChild(list);

      sel.classList.add("combobox-select-hidden");

      function selectedLabel() {
        var opt = sel.options[sel.selectedIndex];
        return opt && opt.value ? opt.textContent.trim() : "";
      }

      input.value = selectedLabel();

      function renderItems(items) {
        list.innerHTML = "";
        if (!items.length) {
          list.innerHTML = '<div class="combobox-empty">Nenhum resultado</div>';
          list.hidden = false;
          return;
        }
        items.forEach(function (item) {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "combobox-option";
          btn.textContent = item.label || item.nome || item.placa || item.id;
          btn.addEventListener("mousedown", function (e) {
            e.preventDefault();
            sel.value = item.id;
            input.value = btn.textContent;
            list.hidden = true;
            sel.dispatchEvent(new Event("change"));
          });
          list.appendChild(btn);
        });
        list.hidden = false;
      }

      var doSearch = debounce(async function () {
        var q = input.value.trim();
        var url = COMBOBOX_URLS[type] + "?q=" + encodeURIComponent(q);
        if (type === "veiculo") {
          var cat = form.querySelector("[name=categoria_id]");
          if (cat && cat.value) url += "&categoria_id=" + encodeURIComponent(cat.value);
        }
        try {
          var data = await fetchJson(url);
          renderItems(data.items || data);
        } catch (_) {
          list.innerHTML = '<div class="combobox-empty">Erro na busca</div>';
          list.hidden = false;
        }
      }, 280);

      input.addEventListener("focus", function () { doSearch(); });
      input.addEventListener("input", function () { doSearch(); });
      input.addEventListener("blur", function () {
        setTimeout(function () { list.hidden = true; }, 180);
      });
    });
  }

  function setupCategoriaVeiculoReserva(form) {
    var cat = form.querySelector("[name=categoria_id]");
    var veicSel = form.querySelector("[name=veiculo_id]");
    if (!cat || !veicSel) return;
    cat.addEventListener("change", function () {
      veicSel.value = "";
      var wrap = veicSel.closest(".combobox-wrap");
      var input = wrap ? wrap.querySelector(".combobox-input") : null;
      if (input) input.value = "";
    });
  }

  function enhanceFields(root, form) {
    if (!root) return;
    root.querySelectorAll("input.form-input, input:not([type=checkbox]):not([type=radio]):not([type=hidden]), textarea.form-input, select.form-input").forEach(function (el) {
      var type = detectMaskType(el);
      if (type) {
        el.dataset.erpMaskType = type;
        delete el.dataset.erpMaskBound;
        bindMask(el, type);
      }
    });
    if (form) setupComboboxes(form);
  }

  function enhanceForm(form) {
    if (form.dataset.erpFormEnhanced) return;
    if ((form.getAttribute("method") || "get").toUpperCase() === "GET") return;
    form.dataset.erpFormEnhanced = "1";
    form.classList.add("erp-form");
    var card = form.closest(".card");
    if (card) card.classList.add("erp-form-card");

    form.querySelectorAll("input.form-input, input:not([type=checkbox]):not([type=radio]):not([type=hidden]), textarea.form-input, select.form-input").forEach(function (el) {
      var type = detectMaskType(el);
      if (type) {
        el.dataset.erpMaskType = type;
        bindMask(el, type);
      }
    });

    markRequiredLabels(form);
    setupPersonToggle(form);
    setupVinculoMotorista(form);
    setupViaCep(form);
    setupIbgeCascade(form);
    setupMarcaModelo(form);
    setupFuelSlider(form);
    setupTaxaCalculo(form);
    setupDefaults(form);
    setupFilialDevolucao(form);
    setupPeriodoReserva(form);
    setupPeriodoContrato(form);
    setupPeriodoVigencia(form);
    setupComboboxes(form);
    setupCategoriaVeiculoReserva(form);

    form.addEventListener("submit", function (ev) {
      if (!validateForm(form)) {
        ev.preventDefault();
        return;
      }
      normalizeOnSubmit(form);
    });

    form.querySelectorAll("input, textarea, select").forEach(function (el) {
      el.addEventListener("input", function () { clearFieldError(el); });
      el.addEventListener("change", function () { clearFieldError(el); });
    });
  }

  function initAll(root) {
    (root || document).querySelectorAll("form").forEach(enhanceForm);
  }

  document.addEventListener("DOMContentLoaded", function () { initAll(document); });
  document.addEventListener("htmx:afterSwap", function (ev) { initAll(ev.detail.target); });

  window.ErpForms = { enhanceFields: enhanceFields, initAll: initAll };
})();
