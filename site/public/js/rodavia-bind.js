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
    homeShowcaseSection: '#home-showcase-section',
    homeShowcase: '#home-showcase',
    groupsPromoSection: '#groups-promo-section',
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
      hidePageTransition();
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

  function normalizeShowcaseUrl(url) {
    if (!url) return null;
    if (url.indexOf('/api/v1/public/vitrine/imagem/') >= 0) {
      return url.replace('/api/v1/public/vitrine/imagem/', '/bff/vitrine/imagem/');
    }
    return url;
  }

  function normalizeGroupsPromoUrl(url) {
    if (!url) return null;
    if (url.indexOf('/api/v1/public/grupos-promo/imagem') >= 0) {
      return '/bff/grupos-promo/imagem';
    }
    if (url.indexOf('/bff/grupos-promo/imagem') >= 0) {
      return url;
    }
    return url;
  }

  function applyGroupsPromo(gp) {
    var section = $(SELECTORS.groupsPromoSection);
    if (!section || !gp || typeof gp !== 'object') return;

    var img = section.querySelector('.groups-promo__img');
    var url = normalizeGroupsPromoUrl(gp.imagem_url);
    if (img && url) {
      img.src = url;
      img.width = Number(gp.largura_px) || 560;
      img.height = Number(gp.altura_px) || 420;
      var altText = (gp.titulo || '').trim();
      if (altText) img.alt = altText;
    }

    var titleEl = section.querySelector('.groups-promo__title');
    var subtitleEl = section.querySelector('.groups-promo__subtitle');
    var textEl = section.querySelector('.groups-promo__text');
    var ctaEl = section.querySelector('.groups-promo__cta');

    var titulo = (gp.titulo || '').trim();
    var subtitulo = (gp.subtitulo || '').trim();
    var texto = (gp.texto || '').trim();
    var ctaTexto = (gp.cta_texto || '').trim();
    var ctaUrl = (gp.cta_url || '').trim();
    var ctaTarget = gp.cta_target === '_blank' ? '_blank' : '_self';

    if (titleEl && titulo) {
      titleEl.textContent = titulo;
      titleEl.removeAttribute('data-i18n');
    }
    if (subtitleEl && subtitulo) {
      subtitleEl.textContent = subtitulo;
      subtitleEl.removeAttribute('data-i18n');
    }
    if (textEl && texto) {
      textEl.textContent = texto;
      textEl.removeAttribute('data-i18n');
    }
    if (ctaEl && ctaUrl) {
      ctaEl.href = ctaUrl;
      ctaEl.textContent = ctaTexto || ctaEl.textContent || 'Saiba mais';
      ctaEl.removeAttribute('data-i18n');
      ctaEl.target = ctaTarget;
      if (ctaTarget === '_blank') {
        ctaEl.rel = 'noopener noreferrer';
      } else {
        ctaEl.removeAttribute('rel');
      }
    }
  }

  function applyHomeShowcase(vitrine) {
    var section = $(SELECTORS.homeShowcaseSection);
    var root = $(SELECTORS.homeShowcase);
    if (!section || !root) return;
    var rows = vitrine && Array.isArray(vitrine.imagens) ? vitrine.imagens : [];
    var anyVisible = false;
    [1, 2, 3].forEach(function (slot) {
      var item = root.querySelector('[data-showcase-slot="' + slot + '"]');
      if (!item) return;
      var row = rows.find(function (entry) {
        return Number(entry && entry.slot) === slot;
      });
      var url = normalizeShowcaseUrl(row && row.imagem_url);
      if (!url) {
        item.hidden = true;
        return;
      }
      var img = item.querySelector('.home-showcase__img');
      if (img) {
        img.src = url;
        img.width = Number(row.largura_px) || 1080;
        img.height = Number(row.altura_px) || 1350;
        var altText = (row.titulo || '').trim();
        img.alt = altText;
      }

      var titleEl = item.querySelector('.home-showcase__title');
      var descEl = item.querySelector('.home-showcase__desc');
      var ctaEl = item.querySelector('.home-showcase__cta');
      var titulo = (row.titulo || '').trim();
      var descricao = (row.descricao || '').trim();
      var ctaTexto = (row.cta_texto || '').trim();
      var ctaUrl = (row.cta_url || '').trim();
      var ctaTarget = row.cta_target === '_blank' ? '_blank' : '_self';

      if (titleEl) {
        if (titulo) {
          titleEl.textContent = titulo;
          titleEl.hidden = false;
        } else {
          titleEl.textContent = '';
          titleEl.hidden = true;
        }
      }
      if (descEl) {
        if (descricao) {
          descEl.textContent = descricao;
          descEl.hidden = false;
        } else {
          descEl.textContent = '';
          descEl.hidden = true;
        }
      }
      if (ctaEl) {
        if (ctaUrl) {
          ctaEl.href = ctaUrl;
          ctaEl.textContent = ctaTexto || 'Saiba mais';
          ctaEl.target = ctaTarget;
          if (ctaTarget === '_blank') {
            ctaEl.rel = 'noopener noreferrer';
          } else {
            ctaEl.removeAttribute('rel');
          }
          ctaEl.hidden = false;
        } else {
          ctaEl.hidden = true;
          ctaEl.removeAttribute('href');
        }
      }

      item.hidden = false;
      anyVisible = true;
    });
    section.hidden = !anyVisible;
  }

  function syncPageTransition(transicao) {
    var overlay = $('#site-page-transition');
    if (!overlay) return;
    if (!transicao || !transicao.ativo) {
      overlay.hidden = true;
      overlay.setAttribute('aria-hidden', 'true');
      overlay.classList.remove('is-hiding');
      return;
    }
    overlay.style.backgroundColor = transicao.fundo || 'var(--color-bg)';
    var img = $('#site-page-transition-logo');
    if (img) {
      var size = Number(transicao.tamanho_px) || 120;
      img.style.width = size + 'px';
      img.style.height = size + 'px';
      var url = transicao.imagem_url || '';
      if (url.indexOf('/api/v1/public/transicao/imagem') >= 0) {
        url = '/bff/transicao/imagem';
      }
      if (url) {
        img.src = url;
        img.hidden = false;
      } else {
        img.removeAttribute('src');
        img.hidden = true;
      }
    }
    overlay.hidden = true;
    overlay.setAttribute('aria-hidden', 'true');
    overlay.classList.remove('is-hiding');
  }

  function hidePageTransition() {
    var overlay = $('#site-page-transition');
    if (!overlay) return;
    overlay.hidden = true;
    overlay.setAttribute('aria-hidden', 'true');
    overlay.classList.remove('is-hiding');
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
    if (tema.transicao) syncPageTransition(tema.transicao);
    if (tema.grupos_promo) applyGroupsPromo(tema.grupos_promo);
    if (tema.vitrine) applyHomeShowcase(tema.vitrine);
    if (global.RodaviaCache && typeof global.RodaviaCache.persistThemeCss === 'function') {
      global.RodaviaCache.persistThemeCss(tema.css, tema.transicao);
    } else {
      try {
        localStorage.setItem(
          'rodavia_theme_v1',
          JSON.stringify({ css: tema.css, transicao: tema.transicao || null })
        );
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
    setApiStatus(true);
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
          combustivel: g.combustivel || 'flex',
          malas_grandes:
            g.malas_grandes != null
              ? g.malas_grandes
              : g.capacidade_porta_malas != null
                ? (g.capacidade_porta_malas >= 2 ? 2 : 1)
                : 1,
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
      var hadCache = hydrateFromCache();
      if (hadCache) {
        restoreFilialFromSearchState();
      }

      var bffOk = await waitForBff(hadCache ? 800 : 3000);
      if (!bffOk) {
        setApiStatus(hadCache);
        setReady(hadCache);
        return { erpOk: hadCache, fromCache: hadCache };
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
        try {
          document.dispatchEvent(new CustomEvent('rodavia:catalog-ready'));
        } catch (_) {
          /* ignore */
        }
        return { erpOk: true, catalog: catalog };
      } catch (err) {
        console.warn('[Rodavia] Falha ao carregar catálogo:', err && err.message ? err.message : err);
        bootPromise = null;
        var stillCached = hydrateFromCache();
        setApiStatus(stillCached);
        setReady(stillCached);
        return { erpOk: stillCached, fromCache: stillCached };
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
    veiculos: function (params) {
      return api().veiculos(params);
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

  function markStatusOk() {
    var statusEl = document.getElementById('bff-status');
    if (!statusEl) return;
    var label =
      w.SiteI18n && typeof w.SiteI18n.t === 'function'
        ? w.SiteI18n.t('bff.connected')
        : 'API conectada';
    statusEl.textContent = label;
    statusEl.classList.add('is-ok');
    statusEl.classList.remove('is-off');
  }

  function run() {
    var cached = w.RodaviaCache && w.RodaviaCache.read();
    if (cached) {
      w.RodaviaBind.applyCatalog(cached);
      document.documentElement.classList.add('erp-ready');
      document.documentElement.classList.remove('erp-loading');
      document.documentElement.classList.remove('erp-boot-fallback');
      var overlay = document.getElementById('site-page-transition');
      if (overlay) {
        overlay.hidden = true;
        overlay.setAttribute('aria-hidden', 'true');
        overlay.classList.remove('is-hiding');
      }
      markStatusOk();
    }
  }

  var imagesReady =
    w.RodaviaCache && typeof w.RodaviaCache.waitForSlideImages === 'function'
      ? w.RodaviaCache.waitForSlideImages()
      : Promise.resolve();
  imagesReady.then(function () {
    run();
    if (typeof w.RodaviaBind.boot === 'function') {
      w.RodaviaBind.boot();
    }
  });
})();
