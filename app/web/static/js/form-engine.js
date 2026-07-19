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
    if (name === "cep" || name === "zip_code") return "cep";
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

  function formActionsEl(form) {
    var nodes = form.querySelectorAll(".form-actions");
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].closest("form") === form) return nodes[i];
    }
    return null;
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
      var actions = formActionsEl(form);
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

  var IBGE_UFS_URL = "/referencia/ibge/ufs";
  var IBGE_MUNICIPIOS_URL = "/referencia/ibge/municipios/";
  var CEP_URL = "/referencia/cep/";

  async function fetchJson(url) {
    var resp = await fetch(url, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    return resp.json();
  }

  function setupViaCep(form) {
    var cep = form.querySelector("#cep, [name=cep], #zip_code, [name=zip_code]");
    if (!cep || cep.dataset.erpCepBound) return;
    cep.dataset.erpCepBound = "1";

    cep.addEventListener("blur", async function () {
      var d = digits(cep.value);
      if (d.length !== 8) return;
      cep.classList.add("is-loading");
      try {
        var data = await fetchJson(CEP_URL + d);
        var set = function (id, val) {
          var el = form.querySelector("#" + id + ", [name=" + id + "]");
          if (el && val && !el.dataset.userEdited) el.value = val;
        };
        set("endereco", data.endereco);
        set("address", data.endereco);
        set("complemento", data.complemento);
        set("complement", data.complemento);
        set("bairro", data.bairro);
        set("district", data.bairro);
        var ufEl = form.querySelector("#uf, [name=uf], #state, [name=state]");
        if (ufEl && data.uf) {
          ufEl.value = data.uf;
          ufEl.dispatchEvent(new Event("change"));
        }
        var cityName = data.cidade || "";
        window.setTimeout(function () {
          var cidadeEl = form.querySelector("#cidade, [name=cidade], #city, [name=city]");
          if (cidadeEl && cityName) {
            if (cidadeEl.tagName === "SELECT") {
              var found = false;
              for (var i = 0; i < cidadeEl.options.length; i++) {
                if (cidadeEl.options[i].value === cityName) {
                  cidadeEl.selectedIndex = i;
                  found = true;
                  break;
                }
              }
              if (!found) {
                var opt = document.createElement("option");
                opt.value = cityName;
                opt.textContent = cityName;
                opt.selected = true;
                cidadeEl.appendChild(opt);
              }
            } else {
              cidadeEl.value = cityName;
            }
            cidadeEl.dispatchEvent(new Event("change"));
          }
        }, 450);
        var num = form.querySelector("#numero, [name=numero], #number, [name=number]");
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
      var ufs = await fetchJson(IBGE_UFS_URL);
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
        var cities = await fetchJson(IBGE_MUNICIPIOS_URL + encodeURIComponent(uf));
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
        var manual = document.createElement("input");
        manual.type = "text";
        manual.className = cidadeEl.className;
        manual.id = cidadeEl.id;
        manual.name = cidadeEl.name;
        manual.required = cidadeEl.required;
        manual.placeholder = "Digite a cidade";
        manual.value = currentCity;
        cidadeEl.replaceWith(manual);
        cidadeEl = manual;
        isSelect = false;
        cidadeEl.disabled = false;
      }
    }

    ufEl.addEventListener("change", loadCities);
    if (ufEl.value) loadCities();
    else if (isSelect) cidadeEl.disabled = true;
  }

  async function setupIbgeMunicipioFiscal(form) {
    var wrap = form.querySelector("[data-ibge-municipio]");
    if (!wrap) return;
    var ufEl = wrap.querySelector("[name=municipio_uf]");
    var cidadeEl = wrap.querySelector("[name=municipio_nome]");
    var ibgeEl = wrap.querySelector("[name=municipio_ibge]");
    if (!ufEl || !cidadeEl) return;

    if (ufEl.tagName !== "SELECT") {
      var ufSelect = document.createElement("select");
      ufSelect.className = ufEl.className;
      ufSelect.id = ufEl.id;
      ufSelect.name = ufEl.name;
      ufSelect.required = ufEl.required;
      ufSelect.innerHTML = '<option value="">Selecione a UF</option>';
      ufEl.replaceWith(ufSelect);
      ufEl = ufSelect;
    }

    try {
      var ufs = await fetchJson(IBGE_UFS_URL);
      ufs.forEach(function (u) {
        var opt = document.createElement("option");
        opt.value = u.sigla;
        opt.textContent = u.sigla + " — " + u.nome;
        ufEl.appendChild(opt);
      });
    } catch (_) {
      UFS_FALLBACK.forEach(function (sigla) {
        var opt = document.createElement("option");
        opt.value = sigla;
        opt.textContent = sigla;
        ufEl.appendChild(opt);
      });
    }

    var currentCity = cidadeEl.value;
    var isSelect = cidadeEl.tagName === "SELECT";

    async function loadCities() {
      var uf = ufEl.value;
      if (!uf) {
        if (isSelect) cidadeEl.innerHTML = '<option value="">Selecione a UF primeiro</option>';
        if (ibgeEl) ibgeEl.value = "";
        cidadeEl.disabled = true;
        return;
      }
      cidadeEl.disabled = true;
      if (!isSelect) {
        var sel = document.createElement("select");
        sel.className = cidadeEl.className;
        sel.id = cidadeEl.id;
        sel.name = cidadeEl.name;
        sel.required = cidadeEl.required;
        cidadeEl.replaceWith(sel);
        cidadeEl = sel;
        isSelect = true;
      }
      cidadeEl.innerHTML = '<option value="">Carregando...</option>';
      try {
        var cities = await fetchJson(IBGE_MUNICIPIOS_URL + encodeURIComponent(uf));
        cidadeEl.innerHTML = '<option value="">Selecione o município</option>';
        cities.forEach(function (c) {
          var opt = document.createElement("option");
          opt.value = c.nome;
          opt.textContent = c.nome;
          opt.dataset.ibgeId = String(c.id);
          if (c.nome === currentCity) opt.selected = true;
          cidadeEl.appendChild(opt);
        });
        cidadeEl.disabled = false;
        if (ibgeEl && cidadeEl.value) {
          var selOpt = cidadeEl.options[cidadeEl.selectedIndex];
          ibgeEl.value = selOpt && selOpt.dataset.ibgeId ? selOpt.dataset.ibgeId : "";
        }
      } catch (_) {
        var manual = document.createElement("input");
        manual.type = "text";
        manual.className = cidadeEl.className;
        manual.id = cidadeEl.id;
        manual.name = cidadeEl.name;
        manual.required = cidadeEl.required;
        manual.placeholder = "Digite o município";
        manual.value = currentCity;
        cidadeEl.replaceWith(manual);
        cidadeEl = manual;
        isSelect = false;
        cidadeEl.disabled = false;
      }
    }

    function syncIbge() {
      if (!ibgeEl) return;
      var opt = cidadeEl.options[cidadeEl.selectedIndex];
      ibgeEl.value = opt && opt.dataset.ibgeId ? opt.dataset.ibgeId : "";
    }

    ufEl.addEventListener("change", loadCities);
    cidadeEl.addEventListener("change", syncIbge);
    if (ufEl.value) loadCities();
    else if (isSelect) cidadeEl.disabled = true;
  }

  function setupDestinatarioCliente(form) {
    var cliente = form.querySelector('[name=cliente_id]');
    var nome = form.querySelector('[name=destinatario_nome]');
    if (!cliente || !nome) return;
    async function sync() {
      if (!cliente.value) return;
      try {
        var data = await fetchJson("/cadastros/clientes/" + encodeURIComponent(cliente.value) + "/resumo");
        if (nome) nome.value = data.nome || "";
        var doc = form.querySelector('[name=destinatario_doc]');
        if (doc) doc.value = data.doc || "";
      } catch (_) { /* ignore */ }
    }
    cliente.addEventListener("change", sync);
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

  /** Textos de ajuda para campos não óbvios (injetados quando ausentes no template). */
  var FIELD_HELP = {
    cpf: "Informe os 11 dígitos; a máscara é aplicada automaticamente.",
    cnpj: "CNPJ da pessoa jurídica (14 dígitos).",
    cep: "Ao sair do campo, o endereço é preenchido via ViaCEP.",
    placa: "Formato Mercosul (ABC1D23) ou antigo (ABC-1234).",
    renavam: "Registro nacional do veículo (até 11 dígitos).",
    chassi: "Identificação única do veículo com 17 caracteres.",
    codigo: "Código único; não pode repetir outro registro ativo.",
    codigo_fipe: "Consulte a tabela FIPE para precificação e seguro.",
    grupo_tarifario: "Agrupa categorias na tabela de preços (ex.: Econômico).",
    limite_credito: "Valor máximo em aberto permitido para novas locações.",
    bloqueado: "Registros bloqueados exigem permissão especial para uso.",
    tipo_pessoa: "Pessoa física exige CPF; jurídica exige CNPJ e razão social.",
    municipio_ibge: "Preenchido automaticamente ao selecionar o município.",
    natureza_operacao: "Conforme legislação municipal ou estadual aplicável.",
    aliquota: "Percentual com duas casas decimais (ex.: 5,00).",
    retencao: "Marque quando o imposto for retido na fonte.",
    vigencia_inicio: "Data a partir da qual a alíquota passa a valer.",
    vigencia_fim: "Deixe vazio para vigência indeterminada.",
    justificativa: "Exigência legal: mínimo de 15 caracteres.",
    xml_file: "Arraste o arquivo XML ou clique para selecionar.",
    scopes: "Permissões concedidas à chave de API pública.",
    webhook_url: "URL HTTPS que receberá eventos assinados.",
    api_key: "Chave secreta; deixe em branco para manter a atual.",
    secret: "Credencial sensível; use o botão para exibir ou ocultar.",
    base_url: "Endpoint raiz do provedor HTTP (sem barra final).",
    timeout_ms: "Tempo máximo de espera por resposta (milissegundos).",
    retry_max: "Tentativas em caso de falha transitória.",
    filial_id: "Filial responsável pelo registro ou operação.",
    cliente_id: "Busque por nome, CPF ou CNPJ.",
    veiculo_id: "Busque por placa, modelo ou categoria.",
    fornecedor_id: "Opcional; vincula o título ao cadastro de fornecedor.",
    motorista_id: "Condutor principal vinculado à reserva ou contrato.",
    categoria_id: "Grupo tarifário do veículo (ex.: Compacto, SUV).",
    marca_id: "Selecione a marca para filtrar os modelos disponíveis.",
    modelo_id: "Modelos dependem da marca selecionada.",
    combustivel_id: "Tipo de combustível cadastrado na frota.",
    tabela_id: "Tabela de preços vigente para o período.",
    vendedor_id: "Comissionado responsável pela venda ou proposta.",
    parceiro_id: "Canal ou parceiro comercial de origem.",
    data_retirada: "Data e hora previstas para retirada do veículo.",
    data_devolucao: "Deve ser posterior à data de retirada.",
    data_inicio: "Início da vigência ou período contratual.",
    data_fim: "Término da vigência; deixe vazio se indeterminado.",
    vencimento: "Data limite para pagamento ou recebimento.",
    valor_original: "Valor nominal antes de juros, multa ou desconto.",
    valor_minimo: "Pedido mínimo para aplicar cupom ou campanha.",
    limite_uso_total: "Quantidade máxima de utilizações do cupom.",
    limite_uso_cliente: "Limite de usos por cliente (CPF/CNPJ).",
    primeira_locacao_apenas: "Restringe o benefício à primeira locação do cliente.",
    tipo_calculo: "Fixo (R$) ou percentual (%) sobre a base.",
    aplicacao: "Momento em que a taxa entra no cálculo da locação.",
    regra_codigo: "Identificador interno para automações e integrações.",
    tributavel: "Indica se compõe base de cálculo de impostos.",
    km_entrada: "Quilometragem do odômetro na entrada da oficina.",
    km_saida: "Quilometragem registrada na liberação do veículo.",
    km_livre: "Quando marcado, não há cobrança por km excedente.",
    franquia_km: "Km incluídos na diária antes de cobrança extra.",
    nivel_combustivel_atual: "Escala de 0 (vazio) a 8 (tanque cheio).",
    combustivel_entrada: "Nível do tanque na retirada (0–8).",
    combustivel_saida: "Nível do tanque na devolução (0–8).",
    forcar_disponibilidade: "Use apenas com permissão especial em conflito.",
    ait: "Número do auto de infração de trânsito.",
    codigo_infracao: "Código CTB ou equivalente do órgão autuador.",
    taxa_admin: "Taxa administrativa cobrada além do valor da multa.",
    pontuacao: "Pontos na CNH do condutor, se aplicável.",
    garantia_dias: "Prazo de garantia do serviço em dias corridos.",
    garantia_km: "Quilometragem coberta pela garantia da OS.",
    responsavel_custo: "Quem arca com o custo: locadora, cliente ou seguro.",
    is_headquarters: "Apenas uma filial pode ser marcada como matriz.",
    code: "Identificador curto da filial; não alterável após criação.",
    role_ids: "Papéis definem as permissões efetivas do usuário.",
    password: "Mínimo de 8 caracteres; use letras, números e símbolos.",
    twofa_enabled: "Autenticação em dois fatores via aplicativo TOTP.",
    periodo_inicio: "Início do intervalo considerado no relatório.",
    periodo_fim: "Fim do intervalo; deve ser igual ou posterior ao início.",
    relatorio_codigo: "Modelo de relatório a ser emitido ou agendado.",
    recorrencia: "Frequência de envio automático por e-mail.",
    email_destinatarios: "Separe vários e-mails por vírgula.",
    saldo_atual: "Saldo inicial da conta para conciliação.",
    integracao_tipo: "Provedor de extrato ou conciliação bancária.",
    item_categoria_id: "Categoria tarifária desta faixa de preço.",
    item_valor_mensal: "Valor diário equivalente para locações longas.",
    condicao: "Expressão ou campo que dispara a regra de automação.",
    acao: "Operação executada quando a condição for verdadeira.",
    ordem: "Ordem de exibição em listas e relatórios (menor primeiro).",
    imagem_url: "URL pública da imagem ilustrativa (HTTPS).",
    logo_url: "URL do logotipo da marca ou empresa.",
    capacidade_passageiros: "Número máximo de passageiros da categoria.",
    transmissao_tipica: "Tipo de câmbio usual (Manual, Automática…).",
    consumo_medio_km_l: "Consumo médio informado pelo fabricante.",
    capacidade_tanque: "Litros do tanque cheio.",
    validade_documento: "Data de vencimento para alertas automáticos.",
    telemetria_imei: "Identificador do rastreador ou telemetria.",
    proposta_validade: "Prazo de validade comercial da proposta.",
    desconto_maximo: "Percentual máximo de desconto permitido ao vendedor.",
    comissao_percentual: "Percentual de comissão sobre o valor fechado.",
    valor_caucao: "Valor de caução ou pré-autorização no cartão.",
    forma_prevista: "Forma de pagamento esperada para o título.",
    beneficiario_nome: "Use quando não houver fornecedor cadastrado.",
    storage_key: "Chave ou URL do arquivo no storage (R2/S3).",
    fase: "Classificação da foto (antes, durante, depois).",
    motivo: "Obrigatório para cancelamentos e alterações críticas.",
    override_valor: "Substitui o valor padrão do parâmetro neste escopo.",
    unidade: "Unidade de medida exibida junto ao valor (ex.: %, km).",
    email: "E-mail de acesso ao painel administrativo.",
  };

  var SKIP_HELP_NAMES = /^(nome|descricao|descrição|observacoes|observações|status|submit|csrf_token|_method)$/i;

  function fieldHelpKey(el) {
    var data = el.getAttribute("data-help");
    if (data) return data;
    var name = (el.name || el.id || "").replace(/\[\]$/, "").split(".")[0].toLowerCase();
    return name;
  }

  function syncAriaDescribedBy(input) {
    var ids = [];
    var group = input.closest(".form-group") || input.parentElement;
    if (group) {
      var help = group.querySelector(".form-help");
      if (help) {
        if (!help.id) help.id = "help-" + (input.id || input.name || "field");
        ids.push(help.id);
      }
    }
    var errId = "err-" + (input.name || input.id || "field");
    if (document.getElementById(errId)) ids.push(errId);
    if (ids.length) input.setAttribute("aria-describedby", ids.join(" "));
    else input.removeAttribute("aria-describedby");
  }

  function injectFieldHelp(form) {
    form.querySelectorAll("input, select, textarea").forEach(function (el) {
      if (el.type === "hidden" || el.type === "submit" || el.type === "button") return;
      var group = el.closest(".form-group");
      if (!group || group.querySelector(".form-help")) return;
      var key = fieldHelpKey(el);
      if (!key || SKIP_HELP_NAMES.test(key)) return;
      var text = FIELD_HELP[key];
      if (!text) return;
      var help = document.createElement("p");
      help.className = "form-help";
      help.id = "help-" + (el.id || el.name || key);
      help.textContent = text;
      group.appendChild(help);
    });
  }

  function ensureFormLegend(form) {
    if (form.querySelector(".form-legend-required")) return;
    var legend = document.createElement("p");
    legend.className = "form-legend-required";
    legend.textContent = "* Campos obrigatórios";
    var actions = formActionsEl(form);
    if (actions) form.insertBefore(legend, actions);
    else form.appendChild(legend);
  }

  function setupA11y(form) {
    var idx = 0;
    form.querySelectorAll("input, select, textarea").forEach(function (el) {
      if (el.type === "hidden" || el.type === "submit" || el.type === "button") return;
      if (!el.id) {
        var base = (el.name || el.type || "field").replace(/[^a-z0-9_-]/gi, "-").replace(/-+/g, "-");
        el.id = "fld-" + base + (idx ? "-" + idx : "");
      }
      idx += 1;
      var group = el.closest(".form-group") || el.parentElement;
      if (group) {
        var labels = group.querySelectorAll("label.form-label, label:not([for])");
        labels.forEach(function (label) {
          if (!label.htmlFor && !label.querySelector("input, select, textarea")) {
            label.htmlFor = el.id;
          }
        });
      }
      syncAriaDescribedBy(el);
    });

    form.querySelectorAll("fieldset").forEach(function (fs, i) {
      var lg = fs.querySelector("legend");
      if (lg && !lg.id) lg.id = "fs-legend-" + i;
      if (lg && lg.id) fs.setAttribute("aria-labelledby", lg.id);
    });

    form.querySelectorAll(".form-repeater-remove, .form-repeater-add, .form-repeater-row button[type=button]").forEach(function (btn) {
      if (btn.getAttribute("aria-label")) return;
      if (btn.classList.contains("form-repeater-add")) btn.setAttribute("aria-label", "Adicionar linha");
      else if (btn.classList.contains("form-repeater-remove") || btn.textContent.trim() === "×") btn.setAttribute("aria-label", "Remover linha");
    });

    form.querySelectorAll("[data-combobox]").forEach(function (el) {
      el.setAttribute("role", "combobox");
      el.setAttribute("aria-autocomplete", "list");
      if (!el.hasAttribute("aria-expanded")) el.setAttribute("aria-expanded", "false");
    });
  }

  function setupDirtyCancel(form) {
    var dirty = false;
    form.addEventListener("input", function () { dirty = true; });
    form.addEventListener("change", function () { dirty = true; });
    form.addEventListener("submit", function () { dirty = false; });
    var actions = formActionsEl(form);
    if (!actions) return;
    actions.querySelectorAll("a.btn[href], a[href].btn").forEach(function (link) {
      link.addEventListener("click", function (ev) {
        if (!dirty) return;
        if (!window.confirm("Existem alterações não salvas. Deseja sair mesmo assim?")) {
          ev.preventDefault();
        }
      });
    });
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
      var group = input.closest(".form-group") || input.parentElement;
      (group || input.parentElement).appendChild(existing);
    }
    existing.textContent = msg;
    syncAriaDescribedBy(input);
  }

  function clearFieldError(input) {
    input.classList.remove("is-invalid");
    input.removeAttribute("aria-invalid");
    var errId = "err-" + (input.name || input.id || "field");
    var el = document.getElementById(errId);
    if (el) el.remove();
    syncAriaDescribedBy(input);
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

    form.querySelectorAll("[data-minlength]").forEach(function (el) {
      if (el.offsetParent === null) return;
      var min = parseInt(el.getAttribute("data-minlength") || "0", 10);
      if (min > 0 && String(el.value || "").trim().length < min) {
        showFieldError(el, "Informe ao menos " + min + " caracteres.");
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
      var firstInvalid = form.querySelector(".is-invalid");
      if (firstInvalid && typeof firstInvalid.focus === "function") firstInvalid.focus();
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
    setupIbgeMunicipioFiscal(form);
    setupDestinatarioCliente(form);
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

    injectFieldHelp(form);
    setupA11y(form);
    ensureFormLegend(form);
    setupDirtyCancel(form);

    form.querySelectorAll("input, textarea, select").forEach(function (el) {
      el.addEventListener("input", function () { clearFieldError(el); });
      el.addEventListener("change", function () { clearFieldError(el); });
    });
  }

  function shouldEnhanceForm(form) {
    if (form.dataset.noFormEngine === "true") return false;
    if (form.closest(".navbar, .user-menu, .theme-switcher, .profile-modal, .profile-modal-backdrop")) {
      return false;
    }
    if (form.classList.contains("user-dropdown-form")) return false;
    return !!form.closest("#app-content");
  }

  function initAll(root) {
    (root || document).querySelectorAll("form").forEach(function (form) {
      if (!shouldEnhanceForm(form)) return;
      enhanceForm(form);
    });
  }

  document.addEventListener("DOMContentLoaded", function () { initAll(document); });
  document.addEventListener("htmx:afterSwap", function (ev) { initAll(ev.detail.target); });

  window.ErpForms = { enhanceFields: enhanceFields, initAll: initAll };
})();
