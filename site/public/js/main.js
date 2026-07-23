import { SITE_CONFIG } from './config.js';
import {
  toIsoDateTime,
  validateSearch,
  fleetGroupTitle,
  fleetGroupDescription,
  searchParamsToQuery
} from './fleet-utils.js';

function bind() {
  if (!window.RodaviaBind) {
    throw new Error('Carregue js/rodavia-cache.js, rodavia-config.js, rodavia-api.js e rodavia-bind.js antes de main.js.');
  }
  return window.RodaviaBind;
}

function $(sel, root) {
  return (root || document).querySelector(sel);
}

function $$(sel, root) {
  return Array.prototype.slice.call((root || document).querySelectorAll(sel));
}
let lastSearch = null;
let fleetGroups = [];
let fleetActiveIndex = 0;
let pendingCategoriaId = null;

function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function initSkipLink() {
  $('.skip-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    $('#main-content')?.focus();
  });
}

function i18n(key, vars) {
  return window.SiteI18n?.t(key, vars) ?? key;
}

function initTopBarCountry() {
  /* Seletor de idioma em site-i18n.js */
}

function initMobileNav() {
  const toggle = $('#nav-toggle');
  const nav = $('#primary-nav');
  toggle?.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(open));
  });
  $$('#primary-nav a').forEach((a) => {
    a.addEventListener('click', () => {
      nav.classList.remove('is-open');
      toggle?.setAttribute('aria-expanded', 'false');
    });
  });
}

function initCarousels() {
  $$('[data-carousel]').forEach((root) => {
    const track = $('.carousel__track', root);
    const prev = $('.carousel__btn--prev', root);
    const next = $('.carousel__btn--next', root);
    if (!track) return;
    const step = () => Math.min(track.clientWidth * 0.85, 320);
    prev?.addEventListener('click', () => track.scrollBy({ left: -step(), behavior: 'smooth' }));
    next?.addEventListener('click', () => track.scrollBy({ left: step(), behavior: 'smooth' }));
  });
}

let heroCarouselTimer = null;

function initHeroCarousel() {
  const root = $('[data-hero-carousel]');
  if (!root) return;
  if (root.dataset.heroBound === '1') return;
  root.dataset.heroBound = '1';

  if (heroCarouselTimer) {
    clearInterval(heroCarouselTimer);
    heroCarouselTimer = null;
  }

  const track = $('[data-hero-track]', root);
  const slides = track ? $$('.hero__slide', track) : $$('.hero__slide', root);
  const dotsContainer = $('.hero__dots', root);
  const dots = $$('.hero__dot', root);
  const prev = $('[data-hero-prev]', root);
  const next = $('[data-hero-next]', root);

  if (!slides.length) return;

  if (slides.length <= 1) {
    slides[0].classList.add('is-active');
    if (track) track.style.transform = 'translateX(0)';
    prev?.setAttribute('hidden', '');
    next?.setAttribute('hidden', '');
    dotsContainer?.setAttribute('hidden', '');
    return;
  }

  prev?.removeAttribute('hidden');
  next?.removeAttribute('hidden');
  dotsContainer?.removeAttribute('hidden');

  let idx = slides.findIndex((s) => s.classList.contains('is-active'));
  if (idx < 0) idx = 0;

  const moveTrack = (index, animate) => {
    if (!track) return;
    if (animate === false) {
      track.classList.add('is-instant');
      track.style.transform = `translateX(-${index * 100}%)`;
      requestAnimationFrame(() => track.classList.remove('is-instant'));
      return;
    }
    track.style.transform = `translateX(-${index * 100}%)`;
  };

  const show = (i, animate) => {
    idx = (i + slides.length) % slides.length;
    slides.forEach((s, j) => s.classList.toggle('is-active', j === idx));
    moveTrack(idx, animate);
    dots.forEach((d, j) => {
      d.classList.toggle('is-active', j === idx);
      d.setAttribute('aria-selected', j === idx ? 'true' : 'false');
    });
  };

  moveTrack(idx, false);
  show(idx, false);

  dots.forEach((d, i) => d.addEventListener('click', () => show(i)));
  prev?.addEventListener('click', () => show(idx - 1));
  next?.addEventListener('click', () => show(idx + 1));
  heroCarouselTimer = setInterval(() => show(idx + 1), 7000);
}

