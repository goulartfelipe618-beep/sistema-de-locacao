/**
 * Interações das páginas institucionais (accordion, simulador, agências, formulários).
 */
(function (global) {
  'use strict';

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function initAccordions() {
    $$('[data-accordion]').forEach(function (root) {
      $$('.accordion__trigger', root).forEach(function (btn) {
        btn.addEventListener('click', function () {
          var item = btn.closest('.accordion__item');
          var panel = item?.querySelector('.accordion__panel');
          var open = btn.getAttribute('aria-expanded') === 'true';
          btn.setAttribute('aria-expanded', open ? 'false' : 'true');
          item?.classList.toggle('is-open', !open);
          if (panel) panel.hidden = open;
        });
      });
    });
  }

  function initFaqSearch() {
    var input = $('#faq-search') || $('#faq-filter');
    if (!input) return;
    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      $$('.accordion__item').forEach(function (item) {
        var text = item.textContent.toLowerCase();
        item.style.display = !q || text.indexOf(q) >= 0 ? '' : 'none';
      });
    });
  }

  var SUBSCRIPTION_BASE = { hatch: 1890, sedan: 2190, suv: 2790, pickup: 3190 };
  var SUBSCRIPTION_KM = { '1000': 0, '2000': 180, livre: 420 };

  function initSubscriptionSimulator() {
    var root = $('#subscription-simulator');
    if (!root) return;
    var cat = $('#simulator-category', root) || $('#sim-category', root);
    var km = $('#simulator-km', root) || $('#sim-km', root);
    var out = $('#simulator-price', root) || $('#sim-result', root);
    if (!cat || !km || !out) return;

    function update() {
      var base = SUBSCRIPTION_BASE[cat.value] || SUBSCRIPTION_BASE.hatch;
      var extra = SUBSCRIPTION_KM[km.value] || 0;
      var total = base + extra;
      out.textContent = 'R$ ' + total.toLocaleString('pt-BR');
    }

    cat.addEventListener('change', update);
    km.addEventListener('change', update);
    update();
  }

  function initLeadForms() {
    $$('[data-lead-form]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var msg = form.querySelector('.form-message') || $('#lead-message');
        if (msg) {
          msg.textContent = 'Solicitação enviada! Nossa equipe entrará em contato em breve.';
          msg.classList.add('is-success');
        }
        form.reset();
      });
    });

    var pfPjToggle = $('[data-lead-type-toggle]');
    var docLabel = $('#lead-doc-label');
    var docInput = $('#lead-doc') || $('#lead-documento');
    var tipoHidden = $('#lead-tipo-pessoa');

    if (pfPjToggle && docLabel && docInput) {
      function setTipo(isPj) {
        $$('[data-lead-type]', pfPjToggle).forEach(function (btn) {
          var pj = btn.getAttribute('data-lead-type') === 'pj';
          var active = pj === isPj;
          btn.classList.toggle('is-active', active);
          btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
        if (tipoHidden) tipoHidden.value = isPj ? 'pj' : 'pf';
        docLabel.textContent = isPj ? 'CNPJ' : 'CPF';
        docInput.placeholder = isPj ? '00.000.000/0001-00' : '000.000.000-00';
        docInput.name = isPj ? 'cnpj' : 'cpf';
      }
      $$('[data-lead-type]', pfPjToggle).forEach(function (btn) {
        btn.addEventListener('click', function () {
          setTipo(btn.getAttribute('data-lead-type') === 'pj');
        });
      });
    } else {
      var pfPj = $('#lead-tipo-pf');
      var pjBtn = $('#lead-tipo-pj');
      if (pfPj && pjBtn && docLabel && docInput) {
        function setTipoLegacy(isPj) {
          pfPj.classList.toggle('is-active', !isPj);
          pjBtn.classList.toggle('is-active', isPj);
          docLabel.textContent = isPj ? 'CNPJ' : 'CPF';
          docInput.placeholder = isPj ? '00.000.000/0001-00' : '000.000.000-00';
          docInput.name = isPj ? 'cnpj' : 'cpf';
        }
        pfPj.addEventListener('click', function () {
          setTipoLegacy(false);
        });
        pjBtn.addEventListener('click', function () {
          setTipoLegacy(true);
        });
      }
    }
  }

  function initFidelityForm() {
    var form = $('#fidelity-signup-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var msg = $('#fidelity-message');
      if (msg) {
        msg.textContent = 'Cadastro realizado! Bem-vindo ao Clube Rodavia.';
        msg.classList.add('is-success');
      }
      form.reset();
    });
  }

  function escapeHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function agencyCardHtml(f) {
    var name = f.nome || f.trade_name || f.razao_social || 'Agência';
    var addr =
      f.endereco_formatado ||
      [f.logradouro, f.numero, f.bairro, f.cidade, f.uf].filter(Boolean).join(', ') ||
      'Endereço sob consulta';
    var tel = f.telefone || f.phone || '';
    var mapsQ = encodeURIComponent(addr);
    return (
      '<article class="agency-card" data-agency-card>' +
      '<h3 class="agency-card__title">' +
      escapeHtml(name) +
      '</h3>' +
      '<p class="agency-card__address">' +
      escapeHtml(addr) +
      '</p>' +
      '<p class="agency-card__hours"><span data-i18n="page.agencies.hours">Horário:</span> Seg–Sáb 8h às 18h</p>' +
      (tel
        ? '<p class="agency-card__phone"><a href="tel:' +
          escapeHtml(tel.replace(/\D/g, '')) +
          '">' +
          escapeHtml(tel) +
          '</a></p>'
        : '') +
      '<p class="agency-card__actions">' +
      '<a class="btn btn--secondary btn--sm" href="https://wa.me/5500000000000" target="_blank" rel="noopener">WhatsApp</a> ' +
      '<a class="btn btn--primary btn--sm" href="https://www.google.com/maps/search/?api=1&query=' +
      mapsQ +
      '" target="_blank" rel="noopener" data-i18n="page.agencies.directions">Como chegar</a>' +
      '</p>' +
      '</article>'
    );
  }

  function initAgencyList() {
    var list = $('#agency-list');
    var filter = $('#agency-filter');
    if (!list) return;

    function render(filiais) {
      var items = filiais || [];
      if (!items.length) {
        list.innerHTML =
          '<p class="agency-list__empty" data-i18n="page.agencies.empty">Nenhuma agência encontrada.</p>';
        if (global.SiteI18n) global.SiteI18n.apply(list);
        return;
      }
      list.innerHTML = items.map(agencyCardHtml).join('');
      if (global.SiteI18n) global.SiteI18n.apply(list);
    }

    function loadFromErp() {
      if (!global.RodaviaBind) return;
      global.RodaviaBind.boot().then(function (result) {
        var catalog = result && result.catalog;
        var filiais = catalog && catalog.filiais;
        if (!filiais && global.RodaviaBind.normalizeList) {
          return;
        }
        var all = global.RodaviaBind.normalizeList(filiais || []);
        list._allAgencies = all;
        render(all);
      });
    }

    if (filter) {
      filter.addEventListener('input', function () {
        var q = filter.value.trim().toLowerCase();
        var all = list._allAgencies || [];
        if (!q) {
          render(all);
          return;
        }
        render(
          all.filter(function (f) {
            return JSON.stringify(f).toLowerCase().indexOf(q) >= 0;
          })
        );
      });
    }

    if ($('[data-agency-placeholder]', list)) {
      loadFromErp();
    } else {
      loadFromErp();
    }
  }

  function initGroupFilters() {
    var panel = $('#groups-filters');
    if (!panel) return;

    panel.addEventListener('change', function () {
      document.dispatchEvent(new CustomEvent('groups:filter-change'));
    });
  }

  function bootChrome() {
    if (!global.SiteChrome) return Promise.resolve();
    var mode = document.body.getAttribute('data-site-chrome') || '';
    if (mode === 'footer') {
      global.SiteChrome.injectFooter();
      if (global.SiteI18n && typeof global.SiteI18n.apply === 'function') {
        global.SiteI18n.apply();
      }
      return global.RodaviaBind && typeof global.RodaviaBind.boot === 'function'
        ? global.RodaviaBind.boot()
        : Promise.resolve();
    }
    return global.SiteChrome.init();
  }

  function bootPage() {
    initAccordions();
    initFaqSearch();
    initSubscriptionSimulator();
    initLeadForms();
    initFidelityForm();
    initAgencyList();
    initGroupFilters();

    if (global.SiteChat && typeof global.SiteChat.init === 'function') {
      global.SiteChat.init();
    }

    bootChrome();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootPage);
  } else {
    bootPage();
  }
})(window);
