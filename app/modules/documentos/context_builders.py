"""Construtores de contexto para templates PDF por entidade."""

from __future__ import annotations

import base64
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.pagination import PageParams
from app.core.storage import storage_service
from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditRepository
from app.modules.cadastros.models import Cliente
from app.modules.cadastros.models_extra import Motorista
from app.modules.cadastros.service import ClienteService
from app.modules.comercial.models import CrmProposta, CrmPropostaItem
from app.modules.comercial.service import PropostaService
from app.modules.financeiro.models import FinContaReceber
from app.modules.financeiro.service import CaixaService, ContaReceberService, FaturamentoService
from app.modules.fiscal.service import NfeService, NfseService
from app.modules.frota.models import FrotaCategoria, FrotaDocumento, FrotaMarca, FrotaModelo, FrotaVeiculo
from app.modules.frota.service import VeiculoService
from app.modules.locacoes.models import LocAvaria, LocContrato, LocContratoAditivo, LocMulta, LocVistoria
from app.modules.locacoes.service import AvariaService, ContratoService, MultaService
from app.modules.manutencao.models import ManOsItem
from app.modules.manutencao.service import OrdemServicoService
from app.modules.reservas.models import ResReserva, ResReservaItem
from app.modules.reservas.service import CotacaoService, ReservaService
from app.modules.tenants.models import Filial
from app.modules.tenants.branding import branding_pdf_context
from app.modules.tenants.repository import TenantRepository
from app.shared.enums import DocumentoVeiculoStatus, TituloStatus, VeiculoStatus, VistoriaTipo


def _qr(url: str | None, label: str = "Validação online") -> dict[str, Any]:
    return {"qr_url": url, "qr_label": label} if url else {}


def _assinatura_b64_from_key(assinatura_key: str | None) -> str | None:
    """Resolve assinatura canvas (R2 key, data URL ou prefixo b64:) para embed no PDF."""
    if not assinatura_key:
        return None
    if assinatura_key.startswith("data:"):
        return assinatura_key.split(",", 1)[-1] if "," in assinatura_key else None
    if assinatura_key.startswith("b64:"):
        return assinatura_key[4:]
    if storage_service.is_configured():
        try:
            return base64.b64encode(storage_service.download_bytes(assinatura_key)).decode("ascii")
        except Exception:  # noqa: BLE001
            return None
    return None


