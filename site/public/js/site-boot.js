/**
 * Compatibilidade com imports ES module — delega a RodaviaBind (rodavia-bind.js).
 */
export async function initErpBoot() {
  if (typeof window !== 'undefined' && window.RodaviaBind) {
    return window.RodaviaBind.boot();
  }
  return { erpOk: false };
}

export function applyEmpresa(empresa) {
  window.RodaviaBind?.applyEmpresa(empresa);
}

export function populateFiliaisSelect(filiaisPayload, selectId) {
  window.RodaviaBind?.populateFiliaisSelect(filiaisPayload, selectId);
}

export function mapGruposToFleet(gruposPayload) {
  return window.RodaviaBind?.mapGruposToFleet(gruposPayload) ?? [];
}
