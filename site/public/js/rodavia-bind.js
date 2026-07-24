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
      root.classList.remove('erp-boot-fallback');
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

  function applySiteTheme(tema) {
    if (!tema || !tema.css || typeof tema.css !== 'object') return;
    var root = document.documentElement;
    Object.keys(tema.css).forEach(function (key) {
      var value = tema.css[key];
      if (value != null && value !== '') {
        root.style.setProperty(key, value);
      }
    });
    root.classList.add('erp-theme-ready');
    if (global.RodaviaCache && typeof global.RodaviaCache.persistThemeCss === 'function') {
      global.RodaviaCache.persistThemeCss(tema.css);
    } else {
      try {
        localStorage.setItem('rodavia_theme_v1', JSON.stringify(tema.css));
      } catch (_) {
        /* ignore */
      }
    }
  }

  function applyEmpresa(empresa) {
    if (!empresa || typeof empresa !== 'object') return;

    if (empresa.tema) applySiteTheme(empresa.tema);

    var img = $(SELECTORS.brandLogoImg);
    var mark = $('.logo__mark');
    if (img) {
      img.removeAttribute('src');
      img.hidden = true;
    }
    if (mark) {
      mark.removeAttribute('hidden');
      mark.textContent = '';
      mark.style.backgroundImage = '';
    }

    setText('.logo__text[data-erp="nome_exibicao"]', empresa.nome_exibicao);
    setText('[data-erp="cnpj"]', empresa.cnpj_formatado);
    setText('[data-erp="endereco"]', empresa.endereco_formatado);
    setText('[data-erp="email"]', empresa.email);
    setText('[data-erp="telefone"]', empresa.telefone || empresa.telefone_formatado);

    if (empresa.nome_exibicao) {
      $$('.logo[aria-label]').forEach(function (el) {
        el.setAttribute('aria-label', i18n('nav.home_page', { name: empresa.nome_exibicao }));
      });
      if (document.title.indexOf('|') >= 0) {
        var parts = document.title.split('|');
        if (parts.length >= 2) {
          document.title = parts[0].trim() + ' | ' + empresa.nome_exibicao;
        }
      }
    }
  }

  function i18n(key, vars) {
    if (global.SiteI18n && global.SiteI18n.t) return global.SiteI18n.t(key, vars);
    return key;
  }

  var lastFiliaisPayload = null;

  function populateFiliaisSelect(filiaisPayload, selectId) {
    lastFiliaisPayload = filiaisPayload;
    var id = selectId || 'pickup-location';
    var select = document.getElementById(id);
    if (!select) return;
    var filiais = normalizeList(filiaisPayload);
    if (!filiais.length) {
      select.innerHTML = '<option value="" data-i18n="branches.none"></option>';
      select.disabled = true;
      if (global.SiteI18n) global.SiteI18n.apply(select);
      return;
    }
    select.disabled = false;
    select.innerHTML =
      '<option value="" data-i18n="search.pickup_prompt"></option>' +
      filiais
        .map(function (f) {
          var fid = f.id || f.filial_id;
          if (!fid) return '';
          return '<option value="' + fid + '">' + filialLabel(f) + '</option>';
        })
        .join('');
    if (global.SiteI18n) global.SiteI18n.apply(select);
  }

  function slideId(slide) {
    if (!slide || typeof slide !== 'object') return '';
    return slide.id || slide.slide_id || '';
  }

  function slideImgTag(networkUrl, label, isActive) {
    var safeUrl = escapeHtml(networkUrl);
    var safeLabel = escapeHtml(label);
    return (
      '<img class="hero__slide-img" src="' +
      safeUrl +
      '" data-network-src="' +
      safeUrl +
      '" alt="' +
      safeLabel +
      '" decoding="async"' +
      (isActive ? ' loading="eager" fetchpriority="high"' : ' loading="lazy"') +
      ' onerror="window.__rodaviaHeroImgFallback&&window.__rodaviaHeroImgFallback(this)" />'
    );
  }

  if (typeof global !== 'undefined') {
    global.__rodaviaHeroImgFallback = function (img) {
      if (!img) return;
      var fallback = img.getAttribute('data-network-src');
      if (fallback && img.src !== fallback) {
        img.src = fallback;
        return;
      }
      img.classList.add('hero__slide-img--broken');
    };
  }

  function heroSlideMarkup(slide, isActive) {
    var id = slideId(slide);
    if (!global.RodaviaAPI || !id) return '';
    var networkUrl = slideNetworkUrl(slide);
    if (!networkUrl) return '';
    var label = slide.titulo || i18n('hero.promo');
    var activeClass = isActive ? ' is-active' : '';
    var erpClass = ' hero__slide--erp';
    var img = slideImgTag(networkUrl, label, isActive);
    if (slide.link_url) {
      return (
        '<a href="' +
        escapeHtml(slide.link_url) +
        '" class="hero__slide hero__slide--linked' +
        erpClass +
        activeClass +
        '" data-slide-id="' +
        escapeHtml(id) +
        '" aria-label="' +
        escapeHtml(label) +
        '">' +
        img +
        '</a>'
      );
    }
    return (
      '<div class="hero__slide' +
      erpClass +
      activeClass +
      '" data-slide-id="' +
      escapeHtml(id) +
      '" role="img" aria-label="' +
      escapeHtml(label) +
      '">' +
      img +
      '</div>'
    );
  }

  function slideNetworkUrl(slide) {
    if (global.RodaviaCache && typeof global.RodaviaCache.slideNetworkUrl === 'function') {
      return global.RodaviaCache.slideNetworkUrl(slide);
    }
    var id = slideId(slide);
    var rawUrl = slide.imagem_url || '';
    var useBff =
      !rawUrl || rawUrl.indexOf('/api/') === 0 || rawUrl.indexOf('/bff/') === 0;
    return useBff ? global.RodaviaAPI.slideImagemUrl(id) : rawUrl;
  }

  function refreshHeroSlideImages(slides) {
    var track = document.querySelector('[data-hero-track]');
    if (!track) return;
    var reals = track.querySelectorAll('.hero__slide:not(.hero__slide--clone)');
    var clones = track.querySelectorAll('.hero__slide--clone');
    if (!reals.length || clones.length < 2) return;
    function copyImg(fromSlide, toSlide) {
      var fromImg = fromSlide && fromSlide.querySelector('.hero__slide-img');
      var toImg = toSlide && toSlide.querySelector('.hero__slide-img');
      if (fromImg && toImg && fromImg.getAttribute('src')) {
        toImg.setAttribute('src', fromImg.getAttribute('src'));
        toImg.setAttribute('alt', fromImg.getAttribute('alt') || '');
      }
    }
    copyImg(reals[reals.length - 1], clones[0]);
    copyImg(reals[0], clones[clones.length - 1]);
  }

  function scheduleSlideImagePrefetch(slides) {
    if (!global.RodaviaCache || typeof global.RodaviaCache.prefetchSlideImages !== 'function') {
      return;
    }
    global.RodaviaCache.prefetchSlideImages(slides).then(function () {
      refreshHeroSlideImages(slides);
    });
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

    slidesRoot.innerHTML =
      '<div class="hero__track" data-hero-track style="transform: translateX(0)">' +
      slides.map(function (s, i) {
        return heroSlideMarkup(s, i === 0);
      }).join('') +
      '</div>';
    slidesRoot.classList.remove('hero__slides--loading');
    slidesRoot.classList.add('hero__slides--erp');

    if (slides.length && global.RodaviaCache) {
      var first = slides[0];
      var firstId = slideId(first);
      var firstUrl = slideNetworkUrl(first);
      if (typeof global.RodaviaCache.preloadHeroImage === 'function' && firstUrl) {
        global.RodaviaCache.preloadHeroImage(firstUrl);
      }
      scheduleSlideImagePrefetch(slides);
    }

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
    try {
      document.dispatchEvent(
        new CustomEvent('rodavia:slides-ready', { detail: { count: slides.length } })
      );
    } catch (_) {
      /* ignore */
    }
    return true;
  }

  function applyCatalog(catalog) {
    if (!catalog || typeof catalog !== 'object') return;
    if (Array.isArray(catalog.slides)) applyHeroSlides(catalog.slides);
    if (catalog.filiais) populateFiliaisSelect(catalog.filiais);
    if (catalog.empresa) applyEmpresa(catalog.empresa);
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
          codigo: g.codigo || g.sigla || g.grupo_tarifario,
          segmento: g.grupo_tarifario || g.segmento,
          categoria_segmento: g.grupo_tarifario || g.categoria_segmento,
          grupo_tarifario: g.grupo_tarifario,
          cambio: g.transmissao_tipica || g.cambio,
          transmissao_tipica: g.transmissao_tipica,
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
    statusEl.textContent = ok ? i18n('bff.connected') : i18n('bff.offline');
    statusEl.classList.toggle('is-ok', ok);
    statusEl.classList.toggle('is-off', !ok);
  }

  document.addEventListener('site:langchange', function () {
    if (lastFiliaisPayload) populateFiliaisSelect(lastFiliaisPayload);
    var statusEl = $(SELECTORS.bffStatus);
    if (statusEl && (statusEl.classList.contains('is-ok') || statusEl.classList.contains('is-off'))) {
      setApiStatus(statusEl.classList.contains('is-ok'));
    }
  });

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
        if (!normalizeSlidesList(catalog.slides).length) {
          try {
            var slidesOnly = await api().slides();
            if (normalizeSlidesList(slidesOnly).length) {
              catalog.slides = slidesOnly;
            }
          } catch (_) {
            /* fallback slides opcional */
          }
        }
        applyCatalog(catalog);
        if (global.RodaviaCache) {
          global.RodaviaCache.write(catalog);
        }
        restoreFilialFromSearchState();
        setApiStatus(true);
        setReady(true);
        global.RodaviaBind._booted = true;
        try {
          document.dispatchEvent(new CustomEvent('rodavia:catalog-ready'));
        } catch (_) {
          /* ignore */
        }
        return { erpOk: true, catalog: catalog };
      } catch (err) {
        console.warn('[Rodavia] Falha ao carregar catálogo:', err && err.message ? err.message : err);
        bootPromise = null;
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

  function run() {
    var cached = w.RodaviaCache && w.RodaviaCache.read();
    if (cached) {
      w.RodaviaBind.applyCatalog(cached);
      document.documentElement.classList.add('erp-ready');
      document.documentElement.classList.remove('erp-loading');
    }
  }

  var imagesReady =
    w.RodaviaCache && typeof w.RodaviaCache.waitForSlideImages === 'function'
      ? w.RodaviaCache.waitForSlideImages()
      : Promise.resolve();
  imagesReady.then(run);
})();
