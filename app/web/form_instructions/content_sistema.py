"""Instruções de formulário — módulo Sistema (Identity, Tenants, Relatórios, Automações, Parâmetros)."""

from app.web.form_instructions._helpers import instr

INSTRUCTIONS = {
    "identity.user": instr(
        "Cadastro de usuários do sistema com login, perfil de acesso, filial padrão e "
        "vínculo opcional com vendedor ou operador. "
        "Controla quem acessa o ERP e quais módulos pode utilizar.",
        (
            "Para que serve",
            [
                "Criar contas de acesso para colaboradores da locadora.",
                "Definir e-mail/login e política de senha.",
                "Vincular perfil (role) que determina permissões.",
                "Associar filial padrão e filiais adicionais permitidas.",
                "Controlar status ativo/inativo e último acesso.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Perfis (roles): conjunto de permissões do usuário.",
                "Filial: unidade operacional padrão ao logar.",
                "Vendedor: vínculo para comissionamento e funil.",
                "Auditoria: registro de ações por usuário.",
                "Caixa: operador responsável por turno de caixa.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Segurança com acesso mínimo necessário (least privilege).",
                "Rastreabilidade de alterações e lançamentos por pessoa.",
                "Desligamento ágil com desativação imediata de acesso.",
                "Experiência personalizada com filial e módulos corretos.",
                "Conformidade com políticas internas de TI.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "E-mail/login único no tenant (empresa).",
                "Usuário inativo não autentica, mas preserva histórico.",
                "Reset de senha via e-mail ou administrador.",
                "MFA/2FA quando habilitado nos parâmetros de segurança.",
                "Superadmin tem acesso irrestrito — uso controlado.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Permissões efetivas atualizadas no próximo login.",
                "Filial padrão alterada reflete menus e dados exibidos.",
                "Automações que notificam usuário usam e-mail atual.",
                "Auditoria registra alteração de perfil ou status.",
                "Vendedor vinculado passa a receber oportunidades atribuídas.",
            ],
        ),
    ),
    "identity.role": instr(
        "Definição de perfis de acesso (roles) com permissões granulares por módulo, "
        "ação (visualizar, criar, editar, excluir, aprovar) e escopo por filial. "
        "Base da segurança e segregação de funções no ERP.",
        (
            "Para que serve",
            [
                "Agrupar permissões em perfis reutilizáveis (Operador, Gerente, Financeiro).",
                "Controlar acesso a módulos: frota, reservas, financeiro, fiscal, etc.",
                "Definir alçadas: desconto máximo, cancelamento, aprovação de pagamento.",
                "Restringir visualização por filial ou dados sensíveis.",
                "Facilitar onboarding de usuários com perfil pré-configurado.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Usuários: cada usuário recebe um ou mais perfis.",
                "Menus e telas: exibição condicionada à permissão.",
                "API: endpoints validam role do token.",
                "Workflows: etapas de aprovação por perfil.",
                "Relatórios: exportação restrita por permissão.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Segurança robusta sem configurar usuário por usuário.",
                "Conformidade com segregação de funções (ex.: quem lança ≠ quem aprova).",
                "Redução de erros operacionais por acesso indevido.",
                "Auditoria clara de quem pode fazer o quê.",
                "Escalabilidade ao crescer equipe e filiais.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Permissões cumulativas se usuário tem múltiplos perfis.",
                "Perfil sistema (admin) não deve ser atribuído indiscriminadamente.",
                "Alteração de perfil afeta todos os usuários vinculados.",
                "Permissão de exclusão separada de edição para dados críticos.",
                "Escopo filial limita dados visíveis mesmo com permissão de módulo.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Usuários com perfil recebem permissões atualizadas.",
                "Menus ocultos ou exibidos conforme nova configuração.",
                "Tentativas de ação negadas/granted imediatamente.",
                "Fluxos de aprovação reconhecem novos aprovadores.",
                "Logs de segurança registram alteração de perfil.",
            ],
        ),
    ),
    "tenants.filial": instr(
        "Cadastro de filiais ou unidades operacionais da locadora, com endereço, "
        "horário de funcionamento, contas bancárias e parâmetros locais. "
        "Cada filial opera reservas, frota e caixa de forma semi-autônoma.",
        (
            "Para que serve",
            [
                "Representar loja, aeroporto ou ponto de atendimento físico.",
                "Definir endereço, telefone e horário para retirada/devolução.",
                "Vincular frota alocada, caixa e contas bancárias da unidade.",
                "Configurar parâmetros específicos (taxa aeroporto, feriados locais).",
                "Segmentar relatórios e permissões por filial.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas: filial de retirada e devolução.",
                "Frota: veículos alocados por filial.",
                "Usuários: escopo de acesso por unidade.",
                "Financeiro: caixa e conta bancária da filial.",
                "Relatórios: performance por unidade.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Operação multi-loja organizada com dados isolados.",
                "Cliente escolhe local correto na reserva.",
                "Gestão comparativa de performance entre filiais.",
                "Conformidade fiscal com IE municipal por unidade.",
                "Escalabilidade ao abrir novas unidades.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Filial inativa não recebe novas reservas.",
                "Transferência de veículo entre filiais registra movimentação.",
                "Taxa de retorno cobrada quando devolução em filial diferente.",
                "Fuso horário e feriados locais afetam cálculo de diárias.",
                "Código da filial único para integrações OTAs.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Reservas listam filiais ativas para seleção.",
                "Usuários com escopo filial veem dados atualizados.",
                "Mapa de frota por unidade recalculado.",
                "Relatórios consolidados incluem/excluem filial conforme status.",
                "Integrações externas sincronizam pontos de retirada.",
            ],
        ),
    ),
    "tenants.empresa": instr(
        "Cadastro da empresa (tenant) locadora, com razão social, CNPJ, regime tributário, "
        "logo e configurações globais. "
        "Entidade raiz que agrupa filiais, usuários e dados do ERP.",
        (
            "Para que serve",
            [
                "Identificar legalmente a locadora no sistema.",
                "Definir CNPJ, IE e regime tributário para emissão fiscal.",
                "Configurar branding (logo, cores) em documentos e portal.",
                "Estabelecer parâmetros globais aplicáveis a todas as filiais.",
                "Servir como isolamento de dados em ambiente multi-tenant.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Filial: unidades pertencentes à empresa.",
                "Fiscal: emissor de NF-e/NFS-e com dados da empresa.",
                "Usuários: escopo de acesso ao tenant.",
                "Relatórios consolidados: visão empresa inteira.",
                "Integrações: credenciais e webhooks por empresa.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Documentos fiscais e contratos com dados legais corretos.",
                "Identidade visual consistente em toda comunicação.",
                "Base sólida para expansão multi-filial.",
                "Isolamento de dados entre locadoras no mesmo ambiente SaaS.",
                "Configuração centralizada reduz retrabalho por filial.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "CNPJ único identifica tenant no sistema.",
                "Regime tributário afeta módulo fiscal inteiro.",
                "Alteração de razão social reflete em novos documentos.",
                "Certificado digital vinculado à empresa para NF-e.",
                "Plano/licença pode limitar filiais, usuários ou veículos.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "NF-e/NFS-e usam dados atualizados do emitente.",
                "Contratos e propostas exibem razão social e logo atuais.",
                "Parâmetros globais propagados para filiais.",
                "Relatórios gerenciais consolidados da empresa.",
                "Integrações usam identificador do tenant.",
            ],
        ),
    ),
    "tenants.sistema": instr(
        "Configurações técnicas e operacionais do ambiente do tenant, incluindo integrações, "
        "notificações, backup e preferências de localização. "
        "Camada de infraestrutura visível ao administrador do sistema.",
        (
            "Para que serve",
            [
                "Configurar idioma, fuso horário e formato de moeda/data.",
                "Gerenciar integrações (OTA, telemetria, pagamento, fiscal).",
                "Definir políticas de notificação (e-mail, SMS, push).",
                "Parametrizar retenção de logs e auditoria.",
                "Controlar recursos habilitados conforme plano contratado.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Todos os módulos: comportamento global derivado da config.",
                "Automações: canais de envio configurados.",
                "Fiscal: certificado e ambiente (homologação/produção).",
                "API externa: chaves e webhooks.",
                "Relatórios: exportação e agendamento de envio.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Sistema adaptado à realidade operacional da locadora.",
                "Integrações funcionais sem erro de ambiente.",
                "Comunicação automática confiável com clientes.",
                "Conformidade com LGPD em retenção de dados.",
                "Estabilidade com backup e monitoramento configurados.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Ambiente fiscal homologação vs produção — cuidado ao alternar.",
                "Chaves de API secretas com permissão restrita.",
                "Alteração de fuso afeta cálculo de diárias e vencimentos.",
                "Desabilitar módulo oculta menus mas preserva dados históricos.",
                "Configuração incorreta de SMTP impede e-mails transacionais.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Integrações passam a usar novas credenciais/endpoints.",
                "Formato de exibição de datas e valores em todo o sistema.",
                "Automações disparam pelos canais configurados.",
                "Emissão fiscal usa ambiente selecionado.",
                "Usuários podem precisar relogar para cache de configuração.",
            ],
        ),
    ),
    "relatorios.emitir": instr(
        "Emissão sob demanda de relatórios operacionais, comerciais, financeiros e de frota, "
        "com filtros por período, filial, categoria e exportação em PDF/Excel. "
        "Ferramenta de análise e tomada de decisão para gestores.",
        (
            "Para que serve",
            [
                "Gerar relatórios instantâneos com filtros personalizados.",
                "Analisar ocupação, receita, inadimplência, multas e custos.",
                "Exportar dados para Excel, PDF ou CSV.",
                "Visualizar gráficos e totalizadores no próprio sistema.",
                "Compartilhar snapshot de dados para reuniões e auditoria.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Todos os módulos: fonte de dados do relatório.",
                "Permissões: acesso restrito por perfil de usuário.",
                "Filial: escopo de dados conforme unidade.",
                "Agendamento: base para relatórios recorrentes.",
                "Dashboard: KPIs derivados dos mesmos dados.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Decisões baseadas em dados atualizados e confiáveis.",
                "Redução de planilhas manuais externas ao sistema.",
                "Filtros salvos agilizam consultas recorrentes.",
                "Exportação facilita apresentações e contabilidade.",
                "Transparência operacional para sócios e investidores.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Período máximo de consulta pode ser limitado por performance.",
                "Dados respeitam escopo de filial do usuário.",
                "Relatório financeiro fechado usa snapshot da competência.",
                "Grandes volumes podem processar em background com notificação.",
                "Campos sensíveis ocultos conforme permissão (ex.: margem).",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Nenhum dado transacional alterado — operação somente leitura.",
                "Histórico de relatórios emitidos registrado para auditoria.",
                "Exportação gerada com timestamp e usuário emissor.",
                "Filtros salvos disponíveis para reutilização.",
                "Cache de dashboard pode ser invalidado após emissão.",
            ],
        ),
    ),
    "relatorios.agendamento": instr(
        "Agendamento de envio automático de relatórios por e-mail em periodicidade definida "
        "(diário, semanal, mensal) para lista de destinatários. "
        "Mantém gestores informados sem acesso manual ao sistema.",
        (
            "Para que serve",
            [
                "Programar envio recorrente de relatórios por e-mail.",
                "Definir destinatários internos (gestores, financeiro, diretoria).",
                "Escolher formato de anexo (PDF, Excel).",
                "Configurar horário e dia da semana/mês de envio.",
                "Garantir recebimento consistente de KPIs operacionais.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Relatórios emitir: modelo e filtros do relatório agendado.",
                "Usuários: destinatários internos por e-mail.",
                "Automações: motor de execução no horário programado.",
                "Parâmetros: servidor SMTP para envio.",
                "Auditoria: log de envios bem-sucedidos e falhas.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Gestão proativa com indicadores na caixa de entrada.",
                "Reduz dependência de operador para gerar relatório.",
                "Padronização de informações para toda equipe gerencial.",
                "Histórico de envios para comprovar comunicação.",
                "Alertas automáticos de anomalias (ex.: inadimplência alta).",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Agendamento inativo suspende envios sem excluir configuração.",
                "Falha de SMTP registra tentativa e alerta administrador.",
                "Relatório vazio ou erro não envia e-mail silenciosamente — registra log.",
                "Destinatário externo pode exigir aprovação por LGPD.",
                "Fuso horário da empresa define horário de disparo.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Job agendado criado/atualizado no motor de automações.",
                "Próximo envio calculado conforme periodicidade.",
                "Destinatários passam a receber relatórios automaticamente.",
                "Log de agendamentos disponível para consulta.",
                "Alteração de filtros reflete a partir do próximo ciclo.",
            ],
        ),
    ),
    "automacoes.regra": instr(
        "Regras de automação baseadas em eventos e condições (se/então), disparando ações "
        "como e-mail, SMS, alteração de status ou criação de tarefa. "
        "Reduz trabalho manual repetitivo na operação da locadora.",
        (
            "Para que serve",
            [
                "Automatizar respostas a eventos do sistema (reserva criada, check-in atrasado).",
                "Definir condições: se status X e filial Y, então ação Z.",
                "Enviar notificações transacionais ao cliente ou equipe interna.",
                "Escalonar alertas (ex.: documento vencendo em 7, 3, 1 dia).",
                "Integrar com webhooks para sistemas externos.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas, contratos, frota, financeiro: eventos gatilho.",
                "Parâmetros de e-mail/SMS: canal de execução.",
                "Usuários: destinatários internos de alertas.",
                "Workflows: regras simples vs fluxos complexos.",
                "Auditoria: log de execuções da regra.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Operação mais ágil com menos intervenção manual.",
                "Cliente informado proativamente (confirmação, lembrete devolução).",
                "Redução de no-show com lembretes automáticos.",
                "Equipe alertada sobre exceções críticas em tempo real.",
                "Consistência na aplicação de políticas operacionais.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Regra inativa não dispara, mas preserva configuração.",
                "Ordem de execução quando múltiplas regras matcham mesmo evento.",
                "Condições aninhadas (AND/OR) para cenários complexos.",
                "Limite de envio para evitar spam (ex.: máx. 1 e-mail/dia por cliente).",
                "Teste/simulação antes de ativar em produção recomendado.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Motor de eventos registra nova regra para matching.",
                "Próximos eventos compatíveis disparam ações configuradas.",
                "Log de automação passa a registrar execuções da regra.",
                "Desativação interrompe disparos imediatamente.",
                "Alteração de template de mensagem reflete nos próximos envios.",
            ],
        ),
    ),
    "automacoes.workflow": instr(
        "Fluxos de trabalho multi-etapa com aprovações, tarefas humanas e integrações, "
        "para processos que exigem sequência ordenada (ex.: aprovação de desconto, pagamento). "
        "Complementa regras simples com orquestração complexa.",
        (
            "Para que serve",
            [
                "Modelar processos com múltiplas etapas e responsáveis.",
                "Exigir aprovação gerencial para descontos, cancelamentos ou pagamentos.",
                "Atribuir tarefas a usuários/perfil com prazo de conclusão.",
                "Integrar etapas automáticas com manuais no mesmo fluxo.",
                "Rastrear status do processo do início ao fim.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Contratos e reservas: aprovação de exceções comerciais.",
                "Financeiro: workflow de aprovação de pagamento.",
                "Usuários e perfis: aprovadores por etapa.",
                "Automações regra: gatilho de início do workflow.",
                "Notificações: alerta ao aprovador pendente.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Controle gerencial sobre decisões de alto impacto.",
                "Rastreabilidade de quem aprovou e quando.",
                "Redução de gargalos com fila visível de pendências.",
                "Conformidade com políticas internas de alçada.",
                "Processos padronizados entre filiais.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Etapa rejeitada encerra fluxo ou retorna para correção.",
                "Timeout de aprovação escala para superior configurado.",
                "Aprovador não pode ser o mesmo que solicitou (segregação).",
                "Workflow paralelo vs sequencial conforme modelagem.",
                "Instância de workflow vinculada ao registro origem (contrato, título).",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Novas solicitações seguem fluxo atualizado.",
                "Instâncias em andamento podem usar versão anterior até concluir.",
                "Fila de aprovações exibe tarefas pendentes.",
                "Ação final (aprovar desconto) executada ao concluir workflow.",
                "Auditoria registra cada transição de etapa.",
            ],
        ),
    ),
    "parametros.geral": instr(
        "Parâmetros gerais da operação da locadora, centralizando defaults e políticas "
        "aplicáveis a reservas, contratos, financeiro e operação. "
        "Evita hardcode e permite adaptação sem customização de software.",
        (
            "Para que serve",
            [
                "Definir valores e comportamentos padrão de todo o ERP.",
                "Configurar política de tanque, antecedência de reserva, idade mínima.",
                "Estabelecer formatos, arredondamentos e moeda.",
                "Parametrizar bloqueios automáticos (CNH vencida, inadimplência).",
                "Controlar features habilitadas (telemetria, intermediação, fiscal).",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e contratos: regras de negócio derivadas dos parâmetros.",
                "Checkout/check-in: política de combustível e KM.",
                "Financeiro: juros, multa e dias de tolerância.",
                "Cadastros: validações automáticas de documentos.",
                "Todos os módulos: defaults globais.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Operação alinhada à política comercial da locadora.",
                "Mudança de regra sem alteração de código.",
                "Consistência entre filiais com parâmetros centralizados.",
                "Onboarding de operadores com regras claras no sistema.",
                "Redução de exceções manuais por defaults bem definidos.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Parâmetros globais vs override por filial quando permitido.",
                "Alteração sensível exige permissão de administrador.",
                "Histórico de alterações auditado com usuário e timestamp.",
                "Alguns parâmetros exigem relogar ou reiniciar sessão.",
                "Valor inválido rejeitado com validação na gravação.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Novas reservas e contratos aplicam regras atualizadas.",
                "Validações em formulários usam parâmetros vigentes.",
                "Cálculos de juros, taxas e arredondamento recalculados.",
                "Features habilitadas/desabilitadas refletem nos menus.",
                "Filhas herdam ou sobrescrevem conforme configuração de propagação.",
            ],
        ),
    ),
    "integracoes.api_publica": instr(
        "Geração de chaves de API para integrações externas: site de reservas, aplicativo mobile ou parceiros tecnológicos. "
        "Controla escopos de acesso e rastreia consumo por chave.",
        (
            "Para que serve",
            [
                "Permitir que sistemas externos consultem disponibilidade e criem reservas.",
                "Restringir o que cada integração pode fazer via escopos.",
                "Identificar origem técnica das requisições (site, app, parceiro).",
                "Revogar acesso comprometido sem afetar outras integrações.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e cotações criadas via API aparecem no fluxo normal.",
                "Tarifário e disponibilidade: endpoints consumidos pelas chaves.",
                "Auditoria e logs de integração para troubleshooting.",
                "Documentação OpenAPI/Swagger publicada no mesmo módulo.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Automatiza canal digital sem digitação manual no balcão.",
                "Segurança granular por escopo (somente leitura vs criação).",
                "Rastreabilidade por chave facilita suporte e billing B2B.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "A chave completa só é exibida uma vez na criação — guarde com segurança.",
                "Header X-Tenant-Slug identifica a locadora em ambientes multi-tenant.",
                "Escopos marcados definem endpoints permitidos; princípio do menor privilégio.",
                "Rotacionar chaves periodicamente em produção.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Nova chave fica ativa imediatamente para requisições autenticadas.",
                "Integrações existentes não são alteradas.",
                "Logs passam a registrar chamadas com o nome da chave.",
            ],
        ),
    ),
}
