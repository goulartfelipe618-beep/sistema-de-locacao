/**
 * Cache do catálogo ERP (empresa, filiais, slides) — evita flash de placeholders.
 */
(function (global) {
  var CACHE_KEY = 'rodavia_catalog_v1';
  var TTL_MS = 15 * 60 * 1000;

  function read() {
    try {
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

  function write(payload) {
    try {
      sessionStorage.setItem(
        CACHE_KEY,
        JSON.stringify({
          savedAt: Date.now(),
          empresa: payload.empresa || null,
          filiais: payload.filiais || [],
          slides: payload.slides || [],
        })
      );
    } catch (_) {
      /* ignore quota */
    }
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
  };

  if (typeof document !== 'undefined') {
    document.documentElement.classList.add('erp-loading');
    var cached = read();
    if (cached) {
      document.documentElement.classList.add('erp-cache-hit');
    }
  }
})(typeof window !== 'undefined' ? window : globalThis);
