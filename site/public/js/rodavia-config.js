/**
 * BFF: mesma origem /bff (nginx faz proxy para o FastAPI interno).
 * Em dev local sem Docker, tenta :8090 como fallback.
 */
(function () {
  if (typeof window.RODAVIA_BFF_BASE === 'string' && window.RODAVIA_BFF_BASE) {
    window.RODAVIA_BFF_READY = true;
    return;
  }

  var host = location.hostname;
  var port = location.port;
  var isLocal = host === 'localhost' || host === '127.0.0.1';

  var candidates = isLocal
    ? (port === '8080' ? ['/bff', 'http://127.0.0.1:8090/bff'] : ['http://127.0.0.1:8090/bff', '/bff'])
    : ['/bff'];

  window.RODAVIA_BFF_BASE = candidates[0];
  window.RODAVIA_BFF_READY = false;

  function pingBase(base) {
    return fetch(base.replace(/\/$/, '') + '/ping', {
      headers: { Accept: 'application/json' },
    }).then(function (res) {
      if (!res.ok) throw new Error(String(res.status));
      return base.replace(/\/$/, '');
    });
  }

  function tryCandidate(i) {
    if (i >= candidates.length) {
      window.RODAVIA_BFF_READY = false;
      return;
    }
    pingBase(candidates[i])
      .then(function (base) {
        window.RODAVIA_BFF_BASE = base;
        window.RODAVIA_BFF_READY = true;
      })
      .catch(function () {
        tryCandidate(i + 1);
      });
  }

  tryCandidate(0);
})();
