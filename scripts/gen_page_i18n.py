"""Generate site-i18n-pages.js from HTML default text."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "site" / "public"
OUT = ROOT / "js" / "site-i18n-pages.js"
keys: dict[str, str] = {}

for html in sorted(ROOT.glob("*.html")):
    text = html.read_text(encoding="utf-8")
    for m in re.finditer(r'data-i18n="([^"]+)"[^>]*>([^<]+)<', text, re.S):
        k = m.group(1)
        v = re.sub(r"\s+", " ", m.group(2)).strip()
        if k.startswith(("page.", "chrome.")):
            keys.setdefault(k, v)
    for m in re.finditer(r'data-i18n-placeholder="([^"]+)"', text):
        k = m.group(1)
        if k.startswith("page."):
            ph = re.search(rf'id="{re.escape(k.split(".")[-1])}"[^>]*placeholder="([^"]+)"', text)
            # simpler: find placeholder near the attribute
            keys.setdefault(k, "")

# Manual placeholders from HTML
placeholders = {
    "page.agencies.filter_placeholder": "Busque por cidade, bairro ou endereço…",
    "page.faq.search_placeholder": "Como podemos ajudar?",
    "page.assinatura.lead_message_ph": "Conte-nos sobre o veículo desejado, prazo ou dúvidas.",
}
keys.update({k: v for k, v in placeholders.items() if k not in keys or not keys[k]})

meta = {
    "meta.assinatura.title": "Carro por Assinatura | LOCADORA RODAVIA",
    "meta.assinatura.description": "Carro por assinatura Rodavia — planos com seguro, manutenção e IPVA inclusos.",
    "meta.app.title": "Carro para APP | LOCADORA RODAVIA",
    "meta.app.description": "Carro para motoristas de aplicativo — planos semanal e mensal com aprovação rápida.",
    "meta.agencias.title": "Rede de Agências | LOCADORA RODAVIA",
    "meta.agencias.description": "Encontre a agência Rodavia mais próxima — endereços, horários e contato.",
    "meta.sobre.title": "Sobre Nós | LOCADORA RODAVIA",
    "meta.sobre.description": "Conheça a história, números e compromisso da LOCADORA RODAVIA.",
    "meta.fidelidade.title": "Clube Rodavia | Fidelidade",
    "meta.fidelidade.description": "Acumule pontos e troque por diárias grátis e upgrades no Clube Rodavia.",
    "meta.duvidas.title": "Dúvidas Frequentes | LOCADORA RODAVIA",
    "meta.duvidas.description": "Central de ajuda Rodavia — reservas, pagamentos, sinistros e requisitos.",
    "meta.termos.title": "Termos e Políticas | LOCADORA RODAVIA",
    "meta.termos.description": "Termos de uso, privacidade e regras de locação Rodavia.",
}
keys.update(meta)

extra = {
    "groups.continue_reserve": "Continuar Reserva",
    "groups.daily_from": "Diária a partir de",
    "groups.empty_filtered": "Nenhum grupo corresponde aos filtros selecionados. Ajuste os filtros ou faça uma nova busca.",
    "groups.specs": "Especificações",
    "groups.tag_seats": "Lugares",
    "groups.tag_doors": "Portas",
    "groups.tag_electric_steer": "Direção elétrica",
    "groups.tag_manual": "Manual",
    "page.grupos.filters": "Filtros",
    "page.grupos.filter_category": "Categoria",
    "page.grupos.filter_transmission": "Câmbio",
    "page.grupos.filter_passengers": "Passageiros",
    "page.grupos.filter_luggage": "Bagagem",
    "page.grupos.filter_fuel": "Combustível",
    "chrome.footer.about_blurb": "Aluguel de carros com retirada rápida, frota diversificada e atendimento em todo o Brasil.",
    "chrome.footer.reservations": "Central de reservas",
    "chrome.footer.assist_24h": "Assistência 24h",
    "chrome.footer.links": "Links rápidos",
    "chrome.footer.terms": "Termos de uso",
    "chrome.footer.privacy": "Política de privacidade",
    "chrome.footer.rental_rules": "Regras de locação",
    "chrome.footer.payments": "Pagamentos e segurança",
    "chrome.footer.ssl": "SSL",
    "chrome.footer.social_instagram": "Instagram",
    "chrome.footer.social_linkedin": "LinkedIn",
    "chrome.footer.social_youtube": "YouTube",
}
keys.update(extra)

js = """/**
 * Page-level i18n messages (auto-generated from HTML + extras).
 * Merged into SiteI18n on load.
 */
(function (global) {
  'use strict';

  var PAGE_MESSAGES = {
    'pt-BR': %s,
    'en-US': {},
    'es-ES': {}
  };

  function mergePageMessages() {
    if (!global.SiteI18n || !global.SiteI18n._mergeLocale) return;
    Object.keys(PAGE_MESSAGES).forEach(function (lang) {
      global.SiteI18n._mergeLocale(lang, PAGE_MESSAGES[lang]);
    });
    if (typeof global.SiteI18n.apply === 'function') {
      global.SiteI18n.apply();
    }
  }

  if (global.SiteI18n) {
    mergePageMessages();
  } else {
    document.addEventListener('DOMContentLoaded', mergePageMessages);
  }
})(window);
""" % json.dumps(keys, ensure_ascii=False, indent=2)

OUT.write_text(js, encoding="utf-8")
print(f"Wrote {OUT} ({len(keys)} keys)")
