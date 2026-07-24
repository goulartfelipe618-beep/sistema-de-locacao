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
  resolveDefaultFilialId,
} from './fleet-utils.js';

const bind = () => {
  if (!window.RodaviaBind) {
    throw new Error('Carregue js/rodavia-config.js, rodavia-api.js e rodavia-bind.js antes de grupos.js.');
  }
  return window.RodaviaBind;
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const ATTRIBUTE_FILTER_NAMES = ['cambio', 'pax', 'bags', 'fuel'];

function i18n(key, vars) {
  return window.SiteI18n?.t(key, vars) ?? key;
}

let lastSearch = null;
let pendingCategoriaId = null;
let pendingVeiculoId = null;
let lastGroups = [];
let lastVehicles = [];
let lastVehiclesPromise = null;
let categoryLookup = new Map();

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

function normalizeCambio(item) {
  const c = String(item.cambio || item.transmissao_tipica || '').toLowerCase();
  if (/auto|cvt|tiptronic|automático|automatico/.test(c)) return 'automatico';
  return 'manual';
}

function normalizePax(item) {
  const p = Number(item.passageiros ?? item.capacidade_passageiros ?? 5);
  return p >= 5 ? '5' : '4';
}

function normalizeFuel(item) {
  const f = String(item.combustivel || item.fuel || 'flex').toLowerCase();
  if (/diesel/.test(f)) return 'diesel';
  return 'flex';
}

function normalizeBags(item) {
  const bg = Number(item.malas_grandes ?? item.capacidade_porta_malas ?? 1);
  return bg >= 2 ? 'large' : 'small';
}

function readFilterState() {
  const panel = $('#groups-filters');
  if (!panel) return null;
  const checked = (name) =>
    [...panel.querySelectorAll(`input[name="${name}"]:checked`)].map((i) => i.value);
  const tarifaInput = panel.querySelector('input[name="tarifa"]:checked');
  return {
    tarifa: tarifaInput?.value || 'all',
    cambio: checked('cambio'),
    pax: checked('pax'),
    fuel: checked('fuel'),
    bags: checked('bags'),
  };
}

function isAttributeFiltersDefault() {
  const panel = $('#groups-filters');
  if (!panel) return true;
  for (const name of ATTRIBUTE_FILTER_NAMES) {
    const inputs = [...panel.querySelectorAll(`input[name="${name}"]`)];
    const checkedCount = inputs.filter((i) => i.checked).length;
    if (checkedCount !== inputs.length) return false;
  }
  return true;
}

function resetTariffToAll() {
  const allRadio = $('#groups-filters input[name="tarifa"][value="all"]');
  if (allRadio && !allRadio.checked) allRadio.checked = true;
}

function resolveViewMode() {
  const filters = readFilterState();
  if (!filters) return 'groups';
  if (filters.tarifa !== 'all') return 'vehicles';
  if (!isAttributeFiltersDefault()) return 'vehicles';
  return 'groups';
}

function rebuildCategoryLookup() {
  categoryLookup = new Map();
  lastGroups.forEach((g) => {
    if (g.categoria_id) categoryLookup.set(g.categoria_id, g);
  });
}

function enrichVehicle(vehicle) {
  const cat = categoryLookup.get(vehicle.categoria_id);
  if (!cat) return { ...vehicle };
  return {
    ...cat,
    ...vehicle,
    categoria_id: vehicle.categoria_id,
    id: vehicle.id,
    modelo_nome: vehicle.modelo_nome,
    ano_modelo: vehicle.ano_modelo,
    cor: vehicle.cor,
    imagem_url: vehicle.imagem_url || cat.imagem_url,
    categoria_nome: vehicle.categoria_nome || cat.nome,
  };
}

function applyVehicleFilters(vehicles) {
  const filters = readFilterState();
  if (!filters) return vehicles.map(enrichVehicle);
  return vehicles.map(enrichVehicle).filter((item) => {
    if (filters.tarifa !== 'all' && fleetGroupLetter(item) !== filters.tarifa) return false;
    if (!isAttributeFiltersDefault()) {
      if (filters.cambio.length && !filters.cambio.includes(normalizeCambio(item))) return false;
      if (filters.pax.length && !filters.pax.includes(normalizePax(item))) return false;
      if (filters.bags.length && !filters.bags.includes(normalizeBags(item))) return false;
      if (filters.fuel.length && !filters.fuel.includes(normalizeFuel(item))) return false;
    }
    return true;
  });
}

function specTagsHtml(group) {
  const p = group.passageiros ?? group.capacidade_passageiros ?? 5;
  const doors = group.portas ?? 4;
  const cambio = group.cambio || group.transmissao_tipica || i18n('groups.tag_manual');
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
  const cambio = group.cambio || group.transmissao_tipica || '—';
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

function vehicleCardHtml(vehicle) {
  const letter = fleetGroupLetter(vehicle);
  const title = escapeHtml(vehicle.modelo_nome || vehicle.categoria_nome || 'Veículo');
  const metaParts = [];
  if (vehicle.categoria_nome && vehicle.modelo_nome) metaParts.push(vehicle.categoria_nome);
  if (vehicle.ano_modelo) metaParts.push(String(vehicle.ano_modelo));
  if (vehicle.cor) metaParts.push(vehicle.cor);
  const subtitle = escapeHtml(metaParts.join(' · ') || fleetGroupSubtitle(vehicle));
  const daily = formatDailyPrice(vehicle);
  const imgUrl = vehicle.imagem_url;
  const media = imgUrl
    ? `<img class="vehicle-card__img" src="${escapeHtml(imgUrl)}" alt="" loading="lazy" />`
    : `<div class="vehicle-card__placeholder" role="img" aria-label="${title}"></div>`;

  return `
    <article
      class="vehicle-card"
      id="veiculo-${escapeHtml(vehicle.id)}"
      data-categoria-id="${escapeHtml(vehicle.categoria_id)}"
      data-veiculo-id="${escapeHtml(vehicle.id)}"
    >
      <div class="vehicle-card__head">
        <span class="vehicle-card__badge">${escapeHtml(letter)}</span>
        <p class="vehicle-card__category">${escapeHtml(vehicle.categoria_nome || fleetGroupTag(vehicle))}</p>
      </div>
      <h2 class="vehicle-card__title">${title}</h2>
      <p class="vehicle-card__subtitle">${subtitle}</p>
      <div class="vehicle-card__media">${media}</div>
      ${specTagsHtml(vehicle)}
      <ul class="vehicle-card__features">${featureRow(vehicle)}</ul>
      ${
        daily
          ? `<p class="vehicle-card__price"><span class="vehicle-card__price-label">${escapeHtml(i18n('groups.daily_from'))}</span> <strong>${escapeHtml(daily)}</strong></p>`
          : ''
      }
      <button type="button" class="vehicle-card__cta btn btn--primary" data-rent>${escapeHtml(i18n('groups.continue_reserve'))}</button>
    </article>
  `;
}

function bindRentButtons(root) {
  $$('.group-card__cta[data-rent], .vehicle-card__cta[data-rent]', root).forEach((btn) => {
    btn.addEventListener('click', () => {
      const card = btn.closest('.group-card, .vehicle-card');
      const categoriaId = card?.getAttribute('data-categoria-id');
      const veiculoId = card?.getAttribute('data-veiculo-id') || null;
      if (categoriaId) openReserveModal(categoriaId, veiculoId);
    });
  });
}

function showEmptyState({ hasData, vehicleMode }) {
  const empty = $('#groups-empty');
  if (!empty) return;
  const emptyText = $('#groups-empty .groups-empty__text');
  if (!hasData) {
    empty.hidden = false;
    if (emptyText) {
      if (vehicleMode && lastVehicles.length) {
        emptyText.textContent = i18n('groups.empty_vehicles_filtered');
      } else if (!vehicleMode && lastGroups.length) {
        emptyText.textContent = i18n('groups.empty_filtered');
      } else {
        emptyText.textContent = i18n('groups.empty');
      }
    }
    $('#groups-rail')?.classList.remove('is-visible');
    return;
  }
  empty.hidden = true;
}

function renderGroupsGrid(groups) {
  const host = $('#groups-sections');
  const rail = $('#groups-rail');
  if (!host) return;

  if (!groups.length) {
    host.innerHTML = '';
    showEmptyState({ hasData: false, vehicleMode: false });
    return;
  }

  showEmptyState({ hasData: true, vehicleMode: false });
  const segments = groupFleetBySegment(groups);
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

  const letters = [...new Map(groups.map((g) => [fleetGroupLetter(g), g])).entries()];
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

  bindRentButtons(host);
}

function renderVehiclesGrid(vehicles) {
  const host = $('#groups-sections');
  const rail = $('#groups-rail');
  if (!host) return;

  const filtered = applyVehicleFilters(vehicles);
  if (!filtered.length) {
    host.innerHTML = '';
    showEmptyState({ hasData: false, vehicleMode: true });
    return;
  }

  showEmptyState({ hasData: true, vehicleMode: true });
  const filters = readFilterState();
  let html = '';

  if (filters?.tarifa !== 'all') {
    html += `
      <section class="groups-section groups-section--vehicles" aria-labelledby="vehicles-tariff">
        <h2 class="groups-section__title" id="vehicles-tariff">${escapeHtml(i18n('groups.vehicle_group_label', { letter: filters.tarifa }))}</h2>
        <div class="vehicles-grid">${filtered.map((v) => vehicleCardHtml(v)).join('')}</div>
      </section>
    `;
  } else {
    const byLetter = new Map();
    filtered.forEach((v) => {
      const letter = fleetGroupLetter(v);
      if (!byLetter.has(letter)) byLetter.set(letter, []);
      byLetter.get(letter).push(v);
    });
    const letters = [...byLetter.keys()].sort();
    html = letters
      .map((letter) => {
        const items = byLetter.get(letter);
        const segId = `veh-${letter}`;
        return `
          <section class="groups-section groups-section--vehicles" aria-labelledby="${segId}">
            <h2 class="groups-section__title" id="${segId}">${escapeHtml(i18n('groups.vehicle_group_label', { letter }))}</h2>
            <div class="vehicles-grid">${items.map((v) => vehicleCardHtml(v)).join('')}</div>
          </section>
        `;
      })
      .join('');
  }

  host.innerHTML = html;
  rail?.classList.remove('is-visible');
  bindRentButtons(host);
}

async function ensureVehiclesLoaded() {
  if (lastVehicles.length) return lastVehicles;
  if (!lastSearch) return [];
  if (lastVehiclesPromise) return lastVehiclesPromise;

  lastVehiclesPromise = bind()
    .veiculos({
      filial_id: lastSearch.filial_id,
      retirada_em: lastSearch.retirada_em,
      devolucao_em: lastSearch.devolucao_em,
    })
    .then((resp) => {
      lastVehicles = normalizeList(resp);
      return lastVehicles;
    })
    .finally(() => {
      lastVehiclesPromise = null;
    });

  return lastVehiclesPromise;
}

async function renderResults() {
  if (!lastGroups.length && !lastSearch) return;
  const mode = resolveViewMode();
  if (mode === 'groups') {
    renderGroupsGrid(lastGroups);
    updateResultsStatus('groups');
    return;
  }

  const loading = $('#groups-loading');
  if (loading) loading.hidden = false;
  try {
    const vehicles = await ensureVehiclesLoaded();
    renderVehiclesGrid(vehicles);
    updateResultsStatus('vehicles', vehicles);
  } catch (err) {
    renderVehiclesGrid([]);
    const emptyText = $('#groups-empty .groups-empty__text');
    if (emptyText) emptyText.textContent = err.message || i18n('search.error.load_groups');
    $('#groups-empty').hidden = false;
  } finally {
    if (loading) loading.hidden = true;
  }
}

function updateResultsStatus(mode, vehicles = []) {
  const statusEl = $('#search-status');
  if (!statusEl || !lastSearch) return;
  if (mode === 'groups') {
    statusEl.textContent = lastGroups.length
      ? i18n('search.status.groups_page', { count: lastGroups.length })
      : i18n('search.status.no_vehicles');
    statusEl.classList.remove('is-error');
    return;
  }
  const filtered = applyVehicleFilters(vehicles.length ? vehicles : lastVehicles);
  statusEl.textContent = filtered.length
    ? i18n('search.status.groups_page', { count: filtered.length })
    : i18n('search.status.no_vehicles');
  statusEl.classList.remove('is-error');
}

async function loadGroups(params) {
  const statusEl = $('#search-status');
  const loading = $('#groups-loading');
  if (statusEl) statusEl.textContent = i18n('groups.loading_groups');
  if (loading) loading.hidden = false;

  lastVehicles = [];
  lastVehiclesPromise = null;

  try {
    const resp = await bind().grupos(params);
    const groups = bind().mapGruposToFleet(resp);
    lastGroups = groups;
    rebuildCategoryLookup();
    await renderResults();
  } catch (err) {
    lastGroups = [];
    rebuildCategoryLookup();
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

function openReserveModal(categoriaId, veiculoId = null) {
  if (!lastSearch) return;
  pendingCategoriaId = categoriaId;
  pendingVeiculoId = veiculoId;
  $('#reserve-modal')?.classList.add('is-open');
  $('#reserve-categoria-id').value = categoriaId;
  const veiculoField = $('#reserve-veiculo-id');
  if (veiculoField) veiculoField.value = veiculoId || '';
  loadCotacaoPreview(categoriaId);
}

async function submitReservation(e) {
  e.preventDefault();
  if (!lastSearch || !pendingCategoriaId) return;
  const msg = $('#reserve-message');
  msg.textContent = i18n('reserve.sending_short');
  try {
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
    if (pendingVeiculoId) payload.veiculo_id = pendingVeiculoId;
    await bind().reservar(payload);
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

  document.addEventListener('groups:filter-change', async (e) => {
    const source = e.detail?.source;
    if (source === 'attribute' && !isAttributeFiltersDefault()) {
      resetTariffToAll();
    }
    await renderResults();
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
  if (!params?.filial_id) {
    const filial_id = resolveDefaultFilialId($('#pickup-location'));
    if (filial_id) {
      params = { ...(params || {}), ...readSearchForm(), filial_id };
    }
  }
  if (params?.filial_id) {
    if (!params.retirada_em || !params.devolucao_em) {
      Object.assign(params, readSearchForm());
    }
    lastSearch = params;
    fillSearchFormFromParams(params);
    loadGroups(params);
  }

  document.addEventListener('site:langchange', () => {
    const empty = $('#groups-empty');
    const emptyText = $('#groups-empty .groups-empty__text');
    if (emptyText && empty && !empty.hidden) {
      emptyText.textContent =
        resolveViewMode() === 'vehicles'
          ? i18n('groups.empty_vehicles_filtered')
          : i18n('groups.empty');
    }
    if (lastGroups.length) renderResults();
  });
});
