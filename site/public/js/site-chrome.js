/**
 * Shared site shell for static pages (topbar, header, footer, cookie banner, chat).
 * Exposes window.SiteChrome.init()
 *
 * Body attributes:
 *   data-site-chrome="auto"  — inject chrome when absent
 *   data-topbar="rental|subscription|app"
 *   data-nav="groups|agencies|about|loyalty|faq" (omit for no active nav)
 */
(function (global) {
  'use strict';

  var COOKIE_CONSENT_KEY = 'rodavia_cookie_consent';
  var SITE_VERSION = 'v1.1.0';

  var TOPBAR_TABS = {
    rental: { href: 'index.html', i18n: 'topbar.rental', label: 'Aluguel de carros' },
    subscription: { href: 'assinatura.html', i18n: 'topbar.subscription', label: 'Carro por assinatura' },
    app: { href: 'app-motoristas.html', i18n: 'topbar.app', label: 'Carro para app' },
  };

  var NAV_LINKS = {
    groups: { href: 'grupos.html', i18n: 'nav.groups', label: 'Grupos de carros' },
    agencies: { href: 'agencias.html', i18n: 'nav.agencies', label: 'Rede de agências' },
    about: { href: 'sobre.html', i18n: 'nav.about', label: 'Sobre nós' },
    loyalty: { href: 'fidelidade.html', i18n: 'nav.loyalty', label: 'Fidelidade' },
    faq: { href: 'duvidas.html', i18n: 'nav.faq', label: 'Dúvidas' },
  };

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function readBodyAttr(name) {
    return document.body.getAttribute(name) || '';
  }

  function buildTopbarHtml(activeTopbar) {
    var tabs = Object.keys(TOPBAR_TABS)
      .map(function (key) {
        var tab = TOPBAR_TABS[key];
        var active = key === activeTopbar ? ' is-active' : '';
        return (
          '<a href="' +
          tab.href +
          '" class="topbar__tab' +
          active +
          '" data-i18n="' +
          tab.i18n +
          '">' +
          tab.label +
          '</a>'
        );
      })
      .join('');

    return (
      '<div class="topbar">' +
      '<nav class="topbar__tabs" data-i18n-aria="topbar.business" aria-label="Negócios Rodavia">' +
      tabs +
      '</nav>' +
      '<div class="topbar__locale" id="locale-selector">' +
      '<button type="button" class="topbar__country" id="country-selector" aria-expanded="false" aria-haspopup="listbox" data-i18n-aria="locale.choose">' +
      '<span class="topbar__flag" data-locale-flag aria-hidden="true">🇧🇷</span>' +
      '<span data-locale-label>Brasil</span>' +
      '<span class="topbar__caret" aria-hidden="true">▾</span>' +
      '</button>' +
      '<ul class="topbar__locale-menu" id="locale-menu" role="listbox" hidden>' +
      '<li role="presentation"><button type="button" class="topbar__locale-option" data-lang-option="pt-BR" role="option">🇧🇷 Português (Brasil)</button></li>' +
      '<li role="presentation"><button type="button" class="topbar__locale-option" data-lang-option="en-US" role="option">🇺🇸 English (USA)</button></li>' +
      '<li role="presentation"><button type="button" class="topbar__locale-option" data-lang-option="es-ES" role="option">🇪🇸 Español (ESP)</button></li>' +
      '</ul>' +
      '</div>' +
      '</div>'
    );
  }

  function buildHeaderHtml(activeNav) {
    var navItems = Object.keys(NAV_LINKS)
      .map(function (key) {
        var link = NAV_LINKS[key];
        var current = key === activeNav ? ' aria-current="page"' : '';
        return (
          '<li><a href="' +
          link.href +
          '"' +
          current +
          ' data-i18n="' +
          link.i18n +
          '">' +
          link.label +
          '</a></li>'
        );
      })
      .join('');

    return (
      '<header class="site-header site-header--brand">' +
      '<div class="site-header__inner">' +
      '<a href="index.html" class="logo logo--brand" aria-label="Página inicial">' +
      '<span class="logo__text" data-erp="nome_exibicao"></span>' +
      '</a>' +
      '<button type="button" class="nav-toggle nav-toggle--light" id="nav-toggle" aria-expanded="false" aria-controls="primary-nav" aria-label="Abrir menu" data-i18n-aria="nav.toggle">' +
      '<span></span><span></span><span></span>' +
      '</button>' +
      '<nav class="primary-nav primary-nav--brand" id="primary-nav" data-i18n-aria="nav.main" aria-label="Menu principal">' +
      '<ul>' +
      navItems +
      '</ul>' +
      '</nav>' +
      '</div>' +
      '</header>'
    );
  }

  function buildShellHtml(activeTopbar, activeNav) {
    return (
      '<a href="#main-content" class="skip-link" data-i18n="skip.main">Ir para conteúdo principal</a>' +
      buildTopbarHtml(activeTopbar) +
      buildHeaderHtml(activeNav)
    );
  }

  function buildFooterHtml() {
    return (
      '<footer class="site-footer site-footer--chrome">' +
      '<div class="container">' +
      '<div class="footer-grid">' +
      '<div class="footer-col footer-col--about">' +
      '<p class="footer-col__logo"><strong class="footer-col__brand" data-erp="nome_exibicao">LOCADORA RODAVIA</strong></p>' +
      '<p class="footer-col__blurb" data-i18n="chrome.footer.about_blurb">' +
      'Aluguel de carros com retirada rápida, frota diversificada e atendimento em todo o Brasil.' +
      '</p>' +
      '<div class="footer-social">' +
      '<a href="#" aria-label="Instagram" data-i18n-aria="chrome.footer.social_instagram">Instagram</a>' +
      '<a href="#" aria-label="LinkedIn" data-i18n-aria="chrome.footer.social_linkedin">LinkedIn</a>' +
      '<a href="#" aria-label="YouTube" data-i18n-aria="chrome.footer.social_youtube">YouTube</a>' +
      '</div>' +
      '</div>' +
      '<div class="footer-col">' +
      '<h3 data-i18n="groups.support">Atendimento</h3>' +
      '<ul>' +
      '<li><span data-i18n="chrome.footer.reservations">Central de reservas</span> <a href="tel:" data-erp="telefone">—</a></li>' +
      '<li><span data-i18n="chrome.footer.assist_24h">Assistência 24h</span> <a href="tel:" data-erp="telefone">—</a></li>' +
      '<li><a href="#" data-i18n="groups.whatsapp">WhatsApp</a></li>' +
      '</ul>' +
      '</div>' +
      '<div class="footer-col">' +
      '<h3 data-i18n="chrome.footer.links">Links</h3>' +
      '<ul>' +
      '<li><a href="termos.html" data-i18n="chrome.footer.terms">Termos de uso</a></li>' +
      '<li><a href="termos.html#privacidade" data-i18n="chrome.footer.privacy">Política de privacidade</a></li>' +
      '<li><a href="termos.html#regras" data-i18n="chrome.footer.rental_rules">Regras de locação</a></li>' +
      '</ul>' +
      '</div>' +
      '<div class="footer-col">' +
      '<h3 data-i18n="chrome.footer.payments">Pagamentos</h3>' +
      '<div class="payment-badges" aria-label="Formas de pagamento">' +
      '<span class="payment-badges__item payment-badges__item--visa" title="Visa">Visa</span>' +
      '<span class="payment-badges__item payment-badges__item--mastercard" title="Mastercard">Mastercard</span>' +
      '<span class="payment-badges__item payment-badges__item--pix" title="PIX">PIX</span>' +
      '<span class="payment-badges__item payment-badges__item--ssl" title="SSL" data-i18n="chrome.footer.ssl">SSL</span>' +
      '</div>' +
      '</div>' +
      '</div>' +
      '<div class="footer-bottom">' +
      '<p data-i18n="footer.rights">© LOCADORA RODAVIA. Todos os direitos reservados.</p>' +
      '<p data-i18n="footer.version">Versão do site ' +
      SITE_VERSION +
      '</p>' +
      '</div>' +
      '</div>' +
      '</footer>'
    );
  }

  function buildWidgetsHtml() {
    return (
      '<aside class="cookie-banner" id="cookie-banner" role="dialog" aria-labelledby="cookie-title" aria-describedby="cookie-desc">' +
      '<div class="cookie-banner__inner">' +
      '<p class="cookie-banner__text" id="cookie-desc">' +
      '<strong id="cookie-title" data-i18n="cookie.title">Cookies</strong> — ' +
      '<span data-i18n="cookie.text">Este site utiliza cookies para garantir que você obtenha a melhor experiência durante sua navegação, melhorar continuamente nossos serviços e lhe ofertar publicidade relevante aos seus interesses. Clique em Rejeitar se não desejar receber ofertas direcionadas.</span>' +
      '</p>' +
      '<div class="cookie-banner__actions">' +
      '<a href="#" class="btn btn--ghost btn--sm" data-i18n="cookie.learn">Saiba mais</a>' +
      '<button type="button" class="btn btn--primary btn--sm" id="cookie-accept" data-i18n="cookie.accept">Manter cookies</button>' +
      '<button type="button" class="btn btn--secondary btn--sm" id="cookie-reject" data-i18n="cookie.reject">Rejeitar</button>' +
      '<a href="#" class="btn btn--ghost btn--sm" id="cookie-prefs-link" data-i18n="cookie.prefs">Preferência de Cookies</a>' +
      '</div>' +
      '</div>' +
      '</aside>' +
      (global.SiteChat ? global.SiteChat.fabHtml() + global.SiteChat.drawerHtml() : (
      '<button type="button" class="chat-fab" id="chat-fab" data-i18n-aria="chat.open" aria-label="Abrir atendimento"></button>' +
      '<div class="chat-drawer" id="chat-drawer" aria-hidden="true"></div>'
      )) +
      '<div class="modal" id="cookie-prefs-modal" aria-hidden="true" role="dialog" aria-labelledby="prefs-title">' +
      '<div class="modal__backdrop" data-close-modal="cookie-prefs-modal"></div>' +
      '<div class="modal__panel">' +
      '<button type="button" class="modal__close" data-close-modal="cookie-prefs-modal" data-i18n-aria="modal.close" aria-label="Fechar">×</button>' +
      '<h2 class="modal__title" id="prefs-title" data-i18n="cookie.prefs_title">Preferência de cookies</h2>' +
      '<p data-i18n="cookie.prefs_text">Sua escolha é salva no navegador (localStorage). Você pode alterá-la limpando os dados do site.</p>' +
      '<button type="button" class="btn btn--primary btn--sm" id="cookie-accept-prefs" data-i18n="cookie.accept">Manter cookies</button>' +
      '</div>' +
      '</div>'
    );
  }

  function findMainAnchor() {
    return $('#main-content') || $('main');
  }

  function injectShell() {
    if ($('#site-chrome-shell')) return;

    var activeTopbar = readBodyAttr('data-topbar') || 'rental';
    if (!TOPBAR_TABS[activeTopbar]) activeTopbar = 'rental';

    var activeNav = readBodyAttr('data-nav');
    if (activeNav === 'null' || activeNav === '') activeNav = null;
    else if (activeNav && !NAV_LINKS[activeNav]) activeNav = null;

    var anchor = findMainAnchor();
    if (!anchor) return;

    var wrap = document.createElement('div');
    wrap.id = 'site-chrome-shell';
    wrap.innerHTML = buildShellHtml(activeTopbar, activeNav);
    anchor.parentNode.insertBefore(wrap, anchor);
  }

  function injectFooter() {
    if ($('.site-footer--chrome')) return;

    var footerHtml = buildFooterHtml();
    var mount = $('#site-footer-mount');
    if (mount) {
      mount.innerHTML = footerHtml;
      return;
    }

    var main = findMainAnchor();
    if (!main) return;

    var tpl = document.createElement('template');
    tpl.innerHTML = footerHtml;
    if (main.nextSibling) {
      main.parentNode.insertBefore(tpl.content, main.nextSibling);
    } else {
      main.parentNode.appendChild(tpl.content);
    }
  }

  function injectWidgets() {
    if ($('#cookie-banner') && $('#chat-fab')) return;

    var tpl = document.createElement('template');
    tpl.innerHTML = buildWidgetsHtml();
    document.body.appendChild(tpl.content);

    if (!document.body.classList.contains('has-cookie-banner')) {
      document.body.classList.add('has-cookie-banner');
    }
  }

  function injectAutoChrome() {
    var mode = readBodyAttr('data-site-chrome');
    if (mode === 'auto') {
      injectShell();
      injectFooter();
      injectWidgets();
    } else if (mode === 'footer') {
      injectFooter();
      if (!$('#cookie-banner')) injectWidgets();
    }
  }

  function initSkipLink() {
    $('.skip-link')?.addEventListener('click', function (e) {
      e.preventDefault();
      var main = $('#main-content') || $('main');
      main?.focus();
    });
  }

  function initMobileNav() {
    var toggle = $('#nav-toggle');
    var nav = $('#primary-nav');
    if (!toggle || !nav) return;

    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });

    $$('#primary-nav a').forEach(function (a) {
      a.addEventListener('click', function () {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  function getCookieConsent() {
    try {
      return localStorage.getItem(COOKIE_CONSENT_KEY);
    } catch (e) {
      return null;
    }
  }

  function setCookieConsent(value) {
    try {
      localStorage.setItem(COOKIE_CONSENT_KEY, value);
    } catch (e) {
      /* ignore */
    }
  }

  function initCookieBanner() {
    var banner = $('#cookie-banner');
    if (!banner) return;

    var consent = getCookieConsent();
    if (consent) {
      banner.classList.add('is-hidden');
      banner.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('has-cookie-banner');
      return;
    }

    banner.classList.remove('is-hidden');
    banner.setAttribute('aria-hidden', 'false');

    $('#cookie-accept')?.addEventListener('click', function () {
      setCookieConsent('accepted');
      banner.classList.add('is-hidden');
      banner.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('has-cookie-banner');
    });

    $('#cookie-reject')?.addEventListener('click', function () {
      setCookieConsent('rejected');
      banner.classList.add('is-hidden');
      banner.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('has-cookie-banner');
    });

    $('#cookie-prefs-link')?.addEventListener('click', function (e) {
      e.preventDefault();
      $('#cookie-prefs-modal')?.classList.add('is-open');
    });

    $('#cookie-accept-prefs')?.addEventListener('click', function () {
      setCookieConsent('accepted');
      $('#cookie-prefs-modal')?.classList.remove('is-open');
      banner.classList.add('is-hidden');
      banner.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('has-cookie-banner');
    });
  }

  function initModals() {
    if (global.SiteChat && typeof global.SiteChat.init === 'function') {
      global.SiteChat.init();
    }

    $$('[data-close-modal]').forEach(function (btn) {
      if (btn.getAttribute('data-close-modal') === 'chat-modal') return;
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-close-modal');
        var el = id ? document.getElementById(id) : btn.closest('.modal');
        el?.classList.remove('is-open');
        el?.setAttribute('aria-hidden', 'true');
      });
    });
  }

  function applyI18n() {
    if (global.SiteI18n && typeof global.SiteI18n.init === 'function') {
      global.SiteI18n.init();
    } else if (global.SiteI18n && typeof global.SiteI18n.apply === 'function') {
      global.SiteI18n.apply();
    }
  }

  function bootErp() {
    if (global.RodaviaBind && typeof global.RodaviaBind.boot === 'function') {
      return global.RodaviaBind.boot();
    }
    return Promise.resolve({ erpOk: false });
  }

  function init() {
    injectAutoChrome();
    initSkipLink();
    initMobileNav();
    initCookieBanner();
    initModals();
    applyI18n();
    return bootErp();
  }

  global.SiteChrome = {
    init: init,
    injectShell: injectShell,
    injectFooter: injectFooter,
    injectWidgets: injectWidgets,
    initMobileNav: initMobileNav,
    initCookieBanner: initCookieBanner,
    initModals: initModals,
  };
})(window);
