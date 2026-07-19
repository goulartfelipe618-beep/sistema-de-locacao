"""Instruções de formulário — módulo Intermediação."""

from app.web.form_instructions._helpers import instr

INSTRUCTIONS = {
    "intermediacao.config": instr(
        "Parametrização geral do módulo de intermediação de frota, definindo regras para operação "
        "com veículos de outras locadoras (fornecedores). "
        "Permite expandir capacidade de atendimento sem investir em frota própria adicional.",
        (
            "Para que serve",
            [
                "Ativar e configurar operação de frota terceirizada de parceiros locadores.",
                "Definir margem padrão, repasse e forma de precificação ao cliente final.",
                "Estabelecer regras de alocação: frota própria primeiro ou mix.",
                "Configurar alertas de indisponibilidade e prazo de confirmação do fornecedor.",
                "Padronizar fluxo operacional de reserva → confirmação → checkout.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Fornecedores: locadoras parceiras cadastradas para intermediação.",
                "Contratos de fornecedor: condições comerciais por parceiro.",
                "Reservas: alocação de veículo terceirizado quando frota própria esgotada.",
                "Financeiro a pagar: repasse ao fornecedor após locação.",
                "Relatórios de intermediação: volume, margem e performance.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Atender demanda em picos sem comprar veículos adicionais.",
                "Operação unificada para cliente — experiência transparente.",
                "Controle de margem e rentabilidade por locação intermediada.",
                "Redução de overbooking com pool ampliado de veículos.",
                "Gestão centralizada de repasses e conciliação.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Veículo terceirizado só aloca se contrato com fornecedor estiver vigente.",
                "Preço ao cliente = custo fornecedor + margem configurada.",
                "Confirmação do fornecedor pode ser manual ou via integração.",
                "Responsabilidade por avarias segue acordo com fornecedor.",
                "Indisponibilidade do fornecedor libera realocação ou cancelamento assistido.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Motor de disponibilidade inclui ou exclui frota terceirizada.",
                "Cotações passam a considerar opções intermediadas.",
                "Fluxo de aprovação de reserva com fornecedor externo.",
                "Relatórios financeiros separam receita própria vs intermediada.",
                "Alertas operacionais usam prazos configurados.",
            ],
        ),
    ),
    "intermediacao.contrato_fornecedor": instr(
        "Contrato comercial com locadora fornecedora de veículos, definindo categorias disponíveis, "
        "preços de repasse, prazos de pagamento, SLAs e condições de substituição. "
        "Base legal e financeira para cada operação intermediada.",
        (
            "Para que serve",
            [
                "Formalizar parceria com outra locadora para uso de sua frota.",
                "Definir tabela de custo (repasse) por categoria e período.",
                "Estabelecer prazo de pagamento e forma de faturamento do fornecedor.",
                "Registrar SLAs: tempo de confirmação, substituição e cancelamento.",
                "Documentar responsabilidades por avarias, multas e seguro.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cadastro de fornecedores: locadora parceira vinculada.",
                "Frota terceirizada: veículos disponíveis sob este contrato.",
                "Reservas e contratos: locações intermediadas.",
                "Financeiro a pagar: títulos de repasse ao fornecedor.",
                "Indisponibilidades: bloqueios comunicados pelo parceiro.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Negociação documentada evita conflitos de repasse.",
                "Precificação automática com margem sobre custo contratual.",
                "Auditoria de locações intermediadas por contrato.",
                "Renovação e vigência controladas com alertas.",
                "Comparativo de fornecedores por custo e qualidade.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Contrato fora de vigência bloqueia novas alocações do fornecedor.",
                "Categorias mapeadas entre locadora e fornecedor (equivalência).",
                "Repasse calculado sobre diárias líquidas conforme cláusula.",
                "Cancelamento tardio pode gerar penalidade repassada ao fornecedor.",
                "Anexos e documentos do acordo armazenados para consulta.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Veículos do fornecedor passam a usar tabela de repasse vigente.",
                "Novas reservas intermediadas aplicam condições atualizadas.",
                "Títulos a pagar futuros seguem prazo de pagamento configurado.",
                "Relatórios de margem recalculam com novo custo.",
                "Integrações API usam identificador do contrato com parceiro.",
            ],
        ),
    ),
    "intermediacao.indisponibilidade": instr(
        "Registro de períodos em que veículos ou categorias de fornecedores parceiros "
        "não estão disponíveis para intermediação. "
        "Evita reservas em veículos que o parceiro não poderá entregar.",
        (
            "Para que serve",
            [
                "Bloquear temporariamente veículo terceirizado informado pelo fornecedor.",
                "Registrar manutenção, locação direta ou indisponibilidade do parceiro.",
                "Evitar confirmações que o fornecedor não honrará.",
                "Planejar realocação para frota própria ou outro fornecedor.",
                "Manter histórico de confiabilidade do parceiro.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Frota terceirizada: status do veículo ou categoria do fornecedor.",
                "Disponibilidade: cálculo de vagas em reservas.",
                "Contratos de fornecedor: veículos cobertos pelo bloqueio.",
                "Reservas: impedimento de alocação no período.",
                "Relatórios de SLA e performance de fornecedores.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Reduz cancelamentos por indisponibilidade do parceiro.",
                "Operação proativa ao comunicar bloqueios antecipadamente.",
                "Cliente recebe alternativa antes da confirmação.",
                "Métricas de confiabilidade por fornecedor.",
                "Sincronização com calendário do parceiro quando integrado.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Bloqueio parcial (categoria) vs total (placa específica).",
                "Período com data/hora início e fim obrigatórios.",
                "Reservas existentes no período podem exigir realocação manual.",
                "Motivo registrado para análise (manutenção, uso próprio, etc.).",
                "Integração pode importar indisponibilidades automaticamente.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Mapa de disponibilidade exclui veículo/categoria no intervalo.",
                "Reservas em elaboração alertam conflito com indisponibilidade.",
                "Sugestões de alocação priorizam frota própria ou outro fornecedor.",
                "Relatórios de fornecedor incluem tempo indisponível.",
                "Automação notifica equipe comercial sobre restrição relevante.",
            ],
        ),
    ),
}
