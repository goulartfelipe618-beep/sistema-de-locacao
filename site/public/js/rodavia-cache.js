/**
 * Cache do catálogo ERP (empresa, filiais, slides) + imagens dos slides (IndexedDB).
 */
(function (global) {
  var CACHE_KEY = 'rodavia_catalog_v4';
  var THEME_KEY = 'rodavia_theme_v1';
  var LEGACY_CACHE_KEY = 'rodavia_catalog_v1';
  var LEGACY_CACHE_KEY_V2 = 'rodavia_catalog_v2';
  var TTL_MS = 15 * 60 * 1000;

  var IMG_DB_NAME = 'rodavia_slide_images_v1';
  var IMG_STORE = 'blobs';
  var IMG_TTL_MS = 7 * 24 * 60 * 60 * 1000;

  var slideBlobUrls = Object.create(null);
  var slideImagesReady = null;

  function slimEmpresa(empresa) {
    if (!empresa || typeof empresa !== 'object') return null;
    return {
      nome_exibicao: empresa.nome_exibicao,
      cnpj_formatado: empresa.cnpj_formatado,
      endereco_formatado: empresa.endereco_formatado,
      email: empresa.email,
      telefone: empresa.telefone || empresa.telefone_formatado,
      tema: empresa.tema || null,
    };
  }

  function read() {
    try {
      sessionStorage.removeItem(LEGACY_CACHE_KEY);
      sessionStorage.removeItem(LEGACY_CACHE_KEY_V2);
      var raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || !data.savedAt) return null;
      if (Date.now() - data.savedAt > TTL_MS) return null;
      return data;
    } catch (_) {
      return null;
    }
  }

  function persistThemeCss(css, transicao) {
    if (!css || typeof css !== 'object') return;
    try {
      localStorage.setItem(
        THEME_KEY,
        JSON.stringify({ css: css, transicao: transicao || null })
      );
    } catch (_) {
      /* ignore quota */
    }
    if (typeof document !== 'undefined') {
      document.documentElement.classList.add('erp-theme-ready');
    }
  }

  function write(payload) {
    try {
      sessionStorage.setItem(
        CACHE_KEY,
        JSON.stringify({
          savedAt: Date.now(),
          empresa: slimEmpresa(payload.empresa),
          filiais: payload.filiais || [],
          slides: payload.slides || [],
        })
      );
      var css = payload.empresa && payload.empresa.tema && payload.empresa.tema.css;
      var transicao = payload.empresa && payload.empresa.tema && payload.empresa.tema.transicao;
      if (css) persistThemeCss(css, transicao);
    } catch (_) {
      /* ignore quota */
    }
  }

  function openImageDb() {
    if (!global.indexedDB) return Promise.reject(new Error('indexedDB unavailable'));
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(IMG_DB_NAME, 1);
      req.onerror = function () {
        reject(req.error || new Error('indexedDB open failed'));
      };
      req.onsuccess = function () {
        resolve(req.result);
      };
      req.onupgradeneeded = function (e) {
        var db = e.target.result;
        if (!db.objectStoreNames.contains(IMG_STORE)) {
          db.createObjectStore(IMG_STORE, { keyPath: 'id' });
        }
      };
    });
  }

  function loadSlideImagesFromDb() {
    if (slideImagesReady) return slideImagesReady;
    slideImagesReady = openImageDb()
      .then(function (db) {
        return new Promise(function (resolve) {
          var tx = db.transaction(IMG_STORE, 'readonly');
          var store = tx.objectStore(IMG_STORE);
          var req = store.getAll();
          req.onsuccess = function () {
            var now = Date.now();
            var staleIds = [];
            (req.result || []).forEach(function (row) {
              if (!row || !row.id || !row.blob) return;
              if (now - (row.savedAt || 0) > IMG_TTL_MS) {
                staleIds.push(row.id);
                return;
              }
              if (!slideBlobUrls[row.id]) {
                slideBlobUrls[row.id] = URL.createObjectURL(row.blob);
              }
            });
            if (staleIds.length) purgeStaleImages(staleIds);
            resolve(slideBlobUrls);
          };
          req.onerror = function () {
            resolve(slideBlobUrls);
          };
        });
      })
      .catch(function () {
        return slideBlobUrls;
      });
    return slideImagesReady;
  }

  function purgeStaleImages(ids) {
    openImageDb()
      .then(function (db) {
        var tx = db.transaction(IMG_STORE, 'readwrite');
        var store = tx.objectStore(IMG_STORE);
        ids.forEach(function (id) {
          store.delete(id);
        });
      })
      .catch(function () {});
  }

  function getSlideImageUrl(slideId, networkUrl) {
    /* URL de rede no DOM — blob revogado após prefetch quebrava o carrossel (ERR_FILE_NOT_FOUND). */
    if (networkUrl) return networkUrl;
    if (slideId && slideBlobUrls[slideId]) return slideBlobUrls[slideId];
    return '';
  }

  function storeSlideImage(slideId, blob) {
    if (!slideId || !blob) return;
    var oldUrl = slideBlobUrls[slideId];
    if (oldUrl) {
      try {
        URL.revokeObjectURL(oldUrl);
      } catch (_) {
        /* ignore */
      }
    }
    slideBlobUrls[slideId] = URL.createObjectURL(blob);
    openImageDb()
      .then(function (db) {
        var tx = db.transaction(IMG_STORE, 'readwrite');
        tx.objectStore(IMG_STORE).put({ id: slideId, blob: blob, savedAt: Date.now() });
      })
      .catch(function () {});
  }

  function slideNetworkUrl(slide) {
    if (!slide || typeof slide !== 'object') return '';
    var id = slide.id || slide.slide_id;
    if (!id) return slide.imagem_url || '';
    var rawUrl = slide.imagem_url || '';
    var useBff =
      !rawUrl || rawUrl.indexOf('/api/') === 0 || rawUrl.indexOf('/bff/') === 0;
    if (useBff) {
      var base =
        (typeof global.RODAVIA_BFF_BASE === 'string' && global.RODAVIA_BFF_BASE) || '/bff';
      return base.replace(/\/$/, '') + '/slides/' + encodeURIComponent(id) + '/imagem';
    }
    return rawUrl;
  }

  function prefetchSlideImages(slides) {
    if (!slides || !slides.length) return Promise.resolve();
    var tasks = slides.map(function (slide) {
      var id = slide && (slide.id || slide.slide_id);
      if (!id || slideBlobUrls[id]) return Promise.resolve();
      var url = slideNetworkUrl(slide);
      if (!url) return Promise.resolve();
      return fetch(url, { credentials: 'same-origin' })
        .then(function (res) {
          if (!res.ok) return;
          return res.blob().then(function (blob) {
            storeSlideImage(id, blob);
          });
        })
        .catch(function () {});
    });
    return Promise.all(tasks);
  }

  function preloadHeroImage(url) {
    if (!url || typeof document === 'undefined') return;
    if (String(url).indexOf('blob:') === 0) return;
    var link = document.querySelector('link[data-hero-preload]');
    if (!link) {
      link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'image';
      link.setAttribute('data-hero-preload', '1');
      document.head.appendChild(link);
    }
    if (link.getAttribute('href') !== url) link.setAttribute('href', url);
  }

  global.RodaviaCache = {
    key: CACHE_KEY,
    ttlMs: TTL_MS,
    read: read,
    write: write,
    clear: function () {
      try {
        sessionStorage.removeItem(CACHE_KEY);
      } catch (_) {
        /* ignore */
      }
    },
    waitForSlideImages: loadSlideImagesFromDb,
    getSlideImageUrl: getSlideImageUrl,
    prefetchSlideImages: prefetchSlideImages,
    preloadHeroImage: preloadHeroImage,
    slideNetworkUrl: slideNetworkUrl,
    persistThemeCss: persistThemeCss,
  };

  if (typeof document !== 'undefined') {
    document.documentElement.classList.add('erp-loading');
    var cached = read();
    if (cached) {
      document.documentElement.classList.add('erp-cache-hit');
    }
    loadSlideImagesFromDb();
  }
})(typeof window !== 'undefined' ? window : globalThis);
