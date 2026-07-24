/**
 * Aplica tema do ERP antes da primeira pintura (evita flash de cores).
 * Deve ser incluído no <head>, sem defer, logo após styles.css.
 */
(function () {
  var THEME_KEY = 'rodavia_theme_v1';
  var CATALOG_KEY = 'rodavia_catalog_v4';
  var COOKIE_CONSENT_KEY = 'rodavia_cookie_consent';
  var BOOT_FALLBACK_MS = 2800;
  var root = document.documentElement;

  try {
    if (localStorage.getItem(COOKIE_CONSENT_KEY)) {
      root.classList.add('cookie-consent-set');
    }
  } catch (_) {
    /* ignore */
  }

  function applyCss(css) {
    if (!css || typeof css !== 'object') return false;
    Object.keys(css).forEach(function (key) {
      var value = css[key];
      if (value != null && value !== '') {
        root.style.setProperty(key, value);
      }
    });
    return true;
  }

  function readCachedThemeCss() {
    try {
      var themeRaw = localStorage.getItem(THEME_KEY);
      if (themeRaw) {
        var parsed = JSON.parse(themeRaw);
        if (parsed && parsed.css && typeof parsed.css === 'object') return parsed.css;
        if (parsed && (parsed['--color-bg'] || parsed['--color-primary'])) return parsed;
      }
    } catch (_) {
      /* ignore */
    }
    try {
      var catalogRaw = sessionStorage.getItem(CATALOG_KEY);
      if (!catalogRaw) return null;
      var catalog = JSON.parse(catalogRaw);
      if (!catalog || !catalog.savedAt) return null;
      if (Date.now() - catalog.savedAt > 15 * 60 * 1000) return null;
      var css = catalog.empresa && catalog.empresa.tema && catalog.empresa.tema.css;
      return css && typeof css === 'object' ? css : null;
    } catch (_) {
      return null;
    }
  }

  if (applyCss(readCachedThemeCss())) {
    root.classList.add('erp-theme-ready');
  }

  setTimeout(function () {
    if (!root.classList.contains('erp-ready') && !root.classList.contains('erp-theme-ready')) {
      root.classList.add('erp-boot-fallback');
    }
  }, BOOT_FALLBACK_MS);
})();
