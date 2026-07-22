/**
 * Liga RodaviaAPI aos seletores do HTML (sem alterar layout/CSS).
 * Depende de: rodavia-config.js, rodavia-api.js (RodaviaAPI global).
 */
(function (global) {
  /** @type {Record<string, string>} IDs usados no index.html / grupos.html */
  var SELECTORS = {
    bffStatus: '#bff-status',
    brandLogoImg: '#brand-logo-img',
    pickupLocation: '#pickup-location',
    searchForm: '#search-form',
    searchStatus: '#search-status',
    fleetTrack: '#fleet-track',
    fleetShowcase: '#fleet-showcase',
    fleetEmpty: '#fleet-empty',
    fleetAllGroupsLink: '#fleet-all-groups-link',
    reserveModal: '#reserve-modal',
    reserveForm: '#reserve-form',
    reserveCategoriaId: '#reserve-categoria-id',
    reserveNome: '#reserve-nome',
    reserveEmail: '#reserve-email',
    reserveCpf: '#reserve-cpf',
    reserveTelefone: '#reserve-telefone',
    reserveCotacao: '#reserve-cotacao',
    reserveMessage: '#reserve-message',
    pickupDate: '#pickup-date',
    pickupTime: '#pickup-time',
    returnDate: '#return-date',
    returnTime: '#return-time',
  };

  var SEARCH_STATE_KEY = 'rodavia_last_search';

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function normalizeList(payload) {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.items)) return payload.items;
    if (payload && Array.isArray(payload.data)) return payload.data;
    if (payload && Array.isArray(payload.filiais)) return payload.filiais;
    if (payload && Array.isArray(payload.grupos)) return payload.grupos;
    return [];
  }

  function setText(selector, value) {
    if (value == null || value === '') return;
    $$(selector).forEach(function (el) {
      if (el.tagName === 'A' && el.getAttribute('href') && el.getAttribute('href').indexOf('mailto:') === 0) {
        el.href = 'mailto:' + value;
        el.textContent = value;
      } else if (el.tagName === 'A' && el.getAttribute('href') && el.getAttribute('href').indexOf('tel:') === 0) {
        el.href = 'tel:' + String(value).replace(/\D/g, '');
        el.textContent = value;
      } else {
        el.textContent = value;
      }
    });
  }

  function filialLabel(f) {
    var nome = f.nome || f.descricao || 'Filial';
    var cidade = f.cidade || f.municipio;
    var uf = f.uf || f.estado;
    if (cidade && uf) return nome + ' — ' + cidade + '/' + uf;
    return nome;
  }

  function applyEmpresa(empresa) {
    if (!empresa || typeof empresa !== 'object') return;

    if (empresa.logo_url) {
      var mark = $('.logo__mark');
      var img = $(SELECTORS.brandLogoImg);
      if (img) {
        img.src = empresa.logo_url;
        img.alt = empresa.nome_exibicao || '';
        img.hidden = false;
        if (mark) mark.setAttribute('hidden', '');
      } else if (mark) {
        mark.style.backgroundImage = 'url(' + empresa.logo_url + ')';
        mark.style.backgroundSize = 'cover';
        mark.textContent = '';
      }
    }

    setText('[data-erp="nome_exibicao"]', empresa.nome_exibicao);
    setText('[data-erp="cnpj"]', empresa.cnpj_formatado);
    setText('[data-erp="endereco"]', empresa.endereco_formatado);
    setText('[data-erp="email"]', empresa.email);
    setText('[data-erp="telefone"]', empresa.telefone || empresa.telefone_formatado);

    if (empresa.nome_exibicao) {
      $$('.logo[aria-label]').forEach(function (el) {
        el.setAttribute('aria-label', 'Página inicial ' + empresa.nome_exibicao);
      });
    }

    if (empresa.nome_exibicao && document.title.indexOf('|') >= 0) {
      var parts = document.title.split('|');
      if (parts.length >= 2) {
        document.title = parts[0].trim() + ' | ' + empresa.nome_exibicao;
      }
    }
  }

  function populateFiliaisSelect(filiaisPayload, selectId) {
    var id = selectId || 'pickup-location';
    var select = document.getElementById(id);
    if (!select) return;
    var filiais = normalizeList(filiaisPayload);
    if (!filiais.length) {
      select.innerHTML = '<option value="">Nenhuma filial disponível</option>';
      select.disabled = true;
      return;
    }
    select.disabled = false;
    select.innerHTML =
      '<option value="">Onde você quer retirar o carro?</option>' +
      filiais
        .map(function (f) {
          var fid = f.id || f.filial_id;
          if (!fid) return '';
          return '<option value="' + fid + '">' + filialLabel(f) + '</option>';
        })
        .join('');
  }

  function mapGruposToFleet(gruposPayload) {
    return normalizeList(gruposPayload)
      .map(function (g) {
        return {
          categoria_id: g.categoria_id || g.id,
          nome: g.nome,
          descricao: g.descricao,
          imagem_url: g.imagem_url,
          veiculosCount: g.veiculos_disponiveis != null ? g.veiculos_disponiveis : g.disponiveis,
          passageiros: g.capacidade_passageiros != null ? g.capacidade_passageiros : g.passageiros,
          codigo: g.codigo || g.sigla,
        };
      })
      .filter(function (g) {
        return g.categoria_id;
      });
  }

  function api() {
    if (!global.RodaviaAPI) {
      throw new Error('RodaviaAPI não carregado. Inclua rodavia-api.js antes de rodavia-bind.js.');
    }
    return global.RodaviaAPI;
  }

  async function pingOk() {
    try {
      await api().ping();
      return true;
    } catch (_) {
      return false;
    }
  }

  function restoreFilialFromSearchState() {
    try {
      var saved = localStorage.getItem(SEARCH_STATE_KEY);
      if (!saved) return;
      var p = JSON.parse(saved);
      var sel = document.getElementById('pickup-location');
      if (sel && p.filial_id) sel.value = p.filial_id;
    } catch (_) {
      /* ignore */
    }
  }

  async function boot() {
    var statusEl = $(SELECTORS.bffStatus);
    var waitStart = Date.now();
    while (window.RODAVIA_BFF_READY === undefined && Date.now() - waitStart < 8000) {
      await new Promise(function (r) {
        setTimeout(r, 50);
      });
    }
    var erpOk = await pingOk();
    if (statusEl) {
      statusEl.textContent = erpOk ? 'API conectada' : 'API offline';
      statusEl.classList.toggle('is-ok', erpOk);
      statusEl.classList.toggle('is-off', !erpOk);
    }
    if (!erpOk) return { erpOk: false };

    await Promise.allSettled([
      api()
        .empresa()
        .then(applyEmpresa),
      api()
        .filiais()
        .then(function (data) {
          populateFiliaisSelect(data);
        }),
    ]);

    restoreFilialFromSearchState();
    global.RodaviaBind._booted = true;
    return { erpOk: true };
  }

  global.RodaviaBind = {
    SELECTORS: SELECTORS,
    SEARCH_STATE_KEY: SEARCH_STATE_KEY,
    normalizeList: normalizeList,
    applyEmpresa: applyEmpresa,
    populateFiliaisSelect: populateFiliaisSelect,
    mapGruposToFleet: mapGruposToFleet,
    boot: boot,
    pingOk: pingOk,
    grupos: function (params) {
      return api().grupos(params);
    },
    cotacao: function (body) {
      return api().cotacao(body);
    },
    reservar: function (body) {
      return api().reservar(body);
    },
  };

  // Boot é disparado por main.js após detectar BFF (rodavia-config.js).
})(typeof window !== 'undefined' ? window : globalThis);
