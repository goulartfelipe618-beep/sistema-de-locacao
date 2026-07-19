"""Instruções de formulário — módulo Fiscal."""

from app.web.form_instructions._helpers import instr

INSTRUCTIONS = {
    "fiscal.nfe": instr(
        "Emissão de Nota Fiscal Eletrônica (NF-e) de produtos ou locação quando aplicável, "
        "com integração à SEFAZ e escrituração fiscal. "
        "Documento exigido para faturamento formal de clientes pessoa jurídica e operações específicas.",
        (
            "Para que serve",
            [
                "Emitir NF-e conforme legislação para receitas de locação e vendas acessórias.",
                "Transmitir documento à SEFAZ e obter autorização de uso.",
                "Vincular NF ao contrato, cliente e título a receber.",
                "Gerar DANFE para entrega ao cliente.",
                "Registrar CFOP, NCM e impostos incidentes corretamente.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Contratos e financeiro a receber: origem da fatura.",
                "Cadastro de clientes: destinatário com CNPJ e IE.",
                "Impostos: cálculo de ICMS, PIS, COFINS conforme regime.",
                "Cancelamentos: evento de cancelamento na SEFAZ.",
                "Relatórios fiscais e SPED.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Conformidade fiscal evita multas e autuações.",
                "Cliente corporativo recebe documento para crédito tributário.",
                "Rastreabilidade completa fatura → NF → recebimento.",
                "Automação reduz erro de digitação manual.",
                "Integração contábil facilitada com XML autorizado.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Certificado digital A1/A3 obrigatório e dentro da validade.",
                "Numeração sequencial ininterrupta por série.",
                "Rejeição SEFAZ exige correção antes de nova transmissão.",
                "Carta de correção para ajustes não substitutivos.",
                "Contingência (FS-DA/SVC) quando SEFAZ indisponível.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Título a receber vinculado à NF autorizada.",
                "Contrato registra número e chave de acesso da NF-e.",
                "Estoque fiscal atualizado se houver movimentação de produto.",
                "Relatórios de faturamento incluem valor da NF.",
                "XML armazenado para envio ao contador e SPED.",
            ],
        ),
    ),
    "fiscal.nfse": instr(
        "Emissão de Nota Fiscal de Serviço Eletrônica (NFS-e) para serviços de locação, "
        "taxas administrativas e demais serviços municipais. "
        "Integração com prefeitura conforme layout de cada município.",
        (
            "Para que serve",
            [
                "Emitir NFS-e para serviços sujeitos a ISS municipal.",
                "Atender exigência de clientes PJ e retenções na fonte.",
                "Calcular ISS conforme alíquota e código de serviço municipal.",
                "Transmitir à prefeitura e obter número da nota.",
                "Gerar PDF/recibo para entrega ao tomador.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Contratos e recebíveis: base de cálculo do serviço.",
                "Cadastro de clientes: tomador com dados fiscais.",
                "Impostos: ISS, PIS, COFINS, retenções.",
                "Contas a pagar: ISS retido quando aplicável.",
                "Relatórios de serviços prestados por município.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Regularidade municipal evita problemas com fiscalização.",
                "Retenções calculadas automaticamente para tomador PJ.",
                "Integração RPS → NFS-e em lote agiliza emissão.",
                "Histórico de serviços por cliente para auditoria.",
                "Substituição de processos manuais na prefeitura.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Código de serviço LC 116 (ex.: 11.01 locação) conforme município.",
                "Regime Simples vs Presumido afeta alíquota e retenção.",
                "RPS convertido em NFS-e; numeração controlada.",
                "Cancelamento dentro do prazo municipal via evento.",
                "Cada filial pode ter inscrição municipal distinta.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Recebível vinculado à NFS-e autorizada.",
                "Contrato exibe número da nota de serviço.",
                "Obrigações acessórias municipais alimentadas.",
                "Retenções geram título a pagar ou crédito conforme regra.",
                "Relatório de faturamento de serviços atualizado.",
            ],
        ),
    ),
    "fiscal.impostos": instr(
        "Parametrização de impostos federais, estaduais e municipais aplicáveis às operações "
        "da locadora: ICMS, ISS, PIS, COFINS, CSLL, IR e retenções. "
        "Define alíquotas, CST, CFOP e regras por tipo de operação.",
        (
            "Para que serve",
            [
                "Configurar alíquotas e bases de cálculo por imposto.",
                "Definir CST/CSOSN conforme regime tributário da empresa.",
                "Mapear CFOP para operações de locação e serviços.",
                "Parametrizar retenções na fonte para clientes PJ.",
                "Suportar diferentes regimes: Simples, Presumido, Real.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "NF-e e NFS-e: cálculo automático na emissão.",
                "Contratos: estimativa de impostos na margem.",
                "Apuração: consolidação mensal de débitos e créditos.",
                "Contas a pagar: guias de impostos a recolher.",
                "Relatórios fiscais e DRE gerencial.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Emissão fiscal com impostos corretos evita rejeições.",
                "Planejamento tributário com simulação de carga.",
                "Retenções automáticas reduzem risco de autuação.",
                "Consistência entre NF, contabilidade e apuração.",
                "Adaptação a mudanças legislativas via parametrização.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Regime tributário da empresa define conjunto de regras ativas.",
                "Operação interna vs interestadual altera ICMS e CFOP.",
                "Isenções e reduções exigem fundamento legal cadastrado.",
                "Imposto sobre locação vs serviço depende enquadramento jurídico.",
                "Alteração retroativa bloqueada após apuração fechada.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Novas NF-e/NFS-e usam alíquotas vigentes.",
                "Simulações comerciais refletem carga tributária atualizada.",
                "Apuração pendente recalcula com novos parâmetros.",
                "Relatórios de impostos por operação atualizados.",
                "Integração contábil recebe novos códigos de imposto.",
            ],
        ),
    ),
    "fiscal.cancelamentos": instr(
        "Registro e transmissão de cancelamentos e inutilizações de notas fiscais eletrônicas, "
        "seguindo prazos e regras da SEFAZ e prefeituras. "
        "Corrige erros ou desistências antes da circulação do documento.",
        (
            "Para que serve",
            [
                "Cancelar NF-e/NFS-e autorizada dentro do prazo legal.",
                "Inutilizar numeração de NF não utilizada (gap na sequência).",
                "Registrar motivo do cancelamento para auditoria.",
                "Estornar financeiramente título vinculado à nota.",
                "Comunicar evento aos órgãos fiscais competentes.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "NF-e/NFS-e emitidas: documento a cancelar.",
                "Financeiro: estorno de recebível vinculado.",
                "Contratos: desvinculação ou nova emissão.",
                "Apuração: reversão de impostos declarados.",
                "Relatórios de notas canceladas e inutilizadas.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Regularidade fiscal mantida com eventos transmitidos.",
                "Evita numeração órfã que impede continuidade da série.",
                "Rastreabilidade de motivos para auditoria interna.",
                "Sincronização financeira automática com cancelamento.",
                "Reduz risco de documento 'fantasma' no faturamento.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Cancelamento NF-e geralmente até 24h; NFS-e conforme município.",
                "Nota com cobrança quitada pode exigir fluxo de estorno primeiro.",
                "Inutilização exige justificativa para numeração pulada.",
                "Carta de correção não substitui cancelamento para erro grave.",
                "Permissão elevada exigida para cancelamento.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Status da NF muda para cancelada/inutilizada.",
                "Título a receber estornado ou cancelado.",
                "Contrato disponível para reemissão corrigida.",
                "Apuração do período exclui ou reverte impostos.",
                "Sequência de numeração liberada após inutilização.",
            ],
        ),
    ),
    "fiscal.xml_import": instr(
        "Importação de XML de notas fiscais de entrada (compras, serviços, peças) "
        "para escrituração automática de despesas e créditos tributários. "
        "Agiliza lançamento de contas a pagar e controle fiscal de fornecedores.",
        (
            "Para que serve",
            [
                "Importar NF-e de fornecedores via upload de XML ou integração.",
                "Pré-preencher contas a pagar com dados do documento.",
                "Registrar créditos de ICMS, PIS e COFINS quando aplicável.",
                "Validar CNPJ do emitente contra cadastro de fornecedor.",
                "Armazenar XML para obrigações acessórias e auditoria.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Fornecedores: match por CNPJ do emitente.",
                "Contas a pagar: título gerado automaticamente.",
                "Manutenção: NF de peças vinculada à OS.",
                "Apuração: créditos tributários de entrada.",
                "Estoque de peças: entrada por NF de compra.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Elimina digitação manual de notas de compra.",
                "Reduz erro de valor, imposto e vencimento.",
                "Créditos fiscais aproveitados corretamente.",
                "Arquivo XML centralizado para fiscalização.",
                "Conciliação compra → pagamento → recebimento físico.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "XML duplicado (mesma chave) é rejeitado.",
                "Fornecedor não cadastrado gera alerta para cadastro prévio.",
                "Divergência de valor vs pedido/OS exige aprovação.",
                "Manifestação do destinatário (ciência/confirmação) quando exigida.",
                "Itens da NF mapeados para plano de contas e centro de custo.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Título a pagar criado com vencimento e valor da NF.",
                "Fornecedor atualiza histórico de compras.",
                "OS de manutenção recebe peças e custos da NF.",
                "Apuração inclui créditos da nota importada.",
                "Relatórios de despesas fiscais atualizados.",
            ],
        ),
    ),
    "fiscal.impostos_apuracao": instr(
        "Processo de apuração periódica de impostos, consolidando débitos de saída (NF emitidas) "
        "e créditos de entrada (NF recebidas) para fechamento mensal. "
        "Gera guias de recolhimento e base contábil.",
        (
            "Para que serve",
            [
                "Fechar competência mensal de impostos federais, estaduais e municipais.",
                "Consolidar débitos de NF-e/NFS-e emitidas no período.",
                "Abater créditos de NF de entrada conforme legislação.",
                "Gerar guias DARF, GNRE e DAS quando aplicável.",
                "Bloquear alterações retroativas após fechamento.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "NF-e/NFS-e emitidas: débitos de impostos.",
                "XML importados: créditos de entrada.",
                "Parametrização de impostos: alíquotas e regras.",
                "Contas a pagar: guias de impostos a recolher.",
                "SPED e obrigações acessórias.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Fechamento estruturado evita esquecimento de recolhimentos.",
                "Visão consolidada de carga tributária do período.",
                "Créditos aproveitados dentro do prazo legal.",
                "Auditoria com trilha débito → crédito → guia.",
                "Integração contábil com valores apurados.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Competência fechada impede alteração de NF do período.",
                "Saldo credor pode ser compensado ou restituído conforme regra.",
                "Simples Nacional usa DAS unificado.",
                "Diferença apurada vs guia exige ajuste documentado.",
                "Reabertura de competência exige permissão especial.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Competência marcada como fechada no sistema.",
                "Guias de impostos geradas em contas a pagar.",
                "Relatórios gerenciais de carga tributária consolidados.",
                "Exportação SPED usa valores apurados.",
                "Alertas de vencimento de guias configurados.",
            ],
        ),
    ),
}
