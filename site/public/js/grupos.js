import { SITE_CONFIG } from './config.js';
import {
  normalizeList,
  toIsoDateTime,
  validateSearch,
  groupFleetBySegment,
  fleetGroupTitle,
  fleetGroupSubtitle,
  fleetGroupTag,
  fleetGroupLetter,
  parseSearchFromUrl,
  searchParamsToQuery,
} from './fleet-utils.js';

const bind = () => {
  if (!window.RodaviaBind) {
    throw new Error('Carregue js/rodavia-config.js, rodavia-api.js e rodavia-bind.js antes de grupos.js.');
  }
  return window.RodaviaBind;
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

function i18n(key, vars) {
  return window.SiteI18n?.t(key, vars) ?? key;
}

let lastSearch = null;
let pendingCategoriaId = null;
let lastGroups = [];

function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function initMobileNav() {
  const toggle = $('#nav-toggle');
  const nav = $('#primary-nav');
  toggle?.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(open));
  });
}

function initCookieBanner() {
  const banner = $('#cookie-banner');
  const consent = localStorage.getItem(SITE_CONFIG.cookieConsentKey);
  if (consent) {
    banner?.classList.add('is-hidden');
    document.body.classList.remove('has-cookie-banner');
    return;
  }
  $('#cookie-accept')?.addEventListener('click', () => {
    localStorage.setItem(SITE_CONFIG.cookieConsentKey, 'accepted');
    banner?.classList.add('is-hidden');
    document.body.classList.remove('has-cookie-banner');
  });
  $('#cookie-reject')?.addEventListener('click', () => {
    localStorage.setItem(SITE_CONFIG.cookieConsentKey, 'rejected');
    banner?.classList.add('is-hidden');
    document.body.classList.remove('has-cookie-banner');
  });
}

function readSearchForm() {
  const filial_id = $('#pickup-location')?.value?.trim() || '';
  const retirada_em = toIsoDateTime($('#pickup-date')?.value, $('#pickup-time')?.value);
  const devolucao_em = toIsoDateTime($('#return-date')?.value, $('#return-time')?.value);
  return { filial_id, retirada_em, devolucao_em };
}

function fillSearchFormFromParams(params) {
  if (!params?.retirada_em) return;
  const [rd, rt] = params.retirada_em.split('T');
  $('#pickup-date').value = rd;
  $('#pickup-time').value = rt?.slice(0, 5) || '10:00';
  if (params.devolucao_em) {
    const [dd, dt] = params.devolucao_em.split('T');
    $('#return-date').value = dd;
    $('#return-time').value = dt?.slice(0, 5) || '10:00';
  }
  if (params.filial_id) $('#pickup-location').value = params.filial_id;
}

function initSearchWidget() {
  const form = $('#search-form');
  const today = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const isoDate = (d) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  if (!$('#pickup-date').value) $('#pickup-date').value = isoDate(today);
  if (!$('#return-date').value) {
    const ret = new Date(today);
    ret.setDate(ret.getDate() + 3);
    $('#return-date').value = isoDate(ret);
  }

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const params = readSearchForm();
    const statusEl = $('#search-status');
    if (!params.filial_id) {
      statusEl.textContent = i18n('search.error.pickup');
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
    localStorage.setItem(bind().SEARCH_STATE_KEY, JSON.stringify(params));
    window.history.replaceState(null, '', `grupos.html?${searchParamsToQuery(params)}`);
    await loadGroups(params);
  });
}

function formatDailyPrice(group) {
  const formatted =
    group.diaria_formatada || group.preco_diaria_formatado || group.valor_diaria_formatado;
  if (formatted) return formatted;
  const n = group.diaria ?? group.preco_diaria ?? group.valor_diaria;
  if (n == null || Number.isNaN(Number(n))) return null;
  return `R$ ${Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}/dia`;
}

function normalizeCategory(group) {
  const seg = String(
    group.segmento || group.categoria_segmento || group.nome || ''
  ).toLowerCase();
  if (/lux|premium|execut|black/.test(seg)) return 'luxo';
  if (/suv|utilit|pickup|van|4x4/.test(seg)) return 'suv';
  if (/sedan|sedã/.test(seg)) return 'sedan';
  if (/hatch|compact|econom|popular/.test(seg)) return 'hatch';
  return 'hatch';
}

function normalizeCambio(group) {
  const c = String(group.cambio || '').toLowerCase();
  if (/auto|cvt|tiptronic|automático|automatico/.test(c)) return 'automatico';
  return 'manual';
}

function normalizePax(group) {
  const p = Number(group.passageiros ?? group.capacidade_passageiros ?? 5);
  return p >= 5 ? '5' : '4';
}

function normalizeFuel(group) {
  const f = String(group.combustivel || group.fuel || 'flex').toLowerCase();
  if (/diesel/.test(f)) return 'diesel';
  return 'flex';
}

