/**
 * Cliente HTTP do site → BFF (mesma origem: /bff).
 * Não altere layout; só integração.
 */
(function (global) {
  var BASE = "/bff";

  function apiUrl(path) {
    return BASE + (path.charAt(0) === "/" ? path : "/" + path);
  }

  async function request(method, path, options) {
    options = options || {};
    var url = apiUrl(path);
    if (options.query) {
      var qs = new URLSearchParams(options.query).toString();
      if (qs) url += (url.indexOf("?") >= 0 ? "&" : "?") + qs;
    }
    var res = await fetch(url, {
      method: method,
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    var data = null;
    try {
      data = await res.json();
    } catch (_) {
      data = null;
    }
    if (!res.ok) {
      var msg = (data && data.error) || res.statusText || "Erro de comunicação";
      throw new Error(msg);
    }
    return data;
  }

  global.RodaviaAPI = {
    ping: function () {
      return request("GET", "/ping");
    },
    empresa: function () {
      return request("GET", "/empresa");
    },
    filiais: function () {
      return request("GET", "/filiais");
    },
    grupos: function (query) {
      return request("GET", "/grupos", { query: query });
    },
    cotacao: function (body) {
      return request("POST", "/cotacao", { body: body });
    },
    reservar: function (body) {
      return request("POST", "/reservas", { body: body });
    },
  };
})(typeof window !== "undefined" ? window : globalThis);
