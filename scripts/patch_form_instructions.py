"""Aplica cabeçalho com botão Instruções nos templates de formulário."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

IMPORT_LINE = '{% from "macros/form_instructions.html" import form_instructions, form_page_header %}'

# caminho relativo ao ROOT -> chave de instrução
MAPPING: dict[str, str] = {
    "app/modules/cadastros/templates/cadastros/cliente_form.html": "cadastros.cliente",
    "app/modules/cadastros/templates/cadastros/parceiro_form.html": "cadastros.parceiro",
    "app/modules/cadastros/templates/cadastros/fornecedor_form.html": "cadastros.fornecedor",
    "app/modules/cadastros/templates/cadastros/vendedor_form.html": "cadastros.vendedor",
    "app/modules/cadastros/templates/cadastros/motorista_form.html": "cadastros.motorista",
    "app/modules/frota/templates/frota/veiculo_form.html": "frota.veiculo",
    "app/modules/frota/templates/frota/categoria_form.html": "frota.categoria",
    "app/modules/frota/templates/frota/marca_form.html": "frota.marca",
    "app/modules/frota/templates/frota/modelo_form.html": "frota.modelo",
    "app/modules/frota/templates/frota/combustivel_form.html": "frota.combustivel",
    "app/modules/frota/templates/frota/acessorio_form.html": "frota.acessorio",
    "app/modules/frota/templates/frota/documento_form.html": "frota.documento",
    "app/modules/frota/templates/frota/telemetria_form.html": "frota.telemetria",
    "app/modules/reservas/templates/reservas/nova.html": "reservas.nova",
    "app/modules/reservas/templates/reservas/cotacao_form.html": "reservas.cotacao",
    "app/modules/locacoes/templates/locacoes/contrato_form.html": "locacoes.contrato",
    "app/modules/locacoes/templates/locacoes/checkout_form.html": "locacoes.checkout",
    "app/modules/locacoes/templates/locacoes/checkin_form.html": "locacoes.checkin",
    "app/modules/locacoes/templates/locacoes/multa_form.html": "locacoes.multa",
    "app/modules/locacoes/templates/locacoes/avaria_form.html": "locacoes.avaria",
    "app/modules/tarifario/templates/tarifario/tabela_form.html": "tarifario.tabela",
    "app/modules/tarifario/templates/tarifario/taxa_form.html": "tarifario.taxa",
    "app/modules/tarifario/templates/tarifario/protecao_form.html": "tarifario.protecao",
    "app/modules/tarifario/templates/tarifario/temporada_form.html": "tarifario.temporada",
    "app/modules/tarifario/templates/tarifario/politica_form.html": "tarifario.politica",
    "app/modules/intermediacao/templates/intermediacao/config.html": "intermediacao.config",
    "app/modules/intermediacao/templates/intermediacao/contrato_form.html": "intermediacao.contrato_fornecedor",
    "app/modules/intermediacao/templates/intermediacao/indisponibilidades_list.html": "intermediacao.indisponibilidade",
    "app/modules/financeiro/templates/financeiro/receber_form.html": "financeiro.receber",
    "app/modules/financeiro/templates/financeiro/pagar_form.html": "financeiro.pagar",
    "app/modules/financeiro/templates/financeiro/banco_form.html": "financeiro.banco",
    "app/modules/financeiro/templates/financeiro/cartao_form.html": "financeiro.cartao",
    "app/modules/fiscal/templates/fiscal/nfe_form.html": "fiscal.nfe",
    "app/modules/fiscal/templates/fiscal/nfse_form.html": "fiscal.nfse",
    "app/modules/fiscal/templates/fiscal/impostos_form.html": "fiscal.impostos",
    "app/modules/fiscal/templates/fiscal/cancelamentos_form.html": "fiscal.cancelamentos",
    "app/modules/fiscal/templates/fiscal/xml_import.html": "fiscal.xml_import",
    "app/modules/fiscal/templates/fiscal/impostos_apuracao.html": "fiscal.impostos_apuracao",
    "app/modules/manutencao/templates/manutencao/os_form.html": "manutencao.os",
    "app/modules/manutencao/templates/manutencao/pneu_form.html": "manutencao.pneu",
    "app/modules/manutencao/templates/manutencao/peca_form.html": "manutencao.peca",
    "app/modules/manutencao/templates/manutencao/preventiva_form.html": "manutencao.preventiva",
    "app/modules/comercial/templates/comercial/cupom_form.html": "comercial.cupom",
    "app/modules/comercial/templates/comercial/campanha_form.html": "comercial.campanha",
    "app/modules/comercial/templates/comercial/proposta_form.html": "comercial.proposta",
    "app/modules/identity/templates/identity/user_form.html": "identity.user",
    "app/modules/identity/templates/identity/role_form.html": "identity.role",
    "app/modules/tenants/templates/tenants/filial_form.html": "tenants.filial",
    "app/modules/tenants/templates/tenants/company.html": "tenants.empresa",
    "app/modules/tenants/templates/tenants/sistema_config.html": "tenants.sistema",
    "app/modules/relatorios/templates/relatorios/emitir_form.html": "relatorios.emitir",
    "app/modules/relatorios/templates/relatorios/agendamento_form.html": "relatorios.agendamento",
    "app/modules/automacoes/templates/automacoes/regras_list.html": "automacoes.regra",
    "app/modules/automacoes/templates/automacoes/workflows_list.html": "automacoes.workflow",
    "app/modules/parametros/templates/parametros/list.html": "parametros.geral",
}

SPECIAL_HEADERS: dict[str, tuple[str, str]] = {
    "app/modules/cadastros/templates/cadastros/tabelas_list.html": (
        '<div class="card">\n  <div class="toolbar">',
        '<div class="card">\n  {{ form_page_header("Tabelas Auxiliares", "cadastros.tabela_auxiliar") }}\n  <div class="toolbar">',
    ),
    "app/modules/comercial/templates/comercial/funil_kanban.html": (
        '<h2 class="card-title">Funil de Vendas</h2>',
        '{{ form_page_header("Funil de Vendas", "comercial.funil_oportunidade") }}',
    ),
    "app/modules/financeiro/templates/financeiro/caixa_list.html": (
        '<h2 class="card-title">Abrir Caixa</h2>',
        '{{ form_page_header("Abrir Caixa", "financeiro.caixa_abertura") }}',
    ),
    "app/modules/parametros/templates/parametros/list.html": (
        '<div class="toolbar">\n    <h2 class="card-title" style="margin:0">Parâmetros do Sistema</h2>',
        '{{ form_page_header("Parâmetros do Sistema", "parametros.geral") }}\n  <div class="toolbar" style="margin-top:-4px">',
    ),
}

TITLE_PATTERN = re.compile(
    r'<h2 class="card-title">\{\{\s*title\s*\}\}</h2>',
    re.MULTILINE,
)
HEADER_REPLACEMENT = r'{{ form_page_header(title, "{key}") }}'


def ensure_import(content: str) -> str:
    if "form_instructions.html" in content:
        return content
    lines = content.splitlines(keepends=True)
    insert_at = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("{% from ") or line.strip().startswith("{% extends "):
            insert_at = i + 1
    lines.insert(insert_at, IMPORT_LINE + "\n")
    return "".join(lines)


def patch_file(rel_path: str, key: str) -> bool:
    path = ROOT / rel_path
    if not path.exists():
        print(f"MISSING {rel_path}")
        return False
    content = path.read_text(encoding="utf-8")
    original = content

    if rel_path in SPECIAL_HEADERS:
        old, new = SPECIAL_HEADERS[rel_path]
        if old in content and new not in content:
            content = content.replace(old, new, 1)
        elif new in content:
            pass
        else:
            print(f"SKIP special {rel_path}")
            return False
    elif TITLE_PATTERN.search(content):
        content = TITLE_PATTERN.sub(HEADER_REPLACEMENT.format(key=key), content, count=1)
    else:
        print(f"SKIP pattern {rel_path}")
        return False

    content = ensure_import(content)
    if content != original:
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"OK {rel_path}")
        return True
    print(f"UNCHANGED {rel_path}")
    return False


def main() -> None:
    ok = 0
    patched: set[str] = set()
    for rel, key in MAPPING.items():
        if patch_file(rel, key):
            ok += 1
            patched.add(rel)
    for rel in SPECIAL_HEADERS:
        if rel in patched:
            continue
        key_map = {
            "app/modules/cadastros/templates/cadastros/tabelas_list.html": "cadastros.tabela_auxiliar",
            "app/modules/comercial/templates/comercial/funil_kanban.html": "comercial.funil_oportunidade",
            "app/modules/financeiro/templates/financeiro/caixa_list.html": "financeiro.caixa_abertura",
            "app/modules/parametros/templates/parametros/list.html": "parametros.geral",
        }
        if patch_file(rel, key_map.get(rel, "")):
            ok += 1
    print(f"Patched {ok} files")


if __name__ == "__main__":
    main()
