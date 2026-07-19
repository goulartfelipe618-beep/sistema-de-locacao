"""Adiciona Instruções + Novo nas listagens."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

IMPORT = '{% from "macros/form_instructions.html" import list_create_actions %}'

REPLACEMENTS: list[tuple[str, str, str, str]] = [
    ("app/modules/cadastros/templates/cadastros/clientes_list.html", "cadastros.cliente", "/cadastros/clientes/novo", "+ Novo Cliente"),
    ("app/modules/cadastros/templates/cadastros/parceiros_list.html", "cadastros.parceiro", "/cadastros/parceiros/novo", "+ Novo Parceiro"),
    ("app/modules/cadastros/templates/cadastros/fornecedores_list.html", "cadastros.fornecedor", "/cadastros/fornecedores/novo", "+ Novo Fornecedor"),
    ("app/modules/cadastros/templates/cadastros/vendedores_list.html", "cadastros.vendedor", "/cadastros/vendedores/novo", "+ Novo Vendedor"),
    ("app/modules/cadastros/templates/cadastros/motoristas_list.html", "cadastros.motorista", "/cadastros/motoristas/novo", "+ Novo Motorista"),
    ("app/modules/frota/templates/frota/veiculos_list.html", "frota.veiculo", "/frota/veiculos/novo", "+ Novo Veículo"),
    ("app/modules/frota/templates/frota/categorias_list.html", "frota.categoria", "/frota/categorias/novo", "+ Nova Categoria"),
    ("app/modules/frota/templates/frota/marcas_list.html", "frota.marca", "/frota/marcas/novo", "+ Nova Marca"),
    ("app/modules/frota/templates/frota/modelos_list.html", "frota.modelo", "/frota/modelos/novo", "+ Novo Modelo"),
    ("app/modules/frota/templates/frota/combustiveis_list.html", "frota.combustivel", "/frota/combustiveis/novo", "+ Novo Combustível"),
    ("app/modules/frota/templates/frota/acessorios_list.html", "frota.acessorio", "/frota/acessorios/novo", "+ Novo Acessório"),
    ("app/modules/frota/templates/frota/documentacao_list.html", "frota.documento", "/frota/documentacao/novo", "+ Novo Documento"),
    ("app/modules/frota/templates/frota/telemetria_list.html", "frota.telemetria", "/frota/telemetria/novo", "+ Novo Dispositivo"),
    ("app/modules/locacoes/templates/locacoes/contratos_list.html", "locacoes.contrato", "/locacoes/contratos/novo", "+ Novo Contrato"),
    ("app/modules/locacoes/templates/locacoes/multas_list.html", "locacoes.multa", "/locacoes/multas/novo", "+ Nova Multa"),
    ("app/modules/locacoes/templates/locacoes/avarias_list.html", "locacoes.avaria", "/locacoes/avarias/novo", "+ Nova Avaria"),
    ("app/modules/reservas/templates/reservas/cotacoes_list.html", "reservas.cotacao", "/reservas/cotacoes/novo", "+ Nova Cotação"),
    ("app/modules/comercial/templates/comercial/cupons_list.html", "comercial.cupom", "/comercial/cupons/novo", "+ Novo Cupom"),
    ("app/modules/comercial/templates/comercial/campanhas_list.html", "comercial.campanha", "/comercial/campanhas/nova", "+ Nova Campanha"),
    ("app/modules/comercial/templates/comercial/propostas_list.html", "comercial.proposta", "/comercial/propostas/nova", "+ Nova Proposta"),
    ("app/modules/financeiro/templates/financeiro/receber_list.html", "financeiro.receber", "/financeiro/receber/novo", "+ Novo Título"),
    ("app/modules/financeiro/templates/financeiro/pagar_list.html", "financeiro.pagar", "/financeiro/pagar/novo", "+ Novo Título"),
    ("app/modules/financeiro/templates/financeiro/bancos_list.html", "financeiro.banco", "/financeiro/bancos/novo", "+ Nova Conta"),
    ("app/modules/financeiro/templates/financeiro/cartoes_list.html", "financeiro.cartao", "/financeiro/cartoes/novo", "+ Nova Transação"),
    ("app/modules/manutencao/templates/manutencao/pneus_list.html", "manutencao.pneu", "/manutencao/pneus/novo", "+ Novo Pneu"),
    ("app/modules/manutencao/templates/manutencao/pecas_list.html", "manutencao.peca", "/manutencao/pecas/novo", "+ Nova Peça"),
    ("app/modules/manutencao/templates/manutencao/preventiva_list.html", "manutencao.preventiva", "/manutencao/preventiva/novo", "+ Novo Plano"),
    ("app/modules/manutencao/templates/manutencao/os_list.html", "manutencao.os", "/manutencao/os/novo", "+ Nova OS"),
    ("app/modules/manutencao/templates/manutencao/corretiva_list.html", "manutencao.os", "/manutencao/corretiva/novo", "+ Nova Corretiva"),
    ("app/modules/identity/templates/identity/users_list.html", "identity.user", "/configuracoes/usuarios/novo", "+ Novo Usuário"),
    ("app/modules/identity/templates/identity/roles_list.html", "identity.role", "/configuracoes/papeis/novo", "+ Novo Papel"),
    ("app/modules/intermediacao/templates/intermediacao/contratos_list.html", "intermediacao.contrato_fornecedor", "/intermediacao/contratos-fornecedor/novo", "+ Novo contrato"),
    ("app/modules/fiscal/templates/fiscal/cancelamentos_list.html", "fiscal.cancelamentos", "/fiscal/cancelamentos/novo", "+ Novo Evento"),
    ("app/modules/fiscal/templates/fiscal/nfe_list.html", "fiscal.nfe", "/fiscal/nfe/novo", "+ Nova NF-e"),
    ("app/modules/fiscal/templates/fiscal/nfse_list.html", "fiscal.nfse", "/fiscal/nfse/novo", "+ Nova NFS-e"),
    ("app/modules/tarifario/templates/tarifario/tabelas_list.html", "tarifario.tabela", "/tarifario/tabelas/novo", "+ Nova Tabela"),
    ("app/modules/tarifario/templates/tarifario/taxas_list.html", "tarifario.taxa", "/tarifario/taxas/novo", "+ Nova Taxa"),
    ("app/modules/tarifario/templates/tarifario/protecoes_list.html", "tarifario.protecao", "/tarifario/protecoes/novo", "+ Nova Proteção"),
    ("app/modules/tarifario/templates/tarifario/temporadas_list.html", "tarifario.temporada", "/tarifario/temporadas/novo", "+ Nova Temporada"),
    ("app/modules/tarifario/templates/tarifario/politicas_list.html", "tarifario.politica", "/tarifario/cancelamento/novo", "+ Nova Política"),
    ("app/modules/tenants/templates/tenants/filiais_list.html", "tenants.filial", "/configuracoes/filiais/nova", "+ Nova Filial"),
]


def ensure_import(content: str) -> str:
    if "macros/form_instructions.html" in content and "list_create_actions" in content:
        return content
    lines = content.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip().startswith("{% extends "):
            lines.insert(i + 1, IMPORT + "\n")
            break
    return "".join(lines)


def patch(rel: str, key: str, href: str, label: str) -> bool:
    path = ROOT / rel
    if not path.exists():
        print(f"MISSING {rel}")
        return False
    content = path.read_text(encoding="utf-8")
    old = f'<a class="btn btn-primary" href="{href}">{label}</a>'
    new = f'{{{{ list_create_actions("{key}", "{label}", "{href}") }}}}'
    if old not in content:
        print(f"SKIP {rel}")
        return False
    content = content.replace(old, new, 1)
    content = ensure_import(content)
    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"OK {rel}")
    return True


def main() -> None:
    n = sum(patch(*row) for row in REPLACEMENTS)
    print(f"Patched {n} list pages")


if __name__ == "__main__":
    main()
