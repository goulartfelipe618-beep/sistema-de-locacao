"""Enumerações compartilhadas entre módulos."""

from __future__ import annotations

import enum


class TenantStatus(str, enum.Enum):
    """Situação de uma empresa (tenant) na plataforma SaaS."""

    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELED = "canceled"


class FilialStatus(str, enum.Enum):
    """Situação de uma filial/unidade operacional."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class PermissionAction(str, enum.Enum):
    """Ações padronizadas do RBAC (verbo da permissão)."""

    VIEW = "visualizar"
    CREATE = "criar"
    EDIT = "editar"
    DELETE = "excluir"
    APPROVE = "aprovar"
    CANCEL = "cancelar"
    REVERSE = "estornar"
    EXPORT = "exportar"


class PersonType(str, enum.Enum):
    """Tipo de pessoa (usado em clientes, fornecedores, etc.)."""

    NATURAL = "pf"  # Pessoa Física
    LEGAL = "pj"  # Pessoa Jurídica


class ClienteStatus(str, enum.Enum):
    """Situação cadastral do cliente."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class CadastroStatus(str, enum.Enum):
    """Situação genérica ativo/inativo para cadastros mestre."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class MotoristaVinculo(str, enum.Enum):
    """Tipo de vínculo do motorista."""

    CLIENTE = "cliente"
    FUNCIONARIO = "funcionario"
    TERCEIRO = "terceiro"


class MotoristaCnhStatus(str, enum.Enum):
    """Situação da CNH do motorista."""

    REGULAR = "regular"
    VENCIDA = "vencida"
    SUSPENSA = "suspensa"
    CASSADA = "cassada"


class ParceiroTipo(str, enum.Enum):
    """Tipo de parceria comercial."""

    INDICACAO = "indicacao"
    WHITE_LABEL = "white_label"
    FRANQUIA = "franquia"
    MARKETPLACE = "marketplace"


class VeiculoStatus(str, enum.Enum):
    """Status operacional do veículo (máquina de estados da frota)."""

    DISPONIVEL = "disponivel"
    RESERVADO = "reservado"
    LOCADO = "locado"
    MANUTENCAO = "manutencao"
    BLOQUEADO = "bloqueado"
    RESTRITO = "restrito"
    BAIXADO = "baixado"


class VeiculoPropriedade(str, enum.Enum):
    """Forma de propriedade / aquisição do veículo."""

    PROPRIA = "propria"
    CONSORCIO = "consorcio"
    FINANCIADA = "financiada"
    TERCEIRIZADA = "terceirizada"


class CombustivelUnidade(str, enum.Enum):
    """Unidade de medida do combustível/energia."""

    LITRO = "litro"
    KWH = "kwh"
    M3 = "m3"


class AcessorioTipo(str, enum.Enum):
    """Tipo de acessório: fixo no veículo ou avulso locável."""

    FIXO = "fixo"
    AVULSO = "avulso"


class DocumentoVeiculoTipo(str, enum.Enum):
    """Tipos de documento com vigência por veículo."""

    CRLV = "crlv"
    SEGURO = "seguro"
    IPVA = "ipva"
    LICENCIAMENTO = "licenciamento"
    VISTORIA = "vistoria"
    AUTORIZACAO_TRANSPORTE = "autorizacao_transporte"
    OUTRO = "outro"


class DocumentoVeiculoStatus(str, enum.Enum):
    """Situação calculada da vigência documental."""

    REGULAR = "regular"
    A_VENCER = "a_vencer"
    VENCIDO = "vencido"


class TelemetriaConnStatus(str, enum.Enum):
    """Status de conexão do rastreador."""

    ONLINE = "online"
    OFFLINE = "offline"
    SEM_SINAL = "sem_sinal"


class TelemetriaEventoTipo(str, enum.Enum):
    """Tipos de evento de telemetria/condução."""

    EXCESSO_VELOCIDADE = "excesso_velocidade"
    GEOFENCE = "geofence"
    COLISAO = "colisao"
    BLOQUEIO = "bloqueio"
    DESBLOQUEIO = "desbloqueio"
    OUTRO = "outro"


class OrdemServicoTipo(str, enum.Enum):
    """Tipo/origem da ordem de serviço."""

    PREVENTIVA = "preventiva"
    CORRETIVA = "corretiva"
    SINISTRO = "sinistro"
    RECALL = "recall"
    ESTETICA = "estetica"


class OrdemServicoOrigem(str, enum.Enum):
    """Como a OS foi gerada."""

    MANUAL = "manual"
    PLANO_PREVENTIVO = "plano_preventivo"
    AVARIA_CHECKIN = "avaria_checkin"


class OrdemServicoStatus(str, enum.Enum):
    """Máquina de estados da OS."""

    ABERTA = "aberta"
    AGUARDANDO_PECA = "aguardando_peca"
    EM_EXECUCAO = "em_execucao"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class OrdemServicoItemTipo(str, enum.Enum):
    """Linha de OS: mão de obra ou peça."""

    MAO_DE_OBRA = "mao_de_obra"
    PECA = "peca"


class CorretivaCausa(str, enum.Enum):
    """Causa raiz típica de OS corretiva."""

    PECA = "peca"
    USO = "uso"
    ACIDENTE = "acidente"
    DESGASTE = "desgaste"
    OUTRO = "outro"


class CorretivaResponsavel(str, enum.Enum):
    """Quem arca com o custo da corretiva."""

    CLIENTE = "cliente"
    SEGURO = "seguro"
    LOCADORA = "locadora"


class EstoqueMovimentoTipo(str, enum.Enum):
    """Tipos de movimentação de estoque de peças."""

    ENTRADA = "entrada"
    SAIDA = "saida"
    AJUSTE = "ajuste"
    TRANSFERENCIA = "transferencia"


class PneuPosicao(str, enum.Enum):
    """Posição do pneu no veículo."""

    DD = "dd"  # dianteiro direito
    DE = "de"
    TD = "td"
    TE = "te"
    ESTEPE = "estepe"


class PneuStatus(str, enum.Enum):
    """Ciclo de vida do pneu."""

    NOVO = "novo"
    EM_USO = "em_uso"
    RECAPADO = "recapado"
    DESCARTADO = "descartado"


class TarifarioCanal(str, enum.Enum):
    """Canal de venda da tabela de tarifas."""

    BALCAO = "balcao"
    SITE = "site"
    APP = "app"
    PARCEIRO = "parceiro"
    TELEFONE = "telefone"
    TODOS = "todos"


class TemporadaAjusteTipo(str, enum.Enum):
    """Como a temporada ajusta o preço base."""

    PERCENTUAL = "percentual"
    VALOR_FIXO = "valor_fixo"
    TABELA_ALTERNATIVA = "tabela_alternativa"


class TaxaCalculoTipo(str, enum.Enum):
    """Forma de cálculo da taxa/encargo."""

    FIXO = "fixo"
    PERCENTUAL = "percentual"
    POR_DIA = "por_dia"
    POR_OCORRENCIA = "por_ocorrencia"


class TaxaAplicacao(str, enum.Enum):
    """Se a taxa entra automática ou como opcional."""

    AUTOMATICA = "automatica"
    OPCIONAL = "opcional"


class PoliticaRetencaoTipo(str, enum.Enum):
    """Tipo de retenção na política de cancelamento."""

    PERCENTUAL = "percentual"
    DIARIAS = "diarias"
    VALOR_FIXO = "valor_fixo"


class ReservaStatus(str, enum.Enum):
    """Máquina de estados da reserva."""

    PENDENTE = "pendente"
    CONFIRMADA = "confirmada"
    CHECKOUT = "checkout"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"
    NO_SHOW = "no_show"


class ReservaAlocacao(str, enum.Enum):
    """Garantida (veículo) ou por categoria."""

    CATEGORIA = "categoria"
    VEICULO = "veiculo"


class ReservaOrigem(str, enum.Enum):
    """Canal de origem da reserva."""

    BALCAO = "balcao"
    WEBSITE = "website"
    APP = "app"
    PARCEIRO = "parceiro"
    TELEFONE = "telefone"


class ReservaItemTipo(str, enum.Enum):
    """Linha de cobranca na reserva/cotação."""

    PROTECAO = "protecao"
    TAXA = "taxa"
    ACESSORIO = "acessorio"
    DESCONTO = "desconto"


class CotacaoStatus(str, enum.Enum):
    """Situação da cotação sem compromisso."""

    ABERTA = "aberta"
    CONVERTIDA = "convertida"
    EXPIRADA = "expirada"
    CANCELADA = "cancelada"


class ContratoStatus(str, enum.Enum):
    """Máquina de estados do contrato de locação."""

    RASCUNHO = "rascunho"
    AGUARDANDO_CHECKOUT = "aguardando_checkout"
    ATIVO = "ativo"
    AGUARDANDO_CHECKIN = "aguardando_checkin"
    ENCERRADO = "encerrado"
    ENCERRADO_PENDENCIA = "encerrado_pendencia"
    CANCELADO = "cancelado"


class ContratoCondicaoPagamento(str, enum.Enum):
    """Condição comercial de pagamento do contrato."""

    AVISTA = "avista"
    CARTAO_RECORRENTE = "cartao_recorrente"
    FATURADO = "faturado"


class VistoriaTipo(str, enum.Enum):
    """Tipo de vistoria vinculada ao contrato."""

    CHECKOUT = "checkout"
    CHECKIN = "checkin"


class AvariaOrigem(str, enum.Enum):
    """Origem do registro de avaria."""

    CHECKOUT = "checkout"
    CHECKIN = "checkin"
    SINISTRO = "sinistro"
    INSPECAO = "inspecao"


class AvariaSeveridade(str, enum.Enum):
    """Severidade da avaria."""

    LEVE = "leve"
    MEDIA = "media"
    GRAVE = "grave"


class AvariaResponsabilidade(str, enum.Enum):
    """Quem arca com a avaria."""

    CLIENTE = "cliente"
    SEGURO = "seguro"
    DESGASTE = "desgaste"
    LOCADORA = "locadora"


class AvariaStatus(str, enum.Enum):
    """Ciclo de vida da avaria."""

    REGISTRADA = "registrada"
    EM_ANALISE = "em_analise"
    RESPONSABILIDADE_DEFINIDA = "responsabilidade_definida"
    OS_GERADA = "os_gerada"
    COBRANCA_GERADA = "cobranca_gerada"
    ENCERRADA = "encerrada"


class MultaStatus(str, enum.Enum):
    """Ciclo de vida da multa de trânsito."""

    RECEBIDA = "recebida"
    VINCULADA = "vinculada"
    NOTIFICADO = "notificado"
    PAGA = "paga"
    CONTESTADA = "contestada"


class AuditAction(str, enum.Enum):
    """Categorias de eventos registrados na trilha de auditoria."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    ACCESS_DENIED = "access_denied"
    EXPORT = "export"
