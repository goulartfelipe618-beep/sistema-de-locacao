"""Setores operacionais (MVP) — mapeamento papel → área de trabalho e atalhos."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.rbac import has_permission
from app.modules.identity.service import AuthenticatedUser


@dataclass(frozen=True, slots=True)
class SectorInfo:
    slug: str
    name: str
    description: str
    color: str


SECTORS: dict[str, SectorInfo] = {
    "admin-empresa": SectorInfo(
        "admin-empresa",
        "Administração",
        "Configuração completa do sistema e todos os módulos.",
        "#1e5aa8",
    ),
    "gerente-filial": SectorInfo(
        "gerente-filial",
        "Gerência",
        "Gestão operacional e financeira da filial.",
        "#0d6e5a",
    ),
    "vendedor": SectorInfo(
        "vendedor",
        "Vendas e Reservas",
        "Cotação, reserva, CRM e propostas comerciais.",
        "#7c3aed",
    ),
    "operador": SectorInfo(
        "operador",
        "Operação / Balcão",
        "Contratos, entrega e devolução de veículos.",
        "#2563eb",
    ),
    "financeiro": SectorInfo(
        "financeiro",
        "Financeiro e Fiscal",
        "Títulos, caixa, conciliação e notas fiscais.",
        "#b45309",
    ),
    "diretoria": SectorInfo(
        "diretoria",
        "Diretoria",
        "Indicadores e relatórios gerenciais.",
        "#475569",
    ),
    "auditor": SectorInfo(
        "auditor",
        "Auditoria",
        "Consulta e trilha de auditoria (somente leitura).",
        "#64748b",
    ),
}

# Prioridade quando o usuário tem mais de um papel.
_SECTOR_PRIORITY: tuple[str, ...] = (
    "admin-empresa",
    "gerente-filial",
    "diretoria",
    "financeiro",
    "operador",
    "vendedor",
    "auditor",
)

# Atalhos do painel inicial — filtrados por permissão efetiva do usuário.
_QUICK_LINKS: tuple[dict[str, str], ...] = (
    {"label": "Nova Reserva", "url": "/reservas/nova", "permission": "reservas.reserva.criar"},
    {"label": "Nova Cotação", "url": "/reservas/cotacoes/nova", "permission": "reservas.cotacao.criar"},
    {"label": "Novo Contrato", "url": "/locacoes/contratos/novo", "permission": "locacoes.contrato.criar"},
    {"label": "Check-out", "url": "/locacoes/checkout", "permission": "locacoes.checkout.criar"},
    {"label": "Check-in", "url": "/locacoes/checkin", "permission": "locacoes.checkin.criar"},
    {"label": "Novo Cliente", "url": "/cadastros/clientes/novo", "permission": "cadastros.cliente.criar"},
    {"label": "Contas a Receber", "url": "/financeiro/receber", "permission": "financeiro.receber.visualizar"},
    {"label": "Contas a Pagar", "url": "/financeiro/pagar", "permission": "financeiro.pagar.visualizar"},
    {"label": "Emitir NFS-e", "url": "/fiscal/nfse/novo", "permission": "fiscal.nfse.criar"},
    {"label": "Relatórios", "url": "/relatorios/gerencial", "permission": "relatorios.gerencial.visualizar"},
    {"label": "Nova OS", "url": "/manutencao/os/novo", "permission": "manutencao.os.criar"},
    {"label": "Disponibilidade", "url": "/reservas/disponibilidade", "permission": "reservas.disponibilidade.visualizar"},
)


def resolve_primary_sector(user: AuthenticatedUser) -> SectorInfo:
    """Retorna o setor principal do usuário com base nos papéis atribuídos."""
    if user.is_superuser:
        return SECTORS["admin-empresa"]
    for slug in _SECTOR_PRIORITY:
        if slug in user.roles and slug in SECTORS:
            return SECTORS[slug]
    return SECTORS["operador"]


def build_quick_links(user: AuthenticatedUser) -> list[dict[str, str]]:
    """Monta atalhos do dashboard conforme permissões do usuário."""
    links: list[dict[str, str]] = []
    for item in _QUICK_LINKS:
        if has_permission(user.permissions, item["permission"], is_superuser=user.is_superuser):
            links.append({"label": item["label"], "url": item["url"]})
    return links
