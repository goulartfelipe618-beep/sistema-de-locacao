"""Instruções de formulário — módulo Comercial."""

from app.web.form_instructions._helpers import instr

INSTRUCTIONS = {
    "comercial.cupom": instr(
        "Cadastro de cupons de desconto promocionais com código, percentual ou valor fixo, "
        "validade e regras de uso. "
        "Aplicados em cotações, reservas e checkout para campanhas de marketing.",
        (
            "Para que serve",
            [
                "Criar códigos promocionais para campanhas de marketing.",
                "Definir desconto percentual ou valor fixo sobre locação.",
                "Limitar uso por quantidade total, por cliente ou por período.",
                "Restringir a categorias, filiais ou canais específicos.",
                "Medir efetividade de campanhas por cupons resgatados.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e cotações: aplicação do código na simulação.",
                "Campanhas: cupom vinculado a ação promocional.",
                "Contratos: desconto registrado no valor final.",
                "Relatórios comerciais: cupons utilizados e receita impactada.",
                "Integrações web/OTA: validação de código online.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Campanhas mensuráveis com rastreio de conversão.",
                "Controle de margem com teto de desconto configurado.",
                "Evita uso indevido com limites e validade.",
                "Marketing cria promoções sem depender de TI.",
                "Cliente finaliza compra com incentivo claro.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Cupom expirado ou esgotado é rejeitado na aplicação.",
                "Desconto pode incidir sobre diárias, total ou itens específicos.",
                "Cumulativo ou exclusivo com outras promoções conforme regra.",
                "Uso único por CPF/CNPJ configurável.",
                "Temporada alta pode bloquear cupons conforme política.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Cotações e reservas validam código com regras vigentes.",
                "Contador de utilizações incrementado a cada uso.",
                "Relatórios de campanha incluem cupom ativo/inativo.",
                "Integrações e-commerce sincronizam códigos publicados.",
                "Contratos fechados registram desconto aplicado para auditoria.",
            ],
        ),
    ),
    "comercial.campanha": instr(
        "Configuração de campanhas comerciais sazonais ou temáticas, agrupando cupons, "
        "tabelas tarifárias especiais, comunicações e metas. "
        "Orquestra ações de marketing e vendas em período definido.",
        (
            "Para que serve",
            [
                "Agrupar ações promocionais em campanha com início e fim.",
                "Vincular cupons, descontos e tabelas exclusivas.",
                "Definir meta de reservas ou receita da campanha.",
                "Segmentar público (corporativo, leisure, parceiros).",
                "Medir ROI da campanha vs investimento em mídia.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cupons: códigos pertencentes à campanha.",
                "Tarifário: tabela promocional exclusiva.",
                "Reservas: origem/campanha para atribuição.",
                "Funil comercial: oportunidades da campanha.",
                "Relatórios de performance e conversão.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Visão consolidada de resultados por campanha.",
                "Coordenação entre marketing, comercial e operação.",
                "Evita conflito de promoções sobrepostas.",
                "Decisão baseada em dados de conversão real.",
                "Replicabilidade de campanhas de sucesso.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Campanha fora da vigência desativa cupons e tarifas vinculadas.",
                "Prioridade entre campanhas sobrepostas configurável.",
                "Orçamento máximo de desconto pode limitar resgates.",
                "Canal de divulgação registrado para análise de eficácia.",
                "Encerramento gera relatório final automático.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Cupons e tarifas da campanha ativados ou desativados.",
                "Reservas passam a registrar origem da campanha.",
                "Dashboard comercial exibe campanha ativa.",
                "Relatórios filtram locações por campanha.",
                "Automações de e-mail marketing usam segmento configurado.",
            ],
        ),
    ),
    "comercial.proposta": instr(
        "Documento comercial formal enviado ao prospect ou cliente corporativo, "
        "consolidando condições de locação, frota, preços, prazos e validade. "
        "Etapa intermediária entre cotação e contrato fechado.",
        (
            "Para que serve",
            [
                "Apresentar proposta comercial estruturada ao cliente.",
                "Consolidar condições negociadas (frota, prazo, desconto, SLA).",
                "Definir validade e versão da proposta para controle.",
                "Registrar aprovação ou recusa do cliente.",
                "Converter proposta aprovada em reserva ou contrato.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cotações: base de valores da proposta.",
                "Funil de oportunidades: estágio de proposta enviada.",
                "Clientes corporativos: histórico de negociações.",
                "Contratos: conversão da proposta aceita.",
                "Relatórios de conversão proposta → contrato.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Profissionalismo na apresentação comercial.",
                "Histórico de versões evita retrabalho e mal-entendidos.",
                "Gestão de pipeline com propostas pendentes visíveis.",
                "Conversão ágil de proposta aprovada em operação.",
                "Auditoria de descontos e condições especiais concedidas.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Proposta expirada exige renovação com recálculo tarifário.",
                "Versões numeradas; apenas última versão ativa para conversão.",
                "Aprovação pode exigir alçada conforme valor ou desconto.",
                "Anexos (PDF, planilha) armazenados com a proposta.",
                "Proposta recusada registra motivo para análise comercial.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Funil atualiza estágio da oportunidade.",
                "Cliente recebe PDF/link se automação configurada.",
                "Conversão gera reserva com parâmetros da proposta.",
                "Relatórios de win/loss incluem proposta.",
                "Metas comerciais consideram valor de propostas enviadas.",
            ],
        ),
    ),
    "comercial.funil_oportunidade": instr(
        "Gestão de oportunidades comerciais no funil de vendas, desde lead até fechamento, "
        "com etapas, probabilidade, valor estimado e responsável. "
        "Visibilidade do pipeline para gestão comercial B2B e corporativo.",
        (
            "Para que serve",
            [
                "Registrar leads e oportunidades de negócio em andamento.",
                "Acompanhar etapas: qualificação, proposta, negociação, fechamento.",
                "Estimar receita ponderada por probabilidade de fechamento.",
                "Atribuir responsável (vendedor) e prazo de follow-up.",
                "Identificar gargalos e taxa de conversão por etapa.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cadastro de clientes/prospects: contato vinculado.",
                "Cotações e propostas: documentos da oportunidade.",
                "Vendedores: proprietário da oportunidade.",
                "Contratos: conversão em fechamento ganho.",
                "Relatórios de pipeline e forecast comercial.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Previsibilidade de receita com pipeline visível.",
                "Nenhuma oportunidade esquecida com alertas de follow-up.",
                "Gestor acompanha performance individual e da equipe.",
                "Análise de motivos de perda para melhoria comercial.",
                "Integração marketing → vendas com rastreio de origem.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Etapa avançada manualmente ou por gatilho (proposta enviada).",
                "Oportunidade ganha gera reserva/contrato; perdida registra motivo.",
                "Valor ponderado = valor estimado × probabilidade da etapa.",
                "Oportunidade inativa após período sem interação (configurável).",
                "Duplicidade de oportunidade para mesmo cliente alertada.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Dashboard comercial atualiza pipeline e forecast.",
                "Alertas de follow-up agendados para vendedor.",
                "Conversão vincula contrato/reserva à oportunidade.",
                "Relatórios de conversão por etapa recalculados.",
                "Metas de vendedor consideram oportunidades em aberto.",
            ],
        ),
    ),
    "comercial.fidelidade": instr(
        "Configuração do programa de fidelidade: regras de pontuação, tiers de benefícios e resgate por clientes recorrentes. "
        "Incentiva retenção e aumenta lifetime value na locadora.",
        (
            "Para que serve",
            [
                "Definir quantos pontos o cliente ganha por real gasto ou por diária.",
                "Criar níveis (tiers) com benefícios progressivos.",
                "Estabelecer validade dos pontos e valor de resgate.",
                "Recompensar clientes frequentes sem depender só de desconto manual.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Encerramento de contratos e faturamento: crédito de pontos.",
                "Cadastro de clientes: saldo e tier exibidos no histórico.",
                "Campanhas e cupons: podem combinar com benefícios de fidelidade.",
                "Relatórios comerciais de retenção e recorrência.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Aumenta retenção com recompensa automática.",
                "Diferencia a locadora para clientes corporativos e PF recorrentes.",
                "Reduz necessidade de desconto ad hoc no balcão.",
                "Permite comunicação marketing por nível de tier.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Pontos por real e por diária podem acumular juntos — calibrar para não distorcer margem.",
                "Validade em meses expira pontos antigos; informar o cliente.",
                "Tiers exigem pontos mínimos cumulativos; ordem importa.",
                "Desativar o programa não apaga histórico, mas para novos créditos.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Novos contratos passam a creditar pontos conforme regra vigente.",
                "Resgates futuros usam valor por ponto configurado.",
                "Clientes podem mudar de tier automaticamente ao atingir pontos.",
                "Extrato de fidelidade reflete parâmetros atuais.",
            ],
        ),
    ),
}
