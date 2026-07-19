"""Instruções de formulário — módulo Operacional (Reservas e Locações)."""

from app.web.form_instructions._helpers import instr

INSTRUCTIONS = {
    "reservas.nova": instr(
        "Formulário para criação de nova reserva de veículo, registrando cliente, período, categoria, "
        "filial de retirada/devolução e condições comerciais. "
        "A reserva garante disponibilidade antes da formalização do contrato de locação.",
        (
            "Para que serve",
            [
                "Bloquear disponibilidade de veículo ou categoria para período definido.",
                "Registrar intenção de locação com dados comerciais (tarifa, proteções, acessórios).",
                "Originar posterior conversão em contrato no checkout.",
                "Controlar reservas de balcão, telefone, web e parceiros/OTAs.",
                "Permitir confirmação, alteração ou cancelamento antes da retirada.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cadastro de clientes: locatário e condutores da reserva.",
                "Frota e categorias: verificação de disponibilidade em tempo real.",
                "Tarifário: cálculo automático de diárias, taxas e proteções.",
                "Contratos: conversão da reserva em contrato no checkout.",
                "Financeiro: pré-pagamento, sinal ou garantia vinculada à reserva.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Evita overbooking com bloqueio antecipado de vaga na frota.",
                "Cliente recebe confirmação clara com datas, local e valor.",
                "Operação prepara veículo e documentação antes da retirada.",
                "Comercial rastreia conversão de reserva em contrato efetivo.",
                "Parceiros e vendedores recebem crédito correto pela origem.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Disponibilidade é validada por categoria ou placa conforme configuração.",
                "Reserva expirada (no-show) libera veículo e pode gerar taxa conforme política.",
                "Alteração de datas recalcula tarifa e revalida disponibilidade.",
                "Status: pendente, confirmada, cancelada, convertida (contrato), no-show.",
                "Antecedência mínima e máxima de reserva definidas no tarifário ou parâmetros.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Grade de disponibilidade reduz vagas no período reservado.",
                "E-mail/SMS de confirmação enviado se automação configurada.",
                "Relatórios de pipeline comercial incluem nova reserva.",
                "Cotação vinculada muda status para 'convertida' se aplicável.",
                "Comissão de parceiro/vendedor fica pré-registrada para fechamento.",
            ],
        ),
    ),
    "reservas.cotacao": instr(
        "Simulação comercial de locação sem comprometer disponibilidade, permitindo comparar categorias, "
        "períodos, proteções e descontos antes da confirmação. "
        "Ideal para atendimento consultivo e envio de proposta ao cliente.",
        (
            "Para que serve",
            [
                "Calcular valor estimado da locação sem gerar reserva firme.",
                "Comparar opções (categorias, proteções, acessórios) para o cliente.",
                "Enviar proposta por e-mail ou WhatsApp com validade definida.",
                "Registrar interesse comercial antes da decisão do cliente.",
                "Alimentar funil de oportunidades com valores projetados.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Tarifário: tabelas, taxas, temporadas e políticas aplicadas no cálculo.",
                "Reservas: conversão da cotação aprovada em reserva confirmada.",
                "Comercial: propostas e funil de oportunidades.",
                "Cadastro de clientes: prospect ou cliente existente.",
                "Cupons e campanhas: descontos promocionais na simulação.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Agiliza atendimento com resposta imediata de preço.",
                "Cliente decide com transparência sobre opções e custos.",
                "Vendedor registra histórico de negociação e versões da proposta.",
                "Reduz reservas canceladas por surpresa no valor final.",
                "Gestão comercial mede taxa de conversão cotação → reserva.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Cotação não bloqueia veículo — disponibilidade confirmada só na reserva.",
                "Validade da cotação expira após prazo configurado; preços podem mudar.",
                "Recálculo automático ao alterar datas, categoria ou adicionais.",
                "Desconto manual pode exigir alçada conforme perfil do usuário.",
                "Múltiplas versões da mesma cotação podem ser salvas para comparação.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Funil comercial registra nova oportunidade ou atualiza existente.",
                "Histórico de cotações fica disponível no cadastro do cliente.",
                "Conversão em reserva herda todos os parâmetros da cotação aprovada.",
                "Relatórios de conversão atualizam métricas do período.",
                "Automação pode enviar PDF ou link da proposta ao cliente.",
            ],
        ),
    ),
    "locacoes.contrato": instr(
        "Formalização do contrato de locação vinculado à reserva ou abertura direta no balcão, "
        "consolidando partes, veículo, período, tarifas, garantias e condições legais. "
        "Documento central que governa toda a locação até o check-in.",
        (
            "Para que serve",
            [
                "Formalizar juridicamente a locação entre locadora e cliente.",
                "Consolidar valores, proteções, taxas e forma de pagamento acordados.",
                "Definir veículo alocado (placa), condutores autorizados e filiais.",
                "Estabelecer condições de uso, franquia, KM e política de combustível.",
                "Servir de base para checkout, extensões, multas e faturamento.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas: origem e conversão em contrato.",
                "Checkout/check-in: execução operacional do contrato.",
                "Financeiro: geração de títulos, faturas e garantias.",
                "Frota: status do veículo alterado para locado.",
                "Fiscal: emissão de NF-e/NFS-e quando aplicável.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Proteção jurídica com termos claros e assinatura digital ou física.",
                "Valores fechados evitam disputas na devolução.",
                "Rastreabilidade completa de alterações e aditivos.",
                "Integração financeira automática reduz lançamentos manuais.",
                "Histórico robusto para clientes recorrentes e análise de risco.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Contrato só avança para checkout após validações (CNH, pagamento, documentos).",
                "Alteração de período gera aditivo com recálculo tarifário.",
                "Substituição de veículo registra placa original e substituta.",
                "Status: elaboração, ativo (checkout feito), encerrado (check-in), cancelado.",
                "Franquia de KM e valor de KM excedente vêm do tarifário/proteção contratada.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Veículo alocado muda status para reservado ou locado conforme fase.",
                "Títulos financeiros são gerados ou atualizados.",
                "Reserva origem marcada como convertida.",
                "Comissões de vendedor/parceiro ficam vinculadas ao contrato.",
                "Impressão/PDF do contrato reflete cláusulas e valores atuais.",
            ],
        ),
    ),
    "locacoes.checkout": instr(
        "Processo de retirada do veículo pelo cliente, registrando condição do automóvel, "
        "quilometragem inicial, nível de combustível, documentos conferidos e assinaturas. "
        "Marca o início efetivo da locação e responsabilidade do locatário.",
        (
            "Para que serve",
            [
                "Registrar formalmente a entrega do veículo ao cliente.",
                "Documentar estado do veículo com fotos, checklist e observações.",
                "Capturar KM e tanque inicial para comparar no check-in.",
                "Validar CNH, cartão de crédito/garantia e condutores autorizados.",
                "Ativar cobrança de diárias e iniciar contagem do período contratual.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Contrato: transição de elaboração para locação ativa.",
                "Frota: veículo passa a status 'locado'.",
                "Financeiro: captura de pré-autorização ou débito inicial.",
                "Telemetria: início de monitoramento se configurado.",
                "Manutenção: registro de saída para controle de uso.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Prova documental em disputas sobre avarias pré-existentes.",
                "Base confiável para cobrança de KM excedente e combustível.",
                "Operação padronizada reduz erros na retirada.",
                "Cliente ciente das condições e responsabilidades desde o início.",
                "Integração com app mobile acelera checklist com fotos.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Checkout incompleto mantém contrato em status intermediário.",
                "Avarias pré-existentes devem ser registradas para não cobrar no check-in.",
                "KM inicial deve ser coerente com último check-in ou telemetria.",
                "Assinatura digital ou termo impresso confirma aceite das condições.",
                "Veículo diferente do contrato exige registro de substituição formal.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Contrato muda para status ativo com data/hora de início efetiva.",
                "Veículo bloqueado para outras locações no período.",
                "Cobrança recorrente ou título principal pode ser disparado.",
                "Alertas de devolução programados para data prevista de check-in.",
                "Histórico do veículo registra evento de saída para locação.",
            ],
        ),
    ),
    "locacoes.checkin": instr(
        "Processo de devolução do veículo, comparando condição, KM e combustível com o checkout, "
        "calculando valores adicionais e encerrando formalmente o contrato. "
        "Momento crítico para cobranças extras e liberação do veículo para nova locação.",
        (
            "Para que serve",
            [
                "Registrar devolução do veículo na filial ou local acordado.",
                "Comparar KM, tanque e avarias com registro do checkout.",
                "Calcular cobranças extras: KM excedente, combustível, avarias, atraso.",
                "Encerrar contrato e liberar veículo para manutenção ou nova locação.",
                "Gerar resumo financeiro final para o cliente.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Contrato: encerramento e status final.",
                "Financeiro: títulos de saldo, multas e avarias.",
                "Frota: veículo disponível ou encaminhado à manutenção.",
                "Manutenção: OS automática se avaria exigir reparo.",
                "Multas: registro de infrações identificadas na devolução.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Cobrança justa e fundamentada em evidências do checkout.",
                "Encerramento ágil libera veículo para maximizar ocupação.",
                "Cliente recebe demonstrativo claro de valores finais.",
                "Reduz pendências financeiras com fechamento completo.",
                "Histórico de condição do veículo alimenta precificação e manutenção.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Atraso na devolução gera diárias extras conforme tarifário.",
                "Avaria nova comparada ao checklist de checkout — só cobra diferença.",
                "KM menor que checkout exige justificativa (troca odômetro, erro).",
                "Devolução antecipada pode aplicar política de reembolso parcial ou não.",
                "Check-in parcial possível com complemento posterior (ex.: lavagem).",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Contrato encerrado com data/hora final e valores consolidados.",
                "Veículo muda para disponível, em limpeza ou manutenção.",
                "Títulos a receber gerados para saldo devedor ou estorno de crédito.",
                "Garantia/pré-autorização liberada ou capturada conforme saldo.",
                "Relatórios de receita e ocupação atualizados para o período.",
            ],
        ),
    ),
    "locacoes.multa": instr(
        "Registro de multas de trânsito ocorridas durante o período de locação, "
        "vinculando infração ao contrato, veículo e responsável (cliente ou locadora). "
        "Controla repasse, cobrança administrativa e contestação.",
        (
            "Para que serve",
            [
                "Registrar auto de infração recebido durante ou após a locação.",
                "Identificar contrato e cliente responsável no período da multa.",
                "Calcular taxa administrativa de repasse conforme contrato.",
                "Controlar status: pendente, cobrada, paga, contestada, transferida.",
                "Documentar comprovantes de pagamento e indicação de condutor.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Contratos: período de locação para identificar responsável.",
                "Financeiro a receber: cobrança da multa + taxa administrativa.",
                "Cadastro de clientes: notificação e débito no CPF/CNPJ.",
                "Frota: placa do veículo autuado.",
                "Relatórios de multas por período, veículo e taxa de repasse.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Repasse rápido evita pagamento em dobro pela locadora.",
                "Cliente notificado com transparência sobre infração e valores.",
                "Controle de inadimplência de multas pendentes.",
                "Auditoria completa para contestações e órgãos de trânsito.",
                "Indicadores de risco por cliente ou categoria de veículo.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Responsabilidade segue cláusula contratual — geralmente locatário.",
                "Taxa administrativa percentual ou fixa definida no contrato/tarifário.",
                "Multa recebida após encerramento ainda vincula ao contrato original.",
                "Indicação de condutor tem prazo legal — alertas configuráveis.",
                "Multa paga pela locadora gera débito automático ao cliente.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Título a receber criado para cliente com vencimento configurado.",
                "Histórico do contrato e cliente registra ocorrência.",
                "Dashboard de pendências inclui multa em aberto.",
                "Automação envia e-mail/notificação ao cliente responsável.",
                "Relatórios financeiros de receita acessória incluem taxa administrativa.",
            ],
        ),
    ),
    "locacoes.avaria": instr(
        "Registro de avarias, danos ou peças faltantes identificados no check-in ou durante a locação, "
        "com estimativa de reparo, fotos e fluxo de cobrança ao cliente ou seguradora.",
        (
            "Para que serve",
            [
                "Documentar danos ao veículo fora do desgaste normal.",
                "Estimar custo de reparo com base em tabela ou orçamento.",
                "Diferenciar avaria coberta por proteção contratada vs responsabilidade total.",
                "Gerar cobrança ao cliente ou acionar seguro conforme cobertura.",
                "Encaminhar veículo à manutenção com OS vinculada.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Check-in: comparação visual e checklist de avarias.",
                "Contrato e proteções: franquia e cobertura aplicável.",
                "Financeiro a receber: cobrança de franquia ou valor integral.",
                "Manutenção: ordem de serviço para reparo do veículo.",
                "Cadastro de peças: custo de reposição para estimativa.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Evidência fotográfica reduz disputas com clientes.",
                "Cobrança alinhada à proteção contratada (básica, completa, etc.).",
                "Rastreabilidade de custo real de reparo vs valor cobrado.",
                "Veículo encaminhado rapidamente à oficina.",
                "Histórico de avarias por cliente para análise de risco.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Avaria pré-existente no checkout não gera cobrança no check-in.",
                "Franquia da proteção limita valor máximo cobrado do cliente.",
                "Gravidade (leve, moderada, grave) pode exigir aprovação gerencial.",
                "Peça faltante (estepe, triângulo) cobrada conforme tabela de reposição.",
                "Sinistro grave pode acionar fluxo securitário separado.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Título a receber gerado para franquia ou valor de reparo.",
                "OS de manutenção criada com descrição e fotos da avaria.",
                "Veículo pode ir para status manutenção até reparo concluído.",
                "Contrato registra ocorrência no histórico de locação.",
                "Relatórios de perdas e avarias atualizam indicadores do período.",
            ],
        ),
    ),
}