function getCookieConsent() {
  try {
    return localStorage.getItem(SITE_CONFIG.cookieConsentKey);
  } catch {
    return null;
  }
}

function setCookieConsent(value) {
  try {
    localStorage.setItem(SITE_CONFIG.cookieConsentKey, value);
  } catch {
    /* ignore */
  }
}

function initCookieBanner() {
  const banner = $('#cookie-banner');
  const consent = getCookieConsent();
  if (consent) {
    banner?.classList.add('is-hidden');
    banner?.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('has-cookie-banner');
    return;
  }
  banner?.classList.remove('is-hidden');
  banner?.setAttribute('aria-hidden', 'false');

  $('#cookie-accept')?.addEventListener('click', () => {
    setCookieConsent('accepted');
    banner.classList.add('is-hidden');
    banner.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('has-cookie-banner');
  });
  $('#cookie-reject')?.addEventListener('click', () => {
    setCookieConsent('rejected');
    banner.classList.add('is-hidden');
    banner.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('has-cookie-banner');
  });
  $('#cookie-prefs-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    $('#cookie-prefs-modal')?.classList.add('is-open');
  });
  $('#cookie-accept-prefs')?.addEventListener('click', () => {
    setCookieConsent('accepted');
    $('#cookie-prefs-modal')?.classList.remove('is-open');
    banner?.classList.add('is-hidden');
    banner?.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('has-cookie-banner');
  });
}

function initModals() {
  if (window.SiteChat && typeof window.SiteChat.init === 'function') {
    window.SiteChat.init();
  }
  $$('[data-close-modal]').forEach((btn) => {
    if (btn.getAttribute('data-close-modal') === 'chat-modal') return;
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-close-modal');
      const el = id ? document.getElementById(id) : btn.closest('.modal');
      el?.classList.remove('is-open');
      el?.setAttribute('aria-hidden', 'true');
    });
  });
}

function fleetRelativeIndex(index, active, total) {
  let delta = index - active;
  while (delta > total / 2) delta -= total;
  while (delta < -total / 2) delta += total;
  return delta;
}

function fleetCardHtml(group) {
  const title = escapeHtml(fleetGroupTitle(group));
  const desc = escapeHtml(fleetGroupDescription(group));
  const imgUrl = group.imagem_url;
  const media = imgUrl
    ? `<img class="fleet-showcase__img" src="${escapeHtml(imgUrl)}" alt="" loading="lazy" />`
    : `<div class="fleet-showcase__img fleet-showcase__img--placeholder" role="img" aria-label="${escapeHtml(i18n('fleet.vehicle_alt', { title }))}"></div>`;

  return `
    <article class="fleet-showcase__card" data-categoria-id="${escapeHtml(group.categoria_id)}" data-index-card>
      <div class="fleet-showcase__figure">
        <span class="fleet-showcase__plate" aria-hidden="true"></span>
        ${media}
      </div>
      <h3 class="fleet-showcase__group-title">${title}</h3>
      <p class="fleet-showcase__desc">${desc}</p>
    </article>
  `;
}

function updateFleetCarouselClasses() {
  const cards = $$('#fleet-track .fleet-showcase__card');
  const total = cards.length;
  if (!total) return;

  cards.forEach((card, index) => {
    const rel = fleetRelativeIndex(index, fleetActiveIndex, total);
    card.classList.toggle('is-center', rel === 0);
    card.classList.toggle('is-left', rel === -1);
    card.classList.toggle('is-right', rel === 1);
    card.classList.toggle('is-off', Math.abs(rel) > 1);
    card.setAttribute('aria-hidden', Math.abs(rel) > 1 ? 'true' : 'false');
  });
  bindFleetCardClicks();
}

function bindFleetCardClicks() {
  $$('#fleet-track .fleet-showcase__card.is-center').forEach((card) => {
    card.onclick = () => {
      const categoriaId = card.getAttribute('data-categoria-id');
      if (categoriaId) openReserveModal(categoriaId);
    };
  });
}