function readFilterState() {
  const panel = $('#groups-filters');
  if (!panel) return null;
  const checked = (name) =>
    [...panel.querySelectorAll(`input[name="${name}"]:checked`)].map((i) => i.value);
  return {
    cat: checked('cat'),
    cambio: checked('cambio'),
    pax: checked('pax'),
    fuel: checked('fuel'),
    bags: checked('bags'),
  };
}

function normalizeBags(group) {
  const bg = Number(group.malas_grandes ?? 1);
  return bg >= 2 ? 'large' : 'small';
}

function applyFilters(groups) {
  const filters = readFilterState();
  if (!filters) return groups;
  return groups.filter((group) => {
    if (filters.cat.length && !filters.cat.includes(normalizeCategory(group))) return false;
    if (filters.cambio.length && !filters.cambio.includes(normalizeCambio(group))) return false;
    if (filters.pax.length && !filters.pax.includes(normalizePax(group))) return false;
    if (filters.bags.length && !filters.bags.includes(normalizeBags(group))) return false;
    if (filters.fuel.length && !filters.fuel.includes(normalizeFuel(group))) return false;
    return true;
  });
}

function specTagsHtml(group) {
  const p = group.passageiros ?? group.capacidade_passageiros ?? 5;
  const doors = group.portas ?? 4;
  const cambio = group.cambio || i18n('groups.tag_manual');
  const ar = group.ar_condicionado !== false ? i18n('feature.ac') : i18n('feature.no_ac');
  const steer = group.direcao || i18n('groups.tag_electric_steer');
  return `
    <ul class="group-card__tags" aria-label="${escapeHtml(i18n('groups.specs'))}">
      <li>${escapeHtml(String(p))} ${escapeHtml(i18n('groups.tag_seats'))}</li>
      <li>${escapeHtml(ar)}</li>
      <li>${escapeHtml(steer)}</li>
      <li>${escapeHtml(String(doors))} ${escapeHtml(i18n('groups.tag_doors'))}</li>
      <li>${escapeHtml(cambio)}</li>
    </ul>
  `;
}

function featureRow(group) {
  const p = group.passageiros ?? group.capacidade_passageiros ?? '—';
  const bg = group.malas_grandes ?? 1;
  const bp = group.malas_pequenas ?? 1;
  const cambio = group.cambio || '—';
  const ar = group.ar_condicionado !== false ? i18n('feature.ac') : i18n('feature.no_ac');
  return `
    <li><span aria-hidden="true">👤</span> ${escapeHtml(p)}</li>
    <li><span aria-hidden="true">🧳</span> ${bg}G ${bp}P</li>
    <li><span aria-hidden="true">⚙</span> ${escapeHtml(cambio)}</li>
    <li><span aria-hidden="true">❄</span> ${ar}</li>
  `;
}

function groupCardHtml(group) {
  const id = group.categoria_id;
  const title = escapeHtml(fleetGroupTitle(group));
  const subtitle = escapeHtml(fleetGroupSubtitle(group));
  const tag = escapeHtml(fleetGroupTag(group));
  const daily = formatDailyPrice(group);
  const imgUrl = group.imagem_url;
  const media = imgUrl
    ? `<img class="group-card__img" src="${escapeHtml(imgUrl)}" alt="" loading="lazy" />`
    : `<div class="group-card__placeholder" role="img" aria-label="${title}"></div>`;

  return `
    <article class="group-card" id="grupo-${escapeHtml(id)}" data-categoria-id="${escapeHtml(id)}">
      <p class="group-card__tag">${tag}</p>
      <h2 class="group-card__title">${title}</h2>
      <p class="group-card__subtitle">${subtitle}</p>
      <div class="group-card__media">${media}</div>
      ${specTagsHtml(group)}
      <ul class="group-card__features">${featureRow(group)}</ul>
      ${
        daily
          ? `<p class="group-card__price"><span class="group-card__price-label">${escapeHtml(i18n('groups.daily_from'))}</span> <strong>${escapeHtml(daily)}</strong></p>`
          : ''
      }
      <button type="button" class="group-card__cta btn btn--primary" data-rent>${escapeHtml(i18n('groups.continue_reserve'))}</button>
    </article>
  `;
}

