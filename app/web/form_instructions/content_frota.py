"""Instruções de formulário — módulo Frota."""

from app.web.form_instructions._helpers import instr

INSTRUCTIONS = {
    "frota.veiculo": instr(
        "Cadastro individual de cada veículo da frota própria ou terceirizada, com placa, chassi, "
        "quilometragem, status operacional e vínculos com categoria, modelo e documentação. "
        "É o núcleo operacional para reservas, contratos, manutenção e controle de disponibilidade.",
        (
            "Para que serve",
            [
                "Identificar unicamente cada automóvel disponível para locação ou em manutenção.",
                "Controlar status (disponível, locado, reservado, manutenção, vendido, indisponível).",
                "Registrar quilometragem, tanque, avarias e histórico de utilização.",
                "Vincular documentos (CRLV, seguro, licenciamento) e telemetria quando aplicável.",
                "Suportar alocação em reservas, contratos e ordens de serviço.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e contratos: alocação do veículo específico ou por grupo/categoria.",
                "Checkout/check-in: registro de KM, combustível e condição na entrega e devolução.",
                "Manutenção: ordens de serviço, pneus e plano preventivo por veículo.",
                "Intermediação: veículos de frota terceirizada vinculados a fornecedor.",
                "Relatórios de utilização, ROI por ativo e depreciação da frota.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Evita double booking — dois contratos no mesmo veículo no mesmo período.",
                "Permite rastrear lucratividade e custo real por placa.",
                "Facilita planejamento de manutenção com base em KM e tempo de uso.",
                "Garante conformidade documental antes de liberar veículo para locação.",
                "Melhora experiência do cliente com veículo correto na retirada.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Placa e chassi devem ser únicos no cadastro da empresa.",
                "Veículo indisponível ou em manutenção não aparece para alocação em novas reservas.",
                "Status muda automaticamente ao abrir checkout (locado) e fechar check-in (disponível).",
                "Veículo terceirizado exige vínculo com contrato de intermediação ativo.",
                "Quilometragem informada no check-in não pode ser inferior à do checkout sem justificativa.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Mapa de disponibilidade e grade de reservas refletem novo status imediatamente.",
                "Contratos futuros consideram categoria e características atualizadas do veículo.",
                "Alertas de documento vencido e manutenção preventiva são recalculados.",
                "Relatórios de frota e taxa de ocupação atualizam contagem por status.",
                "Integrações de telemetria passam a associar dados à placa cadastrada.",
            ],
        ),
    ),
    "frota.categoria": instr(
        "Definição de categorias ou grupos de veículos (econômico, intermediário, SUV, premium) "
        "usados para precificação, reserva e substituição. "
        "A categoria agrupa veículos com características similares para simplificar a operação comercial.",
        (
            "Para que serve",
            [
                "Classificar veículos por padrão de mercado para cotação e reserva.",
                "Vincular tabelas tarifárias e disponibilidade por grupo, não apenas por placa.",
                "Permitir upgrade/downgrade entre categorias conforme política comercial.",
                "Definir capacidade de passageiros, malas e tipo de transmissão esperados.",
                "Organizar frota para exibição em canal de vendas e OTAs.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cadastro de veículos: cada automóvel pertence a uma categoria.",
                "Tarifário: preços de diária, taxas e proteções por categoria.",
                "Reservas: cliente reserva categoria; veículo específico alocado depois.",
                "Substituição: regras de troca entre categorias em caso de indisponibilidade.",
                "Relatórios de ocupação e receita por grupo de frota.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Precificação consistente para todo o grupo de veículos equivalentes.",
                "Reservas mais ágeis sem exigir placa na cotação inicial.",
                "Gestão de overbooking controlada por quantidade disponível na categoria.",
                "Comunicação clara com cliente sobre tipo de veículo contratado.",
                "Análise comercial por segmento (econômico vs premium).",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Código da categoria deve ser único e estável para integrações externas.",
                "Disponibilidade é calculada pela soma de veículos ativos na categoria menos alocações.",
                "Upgrade pode gerar diferença tarifária; downgrade pode gerar crédito ou manter valor.",
                "Categoria inativa impede novas reservas, mas preserva histórico.",
                "Ordem de exibição define posição em listagens comerciais e OTAs.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Veículos vinculados passam a herdar alterações de nome e descrição comercial.",
                "Tabelas tarifárias associadas aplicam novos parâmetros em cotações.",
                "Reservas futuras exibem nome atualizado da categoria.",
                "Regras de substituição e upgrade usam hierarquia entre categorias.",
                "Relatórios de ocupação por grupo recalculam totais.",
            ],
        ),
    ),
    "frota.marca": instr(
        "Cadastro de marcas de veículos (Fabricantes) utilizadas para classificar modelos e veículos da frota. "
        "Mantém padronização de nomenclatura e facilita filtros, relatórios e integrações com tabelas FIPE.",
        (
            "Para que serve",
            [
                "Identificar o fabricante de cada veículo da frota (Volkswagen, Toyota, etc.).",
                "Organizar modelos hierarquicamente: marca → modelo → veículo.",
                "Permitir filtros e relatórios por fabricante.",
                "Suportar integração com tabelas de referência de mercado (FIPE).",
                "Padronizar descrições em contratos e documentos impressos.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cadastro de modelos: cada modelo pertence a uma marca.",
                "Cadastro de veículos: herda marca via modelo.",
                "Relatórios de frota: agrupamento por fabricante.",
                "Manutenção: peças e compatibilidade por marca.",
                "Comercial: filtros em propostas e vitrine de categorias.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Evita duplicidade ('VW' vs 'Volkswagen') em cadastros e relatórios.",
                "Facilita análise de custo de manutenção por fabricante.",
                "Melhora experiência em combos de seleção ordenados alfabeticamente.",
                "Suporta políticas de compra e renovação de frota por marca.",
                "Integrações externas reconhecem códigos padronizados.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Nome da marca deve ser único no cadastro.",
                "Marca inativa oculta novos modelos, mas preserva veículos existentes.",
                "Exclusão bloqueada se houver modelos ou veículos vinculados.",
                "Logo ou imagem da marca pode ser usada em materiais comerciais.",
                "Código externo (FIPE) facilita importação automatizada de valores.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Modelos e veículos exibem nome atualizado da marca.",
                "Filtros de busca e relatórios refletem alterações.",
                "Novos modelos só podem ser criados para marcas ativas.",
                "Integrações que sincronizam frota recebem identificador atualizado.",
                "Documentos gerados passam a usar nomenclatura corrigida.",
            ],
        ),
    ),
    "frota.modelo": instr(
        "Cadastro de modelos de veículos vinculados à marca, definindo nome comercial, ano-base e "
        "características técnicas esperadas. "
        "Serve como elo entre marca e veículos individuais da frota.",
        (
            "Para que serve",
            [
                "Descrever o modelo comercial do veículo (Gol, Corolla, Compass).",
                "Vincular características técnicas: motor, câmbio, portas, combustível padrão.",
                "Facilitar cadastro rápido de novos veículos a partir do modelo.",
                "Suportar referência FIPE para avaliação e depreciação.",
                "Padronizar descrição em reservas, contratos e manutenção.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cadastro de veículos: seleção de modelo define marca e atributos padrão.",
                "Categorias: modelos podem ser sugeridos para determinada categoria.",
                "Manutenção: peças compatíveis e procedimentos por modelo.",
                "Relatórios: análise de desempenho por modelo na frota.",
                "Comercial: descrição em propostas e confirmações de reserva.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Agiliza inclusão de veículos novos com dados pré-preenchidos.",
                "Relatórios consistentes sem variações de grafia do modelo.",
                "Facilita planejamento de compra com histórico por modelo.",
                "Melhora precisão em cotações de seguro e depreciação.",
                "Operadores identificam rapidamente tipo de veículo nos formulários.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Modelo é único dentro da marca (ex.: Gol 1.0 vs Gol 1.6 podem ser modelos distintos).",
                "Modelo inativo impede novos veículos, mas mantém histórico.",
                "Categoria sugerida pode ser aplicada automaticamente ao cadastrar veículo.",
                "Código FIPE opcional para integração com tabelas de mercado.",
                "Alteração de marca exige revisão de todos os veículos vinculados.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Veículos do modelo exibem descrição atualizada em contratos.",
                "Novos veículos herdam combustível, portas e câmbio configurados.",
                "Relatórios de frota por modelo recalculam totais.",
                "Sugestões de categoria em reservas usam vínculo atualizado.",
                "Alertas de manutenção preventiva podem usar parâmetros do modelo.",
            ],
        ),
    ),
    "frota.combustivel": instr(
        "Cadastro de tipos de combustível utilizados pela frota (gasolina, etanol, flex, diesel, elétrico, híbrido). "
        "Influencia política de devolução, custos operacionais e informações ao cliente.",
        (
            "Para que serve",
            [
                "Classificar veículos e modelos pelo tipo de combustível utilizado.",
                "Definir regras de cobrança por diferença de tanque no check-in.",
                "Calcular custos médios de abastecimento por tipo de combustível.",
                "Informar cliente sobre requisitos de abastecimento na devolução.",
                "Suportar relatórios de frota sustentável (elétricos/híbridos).",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cadastro de veículos e modelos: tipo de combustível padrão.",
                "Checkout/check-in: registro de nível de tanque e cobrança de combustível.",
                "Tarifário: taxa de serviço de combustível ou taxa de abastecimento.",
                "Manutenção: procedimentos específicos por tipo de motor.",
                "Relatórios de custo operacional e consumo.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Cobrança justa e transparente por combustível faltante na devolução.",
                "Cliente recebe orientação clara sobre tipo de combustível correto.",
                "Gestão de custos mais precisa por segmento de frota.",
                "Evita erros operacionais em veículos elétricos ou diesel.",
                "Suporta estratégia de renovação de frota por eficiência energética.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Política de tanque (cheio para cheio, mesmo nível) é definida nos parâmetros gerais.",
                "Preço por litro ou taxa fixa pode ser configurado por tipo de combustível.",
                "Veículos flex aceitam gasolina ou etanol — regra de cobrança deve considerar isso.",
                "Veículos elétricos podem usar unidade kWh em vez de litros.",
                "Combustível inativo impede novos veículos com esse tipo.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Check-in recalcula valor de combustível faltante com preço atualizado.",
                "Novos veículos listam apenas combustíveis ativos.",
                "Contratos e termos de responsabilidade exibem instruções atualizadas.",
                "Relatórios de receita com taxa de combustível refletem alterações.",
                "Integrações de telemetria podem mapear tipo de energia/combustível.",
            ],
        ),
    ),
    "frota.acessorio": instr(
        "Cadastro de acessórios e equipamentos opcionais disponíveis para locação, como GPS, cadeira de bebê, "
        "tag de pedágio, rack de teto e capota. "
        "Permite cobrança adicional e controle de estoque de itens não fixos ao veículo.",
        (
            "Para que serve",
            [
                "Registrar itens extras que podem ser adicionados à locação.",
                "Controlar quantidade disponível e alocada por filial.",
                "Definir preço diário ou fixo por acessório.",
                "Rastrear entrega e devolução no checkout/check-in.",
                "Identificar acessórios fixos no veículo vs itens de estoque compartilhado.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Reservas e contratos: inclusão de acessórios opcionais.",
                "Tarifário: preços e taxas vinculadas a cada acessório.",
                "Checkout/check-in: conferência de entrega e devolução.",
                "Financeiro: cobrança como item adicional na fatura.",
                "Relatórios de receita por acessório e taxa de utilização.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Receita adicional organizada e mensurável por tipo de acessório.",
                "Evita prometer item indisponível em reserva.",
                "Controle de perdas e avarias em equipamentos de alto valor.",
                "Cliente visualiza opções claras na cotação.",
                "Operação sabe exatamente o que entregar na retirada.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Estoque limitado: reserva bloqueia quantidade até checkout ou cancelamento.",
                "Acessório pode ser cobrado por diária ou valor único por locação.",
                "Item obrigatório (ex.: tag) pode ser incluído automaticamente por categoria.",
                "Multa por não devolução ou avaria segue regras do contrato.",
                "Acessório inativo não aparece em novas reservas.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Cotações e reservas exibem preço e disponibilidade atualizados.",
                "Contratos em elaboração recalculam total se preço mudar.",
                "Checklist de checkout inclui ou remove acessórios conforme status.",
                "Relatórios de receita acessória refletem alterações imediatas.",
                "Estoque por filial é redistribuído se filial de origem mudar.",
            ],
        ),
    ),
    "frota.documento": instr(
        "Controle de documentos obrigatórios de cada veículo, como CRLV, licenciamento, seguro, "
        "inspeção veicular e autorizações especiais. "
        "Garante conformidade legal antes de liberar o veículo para locação.",
        (
            "Para que serve",
            [
                "Registrar vencimentos e arquivos de documentos veiculares.",
                "Alertar operadores sobre documentos próximos ao vencimento ou vencidos.",
                "Bloquear ou alertar locação de veículo com pendência documental.",
                "Armazenar comprovantes digitais para auditoria e fiscalização.",
                "Rastrear histórico de renovações por veículo.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cadastro de veículos: aba ou seção de documentação vinculada.",
                "Checkout: validação de documentos antes da entrega.",
                "Alertas e dashboard: veículos com documento vencendo.",
                "Manutenção e despachante: workflow de renovação.",
                "Relatórios de conformidade da frota.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Evita multas e apreensões por documentação irregular.",
                "Reduz risco legal de operar veículo sem seguro ou licenciamento.",
                "Planejamento antecipado de renovações com alertas automáticos.",
                "Auditoria facilitada com arquivos centralizados.",
                "Operação confiante ao entregar veículo regularizado ao cliente.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "Documento vencido pode bloquear alocação conforme parâmetro do sistema.",
                "Alertas são disparados X dias antes do vencimento (configurável).",
                "Tipos de documento são definidos em tabela auxiliar padronizada.",
                "Upload de arquivo suporta PDF e imagens para consulta rápida.",
                "Renovação gera novo registro mantendo histórico do anterior.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Status do veículo pode mudar para indisponível se documento crítico vencer.",
                "Mapa de disponibilidade exclui veículos bloqueados por documentação.",
                "Alertas no dashboard são atualizados ou resolvidos.",
                "Checkout impede ou alerta conforme gravidade da pendência.",
                "Relatórios de conformidade recalculam percentual de frota regular.",
            ],
        ),
    ),
    "frota.telemetria": instr(
        "Configuração de dispositivos de telemetria e rastreamento instalados nos veículos, "
        "integrando dados de localização, velocidade, ignição e quilometragem em tempo real ou periódico. "
        "Amplia controle operacional e segurança da frota locada.",
        (
            "Para que serve",
            [
                "Vincular dispositivo de rastreamento (ID/chip) ao veículo.",
                "Receber KM, posição e eventos (ignição, cerca eletrônica) automaticamente.",
                "Detectar uso indevido ou desvio de rota durante locação.",
                "Complementar check-in com KM telemetria vs KM informada.",
                "Suportar recuperação em caso de furto ou apropriação indébita.",
            ],
        ),
        (
            "Onde se conecta no sistema",
            [
                "Cadastro de veículos: identificador do dispositivo de telemetria.",
                "Contratos ativos: monitoramento durante período de locação.",
                "Checkout/check-in: conferência de KM reportada vs odômetro físico.",
                "Alertas operacionais: eventos críticos em tempo real.",
                "Relatórios de utilização e comportamento de condução.",
            ],
        ),
        (
            "Benefícios de cadastrar corretamente",
            [
                "Reduz fraude de quilometragem na devolução.",
                "Localização rápida do veículo em caso de atraso ou emergência.",
                "Dados objetivos para cobrança de KM excedente.",
                "Maior segurança patrimonial da frota.",
                "Histórico de rotas para disputas ou investigação de multas.",
            ],
        ),
        (
            "Lógica e regras importantes",
            [
                "ID do dispositivo deve ser único e corresponder ao equipamento físico instalado.",
                "Integração depende de provedor configurado (API, webhook ou importação).",
                "Divergência grande entre KM telemetria e odômetro gera alerta operacional.",
                "Telemetria inativa não bloqueia locação, mas desativa monitoramento.",
                "Privacidade: monitoramento ativo deve constar no contrato com cliente.",
            ],
        ),
        (
            "O que é afetado ao salvar",
            [
                "Integração passa a enviar/receber dados para o veículo vinculado.",
                "Alertas de evento passam a notificar operadores configurados.",
                "Check-in pode sugerir KM com base na última leitura telemetria.",
                "Relatórios de frota incluem status de conectividade do dispositivo.",
                "Troca de dispositivo exige atualização para não perder rastreamento.",
            ],
        ),
    ),
}