function paintFleetCarousel() {
  const track = $('#fleet-track');
  const showcase = $('#fleet-showcase');
  if (!track || !showcase || !fleetGroups.length) return;

  track.innerHTML = fleetGroups.map((g) => fleetCardHtml(g)).join('');
  updateFleetCarouselClasses();
  showcase.hidden = false;
}

function initFleetShowcase() {
  $('#fleet-prev')?.addEventListener('click', () => {
    if (fleetGroups.length < 2) return;
    fleetActiveIndex = (fleetActiveIndex - 1 + fleetGroups.length) % fleetGroups.length;
    updateFleetCarouselClasses();
  });
  $('#fleet-next')?.addEventListener('click', () => {
    if (fleetGroups.length < 2) return;
    fleetActiveIndex = (fleetActiveIndex + 1) % fleetGroups.length;
    updateFleetCarouselClasses();
  });
}

function renderFleetEmpty(message) {
  const showcase = $('#fleet-showcase');
  const empty = $('#fleet-empty');
  if (showcase) showcase.hidden = true;
  if (empty) {
    empty.hidden = false;
    const textEl = empty.querySelector('.fleet-empty__text');
    if (textEl) textEl.textContent = message || i18n('search.status.no_vehicles');
  }
}

function renderFleet(groups) {
  const empty = $('#fleet-empty');
  if (!groups.length) {
    renderFleetEmpty();
    return;
  }
  fleetGroups = groups;
  fleetActiveIndex = groups.length >= 3 ? 1 : 0;
  if (empty) empty.hidden = true;
  paintFleetCarousel();
}

async function runFleetSearch(params) {
  const statusEl = $('#search-status');
  if (statusEl) statusEl.textContent = i18n('search.status.searching');
  statusEl?.classList.remove('is-error');

  try {
    const resp = await bind().grupos(params);
    const groups = bind().mapGruposToFleet(resp);
    if (!groups.length) {
      renderFleetEmpty();
      if (statusEl) statusEl.textContent = i18n('search.status.no_vehicles');
    } else {
      renderFleet(groups);
      if (statusEl) {
        statusEl.textContent = i18n('search.status.groups', { count: groups.length });
      }
    }
    try {
      localStorage.setItem(bind().SEARCH_STATE_KEY, JSON.stringify(params));
      const link = $('#fleet-all-groups-link');
      if (link) link.href = `grupos.html?${searchParamsToQuery(params)}`;
    } catch {
      /* ignore */
    }
  } catch (err) {
    renderFleetEmpty(i18n('search.error.load_fleet'));
    if (statusEl) {
      statusEl.textContent = err.message || i18n('search.error.generic');
      statusEl.classList.add('is-error');
    }
  }
}

function readSearchForm() {
  const filial_id = $('#pickup-location')?.value?.trim() || '';
  const retirada_em = toIsoDateTime($('#pickup-date')?.value, $('#pickup-time')?.value);
  const devolucao_em = toIsoDateTime($('#return-date')?.value, $('#return-time')?.value);
  return { filial_id, retirada_em, devolucao_em };
}

function validateFilial(filial_id) {
  if (!filial_id) return 'search.error.pickup';
  return null;
}

function initSearchWidget() {
  const form = $('#search-form');
  const pickupDate = $('#pickup-date');
  const returnDate = $('#return-date');
  const today = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const isoDate = (d) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  if (pickupDate && !pickupDate.value) pickupDate.value = isoDate(today);
  if (returnDate && !returnDate.value) {
    const ret = new Date(today);
    ret.setDate(ret.getDate() + 3);
    returnDate.value = isoDate(ret);
  }

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const params = readSearchForm();
    const statusEl = $('#search-status');
    const filialErr = validateFilial(params.filial_id);
    if (filialErr) {
      statusEl.textContent = i18n(filialErr);
      statusEl.classList.add('is-error');
      return;
    }
    const err = validateSearch(params.retirada_em, params.devolucao_em);
    if (err) {
      statusEl.textContent = i18n(err);
      statusEl.classList.add('is-error');
      return;
    }
    lastSearch = params;
    await runFleetSearch(params);
    $('#frota')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  try {
    const saved = localStorage.getItem(bind().SEARCH_STATE_KEY);
    if (saved) {
      const p = JSON.parse(saved);
      if (p.filial_id) {
        const loc = $('#pickup-location');
        if (loc) loc.value = p.filial_id;
      }
      if (p.retirada_em) {
        const [rd, rt] = p.retirada_em.split('T');
        $('#pickup-date').value = rd;
        $('#pickup-time').value = rt?.slice(0, 5) || '10:00';
      }
      if (p.devolucao_em) {
        const [dd, dt] = p.devolucao_em.split('T');
        $('#return-date').value = dd;
        $('#return-time').value = dt?.slice(0, 5) || '10:00';
      }
    }
  } catch {
    /* ignore */
  }
}

