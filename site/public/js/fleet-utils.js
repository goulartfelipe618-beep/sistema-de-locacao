export function normalizeList(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload?.items && Array.isArray(payload.items)) return payload.items;
  if (payload?.data && Array.isArray(payload.data)) return payload.data;
  if (payload?.veiculos && Array.isArray(payload.veiculos)) return payload.veiculos;
  return [];
}

export function shortId(uuid) {
  if (!uuid || typeof uuid !== 'string') return '—';
  return uuid.split('-')[0].toUpperCase();
}

export function toIsoDateTime(dateStr, timeStr) {
  if (!dateStr) return null;
  const t = timeStr || '10:00';
  const [h, m] = t.split(':').map(Number);
  const d = new Date(`${dateStr}T00:00:00`);
  d.setHours(h || 10, m || 0, 0, 0);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`;
}

export function validateSearch(retiradaIso, devolucaoIso) {
  const r = new Date(retiradaIso);
  const d = new Date(devolucaoIso);
  if (Number.isNaN(r.getTime()) || Number.isNaN(d.getTime())) {
    return 'Informe datas válidas.';
  }
  if (d <= r) {
    return 'A devolução deve ser posterior à retirada.';
  }
  return null;
}

export function fleetGroupTitle(group) {
  const code =
    group.codigo ||
    group.sigla ||
    (group.nome && group.nome.length <= 4 ? group.nome : shortId(group.categoria_id).slice(0, 2));
  const label = group.nome && group.nome.length > 4 ? group.nome : group.nome || 'Categoria';
  if (group.nome && group.nome.includes(' - ')) return group.nome;
  return `Grupo ${String(code).toUpperCase()} - ${label}`;
}

export function fleetGroupSubtitle(group) {
  if (group.descricao) return group.descricao;
  if (group.modelos?.length) {
    return `${group.modelos[0]} ou similar`;
  }
  return 'Modelo representativo da categoria';
}

export function fleetGroupLetter(group) {
  const title = fleetGroupTitle(group);
  const match = title.match(/Grupo\s+([A-Za-z0-9]+)/i);
  if (match) return match[1].charAt(0).toUpperCase();
  return shortId(group.categoria_id).charAt(0);
}

export function fleetGroupTag(group) {
  return (
    group.segmento ||
    group.categoria_segmento ||
    group.nome?.split(' - ')[0]?.toUpperCase() ||
    'CATEGORIA'
  );
}

export function groupVeiculosByCategoria(veiculos, disponibilidade) {
  const livresMap = new Map();
  normalizeList(disponibilidade).forEach((row) => {
    const id = row.categoria_id || row.id;
    if (id) livresMap.set(id, row.livres ?? row.disponiveis ?? row.quantidade);
  });

  const map = new Map();
  veiculos.forEach((v) => {
    const catId = v.categoria_id || v.categoria?.id;
    if (!catId) return;
    if (!map.has(catId)) {
      map.set(catId, {
        categoria_id: catId,
        nome: v.categoria?.nome || v.categoria_nome || null,
        segmento: v.categoria?.segmento || v.segmento || null,
        codigo: v.categoria?.codigo || v.categoria_codigo || null,
        modelos: [],
        veiculosCount: 0,
        livres: livresMap.get(catId),
        imagem_url: v.categoria?.imagem_url || v.imagem_url || null,
        passageiros: v.passageiros ?? v.categoria?.passageiros,
        malas_grandes: v.malas_grandes ?? v.categoria?.malas_grandes,
        malas_pequenas: v.malas_pequenas ?? v.categoria?.malas_pequenas,
        cambio: v.cambio ?? v.categoria?.cambio,
        ar_condicionado: v.ar_condicionado ?? v.categoria?.ar_condicionado,
      });
    }
    const g = map.get(catId);
    g.veiculosCount += 1;
    const modelo = v.modelo || v.nome || v.descricao;
    if (modelo && !g.modelos.includes(modelo)) g.modelos.push(modelo);
    if (!g.imagem_url && (v.imagem_url || v.foto_url)) g.imagem_url = v.imagem_url || v.foto_url;
  });

  livresMap.forEach((livres, catId) => {
    if (!map.has(catId) && livres > 0) {
      map.set(catId, {
        categoria_id: catId,
        nome: null,
        segmento: null,
        modelos: [],
        veiculosCount: 0,
        livres,
      });
    }
  });

  return [...map.values()].filter((g) => g.veiculosCount > 0 || (g.livres != null && g.livres > 0));
}

export function fleetGroupDescription(group) {
  if (group.descricao) return group.descricao;
  if (group.modelos?.length) {
    const sample = group.modelos.slice(0, 2).join(', ');
    return `Veículo similar a: ${sample}, dentre outros.`;
  }
  if (group.veiculosCount != null) {
    return `${group.veiculosCount} veículo(s) disponível(is) neste grupo.`;
  }
  return 'Consulte os detalhes do grupo na agência.';
}

export function groupFleetBySegment(groups) {
  const segments = new Map();
  groups.forEach((g) => {
    const key = fleetGroupTag(g);
    if (!segments.has(key)) segments.set(key, []);
    segments.get(key).push(g);
  });
  return segments;
}

export function searchParamsToQuery(params) {
  const q = new URLSearchParams({
    filial_id: params.filial_id,
    retirada_em: params.retirada_em,
    devolucao_em: params.devolucao_em,
  });
  return q.toString();
}

export function parseSearchFromUrl() {
  const q = new URLSearchParams(window.location.search);
  const filial_id = q.get('filial_id');
  const retirada_em = q.get('retirada_em');
  const devolucao_em = q.get('devolucao_em');
  if (filial_id && retirada_em && devolucao_em) {
    return { filial_id, retirada_em, devolucao_em };
  }
  return null;
}
