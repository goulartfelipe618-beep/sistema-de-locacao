"""Instruções de formulário — módulo Cadastros."""

from app.web.form_instructions._helpers import instr

INSTRUCTIONS = {
    "cadastros.cliente": instr(
        "Cadastro central de clientes da locadora, incluindo dados pessoais, contato, endereço e informações de habilitação (CNH). "
        "É a base para reservas, contratos, cobranças e comunicações. "
        "Um cliente bem cadastrado evita retrabalho na abertura de locações e reduz riscos operacionais.",
        (
            "Para que serve",
            [
                "Identificar de forma única cada pessoa física ou jurídica que aluga veículos na empresa.",
                "Armazenar dados de contato, endereço, documentos e CNH para validação na retirada do veículo.",
                "Servir como vínculo principal em reservas, contratos, faturas, multas e histórico de locações.",
                "Permitir segmentação comercial (corporativo, turismo, assinatura) e controle de inadimplência.",
                "Centralizar observações importantes sobre restrições, preferências ou pendências do cliente.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e cotações: seleção do locatário responsável pela reserva.",
                "Contratos de locação: dados do titular e condutores adicionais vinculados ao cliente.",
                "Financeiro a receber: títulos, faturas e cobranças emitidas contra o cadastro.",
                "Multas e avarias: identificação do responsável e envio de cobrança ou débito.",
                "Relatórios de clientes, histórico de locações e indicadores de recorrência.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Agiliza o checkout com CNH e documentos já validados no sistema.",
                "Reduz erros de faturamento por CPF/CNPJ ou endereço incorreto.",
                "Facilita localizar histórico completo de locações, pagamentos e ocorrências.",
                "Melhora a experiência do cliente em reservas futuras com dados pré-preenchidos.",
                "Apoia decisões comerciais com base em perfil, frequência e ticket médio.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "CPF ou CNPJ deve ser único por empresa/filial conforme parametrização do sistema.",
                "CNH com data de validade vencida pode bloquear ou alertar na abertura de contrato.",
                "Cliente inadimplente ou com restrição cadastral pode impedir novas locações.",
                "Pessoa jurídica exige responsável legal e pode ter condutores adicionais vinculados.",
                "Alterações em dados sensíveis (documento, CNH) devem ser feitas com conferência documental.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Reservas em aberto passam a exibir os dados atualizados do cliente.",
                "Contratos futuros utilizam a versão atual do cadastro na impressão e integrações.",
                "Títulos financeiros pendentes mantêm vínculo, mas novos usam endereço e razão social atuais.",
                "Relatórios e dashboards de clientes refletem imediatamente alterações de status ou segmento.",
                "Automações de e-mail/SMS e cobrança usam telefone e e-mail cadastrados no momento do envio.",
            ],
        ),
    ),
    "cadastros.parceiro": instr(
        "Cadastro de parceiros comerciais que indicam ou encaminham clientes para a locadora, como agências, "
        "hotéis, corretores e empresas de turismo. "
        "Não confundir com fornecedores de frota: parceiros atuam na captação de demanda, não na disponibilização de veículos.",
        (
            "Para que serve",
            [
                "Registrar empresas ou profissionais que originam reservas e locações para a locadora.",
                "Controlar comissões, repasses e condições comerciais acordadas com cada parceiro.",
                "Rastrear a origem das vendas para análise de performance e campanhas conjuntas.",
                "Permitir tarifas ou tabelas específicas vinculadas ao canal do parceiro.",
                "Manter contatos comerciais e dados para faturamento de comissões.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e cotações: campo de origem/indicação vinculado ao parceiro.",
                "Contratos: registro da comissão e percentual aplicável na locação.",
                "Financeiro a pagar: geração de títulos de comissão ao fechar períodos.",
                "Relatórios comerciais: produção por parceiro, conversão e ticket médio.",
                "Campanhas e cupons promocionais exclusivos para canais parceiros.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Garante pagamento correto de comissões sem disputas por dados incompletos.",
                "Permite medir ROI de cada canal de indicação com precisão.",
                "Facilita negociações com histórico de volume e receita gerada.",
                "Evita conflito entre vendedor interno e parceiro externo na origem da venda.",
                "Suporta contratos com regras diferenciadas por tipo de parceiro.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Parceiro inativo não deve aparecer para novas reservas, mas permanece no histórico.",
                "Percentual de comissão pode ser padrão ou sobrescrito por contrato/reserva.",
                "Comissão geralmente é calculada sobre diárias líquidas, excluindo taxas ou proteções conforme regra.",
                "CNPJ do parceiro é obrigatório para emissão de nota de comissão quando aplicável.",
                "Um parceiro pode estar vinculado a um vendedor responsável interno.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Novas reservas passam a listar o parceiro com condições atualizadas.",
                "Contratos em elaboração recalculam comissão se percentual for alterado.",
                "Relatórios de produção por parceiro refletem status ativo/inativo.",
                "Títulos de comissão futuros usam dados bancários e fiscais atuais.",
                "Integrações de API externa podem sincronizar identificador do parceiro.",
            ],
        ),
    ),
    "cadastros.fornecedor": instr(
        "Cadastro de fornecedores de serviços e materiais para a operação da locadora, incluindo oficinas, "
        "seguradoras, despachantes e empresas de terceirização de frota. "
        "Diferente do parceiro comercial, o fornecedor recebe pagamentos pela prestação de serviço ou intermediação operacional.",
        (
            "Para que serve",
            [
                "Identificar empresas que prestam serviços à frota ou à locadora (manutenção, seguro, guincho).",
                "Registrar fornecedores de intermediação — outras locadoras que emprestam veículos em outsourcing.",
                "Centralizar dados fiscais, bancários e contatos para contas a pagar.",
                "Vincular ordens de serviço, contratos de intermediação e notas fiscais de entrada.",
                "Controlar prazos, condições de pagamento e avaliação de fornecedores.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Manutenção: ordens de serviço e compra de peças vinculadas ao fornecedor.",
                "Intermediação: contratos com locadoras parceiras para frota terceirizada.",
                "Financeiro a pagar: títulos gerados por NF de serviço, OS ou contrato.",
                "Fiscal: importação de XML e escrituração de despesas.",
                "Cadastro de peças e serviços com fornecedor preferencial.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Agiliza lançamento de despesas com dados fiscais prontos para NF-e/NFS-e.",
                "Reduz erros em pagamentos por PIX, TED ou boleto com dados bancários validados.",
                "Permite comparar custos e prazos entre fornecedores de manutenção.",
                "Facilita auditoria de contratos de intermediação e repasses.",
                "Melhora rastreabilidade de gastos por categoria de fornecedor.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Fornecedor de intermediação deve ser marcado com tipo específico para módulo correto.",
                "CNPJ é chave para conciliação fiscal e não deve duplicar registros.",
                "Fornecedor bloqueado impede novos lançamentos, mas preserva histórico.",
                "Regime tributário e retenções influenciam cálculo de impostos na NF de entrada.",
                "Prazo de pagamento padrão pode ser herdado em novos títulos a pagar.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Novas ordens de serviço e contratos de intermediação usam dados atualizados.",
                "Títulos a pagar em aberto mantêm vínculo; novos usam condição de pagamento atual.",
                "Relatórios de despesas por fornecedor refletem alterações imediatas.",
                "Importação de XML associa automaticamente pelo CNPJ cadastrado.",
                "Workflows de aprovação de pagamento podem validar limite por fornecedor.",
            ],
        ),
    ),
    "cadastros.vendedor": instr(
        "Cadastro de vendedores e consultores comerciais internos responsáveis por atendimento, "
        "negociação e fechamento de reservas e contratos. "
        "Permite controle de metas, comissões internas e accountability sobre a origem das vendas.",
        (
            "Para que serve",
            [
                "Identificar o colaborador responsável pela venda ou atendimento ao cliente.",
                "Calcular comissões internas sobre locações fechadas pelo vendedor.",
                "Distribuir leads e oportunidades no funil comercial.",
                "Gerar relatórios de produção individual e por equipe.",
                "Vincular metas mensais e indicadores de conversão.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e cotações: campo vendedor responsável.",
                "Contratos: registro de quem fechou a locação para comissionamento.",
                "Funil de oportunidades: proprietário da negociação.",
                "Financeiro a pagar: comissões de vendedores como despesa.",
                "Relatórios comerciais: ranking, metas e ticket médio por vendedor.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Transparência no cálculo de comissões evita conflitos internos.",
                "Gestores acompanham performance real de cada consultor.",
                "Facilita redistribuição de carteira quando vendedor sai ou entra de férias.",
                "Permite bonificação por produto (proteção, upgrade, diárias extras).",
                "Suporta auditoria de descontos concedidos por vendedor.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Vendedor inativo não aparece em novas reservas, mas permanece no histórico.",
                "Comissão pode variar por tipo de locação, canal ou tabela tarifária.",
                "Um vendedor pode estar vinculado a uma ou mais filiais.",
                "Desconto acima do limite do vendedor pode exigir aprovação de supervisor.",
                "Usuário do sistema pode ser vinculado ao cadastro de vendedor para login e permissões.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Novas reservas listam apenas vendedores ativos da filial.",
                "Contratos em aberto mantêm vendedor original; alteração pode recalcular comissão.",
                "Relatórios de produção atualizam percentuais e metas configuradas.",
                "Automações de funil reassignam oportunidades se vendedor for desativado.",
                "Pagamento de comissões futuras usa regras vigentes no fechamento do período.",
            ],
        ),
    ),
    "cadastros.motorista": instr(
        "Cadastro complementar de motoristas adicionais autorizados a conduzir o veículo locado, "
        "além do titular do contrato. "
        "Concentra dados de CNH e validações necessárias para inclusão legal no contrato de locação.",
        (
            "Para que serve",
            [
                "Registrar condutores adicionais além do cliente titular do contrato.",
                "Validar CNH, categoria compatível e validade antes da autorização de condução.",
                "Atender exigências contratuais e de seguro sobre múltiplos condutores.",
                "Manter histórico de quem conduziu veículos em locações anteriores.",
                "Permitir reutilização do cadastro em futuras locações do mesmo motorista.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Contratos de locação: inclusão de motoristas adicionais autorizados.",
                "Checkout e check-in: conferência de documentos na retirada e devolução.",
                "Multas de trânsito: identificação de possível condutor responsável.",
                "Cadastro de clientes: motorista pode ser vinculado como pessoa relacionada.",
                "Relatórios de contratos com múltiplos condutores.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Evita locação irregular por condutor não autorizado ou sem CNH válida.",
                "Protege a locadora em caso de sinistro ou multa com condutor identificado.",
                "Agiliza inclusão de motorista recorrente sem redigitar todos os dados.",
                "Reduz risco de negativa de cobertura securitária por condutor não declarado.",
                "Facilita comunicação em caso de ocorrência com contato do motorista.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "CNH deve estar válida e categoria compatível com o veículo locado.",
                "Idade mínima do motorista pode ser validada conforme política da locadora.",
                "Motorista adicional pode gerar taxa extra conforme tabela tarifária.",
                "Titular do contrato pode ou não ser também motorista — verificar campos obrigatóios.",
                "Motorista bloqueado ou com restrição impede inclusão em novos contratos.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Contratos em elaboração passam a listar motorista para autorização.",
                "Termo de responsabilidade e impressão de contrato incluem dados atualizados.",
                "Checklist de checkout valida presença de CNH conforme cadastro.",
                "Taxa de motorista adicional é calculada se vinculada ao contrato.",
                "Histórico de locações do motorista é atualizado ao fechar contratos.",
            ],
        ),
    ),
    "cadastros.tabela_auxiliar": instr(
        "Cadastro de tabelas auxiliares e listas de valores parametrizáveis do sistema, como cores, "
        "tipos de ocorrência, motivos de cancelamento e classificações diversas. "
        "Padroniza opções em formulários e garante consistência nos relatórios e integrações.",
        (
            "Para que serve",
            [
                "Definir listas de opções reutilizáveis em diversos formulários do ERP.",
                "Padronizar nomenclatura de classificações operacionais e comerciais.",
                "Permitir expansão de categorias sem alteração de código do sistema.",
                "Controlar quais opções estão ativas ou disponíveis por filial.",
                "Suportar ordenação e agrupamento de itens em combos e filtros.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Formulários diversos: combos de seleção alimentados pela tabela auxiliar.",
                "Relatórios: filtros e agrupamentos por valores padronizados.",
                "Automações: condições baseadas em valores de listas parametrizadas.",
                "Importações e integrações: mapeamento de códigos externos.",
                "Auditoria: rastreamento de motivos e classificações em eventos do sistema.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Evita digitação livre inconsistente (ex.: 'Cancelado' vs 'cancelado').",
                "Facilita análise estatística com categorias bem definidas.",
                "Permite desativar opções obsoletas sem perder histórico.",
                "Reduz erros de integração por códigos padronizados.",
                "Operadores encontram opções claras e organizadas nos formulários.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Código interno deve ser único dentro de cada tipo de tabela auxiliar.",
                "Itens inativos não aparecem em novos lançamentos, mas permanecem em registros antigos.",
                "Algumas tabelas são globais (empresa) e outras específicas por filial.",
                "Exclusão física geralmente é bloqueada se houver registros vinculados.",
                "Ordem de exibição controla sequência nos combos de seleção.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Formulários passam a exibir novas opções ou ocultar itens inativos.",
                "Filtros de relatórios incluem valores recém-cadastrados.",
                "Automações com gatilho por valor passam a reconhecer novas entradas.",
                "Registros históricos mantêm referência ao valor vigente na época do lançamento.",
                "Integrações externas podem exigir sincronização de códigos alterados.",
            ],
        ),
    ),
}
