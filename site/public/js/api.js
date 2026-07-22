import { SITE_CONFIG } from './config.js';

const { bffBaseUrl } = SITE_CONFIG;

function useRodaviaApi() {
  return typeof window !== 'undefined' && window.RodaviaAPI;
}

async function bffFetch(path, options = {}) {
  const base = (bffBaseUrl || '').replace(/\/$/, '');
  const url = `${base}${path}`;
  let res;
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error('Não foi possível conectar ao serviço. Verifique sua conexão.');
  }
  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error('Resposta inválida do servidor.');
    }
  }
  if (!res.ok) {
    const msg =
      (data && (typeof data.error === 'string' ? data.error : data.message)) ||
      'Não foi possível completar a operação.';
    throw new Error(typeof msg === 'string' ? msg : 'Erro na requisição.');
  }
  return data;
}

export function ping() {
  if (useRodaviaApi()) return window.RodaviaAPI.ping();
  return bffFetch('/bff/ping');
}

export function getEmpresa() {
  if (useRodaviaApi()) return window.RodaviaAPI.empresa();
  return bffFetch('/bff/empresa');
}

export function getFiliais() {
  if (useRodaviaApi()) return window.RodaviaAPI.filiais();
  return bffFetch('/bff/filiais');
}

export function getGrupos({ filial_id, retirada_em, devolucao_em }) {
  if (useRodaviaApi()) {
    return window.RodaviaAPI.grupos({ filial_id, retirada_em, devolucao_em });
  }
  const q = new URLSearchParams({ filial_id, retirada_em, devolucao_em });
  return bffFetch(`/bff/grupos?${q}`);
}

export function getVeiculos({ filial_id, categoria_id, retirada_em, devolucao_em }) {
  const q = new URLSearchParams({ filial_id, retirada_em, devolucao_em });
  if (categoria_id) q.set('categoria_id', categoria_id);
  return bffFetch(`/bff/veiculos?${q}`);
}

export function postCotacao(payload) {
  if (useRodaviaApi()) return window.RodaviaAPI.cotacao(payload);
  return bffFetch('/bff/cotacao', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function createReserva(payload) {
  if (useRodaviaApi()) return window.RodaviaAPI.reservar(payload);
  return bffFetch('/bff/reservas', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function checkErpPing() {
  try {
    await ping();
    return true;
  } catch {
    return false;
  }
}
