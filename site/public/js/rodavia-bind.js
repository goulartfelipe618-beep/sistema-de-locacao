/**
 * Liga RodaviaAPI aos seletores do HTML (sem alterar layout/CSS).
 * Depende de: rodavia-cache.js, rodavia-config.js, rodavia-api.js
 */
(function (global) {
  var SELECTORS = {
    bffStatus: '#bff-status',
    brandLogoImg: '#brand-logo-img',
    pickupLocation: '#pickup-location',
    searchForm: '#search-form',
    searchStatus: '#search-status',
    fleetTrack: '#fleet-track',
    fleetShowcase: '#fleet-showcase',
    fleetEmpty: '#fleet-empty',
    fleetAllGroupsLink: '#fleet-all-groups-link',
    reserveModal: '#reserve-modal',
    reserveForm: '#reserve-form',
    reserveCategoriaId: '#reserve-categoria-id',
    reserveNome: '#reserve-nome',
    reserveEmail: '#reserve-email',
    reserveCpf: '#reserve-cpf',
    reserveTelefone: '#reserve-telefone',
    reserveCotacao: '#reserve-cotacao',
    reserveMessage: '#reserve-message',
    pickupDate: '#pickup-date',
    pickupTime: '#pickup-time',
    returnDate: '#return-date',
    returnTime: '#return-time',
  };

  var SEARCH_STATE_KEY = 'rodavia_last_search';
  var bootPromise = null;

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function escapeHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function normalizeList(payload) {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.items)) return payload.items;
    if (payload && Array.isArray(payload.data)) return payload.data;
    if (payload && Array.isArray(payload.filiais)) return payload.filiais;
    if (payload && Array.isArray(payload.grupos)) return payload.grupos;
    return [];
  }

  function normalizeSlidesList(payload) {
    if (Array.isArray(payload)) return payload;
    if (payload?.items && Array.isArray(payload.items)) return payload.items;
    if (payload?.slides && Array.isArray(payload.slides)) return payload.slides;
    return [];
  }

  function setReady(isReady) {
    var root = document.documentElement;
    if (isReady) {
      root.classList.add('erp-ready');
      root.classList.remove('erp-loading');
    } else {
      root.classList.add('erp-loading');
      root.classList.remove('erp-ready');
    }
  }

  function setText(selector, value) {
    if (value == null || value === '') return;
    $$(selector).forEach(function (el) {
      if (el.tagName === 'A' && el.getAttribute('href') && el.getAttribute('href').indexOf('mailto:') === 0) {
        el.href = 'mailto:' + value;
        el.textContent = value;
      } else if (el.tagName === 'A' && el.getAttribute('href') && el.getAttribute('href').indexOf('tel:') === 0) {
        el.href = 'tel:' + String(value).replace(/\D/g, '');
        el.textContent = value;
      } else {
        el.textContent = value;
      }
    });
  }

  function filialLabel(f) {
    var nome = f.nome || f.descricao || 'Filial';
    var cidade = f.cidade || f.municipio;
    var uf = f.uf || f.estado;
    if (cidade && uf) return nome + ' — ' + cidade + '/' + uf;
    return nome;
  }

  function applyEmpresa(empresa) {
    if (!empresa || typeof empresa !== 'object') return;

    if (empresa.logo_url) {
      var mark = $('.logo__mark');
      var img = $(SELECTORS.brandLogoImg);
      if (img) {
        img.src = empresa.logo_url;
        img.alt = empresa.nome_exibicao || '';
        img.hidden = false;
        if (mark) mark.setAttribute('hidden', '');
      } else if (mark) {
        mark.style.backgroundImage = 'url(' + empresa.logo_url + ')';
        mark.style.backgroundSize = 'cover';
        mark.textContent = '';
      }
    }

    setText('.logo__text[data-erp="nome_exibicao"]', empresa.nome_exibicao);
    setText('[data-erp="cnpj"]', empresa.cnpj_formatado);
    setText('[data-erp="endereco"]', empresa.endereco_formatado);
    setText('[data-erp="email"]', empresa.email);
    setText('[data-erp="telefone"]', empresa.telefone || empresa.telefone_formatado);

    if (empresa.nome_exibicao) {
      $$('.logo[aria-label]').forEach(function (el) {
        el.setAttribute('aria-label', 'Página inicial ' + empresa.nome_exibicao);
      });
      if (document.title.indexOf('|') >= 0) {
        var parts = document.title.split('|');
        if (parts.length >= 2) {
          document.title = parts[0].trim() + ' | ' + empresa.nome_exibicao;
        }
      }
    }
  }

  function populateFiliaisSelect(filiaisPayload, selectId) {
    var id = selectId || 'pickup-location';
    var select = document.getElementById(id);
    if (!select) return;
    var filiais = normalizeList(filiaisPayload);
    if (!filiais.length) {
      select.innerHTML = '<option value="">Nenhuma filial disponível</option>';
      select.disabled = true;
      return;
    }
    select.disabled = false;
    select.innerHTML =
      '<option value="">Onde você quer retirar o carro?</option>' +
      filiais
        .map(function (f) {
          var fid = f.id || f.filial_id;
          if (!fid) return '';
          return '<option value="' + fid + '">' + filialLabel(f) + '</option>';
        })
        .join('');
  }

  function heroSlideMarkup(slide, isActive) {
    if (!global.RodaviaAPI || !slide?.id) return '';
    var rawUrl = slide.imagem_url || '';
    var useBff =
      !rawUrl || rawUrl.indexOf('/api/') === 0 || rawUrl.indexOf('/bff/') === 0;
    var imgUrl = useBff ? global.RodaviaAPI.slideImagemUrl(slide.id) : rawUrl;
    var label = escapeHtml(slide.titulo || 'Destaque promocional');
    var activeClass = isActive ? ' is-active' : '';
    var style = 'background-image:url("' + String(imgUrl).replace(/"/g, '%22') + '")';
    var erpClass = ' hero__slide--erp';
    if (slide.link_url) {
      return (
        '<a href="' +
        escapeHtml(slide.link_url) +
        '" class="hero__slide hero__slide--linked' +
        erpClass +
        activeClass +
        '" role="img" aria-label="' +
        label +
        '" style="' +
        style +
        '"></a>'
      );
    }
    return (
      '<div class="hero__slide' +
      erpClass +
      activeClass +
      '" role="img" aria-label="' +
      label +
      '" style="' +
      style +
      '"></div>'
    );
  }

  function applyHeroSlides(slidesPayload) {
    var slidesRoot = $('#hero-slides');
    var dotsRoot = $('#hero-dots');
    if (!slidesRoot) return false;

    var slides = normalizeSlidesList(slidesPayload)
      .slice()
      .sort(function (a, b) {
        return (a.ordem ?? 0) - (b.ordem ?? 0);
      });

    if (!slides.length) {
      slidesRoot.innerHTML =
        '<div class="hero__slide hero__slide--fallback is-active" role="img" aria-label="Aluguel de carros"></div>';
      if (dotsRoot) {
        dotsRoot.innerHTML = '';
        dotsRoot.setAttribute('hidden', '');
      }
      return false;
    }

    slidesRoot.innerHTML = slides.map(function (s, i) {
      return heroSlideMarkup(s, i === 0);
    }).join('');
    slidesRoot.classList.remove('hero__slides--loading');

    if (dotsRoot) {
      dotsRoot.innerHTML = slides
        .map(function (_, i) {
          return (
            '<button type="button" class="hero__dot' +
            (i === 0 ? ' is-active' : '') +
            '" role="tab" aria-selected="' +
            (i === 0 ? 'true' : 'false') +
            '" aria-label="Slide ' +
            (i + 1) +
            '"></button>'
          );
        })
        .join('');
      if (slides.length > 1) dotsRoot.removeAttribute('hidden');
      else dotsRoot.setAttribute('hidden', '');
    }
    return true;
  }

  function applyCatalog(catalog) {
    if (!catalog || typeof catalog !== 'object') return;
    if (catalog.empresa) applyEmpresa(catalog.empresa);
    if (catalog.filiais) populateFiliaisSelect(catalog.filiais);
    if (catalog.slides) applyHeroSlides(catalog.slides);
  }

  function hydrateFromCache() {
    var cache = global.RodaviaCache && global.RodaviaCache.read();
    if (!cache) return false;
    applyCatalog(cache);
    setReady(true);
    return true;
  }

  function mapGruposToFleet(gruposPayload) {
    return normalizeList(gruposPayload)
      .map(function (g) {
        return {
          categoria_id: g.categoria_id || g.id,
          nome: g.nome,
          descricao: g.descricao,
          imagem_url: g.imagem_url,
          veiculosCount: g.veiculos_disponiveis != null ? g.veiculos_disponiveis : g.disponiveis,
          passageiros: g.capacidade_passageiros != null ? g.capacidade_passageiros : g.passageiros,
          codigo: g.codigo || g.sigla,
        };
      })
      .filter(function (g) {
        return g.categoria_id;
      });
  }

  function api() {
    if (!global.RodaviaAPI) {
      throw new Error('RodaviaAPI não carregado. Inclua rodavia-api.js antes de rodavia-bind.js.');
    }
    return global.RodaviaAPI;
  }

  function waitForBff(maxMs) {
    maxMs = maxMs || 3000;
    if (global.RODAVIA_BFF_READY === true) return Promise.resolve(true);
    if (global.RODAVIA_BFF_READY === false) return Promise.resolve(false);
    var start = Date.now();
    return new Promise(function (resolve) {
      (function tick() {
        if (global.RODAVIA_BFF_READY === true) {
          resolve(true);
          return;
        }
        if (global.RODAVIA_BFF_READY === false || Date.now() - start >= maxMs) {
          resolve(false);
          return;
        }
        setTimeout(tick, 30);
      })();
    });
  }

  function restoreFilialFromSearchState() {
    try {
      var saved = localStorage.getItem(SEARCH_STATE_KEY);
      if (!saved) return;
      var p = JSON.parse(saved);
      var sel = document.getElementById('pickup-location');
      if (sel && p.filial_id) sel.value = p.filial_id;
    } catch (_) {
      /* ignore */
    }
  }

  function setApiStatus(ok) {
    var statusEl = $(SELECTORS.bffStatus);
    if (!statusEl) return;
    statusEl.textContent = ok ? 'API conectada' : 'API offline';
    statusEl.classList.toggle('is-ok', ok);
    statusEl.classList.toggle('is-off', !ok);
  }

  async function boot() {
    if (bootPromise) return bootPromise;

    bootPromise = (async function () {
      hydrateFromCache();

      var bffOk = await waitForBff();
      if (!bffOk) {
        setApiStatus(false);
        setReady(hydrateFromCache());
        return { erpOk: false, fromCache: false };
      }

      try {
        var catalog = await api().catalog();
        applyCatalog(catalog);
        if (global.RodaviaCache) {
          global.RodaviaCache.write(catalog);
        }
        restoreFilialFromSearchState();
        setApiStatus(true);
        setReady(true);
        global.RodaviaBind._booted = true;
        return { erpOk: true, catalog: catalog };
      } catch (err) {
        console.warn('[Rodavia] Falha ao carregar catálogo:', err?.message || err);
        var hadCache = hydrateFromCache();
        setApiStatus(hadCache);
        setReady(hadCache);
        return { erpOk: hadCache, fromCache: hadCache };
      }
    })();

    return bootPromise;
  }

  global.RodaviaBind = {
    SELECTORS: SELECTORS,
    SEARCH_STATE_KEY: SEARCH_STATE_KEY,
    normalizeList: normalizeList,
    applyEmpresa: applyEmpresa,
    populateFiliaisSelect: populateFiliaisSelect,
    applyHeroSlides: applyHeroSlides,
    applyCatalog: applyCatalog,
    mapGruposToFleet: mapGruposToFleet,
    boot: boot,
    _booted: false,
    pingOk: function () {
      return api()
        .ping()
        .then(function () {
          return true;
        })
        .catch(function () {
          return false;
        });
    },
    grupos: function (params) {
      return api().grupos(params);
    },
    cotacao: function (body) {
      return api().cotacao(body);
    },
    reservar: function (body) {
      return api().reservar(body);
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);

(function earlyCatalog() {
  var w = typeof window !== 'undefined' ? window : globalThis;
  if (typeof document === 'undefined' || !w.RodaviaBind) return;
  var cached = w.RodaviaCache && w.RodaviaCache.read();
  if (cached) {
    w.RodaviaBind.applyCatalog(cached);
    document.documentElement.classList.add('erp-ready');
    document.documentElement.classList.remove('erp-loading');
  }
  w.RodaviaBind.boot();
})();
