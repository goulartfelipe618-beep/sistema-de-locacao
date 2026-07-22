"""Popula o tenant com cadastros fictícios completos (idempotente).

Uso:
    python -m scripts.seed          # base (admin, tenant, permissões)
    python -m scripts.seed_demo_data

Variáveis:
    SEED_DEMO_COUNT=7   # registros por formulário (máx. 50)
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.database import UnitOfWork, dispose_engine
from app.core.logging import configure_logging, get_logger
from app.modules.identity.models import User  # noqa: F401 — FK vendedores.usuario_id
from app.modules.cadastros.schemas import ClienteCreate, TabelaAuxiliarCreate
from app.modules.cadastros.schemas_extra import (
    FornecedorCreate,
    ParceiroCreate,
    VendedorCreate,
)
from app.modules.cadastros.service import ClienteService, TabelaAuxiliarService
from app.modules.cadastros.service_extra import (
    FornecedorService,
    ParceiroService,
    VendedorService,
)
from app.modules.comercial.schemas import (
    CampanhaCreate,
    CupomCreate,
    OportunidadeCreate,
    PropostaCreate,
)
from app.modules.comercial.service import CampanhaService, CupomService, FunilService, PropostaService
from app.modules.financeiro.schemas import ContaPagarCreate, ContaReceberCreate
from app.modules.financeiro.service import ContaPagarService, ContaReceberService
from app.modules.frota.models import FrotaModelo
from app.modules.frota.schemas import (
    CategoriaCreate,
    ModeloCreate,
    VeiculoCreate,
)
from app.modules.frota.service import (
    CategoriasService,
    CombustiveisService,
    MarcasService,
    ModelosService,
    VeiculoService,
    ensure_frota_defaults,
)
from app.modules.intermediacao.models import (  # noqa: F401 — FK loc_contratos
    FornecedorContratoLocacao,
    FrotaIndisponibilidadeTerceiro,
)
from app.modules.intermediacao.schemas import ContratoFornecedorCreate
from app.modules.intermediacao.service import IntermediacaoService
from app.modules.locacoes.models import LocContrato, LocVistoria  # noqa: F401
from app.modules.locacoes.schemas import (
    AvariaCreate,
    CheckinConcluirInput,
    CheckoutConcluirInput,
    ContratoCreate,
    MultaCreate,
    RenovacaoInput,
    VistoriaFotoInput,
)
from app.modules.locacoes.service import (
    AvariaService,
    CheckinService,
    CheckoutService,
    ContratoService,
    MultaService,
    RenovacaoService,
)
from app.modules.manutencao.schemas import (
    OrdemServicoCreate,
    PecaCreate,
    PlanoPreventivoCreate,
    PneuCreate,
)
from app.modules.manutencao.service import (
    OrdemServicoService,
    PecaService,
    PlanoPreventivoService,
    PneuService,
)
from app.modules.reservas.schemas import CotacaoCreate, ReservaCreate
from app.modules.reservas.service import CotacaoService, ReservaService
from app.modules.tarifario.schemas import TabelaCreate, TabelaItemCreate
from app.modules.tarifario.service import PricingService, TabelaTarifaService
from app.modules.tenants.models import Filial, Tenant
from app.modules.tenants.repository import FilialRepository, TenantRepository
from app.shared.enums import (
    AvariaOrigem,
    AvariaSeveridade,
    CadastroStatus,
    CorretivaCausa,
    CorretivaResponsavel,
    CrmCupomTipo,
    CrmEstagio,
    OrdemServicoTipo,
    ParceiroTipo,
    PersonType,
    ReservaOrigem,
    ContratoStatus,
    TarifarioCanal,
    VeiculoPropriedade,
    VeiculoStatus,
)
from app.core.pagination import PageParams

from scripts.demo_data.helpers import (
    cnpj_at,
    cpf_at,
    date_future,
    date_past,
    demo_count,
    dt_future,
    dt_past,
    money,
    placa_at,
)

logger = get_logger("seed_demo")


@dataclass
class DemoContext:
    tenant_id: uuid.UUID
    filial_id: uuid.UUID
    filial_ids: list[uuid.UUID] = field(default_factory=list)
    clientes: list[uuid.UUID] = field(default_factory=list)
    parceiros: list[uuid.UUID] = field(default_factory=list)
    fornecedores: list[uuid.UUID] = field(default_factory=list)
    vendedores: list[uuid.UUID] = field(default_factory=list)
    categorias: list[uuid.UUID] = field(default_factory=list)
    marcas: list[uuid.UUID] = field(default_factory=list)
    modelos: list[uuid.UUID] = field(default_factory=list)
    combustiveis: list[uuid.UUID] = field(default_factory=list)
    veiculos: list[uuid.UUID] = field(default_factory=list)
    reservas: list[uuid.UUID] = field(default_factory=list)
    contratos: list[uuid.UUID] = field(default_factory=list)
    pecas: list[uuid.UUID] = field(default_factory=list)


async def _get_tenant_and_filial() -> tuple[Tenant, Filial]:
    async with UnitOfWork(tenant_id=None) as uow:
        tenant = await TenantRepository(uow.session).get_by_slug(settings.default_tenant_slug)
        if tenant is None:
            raise SystemExit("Tenant não encontrado. Execute: python -m scripts.seed")
    async with UnitOfWork(tenant_id=tenant.id) as uow:
        filial = await FilialRepository(uow.session).get_by_code(tenant.id, "0001")
        if filial is None:
            raise SystemExit("Filial matriz não encontrada. Execute: python -m scripts.seed")
        return tenant, filial


async def _enrich_tenant_branding(tenant: Tenant) -> None:
    async with UnitOfWork(tenant_id=tenant.id) as uow:
        t = await uow.session.get(Tenant, tenant.id)
        if t is None:
            return
        if not t.cnpj:
            t.cnpj = "12345678000199"
        if not t.trade_name:
            t.trade_name = "Locadora Rodavia"
        if not t.app_display_name:
            t.app_display_name = "LOCADORA RODAVIA"
        if not t.email:
            t.email = "contato@rodavia.com.br"
        if not t.phone:
            t.phone = "08009792020"
        if not t.city:
            t.city = "São Paulo"
        if not t.state:
            t.state = "SP"
        if not t.address:
            t.address = "Av. Paulista"
            t.number = "1000"
        if t.setup_completed_at is None:
            from datetime import datetime, timezone

            t.setup_completed_at = datetime.now(timezone.utc)
        logger.info("Branding/cadastro empresa demo aplicado.")


async def _ensure_extra_filiais(tenant_id: uuid.UUID, filial_id: uuid.UUID) -> list[uuid.UUID]:
    ids = [filial_id]
    extras = (
        ("0002", "Rodavia — Aeroporto GRU", "Guarulhos", "SP"),
        ("0003", "Rodavia — Centro RJ", "Rio de Janeiro", "RJ"),
    )
    async with UnitOfWork(tenant_id=tenant_id) as uow:
        repo = FilialRepository(uow.session)
        for code, name, city, uf in extras:
            f = await repo.get_by_code(tenant_id, code)
            if f is None:
                f = Filial(
                    tenant_id=tenant_id,
                    code=code,
                    name=name,
                    city=city,
                    state=uf,
                    is_headquarters=False,
                )
                repo.add(f)
                await uow.session.flush()
            ids.append(f.id)
    return ids


async def seed_defaults(ctx: DemoContext) -> None:
    async with UnitOfWork(tenant_id=ctx.tenant_id) as uow:
        await TabelaAuxiliarService(uow.session).ensure_defaults(ctx.tenant_id)
        await ensure_frota_defaults(uow.session, ctx.tenant_id)
        await PricingService(uow.session).ensure_defaults(ctx.tenant_id)

        cats = await CategoriasService(uow.session).list_items(PageParams(page=1, size=100))
        ctx.categorias = [c.id for c in cats.items]
        marcas = await MarcasService(uow.session).list_items(PageParams(page=1, size=100))
        ctx.marcas = [m.id for m in marcas.items]
        comb = await CombustiveisService(uow.session).list_items(PageParams(page=1, size=50))
        ctx.combustiveis = [c.id for c in comb.items]

        # Imagens e ordem nas categorias (site).
        for i, cat in enumerate(cats.items):
            if not cat.imagem_url:
                cat.imagem_url = f"https://picsum.photos/seed/rodavia-cat-{i}/640/360"
            cat.ordem = i
            cat.status = CadastroStatus.ACTIVE
        await uow.session.flush()
    logger.info("Defaults frota/tarifário/auxiliares OK.")


async def seed_cadastros(ctx: DemoContext, n: int) -> None:
    async with UnitOfWork(tenant_id=ctx.tenant_id) as uow:
        cs = ClienteService(uow.session)
        ps = ParceiroService(uow.session)
        fs = FornecedorService(uow.session)
        vs = VendedorService(uow.session)
        aux = TabelaAuxiliarService(uow.session)

        for i in range(n):
            cpf = cpf_at(i)
            if await cs.repo.get_by_cpf(cpf) is None:
                c = await cs.create(
                    ctx.tenant_id,
                    ClienteCreate(
                        person_type=PersonType.NATURAL,
                        nome=f"Cliente Demo {i + 1:02d} Silva",
                        cpf=cpf,
                        email=f"cliente.demo{i + 1}@rodavia.local",
                        telefone=f"1199{i:07d}"[:11],
                        celular=f"1199{i:07d}"[:11],
                        cidade="São Paulo",
                        uf="SP",
                        cep="01310100",
                        endereco=f"Rua Demo {i + 1}",
                        numero=str(100 + i),
                        profissao="Empresário",
                        limite_credito=money(5000, i),
                    ),
                )
                ctx.clientes.append(c.id)
            else:
                existing = await cs.repo.get_by_cpf(cpf)
                if existing:
                    ctx.clientes.append(existing.id)

            cnpj = cnpj_at(i)
            nome_p = f"Parceiro Comercial Demo {i + 1}"
            existing_p = await ps.repo.get_by_cnpj(cnpj)
            if existing_p is None:
                p = await ps.create(
                    ctx.tenant_id,
                    ParceiroCreate(
                        person_type=PersonType.LEGAL,
                        tipo=ParceiroTipo.MARKETPLACE if i % 2 else ParceiroTipo.INDICACAO,
                        nome=nome_p,
                        nome_fantasia=f"Parceiro {i + 1}",
                        cnpj=cnpj,
                        email=f"parceiro{i + 1}@demo.local",
                        comissao_percentual=Decimal(str(5 + i)),
                        telefone=f"1133{i:06d}"[:11],
                        cidade="São Paulo",
                        uf="SP",
                    ),
                )
                ctx.parceiros.append(p.id)
            else:
                ctx.parceiros.append(existing_p.id)

            nome_f = f"Fornecedor Demo {i + 1} Ltda"
            cnpj_f = cnpj_at(i + n)
            existing_f = await fs.repo.get_by_cnpj(cnpj_f)
            if existing_f is None:
                f = await fs.create(
                    ctx.tenant_id,
                    FornecedorCreate(
                        nome=nome_f,
                        nome_fantasia=f"Forn {i + 1}",
                        cnpj=cnpj_f,
                        email=f"fornecedor{i + 1}@demo.local",
                        locadora_parceira=(i < 2),
                        cidade="São Paulo",
                        uf="SP",
                        prazo_pagamento_dias=30,
                        rating=4,
                    ),
                )
                ctx.fornecedores.append(f.id)
            else:
                ctx.fornecedores.append(existing_f.id)

            nome_v = f"Vendedor Demo {i + 1}"
            vend = await vs.list_items(PageParams(page=1, size=200), search=nome_v)
            if not vend.items:
                v = await vs.create(
                    ctx.tenant_id,
                    VendedorCreate(
                        nome=nome_v,
                        email=f"vendedor{i + 1}@rodavia.local",
                        comissao_percentual=Decimal(str(3 + i * 0.5)),
                        meta_faturamento_mes=money(80000, i),
                    ),
                )
                ctx.vendedores.append(v.id)
            elif vend.items:
                ctx.vendedores.append(vend.items[0].id)

            cod_aux = f"cor_demo_{i + 1:02d}"
            grupo = "cor_veiculo"
            exists = await aux.repo.get_by_grupo_codigo(grupo, cod_aux)
            if exists is None:
                await aux.create(
                    ctx.tenant_id,
                    TabelaAuxiliarCreate(
                        grupo=grupo,
                        codigo=cod_aux,
                        descricao=f"Cor demo {( 'Prata', 'Preto', 'Branco', 'Vermelho', 'Azul', 'Cinza', 'Verde')[i % 7]}",
                        ordem=i,
                    ),
                )

    logger.info("Cadastros: %d clientes, parceiros, fornecedores, vendedores.", n)


async def seed_frota(ctx: DemoContext, n: int) -> None:
    if not ctx.marcas or not ctx.categorias or not ctx.combustiveis:
        raise RuntimeError("Frota defaults ausentes.")

    modelos_nomes = (
        "Argo Drive", "Onix Plus", "HB20 Sense", "Corolla XEi", "Compass Longitude",
        "T-Cross Highline", "Civic Touring",
    )

    async with UnitOfWork(tenant_id=ctx.tenant_id) as uow:
        ms = ModelosService(uow.session)
        vs = VeiculoService(uow.session)
        veiculo_repo = vs.repo

        for i in range(n):
            marca_id = ctx.marcas[i % len(ctx.marcas)]
            cat_id = ctx.categorias[i % len(ctx.categorias)]
            nome_mod = modelos_nomes[i % len(modelos_nomes)]
            existing_mod = (
                await uow.session.execute(
                    select(FrotaModelo.id).where(
                        FrotaModelo.tenant_id == ctx.tenant_id,
                        FrotaModelo.marca_id == marca_id,
                        FrotaModelo.nome == nome_mod,
                        FrotaModelo.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if existing_mod:
                modelo_id = existing_mod
            else:
                mod = await ms.create(
                    ctx.tenant_id,
                    ModeloCreate(
                        marca_id=marca_id,
                        nome=nome_mod,
                        categoria_padrao_id=cat_id,
                        versao="Demo",
                        cambio="Automático" if i % 2 else "Manual",
                        portas=4,
                    ),
                )
                modelo_id = mod.id
            ctx.modelos.append(modelo_id)

            placa = placa_at(i)
            if await veiculo_repo.get_by_placa(placa) is None:
                v = await vs.create(
                    ctx.tenant_id,
                    VeiculoCreate(
                        placa=placa,
                        renavam=f"{10000000000 + i}"[-11:],
                        chassi=f"9BWZZZ377VT{i:06d}"[:17],
                        ano_fabricacao=2022 + (i % 3),
                        ano_modelo=2023 + (i % 3),
                        cor=("Prata", "Preto", "Branco", "Vermelho", "Azul", "Cinza", "Verde")[i % 7],
                        marca_id=marca_id,
                        modelo_id=modelo_id,
                        combustivel_id=ctx.combustiveis[i % len(ctx.combustiveis)],
                        filial_id=ctx.filial_ids[i % len(ctx.filial_ids)],
                        propriedade=VeiculoPropriedade.PROPRIA,
                        data_compra=date_past(400 + i * 10),
                        valor_aquisicao=money(85000, i * 100),
                        valor_fipe=money(78000, i * 80),
                        valor_mercado=money(82000, i * 90),
                        km_inicial=1000 + i * 200,
                        km_atual=15000 + i * 1200,
                        publicar_site=True,
                        proprietario_nome="Locadora Rodavia Ltda.",
                        observacoes=f"Veículo demo {i + 1} — publicado no site.",
                    ),
                )
                ctx.veiculos.append(v.id)
            else:
                ex = await veiculo_repo.get_by_placa(placa)
                if ex:
                    ex.publicar_site = True
                    ctx.veiculos.append(ex.id)

        # Categorias extras demo
        cs = CategoriasService(uow.session)
        for i in range(min(3, n)):
            nome = f"Grupo Premium Demo {i + 1}"
            page = await cs.list_items(PageParams(page=1, size=200), search=nome)
            if not page.items:
                c = await cs.create(
                    ctx.tenant_id,
                    CategoriaCreate(
                        nome=nome,
                        descricao="Categoria extra para vitrine demo.",
                        ordem=100 + i,
                        capacidade_passageiros=5,
                        imagem_url=f"https://picsum.photos/seed/rodavia-prem-{i}/640/360",
                    ),
                )
                ctx.categorias.append(c.id)

    logger.info("Frota: %d veículos publicáveis no site.", len(ctx.veiculos))


async def seed_tarifario(ctx: DemoContext) -> None:
    if not ctx.categorias:
        return
    async with UnitOfWork(tenant_id=ctx.tenant_id) as uow:
        svc = TabelaTarifaService(uow.session)
        page = await svc.list_items(PageParams(page=1, size=50), search="Tabela Site Demo")
        if page.items:
            logger.info("Tarifário site demo já existe.")
            return
        itens = [
            TabelaItemCreate(
                categoria_id=cid,
                valor_1_3=money(120, idx),
                valor_4_7=money(105, idx),
                valor_8_15=money(95, idx),
                valor_16_30=money(88, idx),
                valor_mensal=money(2200, idx),
                km_livre=True,
            )
            for idx, cid in enumerate(ctx.categorias[: min(10, len(ctx.categorias))])
        ]
        await svc.create(
            ctx.tenant_id,
            TabelaCreate(
                nome="Tabela Site Demo 2026",
                vigencia_inicio=date(2026, 1, 1),
                canal=TarifarioCanal.SITE,
                prioridade=10,
                itens=itens,
            ),
        )
        await svc.create(
            ctx.tenant_id,
            TabelaCreate(
                nome="Tabela Balcão Demo 2026",
                vigencia_inicio=date(2026, 1, 1),
                canal=TarifarioCanal.BALCAO,
                prioridade=5,
                itens=itens,
            ),
        )
    logger.info("Tarifário demo criado (site + balcão).")


async def seed_manutencao(ctx: DemoContext, n: int) -> None:
    if not ctx.veiculos:
        return
    async with UnitOfWork(tenant_id=ctx.tenant_id) as uow:
        ps = PecaService(uow.session)
        pns = PneuService(uow.session)
        pps = PlanoPreventivoService(uow.session)
        os_svc = OrdemServicoService(uow.session)

        for i in range(n):
            cod = f"PEC-DEMO-{i + 1:03d}"
            if not (await ps.list_items(PageParams(page=1, size=5), search=cod)).items:
                p = await ps.create(
                    ctx.tenant_id,
                    PecaCreate(
                        codigo=cod,
                        nome=f"Peça demo {i + 1} — filtro/óleo",
                        custo_medio=money(45, i),
                    ),
                )
                ctx.pecas.append(p.id)

            nf = f"FOGO-DEMO-{i + 1:04d}"
            if not (await pns.list_items(PageParams(page=1, size=5), search=nf)).items:
                await pns.create(
                    ctx.tenant_id,
                    PneuCreate(
                        numero_fogo=nf,
                        marca="Michelin",
                        modelo="Primacy",
                        medida="205/55 R16",
                        vida_util_km=50000,
                    ),
                )

            nome_plano = f"Plano Preventivo Demo {i + 1}"
            if not (await pps.list_items(PageParams(page=1, size=5), search=nome_plano)).items:
                await pps.create(
                    ctx.tenant_id,
                    PlanoPreventivoCreate(
                        nome=nome_plano,
                        categoria_id=ctx.categorias[i % len(ctx.categorias)] if ctx.categorias else None,
                        intervalo_km=10000,
                        intervalo_meses=6,
                        custo_estimado=money(350, i),
                    ),
                )

            vid = ctx.veiculos[i % len(ctx.veiculos)]
            tipo = OrdemServicoTipo.PREVENTIVA if i % 2 == 0 else OrdemServicoTipo.CORRETIVA
            os_page = await os_svc.list_items(PageParams(page=1, size=200))
            label = f"OS demo {tipo.value} {i + 1}"
            # Mantém os primeiros veículos disponíveis para vitrine/reservas no site.
            if i >= 2 and len(os_page.items) < n * 2:
                await os_svc.create(
                    ctx.tenant_id,
                    OrdemServicoCreate(
                        veiculo_id=vid,
                        tipo=tipo,
                        filial_id=ctx.filial_id,
                        km_entrada=20000 + i * 500,
                        data_previsao=date_future(7 + i),
                        garantia_dias=90,
                        observacoes=label,
                        causa=CorretivaCausa.ACIDENTE if tipo == OrdemServicoTipo.CORRETIVA else None,
                        responsavel_custo=CorretivaResponsavel.CLIENTE
                        if tipo == OrdemServicoTipo.CORRETIVA
                        else None,
                    ),
                )
    logger.info("Manutenção demo: peças, pneus, planos, OS.")


async def seed_intermediacao(ctx: DemoContext, n: int) -> None:
    if not ctx.fornecedores:
        return
    async with UnitOfWork(tenant_id=ctx.tenant_id) as uow:
        svc = IntermediacaoService(uow.session)
        cfg = await svc.get_config(ctx.tenant_id)
        cfg.modo_operacao = cfg.modo_operacao  # touch
        cfg.publicar_terceiros_site = True
        await uow.session.flush()

        for i in range(min(2, n, len(ctx.fornecedores))):
            fid = ctx.fornecedores[i]
            numero = f"CF-DEMO-{i + 1:03d}"
            contratos = await svc.list_contratos_fornecedor(ctx.tenant_id, fornecedor_id=fid)
            if not any(c.numero == numero for c in contratos):
                await svc.create_contrato_fornecedor(
                    ctx.tenant_id,
                    ContratoFornecedorCreate(
                        fornecedor_id=fid,
                        numero=numero,
                        titulo=f"Contrato intermediação demo {i + 1}",
                        vigencia_inicio=date(2026, 1, 1),
                        vigencia_fim=date(2027, 12, 31),
                        percentual_repasse=Decimal("70"),
                        percentual_comissao=Decimal("5"),
                    ),
                )
    logger.info("Intermediação: contratos parceiros demo.")


async def seed_reservas_locacoes(ctx: DemoContext, n: int) -> None:
    if not ctx.clientes or not ctx.categorias or not ctx.veiculos:
        return
    async with UnitOfWork(tenant_id=ctx.tenant_id) as uow:
        rs = ReservaService(uow.session)
        cots = CotacaoService(uow.session)

        existing = await rs.list_items(PageParams(page=1, size=500))
        demo_reservas = {
            r.observacoes: r
            for r in existing.items
            if r.observacoes and r.observacoes.startswith("Reserva demo ")
        }

        for i in range(n):
            label = f"Reserva demo {i + 1}"
            if label in demo_reservas:
                ctx.reservas.append(demo_reservas[label].id)
                continue

            ret = dt_future(10 + i * 3, 10)
            dev = dt_future(13 + i * 3, 10)
            cat = ctx.categorias[i % len(ctx.categorias)]
            cli = ctx.clientes[i % len(ctx.clientes)]

            await cots.create(
                ctx.tenant_id,
                CotacaoCreate(
                    filial_retirada_id=ctx.filial_id,
                    filial_devolucao_id=ctx.filial_id,
                    categoria_id=cat,
                    retirada_em=ret,
                    devolucao_em=dev,
                    cliente_id=cli,
                    vendedor_id=ctx.vendedores[i % len(ctx.vendedores)] if ctx.vendedores else None,
                ),
            )

            res = await rs.create(
                ctx.tenant_id,
                ReservaCreate(
                    cliente_id=cli,
                    categoria_id=cat,
                    filial_retirada_id=ctx.filial_id,
                    filial_devolucao_id=ctx.filial_id,
                    retirada_em=ret,
                    devolucao_em=dev,
                    origem=ReservaOrigem.WEBSITE if i % 2 else ReservaOrigem.BALCAO,
                    vendedor_id=ctx.vendedores[i % len(ctx.vendedores)] if ctx.vendedores else None,
                    observacoes=label,
                ),
            )
            ctx.reservas.append(res.id)

            if i < 3:
                try:
                    await rs.confirmar(res.id)
                except Exception as exc:
                    logger.warning("Confirmar reserva demo %s: %s", res.numero, exc)

    logger.info("Reservas/cotações demo criados.")


_DEMO_FOTO = VistoriaFotoInput(
    storage_key="demo/vistoria/front.jpg",
    angulo="frontal",
    ordem=0,
)


async def seed_locacoes_operacionais(ctx: DemoContext, n: int) -> None:
    """Contratos demo: rascunho, ativo (checkout + renovação), encerrado (check-in)."""
    if not ctx.clientes or not ctx.veiculos:
        return
    async with UnitOfWork(tenant_id=ctx.tenant_id) as uow:
        cs = ContratoService(uow.session)
        checkout = CheckoutService(uow.session)
        checkin = CheckinService(uow.session)
        renov = RenovacaoService(uow.session)
        vs = VeiculoService(uow.session)

        existing = await cs.list_items(PageParams(page=1, size=500))
        demo_contratos = {
            c.observacoes: c
            for c in existing.items
            if c.observacoes and c.observacoes.startswith("Contrato demo ")
        }

        planos = (
            ("Contrato demo 1 — rascunho", None),
            ("Contrato demo 2 — ativo", "ativo"),
            ("Contrato demo 3 — encerrado", "encerrado"),
        )

        for i, (label, fluxo) in enumerate(planos[: min(3, n)]):
            if label in demo_contratos:
                contrato = demo_contratos[label]
                ctx.contratos.append(contrato.id)
                if fluxo == "encerrado" and contrato.status in {
                    ContratoStatus.ATIVO,
                    ContratoStatus.AGUARDANDO_CHECKIN,
                }:
                    await _concluir_checkin_demo(checkin, cs, contrato.id, i)
                continue

            vid = ctx.veiculos[(i + 3) % len(ctx.veiculos)]
            veiculo = await vs.get(vid)
            cli = ctx.clientes[i % len(ctx.clientes)]

            try:
                contrato = await cs.create(
                    ctx.tenant_id,
                    ContratoCreate(
                        cliente_id=cli,
                        veiculo_id=vid,
                        categoria_id=veiculo.categoria_id,
                        filial_retirada_id=ctx.filial_id,
                        filial_devolucao_id=ctx.filial_id,
                        retirada_prevista_em=dt_past(2 + i),
                        devolucao_prevista_em=dt_future(3 + i),
                        observacoes=label,
                    ),
                )
            except Exception as exc:
                logger.warning("Contrato demo '%s': %s", label, exc)
                continue

            ctx.contratos.append(contrato.id)
            if fluxo is None:
                continue

            try:
                await checkout.iniciar(contrato.id)
                contrato = await checkout.concluir(
                    contrato.id,
                    CheckoutConcluirInput(
                        km=veiculo.km_atual or 15000,
                        combustivel_nivel=8,
                        fotos=[_DEMO_FOTO],
                        caucao_confirmada=True,
                        allow_force=True,
                        observacoes=f"Checkout demo {i + 1}",
                    ),
                )
            except Exception as exc:
                logger.warning("Checkout demo '%s': %s", label, exc)
                continue

            if fluxo == "ativo":
                try:
                    await renov.renovar(
                        contrato.id,
                        RenovacaoInput(
                            nova_devolucao=dt_future(8 + i),
                            motivo="Renovação demo",
                        ),
                    )
                except Exception as exc:
                    logger.warning("Renovação demo '%s': %s", label, exc)
                continue

            if fluxo == "encerrado":
                await _concluir_checkin_demo(checkin, cs, contrato.id, i)

    logger.info("Locações operacionais demo: %d contratos.", len(ctx.contratos))


async def _concluir_checkin_demo(
    checkin: CheckinService,
    cs: ContratoService,
    contrato_id: uuid.UUID,
    index: int,
) -> None:
    try:
        contrato = await cs.get(contrato_id)
        if contrato.status == ContratoStatus.ATIVO:
            contrato.status = ContratoStatus.AGUARDANDO_CHECKIN
            await cs.repo.flush()
        km_base = contrato.km_saida or 15000
        await checkin.concluir(
            contrato_id,
            CheckinConcluirInput(
                km_entrada=km_base + 120,
                combustivel_entrada=7,
                fotos=[_DEMO_FOTO],
                observacoes=f"Check-in demo {index + 1}",
            ),
        )
    except Exception as exc:
        logger.warning("Check-in demo contrato %s: %s", contrato_id, exc)


async def seed_comercial_financeiro(ctx: DemoContext, n: int) -> None:
    async with UnitOfWork(tenant_id=ctx.tenant_id) as uow:
        funil = FunilService(uow.session)
        prop = PropostaService(uow.session)
        camp = CampanhaService(uow.session)
        cup = CupomService(uow.session)
        rec = ContaReceberService(uow.session)
        pag = ContaPagarService(uow.session)
        multa = MultaService(uow.session)
        avaria = AvariaService(uow.session)

        op_page = await funil.list_items(PageParams(page=1, size=500))
        demo_ops = {o.titulo for o in op_page.items if o.titulo.startswith("Oportunidade Demo ")}
        prop_page = await prop.list_items(PageParams(page=1, size=500))
        demo_props = {
            p.observacoes for p in prop_page.items if p.observacoes and p.observacoes.startswith("Proposta demo ")
        }
        camp_page = await camp.list_items(PageParams(page=1, size=500))
        demo_camps = {c.nome for c in camp_page.items if c.nome.startswith("CAMP-DEMO-")}
        rec_page = await rec.list_items(PageParams(page=1, size=500))
        demo_rec = {
            r.descricao for r in rec_page.items if r.descricao and r.descricao.startswith("Receber demo locação ")
        }
        pag_page = await pag.list_items(PageParams(page=1, size=500))
        demo_pag = {
            p.descricao for p in pag_page.items if p.descricao and p.descricao.startswith("Pagar demo fornecedor ")
        }

        for i in range(n):
            tit = f"Oportunidade Demo {i + 1} — locação corporativa"
            if tit not in demo_ops:
                await funil.create(
                    ctx.tenant_id,
                    OportunidadeCreate(
                        titulo=tit,
                        estagio=list(CrmEstagio)[i % len(CrmEstagio)],
                        cliente_id=ctx.clientes[i % len(ctx.clientes)] if ctx.clientes else None,
                        vendedor_id=ctx.vendedores[i % len(ctx.vendedores)] if ctx.vendedores else None,
                        valor_estimado=money(3500, i * 100),
                        data_prevista_fechamento=date_future(30 + i),
                    ),
                )

            prop_label = f"Proposta demo {i + 1}"
            if prop_label not in demo_props:
                await prop.create(
                    ctx.tenant_id,
                    PropostaCreate(
                        cliente_id=ctx.clientes[i % len(ctx.clientes)] if ctx.clientes else None,
                        vendedor_id=ctx.vendedores[i % len(ctx.vendedores)] if ctx.vendedores else None,
                        filial_id=ctx.filial_id,
                        observacoes=prop_label,
                    ),
                )

            cn = f"CAMP-DEMO-{i + 1:02d}"
            if cn not in demo_camps:
                await camp.create(
                    ctx.tenant_id,
                    CampanhaCreate(nome=cn, desconto_percentual=Decimal("10")),
                )

            cod_cupom = f"DEMO{i + 1:02d}"
            if await cup.repo.get_by_codigo(cod_cupom) is None:
                await cup.create(
                    ctx.tenant_id,
                    CupomCreate(
                        codigo=cod_cupom,
                        tipo=CrmCupomTipo.PERCENTUAL,
                        valor=Decimal("5"),
                        descricao=f"Cupom demo {i + 1}",
                    ),
                )

            rec_label = f"Receber demo locação {i + 1}"
            if rec_label not in demo_rec:
                await rec.create(
                    ctx.tenant_id,
                    ContaReceberCreate(
                        cliente_id=ctx.clientes[i % len(ctx.clientes)] if ctx.clientes else None,
                        filial_id=ctx.filial_id,
                        descricao=rec_label,
                        valor_original=money(890, i * 10),
                        vencimento=date_future(15 + i),
                    ),
                )

            pag_label = f"Pagar demo fornecedor {i + 1}"
            if pag_label not in demo_pag:
                await pag.create(
                    ctx.tenant_id,
                    ContaPagarCreate(
                        fornecedor_id=ctx.fornecedores[i % len(ctx.fornecedores)]
                        if ctx.fornecedores
                        else None,
                        filial_id=ctx.filial_id,
                        descricao=pag_label,
                        valor_original=money(450, i * 5),
                        vencimento=date_future(20 + i),
                    ),
                )

            if ctx.veiculos:
                multa_label = f"Multa demo {i + 1}"
                multa_page = await multa.list_items(PageParams(page=1, size=500))
                if not any(m.observacoes == multa_label for m in multa_page.items if m.observacoes):
                    await multa.create(
                        ctx.tenant_id,
                        MultaCreate(
                            veiculo_id=ctx.veiculos[i % len(ctx.veiculos)],
                            ocorrido_em=dt_past(20 + i),
                            orgao="DETRAN-SP",
                            codigo_infracao="7455",
                            valor=money(195, i),
                            observacoes=multa_label,
                        ),
                    )
                avaria_label = f"Avaria demo {i + 1}"
                avaria_page = await avaria.list_items(PageParams(page=1, size=500))
                if not any(a.observacoes == avaria_label for a in avaria_page.items if a.observacoes):
                    await avaria.create(
                        ctx.tenant_id,
                        AvariaCreate(
                            veiculo_id=ctx.veiculos[i % len(ctx.veiculos)],
                            origem=AvariaOrigem.CHECKIN,
                            localizacao="Para-choque dianteiro",
                            severidade=AvariaSeveridade.LEVE,
                            observacoes=avaria_label,
                        ),
                    )

    logger.info("Comercial + financeiro + multas/avarias demo.")


async def seed_finalize_site(ctx: DemoContext) -> None:
    """Garante veículos demo publicáveis e disponíveis para a API/site."""
    if not ctx.veiculos:
        return
    async with UnitOfWork(tenant_id=ctx.tenant_id) as uow:
        vs = VeiculoService(uow.session)
        for vid in ctx.veiculos:
            v = await vs.get(vid)
            v.publicar_site = True
            if v.status == VeiculoStatus.MANUTENCAO:
                await vs.change_status(vid, VeiculoStatus.DISPONIVEL, "Seed demo — vitrine site")
    logger.info("Veículos demo prontos para publicação no site.")


async def run_demo_seed() -> DemoContext:
    n = demo_count()
    tenant, filial = await _get_tenant_and_filial()
    await _enrich_tenant_branding(tenant)

    ctx = DemoContext(tenant_id=tenant.id, filial_id=filial.id)
    ctx.filial_ids = await _ensure_extra_filiais(tenant.id, filial.id)

    await seed_defaults(ctx)
    await seed_cadastros(ctx, n)
    await seed_frota(ctx, n)
    await seed_tarifario(ctx)
    await seed_reservas_locacoes(ctx, n)
    await seed_locacoes_operacionais(ctx, n)
    await seed_manutencao(ctx, n)
    await seed_intermediacao(ctx, n)
    await seed_comercial_financeiro(ctx, n)
    await seed_finalize_site(ctx)

    return ctx


async def main() -> None:
    configure_logging()
    logger.info("Iniciando seed demo (SEED_DEMO_COUNT=%s)...", demo_count())
    ctx = await run_demo_seed()
    await dispose_engine()

    print("\n" + "=" * 60)
    print(" SEED DEMO CONCLUÍDO")
    print("=" * 60)
    print(f" Tenant ..........: {settings.default_tenant_slug}")
    print(f" Registros/form ..: {demo_count()}")
    print(f" Clientes ........: {len(ctx.clientes)}")
    print(f" Veículos (site) .: {len(ctx.veiculos)} (publicar_site=true)")
    print(f" Reservas ........: {len(ctx.reservas)}")
    print(f" Contratos .......: {len(ctx.contratos)}")
    print("\n Veículos elegíveis ao site: status disponível + publicar_site.")
    print(" Teste API: GET /api/v1/public/grupos (com API Key)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
