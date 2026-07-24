/**
 * Aplica tema do ERP antes da primeira pintura (evita flash de cores).
 * Deve ser incluído no <head>, sem defer, logo após styles.css.
 */
(function () {
  var THEME_KEY = 'rodavia_theme_v1';
  var CATALOG_KEY = 'rodavia_catalog_v4';
  var BOOT_FALLBACK_MS = 2800;
  var root = document.documentElement;

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

  function readCachedTransition() {
    try {
      var themeRaw = localStorage.getItem(THEME_KEY);
      if (themeRaw) {
        var theme = JSON.parse(themeRaw);
        if (theme && theme.transicao) return theme.transicao;
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
      var transicao =
        catalog.empresa && catalog.empresa.tema && catalog.empresa.tema.transicao;
      return transicao && typeof transicao === 'object' ? transicao : null;
    } catch (_) {
      return null;
    }
  }

  function showCachedTransition(transicao) {
    if (!transicao || !transicao.ativo) return;
    var overlay = document.getElementById('site-page-transition');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'site-page-transition';
      overlay.className = 'site-page-transition';
      overlay.innerHTML =
        '<img class="site-page-transition__logo" id="site-page-transition-logo" alt="" decoding="async" />';
      document.body.appendChild(overlay);
    }
    overlay.hidden = false;
    overlay.style.backgroundColor = transicao.fundo || 'var(--color-bg)';
    var img = document.getElementById('site-page-transition-logo');
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
      }
    }
  }

  if (applyCss(readCachedThemeCss())) {
    root.classList.add('erp-theme-ready');
  }
  showCachedTransition(readCachedTransition());

  setTimeout(function () {
    if (!root.classList.contains('erp-ready') && !root.classList.contains('erp-theme-ready')) {
      root.classList.add('erp-boot-fallback');
    }
  }, BOOT_FALLBACK_MS);
})();
