/**
 * Cliente HTTP do site → BFF (mesma origem: /bff).
 * Não altere layout; só integração.
 */
(function (global) {
  var BASE = (typeof global.RODAVIA_BFF_BASE === 'string' && global.RODAVIA_BFF_BASE) || '/bff';
  BASE = BASE.replace(/\/$/, '');

  function apiUrl(path) {
    return BASE + (path.charAt(0) === '/' ? path : '/' + path);
  }

  function errorMessage(data, res) {
    if (data && typeof data.error === 'string') return data.error;
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && data.message) return String(data.message);
    return res.statusText || 'Erro de comunicação';
  }

  async function request(method, path, options) {
    options = options || {};
    var url = apiUrl(path);
    if (options.query) {
      var qs = new URLSearchParams(options.query).toString();
      if (qs) url += (url.indexOf('?') >= 0 ? '&' : '?') + qs;
    }
    var headers = { Accept: 'application/json' };
    var body = options.body;
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }
    var res;
    try {
      res = await fetch(url, {
        method: method,
        headers: headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        cache: options.cache,
      });
    } catch (_) {
      throw new Error('Não foi possível conectar ao serviço. Verifique sua conexão.');
    }
    var data = null;
    var text = await res.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (_) {
        if (!res.ok) throw new Error('Resposta inválida do servidor.');
      }
    }
    if (!res.ok) {
      throw new Error(errorMessage(data, res));
    }
    return data;
  }

  global.RodaviaAPI = {
    ping: function () {
      return request('GET', '/ping');
    },
    empresa: function () {
      return request('GET', '/empresa');
    },
    filiais: function () {
      return request('GET', '/filiais');
    },
    grupos: function (query) {
      return request('GET', '/grupos', { query: query });
    },
    cotacao: function (body) {
      return request('POST', '/cotacao', { body: body });
    },
    reservar: function (body) {
      return request('POST', '/reservas', { body: body });
    },
    atendimento: function (body) {
      return request('POST', '/atendimento', { body: body });
    },
    slides: function () {
      return request('GET', '/slides');
    },
    catalog: function () {
      return request('GET', '/catalog', { cache: 'no-store' });
    },
    slideImagemUrl: function (slideId) {
      return apiUrl('/slides/' + encodeURIComponent(slideId) + '/imagem');
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);