async function loadCotacaoPreview(categoriaId) {
  const cotacaoEl = $('#reserve-cotacao');
  if (!cotacaoEl || !lastSearch) return;
  cotacaoEl.textContent = i18n('quote.calculating');
  try {
    const data = await bind().cotacao({
      categoria_id: categoriaId,
      filial_retirada_id: lastSearch.filial_id,
      filial_devolucao_id: null,
      retirada_em: lastSearch.retirada_em,
      devolucao_em: lastSearch.devolucao_em,
    });
    const total =
      data?.total_formatado ||
      data?.valor_total_formatado ||
      (data?.total != null ? `Total: R$ ${data.total}` : null);
    cotacaoEl.textContent = total || i18n('quote.on_confirm');
  } catch {
    cotacaoEl.textContent = '';
  }
}

function openReserveModal(categoriaId) {
  if (!lastSearch) {
    $('#search-status').textContent = i18n('search.error.before_reserve');
    $('#search-status')?.classList.add('is-error');
    return;
  }
  pendingCategoriaId = categoriaId;
  const modal = $('#reserve-modal');
  modal?.classList.add('is-open');
  modal?.setAttribute('aria-hidden', 'false');
  $('#reserve-categoria-id').value = categoriaId;
  loadCotacaoPreview(categoriaId);
}

async function submitReservation(e) {
  e.preventDefault();
  if (!lastSearch || !pendingCategoriaId) return;
  const msg = $('#reserve-message');
  msg.textContent = i18n('reserve.sending');
  msg.classList.remove('is-error', 'is-success');

  const payload = {
    cliente: {
      nome: $('#reserve-nome')?.value?.trim(),
      email: $('#reserve-email')?.value?.trim(),
      cpf: $('#reserve-cpf')?.value?.trim(),
      telefone: $('#reserve-telefone')?.value?.trim(),
    },
    categoria_id: pendingCategoriaId,
    filial_retirada_id: lastSearch.filial_id,
    filial_devolucao_id: null,
    retirada_em: lastSearch.retirada_em,
    devolucao_em: lastSearch.devolucao_em,
    observacoes: 'Site Rodavia',
  };

  try {
    await bind().reservar(payload);
    msg.textContent = i18n('reserve.success');
    msg.classList.add('is-success');
  } catch (err) {
    msg.textContent = err.message || i18n('reserve.error');
    msg.classList.add('is-error');
  }
}

function initReserveModal() {
  $('#reserve-form')?.addEventListener('submit', submitReservation);
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    initSkipLink();
    initTopBarCountry();
    initMobileNav();
    initCarousels();
    initCookieBanner();
    initModals();
    initSearchWidget();
    initFleetShowcase();
    initReserveModal();
    document.addEventListener('rodavia:slides-ready', () => {
      const hero = $('[data-hero-carousel]');
      if (hero) delete hero.dataset.heroBound;
      initHeroCarousel();
    });
    document.addEventListener('site:langchange', () => {
      const emptyText = $('#fleet-empty .fleet-empty__text');
      const showcase = $('#fleet-showcase');
      if (emptyText && (!showcase || showcase.hidden)) {
        emptyText.textContent = i18n('fleet.empty');
      }
      if (fleetGroups.length) paintFleetCarousel();
    });
    await bind().boot();
    initHeroCarousel();
  } catch (err) {
    const statusEl = $('#bff-status');
    if (statusEl) {
      statusEl.textContent = i18n('search.error.boot');
      statusEl.classList.add('is-error');
    }
    console.error(err);
  }
});
