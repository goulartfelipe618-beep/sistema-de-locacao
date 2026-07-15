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


class FormaPagamento(str, enum.Enum):
    """Formas de pagamento/recebimento usadas no financeiro (§9)."""

    DINHEIRO = "dinheiro"
    PIX = "pix"
    CARTAO_DEBITO = "cartao_debito"
    CARTAO_CREDITO = "cartao_credito"
    BOLETO = "boleto"
    TRANSFERENCIA = "transferencia"
    FATURADO = "faturado"
    OUTRO = "outro"


class CaixaSessaoStatus(str, enum.Enum):
    """Situação de uma sessão de caixa (§9.1)."""

    ABERTA = "aberta"
    FECHADA = "fechada"


class CaixaLancamentoTipo(str, enum.Enum):
    """Tipo de movimentação de caixa (§9.1)."""

    ENTRADA = "entrada"
    SAIDA = "saida"
    SANGRIA = "sangria"
    SUPRIMENTO = "suprimento"


class ContaReceberOrigem(str, enum.Enum):
    """Origem de um título a receber (§9.2)."""

    CONTRATO = "contrato"
    MULTA = "multa"
    AVARIA = "avaria"
    FATURA = "fatura"
    AVULSO = "avulso"


class ContaPagarOrigem(str, enum.Enum):
    """Origem de um título a pagar (§9.3)."""

    OS = "os"
    FORNECEDOR = "fornecedor"
    COMISSAO = "comissao"
    AVULSO = "avulso"


class TituloStatus(str, enum.Enum):
    """Ciclo de vida de um título financeiro (a receber/a pagar) (§9.2/§9.3)."""

    EM_ABERTO = "em_aberto"
    VENCIDO = "vencido"
    PAGO_PARCIAL = "pago_parcial"
    PAGO = "pago"
    CANCELADO = "cancelado"
    ESTORNADO = "estornado"


class PixChaveTipo(str, enum.Enum):
    """Tipo de chave PIX (§9.4)."""

    CPF = "cpf"
    CNPJ = "cnpj"
    EMAIL = "email"
    TELEFONE = "telefone"
    ALEATORIA = "aleatoria"


class PixCobrancaStatus(str, enum.Enum):
    """Situação de uma cobrança PIX (§9.4)."""

    AGUARDANDO = "aguardando"
    PAGO = "pago"
    EXPIRADO = "expirado"
    CANCELADO = "cancelado"


class CartaoTipo(str, enum.Enum):
    """Modalidade de transação em cartão (§9.5)."""

    DEBITO = "debito"
    CREDITO = "credito"
    PRE_AUTORIZACAO = "pre_autorizacao"


class CartaoTransacaoStatus(str, enum.Enum):
    """Ciclo de vida de uma transação de cartão (§9.5)."""

    AUTORIZADO = "autorizado"
    CAPTURADO = "capturado"
    LIQUIDADO = "liquidado"
    CANCELADO = "cancelado"
    ESTORNADO = "estornado"


class ContaBancariaTipo(str, enum.Enum):
    """Tipo de conta bancária (§9.6)."""

    CORRENTE = "corrente"
    POUPANCA = "poupanca"
    PAGAMENTO = "pagamento"


class BancoIntegracaoTipo(str, enum.Enum):
    """Forma de integração da conta bancária (§9.6)."""

    MANUAL = "manual"
    OFX = "ofx"
    API = "api"


class ExtratoTipo(str, enum.Enum):
    """Natureza da linha de extrato bancário (débito/crédito) (§9.6)."""

    DEBITO = "D"
    CREDITO = "C"


class ConciliacaoStatus(str, enum.Enum):
    """Situação de conciliação de uma linha de extrato (§9.7)."""

    PENDENTE = "pendente"
    CONCILIADO = "conciliado"
    DIVERGENTE = "divergente"
    IGNORADO = "ignorado"


class FaturamentoCiclo(str, enum.Enum):
    """Ciclo de fechamento de faturamento por cliente (§9.8)."""

    MENSAL = "mensal"
    QUINZENAL = "quinzenal"


class FaturaStatus(str, enum.Enum):
    """Ciclo de vida de uma fatura consolidada (§9.8)."""

    RASCUNHO = "rascunho"
    EMITIDA = "emitida"
    PAGA = "paga"
    CANCELADA = "cancelada"


class CrmEstagio(str, enum.Enum):
    """Estágios do funil de vendas (§7.1)."""

    LEAD = "lead"
    QUALIFICACAO = "qualificacao"
    COTACAO_ENVIADA = "cotacao_enviada"
    NEGOCIACAO = "negociacao"
    FECHADO_GANHO = "fechado_ganho"
    PERDIDO = "perdido"


class CrmOrigemLead(str, enum.Enum):
    """Origem/canal de captação do lead (§7.1)."""

    SITE = "site"
    TELEFONE = "telefone"
    INDICACAO = "indicacao"
    PARCEIRO = "parceiro"
    REDES_SOCIAIS = "redes_sociais"
    OUTRO = "outro"


class CrmInteracaoTipo(str, enum.Enum):
    """Tipo de interação registrada na oportunidade (§7.1)."""

    NOTA = "nota"
    LIGACAO = "ligacao"
    EMAIL = "email"


class CrmPropostaStatus(str, enum.Enum):
    """Ciclo de vida de uma proposta comercial (§7.2)."""

    RASCUNHO = "rascunho"
    ENVIADA = "enviada"
    VISUALIZADA = "visualizada"
    ACEITA = "aceita"
    RECUSADA = "recusada"
    EXPIRADA = "expirada"


class CrmCampanhaStatus(str, enum.Enum):
    """Situação de uma campanha de marketing (§7.3)."""

    RASCUNHO = "rascunho"
    ATIVA = "ativa"
    PAUSADA = "pausada"
    ENCERRADA = "encerrada"


class CrmCampanhaCanal(str, enum.Enum):
    """Canal de disparo da campanha (§7.3)."""

    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    SITE = "site"


class CrmCampanhaPublico(str, enum.Enum):
    """Segmentação do público-alvo da campanha (§7.3)."""

    TODOS = "todos"
    CATEGORIA_CLIENTE = "categoria_cliente"
    INATIVOS = "inativos"


class CrmCupomTipo(str, enum.Enum):
    """Tipo de desconto de um cupom (§7.4)."""

    PERCENTUAL = "percentual"
    VALOR_FIXO = "valor_fixo"


class CrmCupomStatus(str, enum.Enum):
    """Situação de um cupom promocional (§7.4)."""

    ATIVO = "ativo"
    EXPIRADO = "expirado"
    ESGOTADO = "esgotado"
    INATIVO = "inativo"


class CrmFidelidadeMovimentoTipo(str, enum.Enum):
    """Natureza de um movimento de pontos de fidelidade (§7.5)."""

    CREDITO = "credito"
    DEBITO = "debito"
    EXPIRACAO = "expiracao"
    AJUSTE = "ajuste"


class CrmFidelidadeOrigem(str, enum.Enum):
    """Origem de um movimento de pontos de fidelidade (§7.5)."""

    CONTRATO = "contrato"
    RESGATE = "resgate"
    EXPIRACAO = "expiracao"
    AJUSTE = "ajuste"


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