function renderGroupsGrid(groups) {
  const filtered = applyFilters(groups);
  const host = $('#groups-sections');
  const rail = $('#groups-rail');
  const empty = $('#groups-empty');
  if (!host) return;

  if (!filtered.length) {
    host.innerHTML = '';
    if (empty) {
      empty.hidden = false;
      const emptyText = $('#groups-empty .groups-empty__text');
      if (emptyText && groups.length) {
        emptyText.textContent = i18n('groups.empty_filtered');
      } else if (emptyText && !groups.length) {
        emptyText.textContent = i18n('groups.empty');
      }
    }
    rail?.classList.remove('is-visible');
    return;
  }

  if (empty) empty.hidden = true;
  const segments = groupFleetBySegment(filtered);
  let html = '';
  segments.forEach((items, segmentTitle) => {
    const segId = segmentTitle.replace(/\W/g, '') || 'geral';
    html += `
      <section class="groups-section" aria-labelledby="seg-${segId}">
        <h2 class="groups-section__title" id="seg-${segId}">${escapeHtml(segmentTitle)}</h2>
        <div class="groups-grid">${items.map((g) => groupCardHtml(g)).join('')}</div>
      </section>
    `;
  });
  host.innerHTML = html;

  const letters = [...new Map(filtered.map((g) => [fleetGroupLetter(g), g])).entries()];
  if (rail) {
    rail.innerHTML = letters
      .map(
        ([letter, g]) =>
          `<button type="button" class="groups-rail__btn" data-jump="grupo-${g.categoria_id}" title="${escapeHtml(fleetGroupTitle(g))}">${letter}</button>`
      )
      .join('');
    rail.classList.add('is-visible');
    $$('.groups-rail__btn', rail).forEach((btn) => {
      btn.addEventListener('click', () => {
        document.getElementById(btn.getAttribute('data-jump'))?.scrollIntoView({ behavior: 'smooth' });
      });
    });
  }

  $$('.group-card__cta[data-rent]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const categoriaId = btn.closest('.group-card')?.getAttribute('data-categoria-id');
      if (categoriaId) openReserveModal(categoriaId);
    });
  });
}

async function loadGroups(params) {
  const statusEl = $('#search-status');
  const loading = $('#groups-loading');
  if (statusEl) statusEl.textContent = i18n('groups.loading_groups');
  if (loading) loading.hidden = false;

  try {
    const resp = await bind().grupos(params);
    const groups = bind().mapGruposToFleet(resp);
    lastGroups = groups;
    renderGroupsGrid(groups);
    if (statusEl) {
      statusEl.textContent = groups.length
        ? i18n('search.status.groups_page', { count: groups.length })
        : i18n('search.status.no_vehicles');
    }
  } catch (err) {
    renderGroupsGrid([]);
    const emptyText = $('#groups-empty .groups-empty__text');
    if (emptyText) emptyText.textContent = err.message || i18n('search.error.load_groups');
    $('#groups-empty').hidden = false;
    if (statusEl) {
      statusEl.textContent = err.message || i18n('search.error.generic');
      statusEl.classList.add('is-error');
    }
  } finally {
    if (loading) loading.hidden = true;
  }
}

async function loadCotacaoPreview(categoriaId) {
  const el = $('#reserve-cotacao');
  if (!el || !lastSearch) return;
  el.textContent = i18n('quote.calculating');
  try {
    const data = await bind().cotacao({
      categoria_id: categoriaId,
      filial_retirada_id: lastSearch.filial_id,
      filial_devolucao_id: null,
      retirada_em: lastSearch.retirada_em,
      devolucao_em: lastSearch.devolucao_em,
    });
    el.textContent =
      data?.total_formatado ||
      data?.valor_total_formatado ||
      (data?.total != null ? `Total: R$ ${data.total}` : '');
  } catch {
    el.textContent = '';
  }
}

function openReserveModal(categoriaId) {
  if (!lastSearch) return;
  pendingCategoriaId = categoriaId;
  $('#reserve-modal')?.classList.add('is-open');
  $('#reserve-categoria-id').value = categoriaId;
  loadCotacaoPreview(categoriaId);
}

async function submitReservation(e) {
  e.preventDefault();
  if (!lastSearch || !pendingCategoriaId) return;
  const msg = $('#reserve-message');
  msg.textContent = i18n('reserve.sending_short');
  try {
    await bind().reservar({
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
    });
    msg.textContent = i18n('reserve.success_short');
    msg.classList.add('is-success');
  } catch (err) {
    msg.textContent = err.message || i18n('reserve.error_short');
    msg.classList.add('is-error');
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  initMobileNav();
  initCookieBanner();
  initSearchWidget();
  $('#reserve-form')?.addEventListener('submit', submitReservation);

  document.addEventListener('groups:filter-change', () => {
    if (lastGroups.length) renderGroupsGrid(lastGroups);
  });

  await bind().boot();

  let params = parseSearchFromUrl();
  if (!params) {
    try {
      const saved = localStorage.getItem(bind().SEARCH_STATE_KEY);
      if (saved) params = JSON.parse(saved);
    } catch {
      /* ignore */
    }
  }
  if (params?.filial_id) {
    lastSearch = params;
    fillSearchFormFromParams(params);
    loadGroups(params);
  }

  document.addEventListener('site:langchange', () => {
    const emptyText = $('#groups-empty .groups-empty__text');
    if (emptyText && $('#groups-empty') && !$('#groups-empty').hidden) {
      emptyText.textContent = i18n('groups.empty');
    }
    if (lastGroups.length) renderGroupsGrid(lastGroups);
  });
});
