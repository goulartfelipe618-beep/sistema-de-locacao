"""Instruções de formulário — módulo Tarifário."""

from app.web.form_instructions._helpers import instr

INSTRUCTIONS = {
    "tarifario.tabela": instr(
        "Configuração de tabelas de preços por categoria de veículo, definindo valores de diária, "
        "km livre, horas extras e períodos mínimos. "
        "É a base do cálculo comercial em reservas, cotações e contratos.",
        (
            "Para que serve",
            [
                "Definir preço base da diária por categoria e grupo de veículo.",
                "Estabelecer período mínimo de locação (1 dia, 3 dias, mensal).",
                "Configurar KM livre diário e valor de KM excedente.",
                "Criar variações por canal (balcão, corporativo, OTA, parceiro).",
                "Vincular vigência e prioridade entre múltiplas tabelas.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e cotações: cálculo automático do valor da locação.",
                "Contratos: tarifa aplicada e congelada ou recalculada conforme regra.",
                "Temporadas: ajustes sobre a tabela base em alta/baixa demanda.",
                "Parceiros e campanhas: tabelas exclusivas por canal.",
                "Relatórios de receita por tabela e margem comercial.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Precificação consistente em todos os pontos de venda.",
                "Flexibilidade comercial sem alterar código do sistema.",
                "Simulações rápidas com valores atualizados.",
                "Controle de margem por segmento e categoria.",
                "Auditoria de alterações tarifárias com histórico de vigência.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Vigência define qual tabela prevalece em caso de sobreposição.",
                "Tabela inativa não aparece em novas cotações, mas preserva contratos antigos.",
                "Diária fracionada (hora extra) segue regra configurada após 24h.",
                "Desconto progressivo por quantidade de diárias pode ser parametrizado.",
                "Moeda e arredondamento seguem parâmetros gerais da empresa.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Novas cotações e reservas usam valores da tabela vigente.",
                "Contratos em elaboração recalculam se tabela for alterada antes do checkout.",
                "Integrações OTAs sincronizam preços conforme tabela publicada.",
                "Relatórios comparativos refletem nova estrutura de preços.",
                "Campanhas vinculadas herdam base tarifária atualizada.",
            ],
        ),
    ),
    "tarifario.taxa": instr(
        "Cadastro de taxas adicionais cobradas na locação, como taxa de aeroporto, taxa de retorno, "
        "taxa de motorista adicional, taxa administrativa e serviços extras. "
        "Complementa a diária base com receitas acessórias parametrizadas.",
        (
            "Para que serve",
            [
                "Definir cobranças fixas ou percentuais além da diária.",
                "Automatizar inclusão de taxas por local, categoria ou canal.",
                "Separar receita de serviços da receita de locação pura.",
                "Atender exigências de aeroportos, shoppings ou convênios.",
                "Controlar quais taxas são obrigatórias vs opcionais.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e contratos: composição do valor total da locação.",
                "Checkout/check-in: taxas de combustível, limpeza ou atraso.",
                "Financeiro: itens discriminados na fatura.",
                "Fiscal: natureza de receita para emissão de NF.",
                "Relatórios de receita acessória por tipo de taxa.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Transparência na fatura com itens claramente identificados.",
                "Automação evita esquecimento de taxas obrigatórias.",
                "Análise de contribuição de cada taxa na receita total.",
                "Conformidade com contratos de locação em aeroportos e hubs.",
                "Facilidade para criar novas taxas sazonais sem desenvolvimento.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Taxa pode ser valor fixo, por diária ou percentual sobre subtotal.",
                "Incidência automática por filial de retirada/devolução configurável.",
                "Taxa inclusa na diária vs cobrada à parte afeta exibição comercial.",
                "Isenção por categoria, parceiro ou campanha pode ser parametrizada.",
                "Taxa inativa preserva histórico em contratos fechados.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Cotações futuras incluem ou excluem taxa conforme configuração.",
                "Contratos em aberto podem recalcular se taxa for alterada antes do checkout.",
                "Faturas e NF discriminam descrição atualizada da taxa.",
                "Relatórios de receita por natureza atualizam classificação.",
                "Integrações externas recebem código e valor da taxa.",
            ],
        ),
    ),
    "tarifario.protecao": instr(
        "Configuração de planos de proteção e cobertura (CDW, LDW, proteção básica, completa, "
        "terceiros) com franquias, exclusões e valores diários. "
        "Reduz exposição financeira do cliente e da locadora em sinistros.",
        (
            "Para que serve",
            [
                "Oferecer níveis de cobertura contra avarias, roubo e terceiros.",
                "Definir franquia (valor máximo de responsabilidade do cliente).",
                "Precificar proteção por diária e categoria de veículo.",
                "Estabelecer exclusões (pneus, vidros, interior) por plano.",
                "Documentar condições para cobrança de franquia em avarias.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e contratos: seleção e cobrança da proteção.",
                "Check-in e avarias: cálculo de franquia aplicável.",
                "Financeiro: receita de proteção discriminada.",
                "Tarifário: combinação com tabela base na cotação.",
                "Relatórios de adesão e receita por tipo de proteção.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Cliente escolhe nível de tranquilidade vs custo.",
                "Locadora padroniza cobrança de franquia em avarias.",
                "Receita adicional significativa com margem elevada.",
                "Reduz disputas com termos claros por plano.",
                "Integração com seguradoras quando proteção é repassada.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Proteção obrigatória vs opcional conforme política comercial.",
                "Franquia zero (super proteção) tem preço premium.",
                "Condutor adicional ou condutor jovem pode exigir upgrade de proteção.",
                "Exclusões devem constar no contrato impresso.",
                "Sinistro total segue regra de franquia ou isenção conforme plano.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Cotações exibem opções e preços de proteção atualizados.",
                "Contratos novos aplicam franquia vigente.",
                "Check-in calcula cobrança de avaria respeitando plano contratado.",
                "Relatórios de adesão medem taxa de venda por proteção.",
                "Termos contratuais refletem exclusões e condições alteradas.",
            ],
        ),
    ),
    "tarifario.temporada": instr(
        "Definição de temporadas comerciais (alta, baixa, feriados, eventos) que ajustam "
        "automaticamente os preços base ou aplicam multiplicadores sobre a tabela tarifária. "
        "Permite maximizar receita em picos e estimular demanda em períodos ociosos.",
        (
            "Para que serve",
            [
                "Aplicar acréscimo ou desconto sazonal sobre diárias.",
                "Configurar réveillon, carnaval, férias escolares e eventos locais.",
                "Definir antecedência mínima de reserva em alta temporada.",
                "Bloquear ou limitar descontos manuais em períodos críticos.",
                "Planejar receita com previsibilidade por calendário comercial.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Tarifário: multiplicador ou tabela alternativa por temporada.",
                "Reservas: cálculo automático conforme datas da locação.",
                "Disponibilidade: mínimo de diárias em alta demanda.",
                "Campanhas: restrição de cupons em temporadas específicas.",
                "Relatórios de receita e ocupação por período sazonal.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Otimização de receita em picos de demanda.",
                "Precificação dinâmica sem intervenção manual diária.",
                "Comunicação clara ao cliente sobre períodos especiais.",
                "Planejamento de frota e staffing conforme calendário.",
                "Comparativo ano a ano de performance por temporada.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Sobreposição de temporadas segue prioridade configurada.",
                "Temporada aplicada por data de retirada ou por noites efetivas.",
                "Mínimo de diárias em alta temporada impede locações curtas.",
                "Antecedência de reserva pode exigir pagamento antecipado.",
                "Temporada encerrada não afeta contratos já fechados.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Cotações em período afetado recalculam automaticamente.",
                "Grade comercial exibe indicador de alta temporada.",
                "OTAs e integrações recebem calendário de preços dinâmicos.",
                "Relatórios de pricing refletem nova configuração sazonal.",
                "Alertas comerciais notificam início de temporada próxima.",
            ],
        ),
    ),
    "tarifario.politica": instr(
        "Cadastro de políticas comerciais de cancelamento, no-show, alteração de reserva, "
        "reembolso e garantia. "
        "Define regras financeiras quando o cliente muda ou desiste da locação.",
        (
            "Para que serve",
            [
                "Estabelecer prazos e penalidades para cancelamento de reserva.",
                "Definir cobrança de no-show quando cliente não retira veículo.",
                "Regras de reembolso para devolução antecipada.",
                "Política de garantia com cartão de crédito ou depósito.",
                "Condições de alteração de datas sem perda total do valor.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas: aplicação automática ao cancelar ou alterar.",
                "Financeiro: estorno parcial, retenção ou cobrança de penalidade.",
                "Contratos: cláusulas refletidas no termo impresso.",
                "Campanhas: política específica para tarifas promocionais.",
                "Atendimento: base para decisões de exceção comercial.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Previsibilidade financeira em cancelamentos e no-shows.",
                "Transparência reduz reclamações e chargebacks.",
                "Operação aplica regras uniformes em todas as filiais.",
                "Flexibilidade com políticas diferenciadas por canal.",
                "Proteção de receita em tarifas não reembolsáveis.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Penalidade pode ser percentual, diárias ou valor fixo.",
                "Prazo de cancelamento gratuito contado em horas/dias antes da retirada.",
                "Tarifa promocional pode ser 100% não reembolsável.",
                "No-show libera veículo e retém sinal conforme política.",
                "Exceções gerenciais registram override com motivo auditável.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Cancelamentos futuros calculam penalidade com regra vigente.",
                "Termos de reserva online exibem política atualizada.",
                "Estornos automáticos seguem percentual configurado.",
                "Relatórios de cancelamento e no-show usam nova classificação.",
                "Integrações OTAs sincronizam política de cancelamento.",
            ],
        ),
    ),
}
