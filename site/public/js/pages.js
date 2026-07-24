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
    var root = $('#loyalty-tiers-root');
    if (!root) return;

    function renderTiers(fidelidade) {
      var loading = $('#loyalty-tiers-loading');
      if (loading) loading.remove();

      if (!fidelidade || !fidelidade.ativo) {
        root.innerHTML =
          '<p class="tier-table__empty" data-i18n="page.loyalty.tiers_inactive">' +
          'Programa de fidelidade indisponível no momento. Consulte nossa equipe.' +
          '</p>';
        if (global.SiteI18n) global.SiteI18n.apply(root);
        return;
      }

      var regra = fidelidade.regra || {};
      var tiers = fidelidade.tiers || [];
      var summary = $('#loyalty-regra-summary');
      if (summary && regra.pontos_por_real != null) {
        var ptsReal = Number(regra.pontos_por_real);
        var ptsDiaria = Number(regra.pontos_por_diaria || 0);
        summary.textContent =
          'Ganhe ' +
          ptsReal.toLocaleString('pt-BR') +
          ' ponto(s) por R$ 1,00' +
          (ptsDiaria > 0 ? ' e ' + ptsDiaria.toLocaleString('pt-BR') + ' por diária' : '') +
          (regra.validade_meses
            ? '. Pontos válidos por ' + regra.validade_meses + ' meses.'
            : '.');
        summary.hidden = false;
      }

      if (!tiers.length) {
        root.innerHTML =
          '<p class="tier-table__empty" data-i18n="page.loyalty.tiers_empty">' +
          'Níveis do programa serão publicados em breve.' +
          '</p>';
        if (global.SiteI18n) global.SiteI18n.apply(root);
        return;
      }

      var rows =
        '<table class="tier-table">' +
        '<caption class="visually-hidden" data-i18n="page.loyalty.tiers_caption">' +
        'Níveis e benefícios do programa de fidelidade' +
        '</caption>' +
        '<thead><tr>' +
        '<th scope="col" data-i18n="page.loyalty.col_level">Nível</th>' +
        '<th scope="col" data-i18n="page.loyalty.col_points_min">Pontos mínimos</th>' +
        '<th scope="col" data-i18n="page.loyalty.col_benefit">Benefícios</th>' +
        '</tr></thead><tbody>';

      tiers.forEach(function (tier) {
        rows +=
          '<tr><th scope="row">' +
          escapeHtml(tier.nome || '—') +
          '</th><td>' +
          escapeHtml(String(tier.pontos_minimos != null ? tier.pontos_minimos : '—')) +
          '</td><td>' +
          escapeHtml(tier.beneficio || tier.beneficio_descricao || '—') +
          '</td></tr>';
      });

      rows += '</tbody></table>';
      root.innerHTML = rows;
      if (global.SiteI18n) global.SiteI18n.apply(root);
    }

    function load() {
      if (!global.RodaviaBind) return;
      global.RodaviaBind.boot().then(function (result) {
        var catalog = result && result.catalog;
        renderTiers(catalog && catalog.fidelidade);
      });
    }

    load();
  }

  function loadStylesheet(href, id) {
    if (id && document.getElementById(id)) return Promise.resolve();
    return new Promise(function (resolve, reject) {
      var link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      if (id) link.id = id;
      link.onload = function () {
        resolve();
      };
      link.onerror = reject;
      document.head.appendChild(link);
    });
  }

  function loadScript(src, id) {
    if (id && document.getElementById(id)) return Promise.resolve();
    return new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      script.src = src;
      if (id) script.id = id;
      script.onload = function () {
        resolve();
      };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  var agencyMapState = {
    map: null,
    markers: [],
    filiais: [],
  };

  function clearAgencyMarkers() {
    agencyMapState.markers.forEach(function (marker) {
      marker.remove();
    });
    agencyMapState.markers = [];
  }

  function addAgencyMarkers(map, filiais) {
    if (!map || !global.mapboxgl) return;
    clearAgencyMarkers();
    var bounds = new global.mapboxgl.LngLatBounds();
    var withCoords = 0;

    filiais.forEach(function (f) {
      var lat = f.latitude != null ? Number(f.latitude) : NaN;
      var lng = f.longitude != null ? Number(f.longitude) : NaN;
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
      withCoords += 1;

      var el = document.createElement('button');
      el.type = 'button';
      el.className = 'agency-marker' + (f.matriz || f.is_headquarters ? ' agency-marker--matriz' : '');
      el.setAttribute('aria-label', f.nome || 'Agência');

      var popupHtml =
        '<div class="agency-popup">' +
        '<strong>' +
        escapeHtml(f.nome || 'Agência') +
        '</strong>' +
        (f.endereco_formatado
          ? '<p>' + escapeHtml(f.endereco_formatado) + '</p>'
          : '') +
        '</div>';

      var marker = new global.mapboxgl.Marker({ element: el, anchor: 'bottom' })
        .setLngLat([lng, lat])
        .setPopup(new global.mapboxgl.Popup({ offset: 24 }).setHTML(popupHtml))
        .addTo(map);

      el.addEventListener('click', function () {
        var card = document.querySelector('[data-agency-id="' + f.id + '"]');
        if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });

      agencyMapState.markers.push(marker);
      bounds.extend([lng, lat]);
    });

    if (withCoords > 0) {
      map.fitBounds(bounds, { padding: 56, maxZoom: 14, duration: 0 });
    } else {
      map.setCenter([-47.8825, -15.7942]);
      map.setZoom(4);
    }
  }

  function initAgencyMap(token, filiais) {
    var mapEl = $('#agency-map');
    if (!mapEl) return Promise.resolve();

    if (!token) {
      mapEl.innerHTML =
        '<p class="agency-map__placeholder" data-i18n="page.agencies.map_token_missing">' +
        'Configure o token Mapbox em Integrações → Website no ERP para exibir o mapa interativo.' +
        '</p>';
      if (global.SiteI18n) global.SiteI18n.apply(mapEl);
      return Promise.resolve();
    }

    return loadStylesheet('https://api.mapbox.com/mapbox-gl-js/v3.3.0/mapbox-gl.css', 'mapbox-gl-css')
      .then(function () {
        return loadStylesheet(
          'https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-geocoder/v5.0.2/mapbox-gl-geocoder.css',
          'mapbox-geocoder-css'
        );
      })
      .then(function () {
        return loadScript('https://api.mapbox.com/mapbox-gl-js/v3.3.0/mapbox-gl.js', 'mapbox-gl-js');
      })
      .then(function () {
        return loadScript(
          'https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-geocoder/v5.0.2/mapbox-gl-geocoder.min.js',
          'mapbox-geocoder-js'
        );
      })
      .then(function () {
        global.mapboxgl.accessToken = token;
        var map = new global.mapboxgl.Map({
          container: 'agency-map',
          style: 'mapbox://styles/mapbox/streets-v12',
          center: [-47.8825, -15.7942],
          zoom: 4,
        });
        map.addControl(new global.mapboxgl.NavigationControl(), 'top-right');
        agencyMapState.map = map;
        agencyMapState.filiais = filiais || [];

        map.on('load', function () {
          addAgencyMarkers(map, agencyMapState.filiais);
        });

        var geocoderHost = $('#agency-geocoder');
        if (geocoderHost && global.MapboxGeocoder) {
          var geocoder = new global.MapboxGeocoder({
            accessToken: token,
            mapboxgl: global.mapboxgl,
            marker: false,
            placeholder: 'Busque por cidade, bairro ou endereço…',
            language: 'pt-BR',
            countries: 'br',
            bbox: [-73.99, -33.75, -34.79, 5.27],
          });
          geocoderHost.appendChild(geocoder.onAdd(map));

          geocoder.on('result', function () {
            var list = $('#agency-list');
            if (list && list._filterAgencies) list._filterAgencies('');
          });

          var geocoderInput = geocoderHost.querySelector('.mapboxgl-ctrl-geocoder--input');
          if (geocoderInput) {
            geocoderInput.setAttribute('aria-label', 'Buscar agência por endereço');
            geocoderInput.addEventListener('input', function () {
              var list = $('#agency-list');
              if (list && list._filterAgencies) {
                list._filterAgencies(geocoderInput.value.trim().toLowerCase());
              }
            });
          }
        } else {
          var fallback = $('#agency-filter');
          if (fallback) fallback.hidden = false;
        }
      })
      .catch(function () {
        mapEl.innerHTML =
          '<p class="agency-map__placeholder" data-i18n="page.agencies.map_load_error">' +
          'Não foi possível carregar o mapa. Tente recarregar a página.' +
          '</p>';
        if (global.SiteI18n) global.SiteI18n.apply(mapEl);
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
    var matrizBadge =
      f.matriz || f.is_headquarters
        ? ' <span class="agency-card__badge" data-i18n="page.agencies.headquarters">Matriz</span>'
        : '';
    var addr =
      f.endereco_formatado ||
      [f.logradouro, f.numero, f.bairro, f.cidade, f.uf].filter(Boolean).join(', ') ||
      'Endereço sob consulta';
    var tel = f.telefone || f.phone || '';
    var mapsQ = encodeURIComponent(addr);
    var idAttr = f.id ? ' data-agency-id="' + escapeHtml(f.id) + '"' : '';
    return (
      '<article class="agency-card"' +
      idAttr +
      ' data-agency-card>' +
      '<h3 class="agency-card__name">' +
      escapeHtml(name) +
      matrizBadge +
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

    function filterAgencies(q) {
      var all = list._allAgencies || [];
      if (!q) {
        render(all);
        if (agencyMapState.map) addAgencyMarkers(agencyMapState.map, all);
        return;
      }
      var filtered = all.filter(function (f) {
        return JSON.stringify(f).toLowerCase().indexOf(q) >= 0;
      });
      render(filtered);
      if (agencyMapState.map) addAgencyMarkers(agencyMapState.map, filtered);
    }

    list._filterAgencies = filterAgencies;

    function loadFromErp() {
      if (!global.RodaviaBind) return;
      global.RodaviaBind.boot().then(function (result) {
        var catalog = result && result.catalog;
        var filiais = catalog && catalog.filiais;
        var all = global.RodaviaBind.normalizeList(filiais || []);
        list._allAgencies = all;
        render(all);

        var token =
          catalog &&
          catalog.empresa &&
          catalog.empresa.tema &&
          catalog.empresa.tema.mapbox &&
          catalog.empresa.tema.mapbox.access_token;
        initAgencyMap(token, all);
      });
    }

    if (filter) {
      filter.addEventListener('input', function () {
        filterAgencies(filter.value.trim().toLowerCase());
      });
    }

    loadFromErp();
  }

  function initGroupFilters() {
    var panel = $('#groups-filters');
    if (!panel) return;

    panel.addEventListener('change', function (e) {
      var target = e.target;
      if (!target || !target.name) return;
      var source = target.name === 'tarifa' ? 'tariff' : 'attribute';
      document.dispatchEvent(
        new CustomEvent('groups:filter-change', { detail: { source: source } })
      );
    });
  }

  function bootChrome() {
    if (!global.SiteChrome) return Promise.resolve();
    var mode = document.body.getAttribute('data-site-chrome') || '';
    if (mode === 'footer') {
      global.SiteChrome.injectFooter();
      global.SiteChrome.ensureGlobalWidgets();
      global.SiteChrome.initBackToTop();
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