async def build_empresa_pdf_context(session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Contexto de empresa/tenant para templates PDF (contratos, relatórios, etc.)."""
    return await _empresa(session, tenant_id)


async def _empresa(session: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    tenant = await TenantRepository(session).get(tenant_id)
    if tenant is None:
        raise NotFoundError("Empresa não encontrada.")
    return {
        "empresa_nome": tenant.sidebar_display_name,
        "empresa_razao": tenant.legal_name,
        "empresa_cnpj": tenant.cnpj or "—",
        "empresa_email": tenant.email or "—",
        "empresa_phone": tenant.phone or "—",
        **branding_pdf_context(tenant),
    }


async def _filial_nome(session: AsyncSession, filial_id: uuid.UUID | None) -> str:
    if filial_id is None:
        return "—"
    row = await session.get(Filial, filial_id)
    return row.name if row else "—"


async def _cliente_nome(session: AsyncSession, cliente_id: uuid.UUID) -> str:
    row = await session.get(Cliente, cliente_id)
    return row.nome if row else str(cliente_id)


async def _veiculo_label(session: AsyncSession, veiculo_id: uuid.UUID | None) -> str:
    if veiculo_id is None:
        return "—"
    v = await session.get(FrotaVeiculo, veiculo_id)
    if v is None:
        return str(veiculo_id)
    modelo = await session.get(FrotaModelo, v.modelo_id)
    marca = await session.get(FrotaMarca, v.marca_id) if v.marca_id else None
    nome = f"{marca.nome if marca else ''} {modelo.nome if modelo else ''}".strip()
    return f"{v.placa} — {nome or 'Veículo'}"


async def build_reserva(session: AsyncSession, tenant_id: uuid.UUID, reserva_id: uuid.UUID) -> dict:
    reserva = await ReservaService(session).get(reserva_id)
    itens = (
        await session.execute(
            select(ResReservaItem).where(
                ResReservaItem.reserva_id == reserva_id,
                ResReservaItem.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Reserva {reserva.numero}",
            "reserva": reserva,
            "cliente_nome": await _cliente_nome(session, reserva.cliente_id),
            "veiculo_label": await _veiculo_label(session, reserva.veiculo_id),
            "filial_retirada": await _filial_nome(session, reserva.filial_retirada_id),
            "filial_devolucao": await _filial_nome(session, reserva.filial_devolucao_id),
            "itens": itens,
            "watermark": None,
        }
    )
    if reserva.status.value in ("cancelada", "no_show"):
        ctx["watermark"] = "CANCELADO"
    return ctx


async def build_reserva_terceirizada(
    session: AsyncSession, tenant_id: uuid.UUID, reserva_id: uuid.UUID
) -> dict:
    from app.modules.cadastros.models_extra import Fornecedor
    from app.modules.intermediacao.models import FornecedorContratoLocacao

    ctx = await build_reserva(session, tenant_id, reserva_id)
    reserva = ctx["reserva"]
    ctx["doc_titulo"] = f"Confirmação Intermediação — Reserva {reserva.numero}"
    ctx["fornecedor_nome"] = "—"
    ctx["contrato_numero"] = None
    ctx["contrato_titulo"] = None
    ctx["modelo_negocio"] = reserva.modelo_negocio_terceiro.value if reserva.modelo_negocio_terceiro else "—"
    ctx["intermediacao_status"] = reserva.intermediacao_status.value
    ctx["valor_repasse"] = reserva.valor_repasse_total
    ctx["valor_comissao"] = reserva.valor_comissao
    ctx["valor_margem"] = reserva.valor_margem
    if reserva.fornecedor_id:
        forn = (
            await session.execute(
                select(Fornecedor).where(
                    Fornecedor.id == reserva.fornecedor_id,
                    Fornecedor.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if forn:
            ctx["fornecedor_nome"] = forn.nome
    if reserva.contrato_fornecedor_id:
        contrato = (
            await session.execute(
                select(FornecedorContratoLocacao).where(
                    FornecedorContratoLocacao.id == reserva.contrato_fornecedor_id,
                    FornecedorContratoLocacao.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if contrato:
            ctx["contrato_numero"] = contrato.numero
            ctx["contrato_titulo"] = contrato.titulo
    return ctx


async def build_cotacao(session: AsyncSession, tenant_id: uuid.UUID, cotacao_id: uuid.UUID) -> dict:
    cotacao = await CotacaoService(session).get(cotacao_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Cotação {cotacao.numero}",
            "cotacao": cotacao,
            "cliente_nome": await _cliente_nome(session, cotacao.cliente_id)
            if cotacao.cliente_id
            else "—",
            "veiculo_label": await _veiculo_label(session, cotacao.veiculo_id),
            "filial_retirada": await _filial_nome(session, cotacao.filial_retirada_id),
            "watermark": "EXPIRADA" if cotacao.status.value == "expirada" else None,
        }
    )
    return ctx


async def build_contrato(session: AsyncSession, tenant_id: uuid.UUID, contrato_id: uuid.UUID) -> dict:
    contrato = await ContratoService(session).get(contrato_id)
    ctx = await _empresa(session, tenant_id)
    watermark = None
    if contrato.status.value == "cancelado":
        watermark = "CANCELADO"
    elif contrato.status.value == "rascunho":
        watermark = "RASCUNHO"
    ctx.update(
        {
            "doc_titulo": f"Contrato {contrato.numero}",
            "contrato": contrato,
            "cliente_nome": await _cliente_nome(session, contrato.cliente_id),
            "veiculo_label": await _veiculo_label(session, contrato.veiculo_id),
            "filial_retirada": await _filial_nome(session, contrato.filial_retirada_id),
            "filial_devolucao": await _filial_nome(session, contrato.filial_devolucao_id),
            "watermark": watermark,
            "assinatura_b64": _assinatura_b64_from_key(contrato.assinatura_key),
            **_qr(f"/locacoes/contratos/{contrato_id}"),
        }
    )
    return ctx


async def build_vistoria(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    contrato_id: uuid.UUID,
    tipo: VistoriaTipo,
) -> dict:
    contrato = await ContratoService(session).get(contrato_id)
    vistoria = (
        await session.execute(
            select(LocVistoria)
            .where(
                LocVistoria.contrato_id == contrato_id,
                LocVistoria.tipo == tipo,
                LocVistoria.deleted_at.is_(None),
            )
            .order_by(LocVistoria.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    ctx = await build_contrato(session, tenant_id, contrato_id)
    ctx["doc_titulo"] = (
        "Termo de Vistoria (Check-out)"
        if tipo == VistoriaTipo.CHECKOUT
        else "Termo de Devolução (Check-in)"
    )
    ctx["vistoria"] = vistoria
    ctx["vistoria_tipo"] = tipo.value
    return ctx


async def build_avaria(session: AsyncSession, tenant_id: uuid.UUID, avaria_id: uuid.UUID) -> dict:
    avaria = await AvariaService(session).get(avaria_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Laudo de Avaria — {avaria.localizacao}",
            "avaria": avaria,
            "contrato_numero": None,
            "veiculo_label": await _veiculo_label(session, avaria.veiculo_id),
            "watermark": None,
        }
    )
    if avaria.contrato_id:
        c = await session.get(LocContrato, avaria.contrato_id)
        ctx["contrato_numero"] = c.numero if c else None
    return ctx


async def build_ordem_servico(
    session: AsyncSession, tenant_id: uuid.UUID, os_id: uuid.UUID
) -> dict:
    os = await OrdemServicoService(session).get(os_id)
    itens = (
        await session.execute(
            select(ManOsItem).where(
                ManOsItem.os_id == os_id,
                ManOsItem.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    ctx = await _empresa(session, tenant_id)
    watermark = "CANCELADA" if os.status.value == "cancelada" else None
    ctx.update(
        {
            "doc_titulo": f"OS {os.numero}",
            "os": os,
            "itens": itens,
            "veiculo_label": await _veiculo_label(session, os.veiculo_id),
            "filial_nome": await _filial_nome(session, os.filial_id),
            "watermark": watermark,
        }
    )
    return ctx


async def build_ficha_veiculo(
    session: AsyncSession, tenant_id: uuid.UUID, veiculo_id: uuid.UUID
) -> dict:
    veiculo = await VeiculoService(session).get(veiculo_id)
    modelo = await session.get(FrotaModelo, veiculo.modelo_id)
    marca = await session.get(FrotaMarca, veiculo.marca_id) if veiculo.marca_id else None
    categoria = await session.get(FrotaCategoria, veiculo.categoria_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Ficha — {veiculo.placa}",
            "veiculo": veiculo,
            "marca_nome": marca.nome if marca else "—",
            "modelo_nome": modelo.nome if modelo else "—",
            "categoria_nome": categoria.nome if categoria else "—",
            "filial_nome": await _filial_nome(session, veiculo.filial_id),
            "watermark": "BAIXADO" if veiculo.status.value == "baixado" else None,
        }
    )
    return ctx


async def build_proposta(
    session: AsyncSession, tenant_id: uuid.UUID, proposta_id: uuid.UUID
) -> dict:
    proposta = await PropostaService(session).get(proposta_id)
    itens = (
        await session.execute(
            select(CrmPropostaItem).where(
                CrmPropostaItem.proposta_id == proposta_id,
                CrmPropostaItem.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    ctx = await _empresa(session, tenant_id)
    watermark = None
    if proposta.status.value in ("recusada", "expirada"):
        watermark = proposta.status.value.upper()
    ctx.update(
        {
            "doc_titulo": f"Proposta {proposta.numero}",
            "proposta": proposta,
            "itens": itens,
            "cliente_nome": await _cliente_nome(session, proposta.cliente_id)
            if proposta.cliente_id
            else "—",
            "watermark": watermark,
        }
    )
    return ctx


async def build_recibo_pagamento(
    session: AsyncSession, tenant_id: uuid.UUID, titulo_id: uuid.UUID
) -> dict:
    titulo = await ContaReceberService(session).get(titulo_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Recibo {titulo.numero}",
            "titulo": titulo,
            "cliente_nome": await _cliente_nome(session, titulo.cliente_id)
            if titulo.cliente_id
            else "—",
            "filial_nome": await _filial_nome(session, titulo.filial_id),
            "watermark": None,
        }
    )
    return ctx


async def build_danfe(
    session: AsyncSession, tenant_id: uuid.UUID, nfe_id: uuid.UUID
) -> dict:
    nfe_svc = NfeService(session)
    nfe = await nfe_svc.get(nfe_id)
    itens = await nfe_svc.list_nfe_itens(nfe_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"DANFE {nfe.numero}",
            "nfe": nfe,
            "itens": itens,
            "filial_nome": await _filial_nome(session, nfe.filial_id),
            "watermark": None,
        }
    )
    return ctx


async def build_danfse(
    session: AsyncSession, tenant_id: uuid.UUID, nfse_id: uuid.UUID
) -> dict:
    nfse = await NfseService(session).get(nfse_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"DANFSE {nfse.numero}",
            "nfse": nfse,
            "filial_nome": await _filial_nome(session, nfse.filial_id),
            "cliente_nome": await _cliente_nome(session, nfse.cliente_id)
            if nfse.cliente_id
            else "Consumidor não identificado",
            "watermark": None,
        }
    )
    return ctx


async def build_relatorio_analitico(
    titulo: str,
    columns: list[str],
    rows: list[list[Any]],
    summary: dict[str, Any],
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> dict:
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": titulo,
            "columns": columns,
            "rows": rows,
            "summary": summary,
            "watermark": None,
        }
    )
    return ctx


async def build_recibo_caucao(
    session: AsyncSession, tenant_id: uuid.UUID, contrato_id: uuid.UUID
) -> dict:
    contrato = await ContratoService(session).get(contrato_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Recibo de Caução — Contrato {contrato.numero}",
            "contrato": contrato,
            "cliente_nome": await _cliente_nome(session, contrato.cliente_id),
            "veiculo_label": await _veiculo_label(session, contrato.veiculo_id),
            "filial_nome": await _filial_nome(session, contrato.filial_retirada_id),
            "valor_caucao": contrato.caucao,
            "forma_pagamento": contrato.forma_pagamento or "—",
            "watermark": None,
            **_qr(f"/locacoes/contratos/{contrato_id}", "Consultar contrato"),
        }
    )
    return ctx


async def build_boleto_fatura(
    session: AsyncSession, tenant_id: uuid.UUID, fatura_id: uuid.UUID
) -> dict:
    fat_svc = FaturamentoService(session)
    fatura = await fat_svc.get_fatura(fatura_id)
    titulos = await fat_svc.list_titulos(fatura_id)
    ctx = await _empresa(session, tenant_id)
    linha = f"23793.38128 60000.000003 00000.000400 1 {int(fatura.valor_total * 100):011d}"
    ctx.update(
        {
            "doc_titulo": f"Fatura {fatura.numero}",
            "fatura": fatura,
            "titulos": titulos,
            "cliente_nome": await _cliente_nome(session, fatura.cliente_id),
            "linha_digitavel": linha,
            "watermark": "RASCUNHO" if fatura.status.value == "rascunho" else None,
            **_qr(f"/financeiro/faturamento/{fatura_id}", "Detalhe da fatura"),
        }
    )
    return ctx


async def build_doc_vencimentos(
    session: AsyncSession, tenant_id: uuid.UUID, scope_id: uuid.UUID, *, dias: int = 90
) -> dict:
    limite = date.today() + timedelta(days=dias)
    stmt = (
        select(FrotaDocumento, FrotaVeiculo)
        .join(FrotaVeiculo, FrotaVeiculo.id == FrotaDocumento.veiculo_id)
        .where(
            FrotaDocumento.tenant_id == tenant_id,
            FrotaDocumento.deleted_at.is_(None),
            FrotaDocumento.data_validade.is_not(None),
            FrotaDocumento.data_validade <= limite,
        )
        .order_by(FrotaDocumento.data_validade)
    )
    rows = (await session.execute(stmt)).all()
    itens = [
        {
            "placa": v.placa,
            "tipo": d.tipo.value,
            "numero": d.numero or "—",
            "validade": d.data_validade,
            "status": d.status.value,
        }
        for d, v in rows
    ]
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Vencimentos de Documentação ({dias} dias)",
            "itens": itens,
            "dias": dias,
            "total": len(itens),
            "watermark": None,
        }
    )
    return ctx


async def build_ficha_cliente(
    session: AsyncSession, tenant_id: uuid.UUID, cliente_id: uuid.UUID
) -> dict:
    cliente = await ClienteService(session).get(cliente_id)
    ctx = await _empresa(session, tenant_id)
    watermark = "BLOQUEADO" if cliente.blacklist else None
    ctx.update(
        {
            "doc_titulo": f"Ficha Cadastral — {cliente.nome}",
            "cliente": cliente,
            "filial_nome": await _filial_nome(session, cliente.filial_id),
            "watermark": watermark,
        }
    )
    return ctx


async def build_extrato_cliente(
    session: AsyncSession, tenant_id: uuid.UUID, cliente_id: uuid.UUID
) -> dict:
    cliente = await ClienteService(session).get(cliente_id)
    contratos = (
        await session.execute(
            select(LocContrato)
            .where(
                LocContrato.tenant_id == tenant_id,
                LocContrato.cliente_id == cliente_id,
                LocContrato.deleted_at.is_(None),
            )
            .order_by(LocContrato.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    titulos = (
        await session.execute(
            select(FinContaReceber)
            .where(
                FinContaReceber.tenant_id == tenant_id,
                FinContaReceber.cliente_id == cliente_id,
                FinContaReceber.deleted_at.is_(None),
            )
            .order_by(FinContaReceber.vencimento.desc())
            .limit(20)
        )
    ).scalars().all()
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Extrato de Relacionamento — {cliente.nome}",
            "cliente": cliente,
            "contratos": contratos,
            "titulos": titulos,
            "watermark": None,
        }
    )
    return ctx


async def build_multa_condutor(
    session: AsyncSession, tenant_id: uuid.UUID, multa_id: uuid.UUID
) -> dict:
    multa = await MultaService(session).get(multa_id)
    motorista = await session.get(Motorista, multa.motorista_id) if multa.motorista_id else None
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Indicação de Condutor — AIT {multa.ait or multa.codigo_infracao}",
            "multa": multa,
            "motorista": motorista,
            "veiculo_label": await _veiculo_label(session, multa.veiculo_id),
            "cliente_nome": await _cliente_nome(session, multa.cliente_id)
            if multa.cliente_id
            else "—",
            "contrato_numero": None,
            "watermark": None,
        }
    )
    if multa.contrato_id:
        c = await session.get(LocContrato, multa.contrato_id)
        ctx["contrato_numero"] = c.numero if c else None
    return ctx


async def build_auditoria_export(
    session: AsyncSession, tenant_id: uuid.UUID, scope_id: uuid.UUID, *, limit: int = 500
) -> dict:
    repo = AuditRepository(session)
    result = await repo.paginate(
        PageParams(page=1, size=limit),
        tenant_id=tenant_id,
    )
    logs: list[AuditLog] = result.items
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": "Trilha de Auditoria — Exportação",
            "logs": logs,
            "total": result.total,
            "watermark": "CONFIDENCIAL",
        }
    )
    return ctx


async def build_termo_responsabilidade(
    session: AsyncSession, tenant_id: uuid.UUID, contrato_id: uuid.UUID
) -> dict:
    ctx = await build_contrato(session, tenant_id, contrato_id)
    ctx["doc_titulo"] = f"Termo de Responsabilidade — {ctx['contrato'].numero}"
    return ctx


async def build_aditivo_contratual(
    session: AsyncSession, tenant_id: uuid.UUID, aditivo_id: uuid.UUID
) -> dict:
    aditivo = await session.get(LocContratoAditivo, aditivo_id)
    if aditivo is None or aditivo.deleted_at is not None:
        raise NotFoundError("Aditivo contratual não encontrado.")
    contrato = await ContratoService(session).get(aditivo.contrato_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Aditivo v{aditivo.versao} — Contrato {contrato.numero}",
            "aditivo": aditivo,
            "contrato": contrato,
            "cliente_nome": await _cliente_nome(session, contrato.cliente_id),
            "veiculo_label": await _veiculo_label(session, contrato.veiculo_id),
            "filial_nome": await _filial_nome(session, contrato.filial_retirada_id),
            "watermark": None,
            **_qr(f"/locacoes/contratos/{contrato.id}"),
        }
    )
    return ctx


async def build_declaracao_quitacao(
    session: AsyncSession, tenant_id: uuid.UUID, cliente_id: uuid.UUID
) -> dict:
    cliente = await ClienteService(session).get(cliente_id)
    pendentes = (
        await session.execute(
            select(func.count())
            .select_from(FinContaReceber)
            .where(
                FinContaReceber.tenant_id == tenant_id,
                FinContaReceber.cliente_id == cliente_id,
                FinContaReceber.deleted_at.is_(None),
                FinContaReceber.status.in_(
                    (TituloStatus.EM_ABERTO, TituloStatus.VENCIDO, TituloStatus.PAGO_PARCIAL)
                ),
            )
        )
    ).scalar_one()
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Declaração de Quitação — {cliente.nome}",
            "cliente": cliente,
            "filial_nome": await _filial_nome(session, cliente.filial_id),
            "quitado": int(pendentes or 0) == 0,
            "titulos_pendentes": int(pendentes or 0),
            "watermark": "PENDÊNCIAS" if int(pendentes or 0) > 0 else None,
        }
    )
    return ctx


async def build_certidao_regularidade_frota(
    session: AsyncSession, tenant_id: uuid.UUID, scope_id: uuid.UUID
) -> dict:
    _ = scope_id
    veiculos = (
        await session.execute(
            select(FrotaVeiculo).where(
                FrotaVeiculo.tenant_id == tenant_id,
                FrotaVeiculo.deleted_at.is_(None),
                FrotaVeiculo.status != VeiculoStatus.BAIXADO,
            )
        )
    ).scalars().all()
    irregular: list[dict[str, str]] = []
    for v in veiculos:
        vencidos = (
            await session.execute(
                select(FrotaDocumento).where(
                    FrotaDocumento.veiculo_id == v.id,
                    FrotaDocumento.deleted_at.is_(None),
                    FrotaDocumento.status == DocumentoVeiculoStatus.VENCIDO,
                )
            )
        ).scalars().all()
        if vencidos:
            irregular.append(
                {
                    "placa": v.placa,
                    "pendencias": ", ".join(d.tipo.value for d in vencidos),
                }
            )
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": "Certidão de Regularidade da Frota",
            "total_veiculos": len(veiculos),
            "veiculos_irregulares": irregular,
            "regular": len(irregular) == 0,
            "watermark": "IRREGULAR" if irregular else None,
        }
    )
    return ctx


async def build_fechamento_caixa(
    session: AsyncSession, tenant_id: uuid.UUID, sessao_id: uuid.UUID
) -> dict:
    caixa_svc = CaixaService(session)
    sessao = await caixa_svc.get(sessao_id)
    lancamentos = await caixa_svc.list_lancamentos(sessao_id)
    saldo = await caixa_svc.calcular_saldo(sessao_id)
    ctx = await _empresa(session, tenant_id)
    ctx.update(
        {
            "doc_titulo": f"Fechamento de Caixa — {sessao.aberta_em:%d/%m/%Y}",
            "sessao": sessao,
            "lancamentos": lancamentos,
            "saldo_calculado": saldo,
            "filial_nome": await _filial_nome(session, sessao.filial_id),
            "watermark": None,
        }
    )
    return ctx


BUILDERS: dict[str, str] = {
    "reserva_confirmacao": "reserva",
    "reserva_confirmacao_terceirizada": "reserva",
    "reserva_voucher": "reserva",
    "cotacao": "cotacao",
    "contrato_locacao": "contrato",
    "vistoria_checkout": "contrato",
    "vistoria_checkin": "contrato",
    "laudo_avaria": "avaria",
    "ordem_servico": "ordem_servico",
    "ficha_veiculo": "veiculo",
    "proposta_comercial": "proposta",
    "recibo_pagamento": "conta_receber",
    "recibo_caucao": "contrato",
    "boleto_fatura": "fatura",
    "doc_vencimentos": "tenant",
    "ficha_cliente": "cliente",
    "extrato_cliente": "cliente",
    "multa_condutor": "multa",
    "auditoria_export": "tenant",
    "termo_responsabilidade": "contrato",
    "aditivo_contratual": "aditivo",
    "declaracao_quitacao": "cliente",
    "certidao_regularidade_frota": "tenant",
    "fechamento_caixa": "caixa_sessao",
}


async def build_context(
    session: AsyncSession,
    template_id: str,
    tenant_id: uuid.UUID,
    entidade_id: uuid.UUID,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Despacha construção de contexto conforme template."""
    extra = extra or {}
    if template_id in ("reserva_confirmacao", "reserva_voucher"):
        ctx = await build_reserva(session, tenant_id, entidade_id)
        ctx["doc_titulo"] = (
            "Confirmação de Reserva" if template_id == "reserva_confirmacao" else "Voucher de Reserva"
        )
        return ctx
    if template_id == "reserva_confirmacao_terceirizada":
        ctx = await build_reserva_terceirizada(session, tenant_id, entidade_id)
        return ctx
    if template_id == "cotacao":
        return await build_cotacao(session, tenant_id, entidade_id)
    if template_id == "contrato_locacao":
        return await build_contrato(session, tenant_id, entidade_id)
    if template_id == "vistoria_checkout":
        return await build_vistoria(session, tenant_id, entidade_id, VistoriaTipo.CHECKOUT)
    if template_id == "vistoria_checkin":
        return await build_vistoria(session, tenant_id, entidade_id, VistoriaTipo.CHECKIN)
    if template_id == "laudo_avaria":
        return await build_avaria(session, tenant_id, entidade_id)
    if template_id == "ordem_servico":
        return await build_ordem_servico(session, tenant_id, entidade_id)
    if template_id == "ficha_veiculo":
        return await build_ficha_veiculo(session, tenant_id, entidade_id)
    if template_id == "proposta_comercial":
        return await build_proposta(session, tenant_id, entidade_id)
    if template_id == "recibo_pagamento":
        return await build_recibo_pagamento(session, tenant_id, entidade_id)
    if template_id == "danfe":
        return await build_danfe(session, tenant_id, entidade_id)
    if template_id == "danfse":
        return await build_danfse(session, tenant_id, entidade_id)
    if template_id == "relatorio_analitico":
        return await build_relatorio_analitico(
            extra.get("titulo", "Relatório"),
            extra.get("columns", []),
            extra.get("rows", []),
            extra.get("summary", {}),
            tenant_id,
            session,
        )
    if template_id == "recibo_caucao":
        return await build_recibo_caucao(session, tenant_id, entidade_id)
    if template_id == "boleto_fatura":
        return await build_boleto_fatura(session, tenant_id, entidade_id)
    if template_id == "doc_vencimentos":
        return await build_doc_vencimentos(session, tenant_id, entidade_id)
    if template_id == "ficha_cliente":
        return await build_ficha_cliente(session, tenant_id, entidade_id)
    if template_id == "extrato_cliente":
        return await build_extrato_cliente(session, tenant_id, entidade_id)
    if template_id == "multa_condutor":
        return await build_multa_condutor(session, tenant_id, entidade_id)
    if template_id == "auditoria_export":
        return await build_auditoria_export(session, tenant_id, entidade_id)
    if template_id == "termo_responsabilidade":
        return await build_termo_responsabilidade(session, tenant_id, entidade_id)
    if template_id == "aditivo_contratual":
        return await build_aditivo_contratual(session, tenant_id, entidade_id)
    if template_id == "declaracao_quitacao":
        return await build_declaracao_quitacao(session, tenant_id, entidade_id)
    if template_id == "certidao_regularidade_frota":
        return await build_certidao_regularidade_frota(session, tenant_id, entidade_id)
    if template_id == "fechamento_caixa":
        return await build_fechamento_caixa(session, tenant_id, entidade_id)
    raise NotFoundError(f"Template desconhecido: {template_id}")
