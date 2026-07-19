"""Instruções de formulário — módulo Manutenção."""

from app.web.form_instructions._helpers import instr

INSTRUCTIONS = {
    "manutencao.os": instr(
        "Ordem de Serviço (OS) para reparos, revisões e serviços em veículos da frota, "
        "registrando diagnóstico, peças, mão de obra, fornecedor/oficina e custos. "
        "Controla indisponibilidade do veículo e impacto financeiro.",
        (
            "Para que serve",
            [
                "Documentar serviço de manutenção corretiva ou programada.",
                "Registrar peças utilizadas, horas de mão de obra e custo total.",
                "Vincular veículo, quilometragem e motivo da intervenção.",
                "Controlar status: aberta, em execução, aguardando peça, concluída.",
                "Integrar com contas a pagar e indisponibilidade da frota.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cadastro de veículos: histórico de manutenções.",
                "Check-in e avarias: OS originada de dano na locação.",
                "Fornecedores/oficinas: execução externa do serviço.",
                "Peças: baixa de estoque e custo.",
                "Financeiro a pagar: título ao concluir OS.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Custo real de manutenção por veículo para análise de ROI.",
                "Veículo indisponível refletido na grade de reservas.",
                "Rastreabilidade de reparos para garantia e recall.",
                "Orçamento vs realizado controlado por OS.",
                "Planejamento de frota considera tempo em oficina.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "OS aberta pode alterar status do veículo para manutenção.",
                "Avaria de locação pode gerar OS com cobrança ao cliente vinculada.",
                "Aprovação gerencial acima de valor limite configurável.",
                "OS concluída exige KM e data de retorno à operação.",
                "Serviço interno vs externo define fluxo de pagamento.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Status do veículo atualizado (manutenção ou disponível).",
                "Estoque de peças baixado ao consumir itens.",
                "Título a pagar gerado para oficina/fornecedor.",
                "Histórico de custos do veículo incrementado.",
                "Mapa de disponibilidade reflete retorno ou continuidade da indisponibilidade.",
            ],
        ),
    ),
    "manutencao.pneu": instr(
        "Controle de pneus por veículo ou estoque rotativo, registrando marca, medida, "
        "posição, profundidade de sulco e histórico de rodízio/substituição. "
        "Essencial para segurança e custo operacional da frota.",
        (
            "Para que serve",
            [
                "Cadastrar pneus instalados ou em estoque de reposição.",
                "Registrar medida, marca, DOT e profundidade de sulco.",
                "Controlar rodízio e vida útil por KM rodado.",
                "Alertar substituição quando sulco atingir limite mínimo.",
                "Calcular custo por KM de pneu por veículo.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Veículos: pneus instalados por posição (DD, DE, traseiros).",
                "Ordens de serviço: substituição e rodízio.",
                "Fornecedores: compra de pneus novos.",
                "Check-in: avaria de pneu registrada na locação.",
                "Relatórios de custo de pneus por placa e frota.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Segurança da frota com substituição preventiva.",
                "Redução de custo com rodízio prolongando vida útil.",
                "Rastreio de pneus removidos para recapagem ou descarte.",
                "Cobrança de avaria de pneu fundamentada em estado documentado.",
                "Compliance com exigências de vistoria e seguro.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Sulco mínimo legal (1,6mm) gera alerta operacional.",
                "Pneu reserva registrado separadamente.",
                "Substituição vincula pneu removido (destino: estoque, sucata, recapagem).",
                "Medida incompatível com veículo gera alerta.",
                "KM do pneu acumulado desde instalação ou recapagem.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Ficha do veículo exibe pneus atuais por posição.",
                "Alertas de substituição atualizados ou resolvidos.",
                "OS de rodízio/substituição registra movimentação.",
                "Custo de pneu alocado ao histórico do veículo.",
                "Relatórios de frota incluem status de conformidade de pneus.",
            ],
        ),
    ),
    "manutencao.peca": instr(
        "Cadastro de peças e materiais de reposição usados na manutenção da frota, "
        "com código, descrição, estoque, custo e fornecedor preferencial. "
        "Base para OS, compras e controle de inventário.",
        (
            "Para que serve",
            [
                "Registrar peças de reposição (filtros, pastilhas, lâmpadas, etc.).",
                "Controlar estoque mínimo, máximo e ponto de reposição.",
                "Definir custo médio, último preço e fornecedor preferencial.",
                "Vincular compatibilidade com marcas/modelos de veículos.",
                "Suportar entrada por NF de compra e saída por OS.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Ordens de serviço: consumo de peças no reparo.",
                "Fornecedores: compra e cotação de peças.",
                "XML import: entrada de estoque por NF.",
                "Contas a pagar: pagamento de compras.",
                "Relatórios de giro de estoque e custo de peças.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Evita parada de veículo por falta de peça com estoque mínimo.",
                "Custo real de OS preciso com peças atualizadas.",
                "Rastreabilidade de peça → veículo → OS.",
                "Negociação com fornecedores baseada em histórico de consumo.",
                "Inventário confiável para auditoria.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Código da peça único; código de barras opcional.",
                "Baixa de estoque automática ao concluir OS.",
                "Estoque negativo bloqueado ou permitido conforme parâmetro.",
                "Peça genérica vs específica por modelo afeta sugestões na OS.",
                "Peça inativa não aparece em novas OS, mas preserva histórico.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "OS futuras listam peça com custo e estoque atualizados.",
                "Alertas de estoque mínimo recalculados.",
                "Entrada por NF incrementa quantidade em estoque.",
                "Relatórios de custo de manutenção por categoria de peça.",
                "Cotações de compra usam fornecedor preferencial configurado.",
            ],
        ),
    ),
    "manutencao.preventiva": instr(
        "Plano de manutenção preventiva por veículo, modelo ou categoria, definindo "
        "intervalos por KM ou tempo para revisões, trocas de óleo, filtros e inspeções. "
        "Reduz quebras e prolonga vida útil da frota.",
        (
            "Para que serve",
            [
                "Programar revisões periódicas antes de falhas ocorrerem.",
                "Definir intervalos por KM (ex.: 10.000 km) ou meses.",
                "Gerar alertas e OS automáticas quando veículo atingir gatilho.",
                "Padronizar checklist de itens por tipo de revisão.",
                "Comparar aderência ao plano entre veículos e filiais.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Veículos: KM atual vs próximo serviço programado.",
                "Ordens de serviço: geração automática de OS preventiva.",
                "Modelos/categorias: plano padrão herdado por veículo.",
                "Disponibilidade: bloqueio antecipado para manutenção programada.",
                "Relatórios de conformidade do plano preventivo.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Menos paradas emergenciais e custo de reparo corretivo.",
                "Veículos mais confiáveis para locação.",
                "Valor residual da frota preservado com histórico de revisões.",
                "Operação planeja indisponibilidade com antecedência.",
                "Seguro e garantia de fábrica mantidos em dia.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Gatilho por KM ou data — o que ocorrer primeiro dispara alerta.",
                "Plano pode ser específico por modelo (ex.: câmbio automático).",
                "OS preventiva gerada pode exigir agendamento com oficina.",
                "Atraso na preventiva gera alerta escalonado (amarelo/vermelho).",
                "Conclusão da OS atualiza próximo gatilho automaticamente.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Veículos vinculados recalculam data/KM do próximo serviço.",
                "Dashboard de manutenção exibe alertas atualizados.",
                "Novos veículos herdam plano padrão do modelo/categoria.",
                "Grade de reservas pode sugerir evitar alocação próxima ao serviço.",
                "Relatórios de conformidade medem % de preventivas em dia.",
            ],
        ),
    ),
}
