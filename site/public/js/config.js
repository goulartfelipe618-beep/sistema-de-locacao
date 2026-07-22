/** Apenas configuração pública do front — sem segredos nem dados do ERP. */
export const SITE_CONFIG = Object.freeze({
  siteVersion: 'v1.0.0',
  /** Legado Node BFF; integração principal usa RodaviaAPI + `/bff` (rodavia-config.js). */
  bffBaseUrl: '',
  cookieConsentKey: 'rodavia_cookie_consent',
  searchStateKey: 'rodavia_last_search',
});
