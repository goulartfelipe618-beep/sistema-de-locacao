"""Instruções de formulário — módulo Financeiro."""

from app.web.form_instructions._helpers import instr

INSTRUCTIONS = {
    "financeiro.receber": instr(
        "Lançamento e gestão de contas a receber originadas de locações, taxas, multas, avarias "
        "e demais receitas da operação. "
        "Centraliza cobrança, baixa, conciliação e inadimplência de clientes.",
        (
            "Para que serve",
            [
                "Registrar títulos a receber de clientes (PF/PJ) e parceiros devedores.",
                "Controlar vencimentos, parcelas e formas de pagamento.",
                "Baixar recebimentos via boleto, PIX, cartão ou transferência.",
                "Gerenciar inadimplência com juros, multa e negativação.",
                "Conciliar recebimentos com extrato bancário.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Contratos e check-in: geração automática de faturas.",
                "Multas e avarias: cobrança de valores adicionais.",
                "Fiscal: NF-e/NFS-e vinculada ao título.",
                "Caixa e bancos: destino do recebimento.",
                "Relatórios de fluxo de caixa e aging de recebíveis.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Visão clara do que clientes devem e quando.",
                "Redução de perdas por esquecimento de cobrança.",
                "Conciliação bancária ágil com identificação de pagamentos.",
                "Histórico financeiro completo por cliente.",
                "Base para decisão de crédito em novas locações.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Título pode ser gerado automaticamente ou manualmente.",
                "Baixa parcial permitida com saldo remanescente.",
                "Estorno exige motivo e permissão conforme perfil.",
                "Cliente inadimplente pode bloquear novas locações.",
                "Juros e multa calculados conforme parâmetros e dias de atraso.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Saldo devedor do cliente atualizado imediatamente.",
                "Contrato registra quitação ou pendência financeira.",
                "Fluxo de caixa projeta entrada na data de vencimento.",
                "Automações de cobrança disparam conforme status.",
                "Relatórios DRE e aging refletem movimentação.",
            ],
        ),
    ),
    "financeiro.pagar": instr(
        "Gestão de contas a pagar para fornecedores, comissões de parceiros, repasses de intermediação, "
        "despesas operacionais e obrigações fiscais. "
        "Controla compromissos financeiros e fluxo de saídas.",
        (
            "Para que serve",
            [
                "Registrar títulos a pagar a fornecedores e credores.",
                "Programar pagamentos conforme vencimento e fluxo de caixa.",
                "Vincular pagamento a NF de entrada, OS ou contrato.",
                "Controlar aprovação de pagamentos conforme alçada.",
                "Baixar pagamentos e conciliar com extrato bancário.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Fornecedores: dados bancários e condição de pagamento.",
                "Manutenção: OS concluída gera título a pagar.",
                "Intermediação: repasse à locadora fornecedora.",
                "Comercial: comissões de parceiros e vendedores.",
                "Fiscal: escrituração de despesas com crédito tributário.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Evita pagamentos em duplicidade ou fora do prazo.",
                "Planejamento de caixa com visão de compromissos futuros.",
                "Rastreabilidade despesa → documento → pagamento.",
                "Controle de aprovação reduz fraudes e erros.",
                "Análise de custos por categoria de despesa.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Pagamento pode exigir aprovação em dois níveis acima de valor limite.",
                "Retenções de impostos calculadas na NF de serviço.",
                "Baixa vinculada a conta bancária ou caixa específico.",
                "Título agrupado (lote) para pagamento em massa.",
                "Fornecedor bloqueado impede novos lançamentos.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Fluxo de caixa projeta saída na data programada.",
                "Fornecedor atualiza saldo em aberto.",
                "Contrato de intermediação registra repasse efetuado.",
                "Relatórios de despesas por centro de custo atualizados.",
                "Conciliação bancária identifica pagamento realizado.",
            ],
        ),
    ),
    "financeiro.banco": instr(
        "Cadastro de contas bancárias da empresa para recebimentos, pagamentos e conciliação. "
        "Inclui dados de agência, conta, PIX e integração com extrato.",
        (
            "Para que serve",
            [
                "Registrar contas correntes e poupança da locadora.",
                "Definir conta padrão para recebimentos e pagamentos.",
                "Configurar chave PIX e dados para boletos.",
                "Integrar com banco para importação de extrato (OFX/CNAB).",
                "Controlar saldo por conta e por filial.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Contas a receber/pagar: baixa vinculada à conta.",
                "Caixa: transferências entre caixa e banco.",
                "Conciliação bancária: match automático de movimentos.",
                "Filial: conta operacional por unidade.",
                "Relatórios de posição financeira e fluxo de caixa.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Conciliação automática reduz trabalho manual.",
                "Saldo atualizado por conta em tempo real.",
                "Boletos e PIX gerados com dados corretos.",
                "Separação de contas por filial facilita auditoria.",
                "Integração bancária segura e rastreável.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Conta inativa não recebe novos lançamentos.",
                "Uma conta pode ser marcada como padrão por filial.",
                "Integração exige credenciais e certificado quando aplicável.",
                "Moeda e banco devem ser compatíveis com forma de pagamento.",
                "Alteração de dados sensíveis exige permissão elevada.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Novos recebimentos usam conta padrão configurada.",
                "Importação de extrato associa movimentos à conta.",
                "Relatórios de saldo recalculam por conta.",
                "Boletos emitidos usam convênio e conta atualizados.",
                "Transferências entre contas registradas corretamente.",
            ],
        ),
    ),
    "financeiro.cartao": instr(
        "Configuração de máquinas de cartão, adquirentes e taxas de antecipação para recebimento "
        "via crédito e débito. "
        "Integra captura no checkout com conciliação de recebíveis de cartão.",
        (
            "Para que serve",
            [
                "Cadastrar adquirentes (Cielo, Rede, Stone) e taxas por bandeira.",
                "Registrar terminais (POS) por filial ou ponto de atendimento.",
                "Configurar prazo de recebimento (D+1, D+30) e taxa MDI.",
                "Vincular captura de pré-autorização/garantia no contrato.",
                "Conciliar recebíveis de cartão com extrato da adquirente.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Checkout e contratos: pagamento e pré-autorização.",
                "Contas a receber: título originado de venda cartão.",
                "Caixa: fechamento com totalizadores por bandeira.",
                "Conciliação: match de vendas vs repasse adquirente.",
                "Relatórios de taxas e custo financeiro de cartão.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Taxa de cartão considerada no cálculo de margem.",
                "Pré-autorização de garantia automatizada no checkout.",
                "Conciliação de recebíveis sem planilhas externas.",
                "Controle de chargebacks vinculados ao contrato.",
                "Visibilidade de custo por filial e terminal.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Taxa percentual varia por bandeira, tipo (crédito/débito) e parcelas.",
                "Pré-autorização expira em prazo definido pela adquirente.",
                "Captura parcial ou total conforme saldo do check-in.",
                "Estorno no cartão exige vínculo com título original.",
                "Terminal inativo não aparece no checkout da filial.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Checkout oferece bandeiras e parcelamento configurados.",
                "Projeção de recebíveis usa prazo D+N atualizado.",
                "Relatórios de taxa efetiva de cartão recalculam.",
                "Integração TEF/API usa credenciais da configuração.",
                "Conciliação futura associa vendas ao terminal correto.",
            ],
        ),
    ),
    "financeiro.caixa_abertura": instr(
        "Abertura de caixa físico ou lógico por operador/filial, registrando fundo de troco inicial "
        "e iniciando turno de recebimentos em dinheiro. "
        "Base para controle de sangria, suprimento e fechamento diário.",
        (
            "Para que serve",
            [
                "Iniciar turno de caixa com valor de abertura (fundo de troco).",
                "Identificar operador responsável pelo caixa no período.",
                "Controlar recebimentos em espécie vinculados ao caixa aberto.",
                "Permitir sangria e suprimento durante o turno.",
                "Preparar fechamento com conferência de saldo.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Checkout e recebimentos: pagamento em dinheiro.",
                "Contas a receber: baixa em espécie no caixa.",
                "Filial: caixa vinculado à unidade operacional.",
                "Usuário: operador logado responsável.",
                "Relatórios de fechamento de caixa e diferenças.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Rastreabilidade de todo dinheiro recebido por operador.",
                "Reduz diferenças de caixa com controle por turno.",
                "Auditoria de movimentações (sangria/suprimento).",
                "Fechamento estruturado com conferência de valores.",
                "Separação de responsabilidade entre operadores.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Apenas um caixa aberto por operador/filial conforme regra.",
                "Recebimento em dinheiro exige caixa aberto.",
                "Sangria transfere excedente para cofre/banco.",
                "Fechamento com diferença exige justificativa.",
                "Caixa não fechado impede abertura de novo turno pelo mesmo operador.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Operador pode registrar recebimentos em espécie.",
                "Dashboard de caixa exibe saldo em tempo real.",
                "Movimentações ficam vinculadas ao turno aberto.",
                "Relatório de fechamento aguarda encerramento do turno.",
                "Alertas de caixa aberto há muito tempo podem ser disparados.",
            ],
        ),
    ),
}
