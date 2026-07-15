# Especificação Funcional Completa — Sistema de Locação de Veículos (ERP Locadora)

**Versão:** 1.0
**Objetivo do documento:** servir de especificação de referência para implementação (Cursor) de TODOS os menus do painel, com regras de negócio, modelos de dados (campos principais), fluxos, estados, permissões, integrações e emissões em PDF/relatórios.

## 0.1 Stack confirmada (Fase 0 — Fundação)

- Python 3.12, FastAPI (API + painel SSR no mesmo app)
- Gunicorn + Uvicorn (produção)
- Pydantic / pydantic-settings
- Starlette (sessão, middlewares, estáticos)
- Jinja2 + HTMX + Alpine.js (sem React/Vue/Next)
- PostgreSQL 16 + Row-Level Security (RLS), SQLAlchemy 2.0 async (asyncpg), Alembic, psycopg (sync)
- Redis 7 (cache/broker)
- Celery + Celery Beat (jobs, automações, geração assíncrona de PDF/relatórios)
- bcrypt, PyJWT, sessão por cookie + CSRF, RBAC próprio
- Cloudflare R2 via boto3 (armazenamento de arquivos: PDFs, XMLs, fotos, documentos)
- Docker + Docker Compose, Nginx, Easypanel
- Clean Architecture / DDD / SOLID, Repository + Service + Unit of Work
- Multitenant (`tenant_id`) + Multifilial (`filial_id`), RLS aplicando isolamento por tenant em toda tabela de negócio
- Duas superfícies: Web HTML (SSR) + API `/api/v1` (mesmas regras de negócio, camada de serviço compartilhada)

## 0.2 Convenções gerais válidas para TODOS os módulos abaixo

Estas regras são transversais e não serão repetidas em cada módulo, mas se aplicam a todos:

1. **Multitenant/Multifilial**: toda entidade de negócio tem `tenant_id` (RLS) e, quando aplicável, `filial_id`. Listagens são filtráveis por filial; usuário pode ter acesso a 1 ou N filiais.
2. **Auditoria automática**: toda tabela de negócio possui `created_at`, `created_by`, `updated_at`, `updated_by`, e nunca é deletada fisicamente por padrão — usa `soft delete` (`deleted_at`, `deleted_by`) exceto onde explicitamente indicado. Toda alteração relevante gera evento na Trilha de Auditoria (módulo 15).
3. **Numeração sequencial por tenant/filial**: contratos, reservas, OS, propostas, notas etc. têm numeração própria sequencial (`RES-2026-000123`, `CT-2026-000045`), configurável em Parâmetros.
4. **Anexos**: qualquer entidade com documentos (CNH, CRLV, contrato assinado, foto de avaria) armazena arquivo no R2 e mantém metadados (nome, tipo, tamanho, hash, usuário que subiu, data).
5. **Emissão de PDF**: motor único de geração de PDF (ver seção 16 — Motor de Relatórios/PDF) usado por todos os módulos. Toda emissão gera registro em log de emissões, pode ser reemitida, e é assíncrona via Celery quando o relatório é pesado (Celery gera, salva no R2, notifica usuário / HTMX poll).
6. **Status/workflow**: todo processo com ciclo de vida (reserva, contrato, OS, proposta, NF) tem máquina de estados explícita, transições validadas no Service Layer, e histórico de mudança de status gravado.
7. **Permissões**: cada menu/submenu = 1 ou mais `permission keys` (ex.: `frota.veiculos.view`, `frota.veiculos.edit`, `financeiro.contas_pagar.aprovar`). RBAC por papel (módulo 14 — Papéis e Permissões), granularidade CRUD + ações especiais (aprovar, cancelar, estornar, emitir).
8. **Busca e filtros**: toda listagem tem busca textual server-side (HTMX), filtros persistentes por sessão, paginação, export (CSV/PDF/XLSX quando fizer sentido).
9. **Notificações**: eventos de negócio (reserva confirmada, contrato vencendo, manutenção agendada, boleto vencido) disparam notificações (in-app + e-mail + opcional WhatsApp via integração) geridas pelo módulo de Automações.
10. **Soft-delete com dependência**: exclusão só permitida se não houver vínculo ativo; caso contrário, sistema oferece "inativar" em vez de excluir.
---

# 1. DASHBOARD

**Objetivo:** visão executiva consolidada, ponto de entrada do sistema.

**Widgets/KPIs (cada um com filtro de período e filial):**
- Frota: total de veículos, % locados, % disponíveis, % em manutenção, % bloqueados/sinistro.
- Ocupação: taxa de ocupação da frota (locados/disponíveis), gráfico últimos 30/90 dias.
- Reservas: reservas do dia, próximas 48h (check-outs previstos), reservas pendentes de confirmação.
- Locações ativas: contratos vigentes, contratos vencendo em 24/48h (renovação ou devolução).
- Financeiro: faturamento do dia/mês, contas a receber em aberto/vencidas, contas a pagar em aberto/vencidas, saldo de caixa consolidado por filial.
- Manutenção: OS abertas, veículos com preventiva vencida/próxima, veículos com pneus a trocar.
- Alertas críticos (lista acionável): documentação de veículo vencendo (CRLV, seguro, licenciamento), CNH de motorista vencendo, contrato sem check-in registrado, multa não vinculada, NF-e rejeitada pela SEFAZ.
- Comercial: funil de vendas resumido (propostas em aberto por estágio), taxa de conversão do mês.
- Atalhos rápidos: Nova Reserva, Novo Contrato, Novo Cliente, Nova OS.

**Dados/Modelo:** Dashboard não persiste dados próprios; é camada de agregação (queries otimizadas/materialized views atualizadas por Celery Beat a cada X minutos, configurável).

**Permissão:** `dashboard.view`, com widgets condicionados às permissões do usuário nos módulos de origem (ex.: usuário sem acesso a Financeiro não vê KPIs financeiros).

---

# 2. CADASTROS

## 2.1 Clientes

**Objetivo:** cadastro único de clientes PF/PJ que locam veículos.

**Campos principais:**
- Tipo: PF ou PJ
- PF: nome completo, CPF, RG, data nascimento, estado civil, profissão
- PJ: razão social, nome fantasia, CNPJ, IE, representante legal
- Contato: e-mails (múltiplos), telefones (múltiplos, com WhatsApp flag)
- Endereços (múltiplos: residencial/cobrança/entrega), CEP com autopreenchimento (integração ViaCEP)
- Dados de CNH (se PF também for motorista) — ou vínculo com registro em Motoristas
- Classificação: categoria de cliente (Varejo, Corporativo, Frota, Turismo), tabela de tarifa padrão, limite de crédito
- Dados bancários (para estorno/reembolso)
- Score de crédito (interno + integração externa — módulo 12.3)
- Status: Ativo, Inativo, Bloqueado (inadimplência, restrição)
- Documentos anexos: CNH digitalizada, comprovante de residência, contrato social (PJ)
- Histórico consolidado: reservas, contratos, faturas, multas, avarias causadas

**Regras de negócio:**
- Validação de CPF/CNPJ (dígito verificador) e consulta opcional em Receita Federal via integração.
- Bloqueio automático por inadimplência (regra configurável em Automações: X dias de atraso → bloqueia novas reservas).
- Blacklist: cliente pode ser marcado com restrição (ex.: sinistro anterior, fraude) impedindo nova locação sem aprovação manual.
- Duplicidade: sistema alerta se CPF/CNPJ já cadastrado.
- Cliente PJ pode ter múltiplos condutores autorizados vinculados (motoristas).

**Relatórios/PDF:** ficha cadastral do cliente, extrato de relacionamento (todas locações), declaração de quitação.

**Permissões:** `cadastros.clientes.*` (view/create/edit/delete/bloquear).

## 2.2 Motoristas

**Objetivo:** cadastro de condutores habilitados a dirigir veículos da frota (podem ser o próprio cliente, condutor autorizado de PJ, ou motorista da locadora/parceiro).

**Campos principais:**
- Vínculo: Cliente (condutor autorizado), Funcionário, ou Terceiro
- Dados pessoais + CNH: número, categoria (A/B/AB/etc.), data de emissão, validade, órgão emissor
- Foto da CNH (frente/verso), CNH Digital (QRCode opcional)
- Situação: Regular, Vencida, Suspensa, Cassada
- Pontuação/CNH (opcional, integração DETRAN — módulo 12.2)
- Histórico de multas como condutor

**Regras de negócio:**
- Bloqueio de vínculo a contrato se CNH vencida/suspensa/categoria incompatível com o veículo.
- Alerta automático 30/15/7 dias antes do vencimento da CNH (Automações).
- Consulta periódica de pontuação/situação via integração DETRAN (job agendado).

**Relatórios:** ficha do motorista, histórico de infrações.

**Permissões:** `cadastros.motoristas.*`.

## 2.3 Parceiros

**Objetivo:** cadastro de parceiros comerciais (agências de turismo, imobiliárias de frota, marketplaces, franqueados, revendedores que geram reservas/indicações).

**Campos principais:**
- Razão social/CNPJ ou nome/CPF, tipo de parceria (Indicação, White-label, Franquia, Marketplace)
- Comissão: percentual ou valor fixo por reserva/contrato fechado, regra de cálculo
- Tabela de tarifa específica do parceiro (vínculo com Tarifário)
- Dados bancários para repasse de comissão
- Contrato de parceria (documento anexo, vigência)
- API Key própria (se parceiro integra via API Pública — módulo 12.5)

**Regras de negócio:**
- Toda reserva/contrato originado por um parceiro é marcado com `parceiro_id`, gerando lançamento de comissão a pagar (Financeiro > Contas a Pagar) automático na confirmação/encerramento do contrato.
- Relatório de performance por parceiro (conversão, ticket médio, comissão gerada).

**Relatórios:** extrato de comissões, contrato de parceria em PDF.

**Permissões:** `cadastros.parceiros.*`.

## 2.4 Fornecedores

**Objetivo:** cadastro de fornecedores de bens/serviços (oficinas, peças, seguradoras, postos, guincho, locadoras parceiras para subcontratação, fornecedores de veículos/frota).

**Campos principais:**
- Razão social/CNPJ, categoria de fornecimento (Peças, Serviço de Manutenção, Seguro, Combustível, Pneus, Rastreador/Telemetria, Financeiro/Banco, Outros)
- Contato, endereço, dados bancários (para pagamento)
- Condições comerciais: prazo de pagamento padrão, desconto negociado
- Avaliação/rating interno (histórico de qualidade/prazo)

**Regras de negócio:**
- Vínculo direto com Manutenção (OS) e Financeiro (Contas a Pagar).
- Bloqueio de fornecedor inadimplente/inativo para novas OS.

**Relatórios:** ficha do fornecedor, extrato de compras/pagamentos.

**Permissões:** `cadastros.fornecedores.*`.

## 2.5 Vendedores

**Objetivo:** cadastro de vendedores/atendentes internos vinculados a metas comerciais e comissionamento (distinto de Usuários do sistema, embora normalmente vinculado a um `usuario_id`).

**Campos principais:**
- Nome, vínculo com Usuário do sistema, filial de atuação
- Meta mensal (quantidade de contratos e/ou valor faturado)
- Regra de comissão (percentual sobre faturamento, escalonado por meta atingida)
- Ranking/performance

**Regras de negócio:**
- Toda proposta/reserva/contrato registra `vendedor_id` (auto-preenchido pelo usuário logado, editável por supervisor).
- Cálculo automático de comissão mensal (Celery Beat, fecha no fim do mês) gerando lançamento em Contas a Pagar.

**Relatórios:** ranking de vendedores, extrato de comissão, acompanhamento de meta.

**Permissões:** `cadastros.vendedores.*`.

## 2.6 Tabelas Auxiliares

**Objetivo:** cadastros genéricos de apoio (domínios) usados como listas de seleção em todo o sistema, evitando hardcode.

**Itens tipicamente gerenciados aqui:**
- Estados civis, profissões, bancos, tipos de documento
- Motivos de cancelamento, motivos de bloqueio, motivos de avaria
- Cores de veículo, tipos de combustível (link com 3.5), tipos de acessório (link com 3.6)
- Feriados (para cálculo de diária/SLA)
- Unidades de medida, moedas (se multi-moeda futuramente)

**Modelo:** estrutura genérica `TabelaAuxiliar (grupo, codigo, descricao, ativo, ordem)` — CRUD único e reutilizável, versus criar 20 telas distintas. Cada "grupo" é parametrizável e pode ser estendido sem migration.

**Regras de negócio:**
- Itens em uso não podem ser excluídos, apenas inativados.
- Alguns grupos são "protegidos" (criados pelo sistema, não deletáveis, ex.: status de contrato).

**Permissões:** `cadastros.tabelas_auxiliares.*` (tipicamente restrito a admin).
---

# 3. FROTA

## 3.1 Veículos

**Objetivo:** núcleo do sistema — cadastro e ciclo de vida de cada veículo.

**Campos principais:**
- Identificação: placa, RENAVAM, chassi, ano fabricação/modelo, cor, categoria, marca, modelo, combustível
- Aquisição: data de compra, fornecedor, valor de aquisição, forma (própria, consórcio, financiada, terceirizada/afiliada), km inicial
- Situação atual (status operacional — ver máquina de estados abaixo)
- Filial/pátio onde está localizado
- Km atual (atualizado por check-in/check-out e telemetria)
- Acessórios instalados (vínculo com 3.6)
- Documentação vinculada (vínculo com 3.7): CRLV, seguro, IPVA, licenciamento
- Rastreador/telemetria vinculado (vínculo com 3.8)
- Grupo de tarifa/categoria de precificação (vínculo com Tarifário)
- Fotos do veículo (múltiplas, com data — usadas para comparação em check-out/check-in)
- Valor FIPE (atualização periódica via integração), valor de mercado interno
- Proprietário real (frota própria vs. veículo de terceiro/afiliado com repasse — para modelo de locação com parceiros donos de carro)

**Máquina de estados (status operacional):**
`Disponível → Reservado → Locado → Em Manutenção → Bloqueado (sinistro/judicial) → Baixado (venda/sinistro total)`
- Transições validadas: um veículo só entra em "Locado" via check-out de contrato; só volta a "Disponível" via check-in aprovado; só vai a "Em Manutenção" com OS aberta vinculada; "Baixado" é estado final (não retorna, exceto correção administrativa com permissão especial + auditoria).

**Regras de negócio:**
- Veículo com documentação vencida (seguro, licenciamento) fica automaticamente sinalizado como "Restrito" — impede nova reserva/check-out até regularização, salvo override com permissão + justificativa.
- Km e combustível registrados obrigatoriamente em toda troca de estado (check-in/check-out/manutenção).
- Histórico completo por veículo: todas as locações, OS, avarias, multas, custos totais (TCO) e receita gerada (para relatório de rentabilidade por veículo).
- Depreciação/valor contábil (campo calculado, opcional, para relatório gerencial).

**Relatórios/PDF:** ficha técnica do veículo, laudo de vistoria, histórico completo (linha do tempo), relatório de rentabilidade individual.

**Permissões:** `frota.veiculos.*` (+ `frota.veiculos.baixar`, `frota.veiculos.bloquear`).

## 3.2 Categorias

**Objetivo:** agrupamento de veículos por categoria comercial (Econômico, Compacto, SUV, Executivo, Utilitário, Blindado etc.) — base para tarifação e busca de disponibilidade.

**Campos:** nome, descrição, capacidade (passageiros/porta-malas), transmissão típica, imagem ilustrativa, ordem de exibição, grupo tarifário padrão.

**Regras:** categoria é referência obrigatória do Veículo e chave de busca em Reservas/Disponibilidade.

**Permissões:** `frota.categorias.*`.

## 3.3 Marcas

**Objetivo:** cadastro de montadoras/marcas (Fiat, Chevrolet, Toyota...).

**Campos:** nome, logo (opcional), país de origem.

**Permissões:** `frota.marcas.*`.

## 3.4 Modelos

**Objetivo:** cadastro de modelos vinculados a marca (Onix, Corolla, HB20...), com variações de versão/motorização.

**Campos:** marca (FK), nome do modelo, versão, motorização, câmbio, nº de portas, capacidade de tanque, categoria padrão sugerida, ficha técnica (consumo médio km/l, opcional integração FIPE).

**Regras:** modelo é referência do Veículo; permite relatórios agregados por modelo (ex.: custo de manutenção médio por modelo).

**Permissões:** `frota.modelos.*`.

## 3.5 Combustíveis

**Objetivo:** tabela de tipos de combustível (Gasolina, Etanol, Flex, Diesel, GNV, Elétrico, Híbrido) usada em Veículo e para regra de cobrança de combustível no check-in/check-out.

**Campos:** nome, unidade de medida, preço de referência atual (para cálculo de cobrança de "tanque não reabastecido"), atualizável manual ou via integração de preço de combustível.

**Permissões:** `frota.combustiveis.*`.

## 3.6 Acessórios

**Objetivo:** catálogo de acessórios/itens opcionais que podem ser vinculados ao veículo e/ou vendidos como opcional em contrato (cadeirinha infantil, GPS, Wi-Fi, rack de teto, corrente de neve, bebê conforto).

**Campos:** nome, descrição, tipo (fixo no veículo x avulso locável), valor de locação por diária, estoque disponível (para os avulsos), foto.

**Regras de negócio:**
- Acessórios "fixos" pertencem ao veículo (checados no check-out/check-in, gera avaria se faltar/danificado).
- Acessórios "avulsos" têm controle de estoque próprio e são adicionados ao contrato como item de cobrança (integra com Tarifário > Taxas e Encargos).

**Permissões:** `frota.acessorios.*`.

## 3.7 Documentação

**Objetivo:** controle centralizado de documentos obrigatórios por veículo com vigência (CRLV, Seguro Obrigatório/Apólice, Licenciamento anual, Vistoria, Autorização de transporte se aplicável).

**Campos:** veículo (FK), tipo de documento, número, órgão emissor, data emissão, data validade, arquivo anexo (PDF/imagem), status (Regular/A vencer/Vencido).

**Regras de negócio:**
- Job diário (Celery Beat) varre vencimentos e dispara alertas em 30/15/7/1 dia(s) antes (Automações + notificações).
- Documento vencido muda automaticamente o status do veículo para "Restrito" (integração com 3.1).
- Renovação gera novo registro versionado, mantendo histórico.

**Relatórios:** relatório de vencimentos (próximos 30/60/90 dias), certidão de regularidade da frota.

**Permissões:** `frota.documentacao.*`.

## 3.8 Telemetria

**Objetivo:** integração com rastreadores/telemetria veicular (GPS, telemetria de condução, bloqueio remoto) — tela de configuração e monitoramento (execução real via integração externa, módulo 12.4).

**Campos:** veículo (FK), fabricante/provedor do rastreador, ID do equipamento, status de conexão (online/offline/sem sinal), última posição conhecida (lat/long, timestamp), km via telemetria, eventos (excesso de velocidade, cerca eletrônica/geofence, colisão detectada, bloqueio ativado).

**Regras de negócio:**
- Sincronização periódica via job Celery consumindo API do provedor (módulo 12.4).
- Divergência entre km informado no check-in/check-out e km da telemetria gera alerta de auditoria.
- Geofence: veículo saindo de área permitida sem contrato ativo dispara alerta crítico.

**Relatórios:** mapa de localização da frota (tela interativa), relatório de uso/quilometragem por telemetria, relatório de eventos de condução (para score de risco do motorista).

**Permissões:** `frota.telemetria.*`.
---

# 4. MANUTENÇÃO

## 4.1 Ordens de Serviço (OS)

**Objetivo:** documento central que orquestra qualquer intervenção no veículo (entidade "mãe"; Preventiva e Corretiva são tipos/origens de OS, não módulos isolados de dados).

**Campos principais:**
- Número da OS (sequencial), veículo (FK), tipo (Preventiva, Corretiva, Sinistro, Recall, Estética/Higienização)
- Origem: manual, gerada automaticamente por plano preventivo (km/tempo), gerada por avaria de check-in
- Fornecedor/oficina executante (interna ou externa — FK Fornecedores)
- Status: `Aberta → Aguardando Peça → Em Execução → Aguardando Aprovação → Concluída → Cancelada`
- Itens de serviço (mão de obra) e itens de peça (vínculo com 4.4 Peças/Estoque), cada um com valor
- Km do veículo na entrada/saída da oficina
- Datas: abertura, previsão de conclusão, conclusão real
- Custo total (peças + mão de obra), autorização de custo (alçada de aprovação se acima de valor configurado)
- Garantia do serviço (prazo/km)
- Fotos antes/depois

**Regras de negócio:**
- Ao abrir OS, veículo muda automaticamente para status "Em Manutenção" (bloqueando novas reservas para aquele período).
- Ao concluir OS, veículo retorna a "Disponível" (ou ao status anterior, se havia contrato pausado) e km é atualizado na ficha do veículo.
- OS acima de valor-limite (parametrizável) exige aprovação de gestor antes de execução (workflow de aprovação — integra com Automações).
- Toda OS concluída gera lançamento automático em Contas a Pagar (para fornecedor externo) e baixa de estoque (peças usadas, internas).
- Custos da OS alimentam o cálculo de TCO/rentabilidade do veículo (relatório gerencial).

**Relatórios/PDF:** Ordem de Serviço impressa (para oficina), relatório de custo de manutenção por veículo/período/fornecedor.

**Permissões:** `manutencao.os.*` (+ `manutencao.os.aprovar`).

## 4.2 Preventiva

**Objetivo:** planos de manutenção preventiva por modelo/categoria (revisões programadas por km ou tempo), gerando OS automaticamente.

**Campos:** plano (nome), modelo/categoria aplicável, gatilho (a cada X km OU a cada Y meses, o que ocorrer primeiro), checklist de itens da revisão (óleo, filtros, correias, freios...), fornecedor sugerido, custo estimado.

**Regras de negócio:**
- Job diário compara km atual (telemetria/check-in) e data da última preventiva de cada veículo contra o plano vinculado; ao atingir 90% do gatilho, gera alerta; ao atingir 100%, gera OS automaticamente com status "Aberta" (parametrizável: automático vs. sugestão para aprovação manual).
- Tela lista "próximas preventivas" ordenadas por urgência (km restante / dias restantes).

**Relatórios:** cronograma de preventivas (próximos 30/60/90 dias), aderência ao plano (% cumprido no prazo).

**Permissões:** `manutencao.preventiva.*`.

## 4.3 Corretiva

**Objetivo:** tela de gestão focada nas OS do tipo Corretiva (reparo por quebra/defeito/sinistro/avaria identificada em check-in), com foco em causa raiz e recorrência.

**Campos adicionais em relação à OS padrão:** causa (peça/uso/acidente/desgaste natural), vínculo com Avaria (módulo 6.7) ou Sinistro, responsabilização (cliente/seguro/locadora) — usado para decidir cobrança ao cliente.

**Regras de negócio:**
- Corretiva vinculada a avaria de check-in pode gerar cobrança automática ao cliente (integra com Financeiro > Contas a Receber) conforme regra de responsabilidade definida no laudo.
- Relatório de recorrência: mesmo veículo/modelo com múltiplas corretivas do mesmo tipo em período curto → alerta de possível defeito de série ou mau uso.

**Permissões:** `manutencao.corretiva.*`.

## 4.4 Peças / Estoque

**Objetivo:** controle de estoque de peças e insumos usados nas OS (multi-almoxarifado por filial).

**Campos:** peça (código, nome, categoria, unidade), fornecedor(es) homologado(s), estoque atual por filial, estoque mínimo/máximo, custo médio, localização física no almoxarifado.

**Movimentações:** Entrada (compra — vínculo Contas a Pagar), Saída (uso em OS), Ajuste (inventário), Transferência entre filiais.

**Regras de negócio:**
- Baixa automática de estoque ao vincular peça a uma OS concluída.
- Alerta de estoque mínimo dispara sugestão de compra (Automações).
- Curva ABC de peças (relatório) para priorizar negociação com fornecedores.

**Relatórios:** posição de estoque, movimentação por período, curva ABC, peças mais usadas por modelo de veículo.

**Permissões:** `manutencao.pecas.*`.

## 4.5 Pneus

**Objetivo:** controle específico do ciclo de vida de pneus (item de alto custo e giro, tratado à parte do estoque genérico).

**Campos:** pneu (identificação/número de fogo, marca, modelo, medida), veículo atual (posição: DD, DE, TD, TE, estepe), km de instalação, km atual, vida útil estimada (km), histórico de rodízio, status (Novo, Em uso, Recapado, Descartado).

**Regras de negócio:**
- Alerta de troca ao atingir % da vida útil estimada ou por sulco mínimo informado em inspeção.
- Rodízio programável (a cada X km) gera tarefa/OS.
- Vinculação a check-in/check-out para registrar desgaste percebido/avaria de pneu.

**Relatórios:** vida útil por pneu/veículo, custo de pneus por km rodado (indicador de eficiência).

**Permissões:** `manutencao.pneus.*`.
---

# 5. RESERVAS

## 5.1 Nova Reserva

**Objetivo:** wizard de criação de reserva (também é o ponto de entrada usado pelo Website/API Pública — módulo 12.5).

**Fluxo (wizard):**
1. Período (data/hora retirada e devolução) + local de retirada/devolução (filial ou endereço de entrega, se houver serviço de entrega).
2. Busca de disponibilidade (consulta módulo 5.4) por categoria/veículo, exibindo preço já calculado pelo Tarifário (tabela + temporada + taxas).
3. Seleção de categoria (ou veículo específico, se "garantido").
4. Seleção de cliente (buscar existente ou cadastrar rápido — mini-form).
5. Seleção de motorista(s)/condutor(es).
6. Opcionais: proteções (módulo 7.4), acessórios (3.6), taxas extras (7.3) — recalcula valor total em tempo real (HTMX).
7. Cupom de desconto (opcional — módulo 6.4).
8. Forma de pagamento prevista, política de cancelamento aplicável (exibida e aceita).
9. Confirmação → gera registro de Reserva + envia PDF de confirmação por e-mail (módulo 16).

**Regras de negócio:**
- Validação de disponibilidade real (lock otimista/pessimista para evitar overbooking em concorrência).
- Reserva pode ser "Garantida" (veículo específico alocado) ou "Por categoria" (qualquer veículo da categoria, definido no check-out).
- Reserva de cliente bloqueado/inadimplente exige aprovação manual.

**Permissões:** `reservas.criar`.

## 5.2 Reservas (listagem/gestão)

**Objetivo:** gestão de todas as reservas existentes.

**Campos da entidade Reserva:** número, cliente, motorista(s), veículo/categoria, data/hora retirada e devolução previstas, local retirada/devolução, valor total estimado, forma de pagamento prevista, origem (Balcão, Website, App, Parceiro, Telefone), vendedor/parceiro, status.

**Máquina de estados:** `Pendente → Confirmada → Check-out Realizado (vira Contrato/Locação) → Concluída` | `Cancelada` | `No-show` (cliente não compareceu).

**Regras de negócio:**
- Ao confirmar, veículo (se garantido) muda para "Reservado".
- No-show automático: job identifica reservas confirmadas cuja hora de retirada passou X horas sem check-out e sem contato — marca como No-show e libera veículo, aplicando política de cancelamento (possível retenção de caução/taxa).
- Cancelamento aplica regra da Política de Cancelamento vigente (módulo 7.5) — pode gerar multa/retenção.
- Reserva confirmada gera bloqueio de disponibilidade do veículo/categoria para o período (módulo 5.3/5.4).

**Relatórios/PDF:** confirmação de reserva (PDF/e-mail), voucher de reserva, relatório de reservas por período/status/origem/canal.

**Permissões:** `reservas.*` (+ `reservas.cancelar`, `reservas.aprovar_bloqueado`).

## 5.3 Calendário

**Objetivo:** visão de calendário (dia/semana/mês) das reservas e locações, por veículo ou por categoria, estilo "gantt"/agenda.

**Funcionalidades:**
- Arrastar-e-soltar (drag&drop via Alpine/HTMX) para realocar reserva a outro veículo, com validação de conflito.
- Cores por status (Pendente, Confirmada, Em andamento, Atrasada).
- Filtro por filial, categoria, veículo.

**Permissões:** `reservas.calendario.view`.

## 5.4 Disponibilidade

**Objetivo:** motor de consulta de disponibilidade — usado por Nova Reserva, Website e API Pública.

**Lógica:**
- Para um período (data/hora início-fim) e filial, calcula veículos livres = Frota ativa da filial − (veículos com Reserva Confirmada/Contrato ativo sobrepondo o período) − (veículos em Manutenção/Bloqueado no período).
- Retorna disponibilidade agregada por categoria (quantidade livre) e, opcionalmente, veículo específico.
- Considera tempo de buffer entre locações (ex.: 2h para limpeza/vistoria, parametrizável).

**Regras de negócio:**
- Overbooking controlado: parâmetro permite vender N% acima da frota física por categoria (aposta em cancelamentos), configurável em Parâmetros — usar com cautela, exibir alerta ao operador.

**Permissões:** `reservas.disponibilidade.view` (endpoint também exposto via API Pública para o site).

## 5.5 Cotações

**Objetivo:** simulação de preço sem compromisso (não bloqueia disponibilidade nem gera obrigação), usada por atendimento ou pelo site para "calcule sua diária".

**Campos:** mesmos parâmetros de busca de Nova Reserva, mas gera apenas um registro de Cotação com valor calculado e validade (ex.: 24h), sem reservar veículo.

**Regras de negócio:**
- Cotação pode ser convertida em Reserva com 1 clique (reaproveita dados).
- Cotações não convertidas alimentam funil de vendas (módulo 6.1) como leads para follow-up.

**Relatórios:** PDF de cotação/orçamento para envio ao cliente.

**Permissões:** `reservas.cotacoes.*`.
---

# 6. LOCAÇÕES

## 6.1 Contratos

**Objetivo:** entidade central da operação — o contrato de locação, gerado a partir de uma Reserva (ou criado diretamente no balcão sem reserva prévia).

**Campos principais:**
- Número do contrato, reserva de origem (opcional), cliente, motorista(s) autorizados, veículo, filial de retirada/devolução
- Período contratado (previsto) x período real (check-out/check-in)
- Valor: diária base, dias, subtotal, proteções, acessórios, taxas, descontos/cupom, caução, total
- Forma de pagamento, condição (à vista, cartão recorrente, faturado PJ)
- Cláusulas/política de cancelamento e de combustível aplicadas (snapshot do texto vigente no momento — imutável após assinatura, para valor jurídico)
- Assinatura: digital (desenho/certificado) ou física escaneada, anexo do PDF assinado
- Status (ver máquina de estados)

**Máquina de estados:** `Rascunho → Aguardando Check-out → Ativo (em vigência) → Aguardando Check-in → Encerrado` | `Cancelado`
- "Ativo" só é atingido após Check-out (6.2) concluído. "Encerrado" só após Check-in (6.3) concluído e financeiro quitado (ou faturado, conforme condição comercial).

**Regras de negócio:**
- Contrato gerado automaticamente ao concluir Check-out de uma Reserva confirmada, ou manualmente (locação de balcão sem reserva).
- Snapshot de tarifa/política no momento da assinatura (não deve mudar retroativamente se a tabela de preço mudar depois).
- Geração automática do PDF do contrato assinável (módulo 16) e envio para assinatura (link) ou impressão.
- Ao ativar, veículo muda para "Locado"; ao encerrar, volta a "Disponível" (após checklist de check-in).
- Contrato pode ter aditivos (renovação — 6.4) sem gerar novo número, apenas versão.

**Relatórios/PDF:** contrato completo, termo de responsabilidade, recibo de caução.

**Permissões:** `locacoes.contratos.*` (+ `locacoes.contratos.cancelar`).

## 6.2 Check-out

**Objetivo:** processo operacional de entrega do veículo ao cliente (retirada), transformando Reserva/Contrato Rascunho em Contrato Ativo.

**Fluxo:**
1. Conferência de documentos: CNH do(s) motorista(s) válida, contrato social/procuração se PJ.
2. Vistoria de saída: checklist do estado do veículo (carroceria — diagrama clicável marcando avarias existentes), nível de combustível, km atual, itens/acessórios presentes, fotos (mínimo N fotos obrigatórias: frente/trás/laterais/interior/painel km).
3. Conferência de pagamento/caução (pré-autorização de cartão ou depósito — integra Financeiro/Pagamentos).
4. Assinatura do cliente (contrato + termo de vistoria) — tablet/touch ou link remoto.
5. Emissão do contrato em PDF e envio automático por e-mail/WhatsApp.

**Regras de negócio:**
- Não permite concluir check-out se: documentação do veículo vencida, motorista sem CNH válida, pagamento/caução não confirmados (salvo override com permissão).
- Vistoria de saída é a baseline comparada no check-in (6.3) para apuração de novas avarias.
- Ao concluir: veículo → "Locado", Reserva → "Check-out Realizado", Contrato → "Ativo".

**Permissões:** `locacoes.checkout.*`.

## 6.3 Check-in

**Objetivo:** processo de devolução do veículo, encerrando (ou permitindo renovar) o contrato.

**Fluxo:**
1. Vistoria de entrada: mesmo checklist do check-out, comparado automaticamente (diff visual) com a vistoria de saída.
2. Registro de km final e combustível final → cálculo automático de km rodado e cobrança de combustível faltante (regra: tabela cheia/cheia, ou cobrança por litro faltante conforme política).
3. Identificação de avarias novas → gera registro em Avarias (6.7) com laudo/fotos, decide responsabilidade (cliente/seguro/desgaste natural) e pode gerar OS corretiva (4.3) + cobrança (Contas a Receber).
4. Apuração de excedentes: km excedente (se plano limitado), atraso na devolução (cobrança de hora/diária extra), multas de trânsito pendentes ainda não recebidas (fica pendente para vinculação — 6.6).
5. Fechamento financeiro do contrato: soma valor previsto + ajustes (combustível, km excedente, atraso, avarias) − caução devolvida = valor final; gera fatura/cobrança complementar se houver saldo devedor, ou estorno se houver crédito.
6. Emissão do recibo/termo de devolução em PDF.

**Regras de negócio:**
- Ao concluir: veículo → "Disponível" (ou "Em Manutenção" se avaria grave detectada), Contrato → "Encerrado".
- Se houver pendência financeira, contrato pode ficar "Encerrado com Pendência" até quitação — cliente pode ser bloqueado para nova reserva (integração 2.1).

**Relatórios/PDF:** termo de devolução/check-in, laudo de vistoria comparativo, fatura final do contrato.

**Permissões:** `locacoes.checkin.*`.

## 6.4 Renovações

**Objetivo:** estender o período de um contrato ativo sem encerrá-lo (aditivo).

**Fluxo:**
- Solicitação (pelo cliente via app/site ou pelo atendente), verificação de disponibilidade do mesmo veículo para o novo período (se outro cliente já reservou o veículo em seguida, bloqueia ou sugere troca de veículo), recálculo de valor (aplicando tarifa vigente para o período extra, podendo haver tabela específica de renovação), aprovação (automática se dentro de regras, ou manual), gera aditivo vinculado ao contrato original (mesmo número, nova versão) e atualiza data prevista de devolução.

**Regras de negócio:**
- Renovação bloqueada se veículo tiver reserva futura conflitante, cliente inadimplente, ou documentação vencida.
- Cada renovação gera novo registro no histórico do contrato (rastreável) e pode exigir novo pagamento/pré-autorização.

**Relatórios:** aditivo contratual em PDF.

**Permissões:** `locacoes.renovacoes.*`.

## 6.5 Encerramentos

**Objetivo:** tela de gestão consolidada de contratos encerrados (histórico) e de encerramentos pendentes de regularização financeira ("Encerrado com Pendência"), separada da operação de Check-in para fins de acompanhamento gerencial/cobrança.

**Funcionalidades:** listagem de contratos encerrados com filtro por pendência financeira, tempo médio de regularização, ação de "reabrir" (com permissão elevada + auditoria) em caso de erro operacional.

**Relatórios:** relatório de encerramentos por período, contratos com pendência em aberto.

**Permissões:** `locacoes.encerramentos.*` (+ `locacoes.encerramentos.reabrir`).

## 6.6 Multas e Infrações

**Objetivo:** gestão de multas de trânsito recebidas (via integração DETRAN — 12.2, ou lançamento manual do órgão autuador) e seu repasse/cobrança ao cliente responsável pelo período da infração.

**Campos:** veículo (FK), data/hora da infração, órgão autuador, código de infração, valor, pontuação, AIT (auto de infração), status (Recebida → Vinculada ao Contrato → Notificado Condutor → Paga → Contestada), contrato/cliente vinculado (identificado pela data/hora da infração cruzada com período de contratos daquele veículo).

**Regras de negócio:**
- Vinculação automática: sistema cruza data/hora da infração com o(s) contrato(s) daquele veículo vigentes na data, sugerindo o cliente responsável (confirmação manual se houver ambiguidade, ex.: troca de condutor no mesmo dia).
- Indicação de condutor: gera automaticamente documento de "Identificação de Condutor Infrator" (formulário DETRAN) em PDF pré-preenchido para envio ao órgão, transferindo a responsabilidade/pontuação ao cliente.
- Cobrança ao cliente: gera lançamento em Contas a Receber (valor da multa + taxa administrativa configurável).
- Multa sem contrato vinculado (veículo estava com a locadora/sem locação) fica sob responsabilidade da empresa.

**Relatórios:** relatório de multas por veículo/cliente/período, formulário de indicação de condutor.

**Permissões:** `locacoes.multas.*`.

## 6.7 Avarias

**Objetivo:** cadastro e gestão do ciclo de vida de avarias/danos identificados em vistorias (check-out, check-in, ou inspeção avulsa/sinistro).

**Campos:** veículo (FK), contrato vinculado, tipo de origem (Check-in, Check-out, Sinistro, Inspeção Avulsa), localização no diagrama do veículo (mapa clicável: para-choque diant., porta esq., etc.), severidade (Leve/Média/Grave), fotos (múltiplas, com timestamp/geolocalização), laudo descritivo, responsabilidade (Cliente/Seguro/Desgaste Natural/Locadora), valor do reparo (vínculo com OS 4.3), status (Registrada → Em Análise → Responsabilidade Definida → OS Gerada → Cobrança Gerada → Encerrada).

**Regras de negócio:**
- Avaria grave detectada no check-in bloqueia automaticamente o veículo (→ "Em Manutenção"/"Bloqueado") impedindo nova reserva até vistoria/reparo.
- Ao definir responsabilidade "Cliente", gera cobrança automática em Contas a Receber; se "Seguro", abre processo de sinistro (pode integrar com seguradora — Fornecedores/Integrações futuras).
- Comparação automática entre fotos de check-out e check-in auxilia (visualmente, lado a lado) na identificação de nova avaria — decisão final é sempre humana (atendente confirma).

**Relatórios/PDF:** laudo de avaria com fotos, relatório de avarias por veículo/cliente/período, relatório de responsabilização (quanto foi cobrado x quanto ficou com a empresa).

**Permissões:** `locacoes.avarias.*`.
---

# 7. COMERCIAL / CRM

## 7.1 Funil de Vendas

**Objetivo:** pipeline visual (kanban, drag&drop) de oportunidades — desde Cotação/Lead até Contrato fechado ou perda.

**Estágios (configuráveis):** Lead/Novo Contato → Qualificação → Cotação Enviada → Negociação → Fechado/Ganho (vira Contrato) → Perdido (com motivo).

**Campos:** origem do lead (Site, Telefone, Indicação, Parceiro, Redes Sociais), vendedor responsável, valor estimado, data prevista de fechamento, histórico de interações (notas/ligações/e-mails registrados).

**Regras de negócio:**
- Cotações não convertidas (5.5) entram automaticamente no funil como oportunidade.
- Cada mudança de estágio registra timestamp (para cálculo de tempo médio por estágio e taxa de conversão).
- Alertas de oportunidade "parada" há X dias sem interação (Automações).

**Relatórios:** funil consolidado, taxa de conversão por vendedor/origem, motivos de perda.

**Permissões:** `comercial.funil.*`.

## 7.2 Propostas

**Objetivo:** documento comercial formal (orçamento detalhado) enviado ao cliente antes do fechamento, especialmente para clientes corporativos/frota (locação de múltiplos veículos, contratos longos).

**Campos:** cliente, itens (veículo/categoria, quantidade, período, valores), condições comerciais, validade da proposta, status (Rascunho → Enviada → Visualizada [tracking] → Aceita → Recusada → Expirada).

**Regras de negócio:**
- Proposta aceita gera automaticamente Reserva(s)/Contrato(s) correspondentes.
- Versionamento: proposta pode ser revisada mantendo histórico de versões anteriores.

**Relatórios/PDF:** proposta comercial formatada (com logo, condições, assinatura).

**Permissões:** `comercial.propostas.*`.

## 7.3 Campanhas

**Objetivo:** gestão de campanhas promocionais/marketing (períodos de desconto, campanhas sazonais, e-mail marketing para base de clientes).

**Campos:** nome, período de vigência, público-alvo (segmentação: todos, categoria de cliente, clientes inativos há X dias), regra de desconto aplicada (vínculo com Tarifário ou Cupons), canal (E-mail, SMS, WhatsApp, Site), métricas (enviados, abertos, convertidos).

**Regras de negócio:**
- Disparo de campanha via Celery (fila de envio), respeitando opt-out/LGPD.
- Métricas de conversão cruzam com Reservas/Contratos gerados na vigência da campanha.

**Relatórios:** performance de campanha (ROI, taxa de conversão).

**Permissões:** `comercial.campanhas.*`.

## 7.4 Cupons

**Objetivo:** códigos de desconto aplicáveis em Reservas/Propostas (autoatendimento site ou uso interno pelo atendente).

**Campos:** código, tipo de desconto (percentual/valor fixo), regras de elegibilidade (categoria de veículo, valor mínimo, primeira locação, período de uso), limite de uso (total e por cliente), validade, status (Ativo/Expirado/Esgotado).

**Regras de negócio:**
- Validação em tempo real na Nova Reserva (5.1) e no Website (via API Pública).
- Cupom vinculado a Parceiro/Campanha para rastrear origem do desconto.

**Relatórios:** relatório de uso de cupons, desconto total concedido por período/cupom.

**Permissões:** `comercial.cupons.*`.

## 7.5 Fidelidade

**Objetivo:** programa de pontos/benefícios para clientes recorrentes.

**Campos:** regra de acúmulo (X pontos por R$ locado ou por diária), regra de resgate (desconto, upgrade de categoria, diária grátis), tiers/níveis (Bronze/Prata/Ouro com benefícios crescentes), extrato de pontos por cliente (créditos/débitos com origem em cada contrato).

**Regras de negócio:**
- Pontuação creditada automaticamente ao encerrar contrato (Check-in) sem pendência financeira.
- Resgate aplicável diretamente na Nova Reserva como forma de desconto/pagamento parcial.
- Expiração de pontos (configurável, ex.: 12 meses) via job.

**Relatórios:** extrato de fidelidade, ranking de clientes por pontos/tier.

**Permissões:** `comercial.fidelidade.*`.

---

# 8. TARIFÁRIO

## 8.1 Tabelas de Tarifas

**Objetivo:** núcleo de precificação — define o valor da diária por categoria/veículo, por filial, por canal (balcão x site x parceiro), por faixa de duração (diária, semanal, mensal com desconto progressivo).

**Campos:** nome da tabela, vigência (data início/fim), filial(is) aplicável(is), canal aplicável, por categoria: valor diária 1-3 dias, 4-7 dias, 8-15 dias, 16-30 dias, mensal (faixas configuráveis), regra de km (livre/limitado + valor km excedente).

**Regras de negócio:**
- Apenas uma tabela "vigente" por combinação filial+categoria+canal em um dado momento (validação de sobreposição).
- Tabela pode ser específica de Parceiro (2.3) ou Cliente/Categoria de cliente (2.1) — hierarquia de prioridade: Tabela do Cliente > Tabela do Parceiro > Tabela da Campanha > Tabela padrão da filial/canal.
- Motor de cálculo é um serviço único (`PricingService`) consumido por Nova Reserva, Cotação, Website/API, Renovação — garante consistência.

**Relatórios:** simulação de tarifa, comparativo de tabelas.

**Permissões:** `tarifario.tabelas.*`.

## 8.2 Temporadas

**Objetivo:** ajustes de tarifa por período sazonal (alta temporada, feriados, eventos) — multiplicador ou tabela específica que sobrepõe a tabela padrão.

**Campos:** nome (ex.: "Réveillon 2027"), data início/fim, tipo de ajuste (percentual sobre tabela base, valor fixo, ou tabela alternativa completa), categorias/filiais afetadas, estadia mínima (regra comum em alta temporada, ex.: mínimo 3 diárias).

**Regras de negócio:**
- Aplicado automaticamente pelo `PricingService` quando o período da reserva intersecta a temporada.
- Múltiplas temporadas sobrepostas: usa prioridade configurável ou a de maior especificidade (filial+categoria específica vence regra geral).

**Permissões:** `tarifario.temporadas.*`.

## 8.3 Taxas e Encargos

**Objetivo:** cadastro de taxas adicionais cobráveis (taxa de retirada em outra filial/one-way, taxa de entrega/busca, taxa de condutor adicional, taxa de menor de idade, taxa administrativa de multa, taxa de limpeza extraordinária, combustível faltante).

**Campos:** nome, tipo de cálculo (valor fixo, percentual sobre contrato, por dia, por ocorrência), aplicação (automática por regra x opcional selecionável), tributável (impacta módulo Fiscal) sim/não.

**Regras de negócio:**
- Taxas "automáticas" são aplicadas pelo `PricingService` conforme condição (ex.: retirada ≠ devolução → taxa one-way automática).
- Taxas "opcionais" aparecem como checkbox no wizard de reserva/contrato.

**Permissões:** `tarifario.taxas.*`.

## 8.4 Proteções

**Objetivo:** cadastro dos seguros/proteções oferecidos (LDW - Isenção de Danos, TP - Proteção Terceiros, Proteção Vidros/Pneus, Cobertura Total), vendidos como opcional na reserva/contrato.

**Campos:** nome, descrição/cobertura, valor por diária, franquia (valor que o cliente ainda paga mesmo com a proteção em caso de sinistro), fornecedor/seguradora (FK Fornecedores, se terceirizado), regras de exclusão (o que não cobre).

**Regras de negócio:**
- Proteção contratada reduz (ou zera) a cobrança de avaria em Check-in (6.7) até o limite da franquia.
- Pode ser obrigatória para certas categorias (ex.: veículos de luxo exigem proteção mínima).

**Relatórios:** taxa de adesão de proteção (conversão), sinistralidade por proteção.

**Permissões:** `tarifario.protecoes.*`.

## 8.5 Políticas de Cancelamento

**Objetivo:** regras que definem penalidade/retenção em caso de cancelamento de reserva ou no-show, aplicadas automaticamente.

**Campos:** nome, faixas de antecedência (ex.: >72h = sem multa; 24-72h = retém 20%; <24h/no-show = retém 100% ou 1 diária), aplicável a quais canais/tabelas.

**Regras de negócio:**
- Snapshot da política vigente é gravado na Reserva/Contrato no momento da criação (não muda retroativamente).
- Motor de cancelamento (5.2) consulta esta política para calcular automaticamente o valor retido/estornado.

**Permissões:** `tarifario.politicas_cancelamento.*`.
---

# 9. FINANCEIRO

## 9.1 Caixa

**Objetivo:** controle de caixa físico/operacional por filial (recebimentos e pequenos pagamentos no balcão).

**Campos:** sessão de caixa (abertura/fechamento por operador/turno), valor de abertura (fundo de troco), lançamentos (entradas/saídas com categoria e forma), valor de fechamento informado x valor calculado (divergência sinalizada).

**Regras de negócio:**
- Abertura/fechamento obrigatórios por turno/usuário; fechamento gera relatório de conferência (sangria, suprimento, diferença).
- Todo recebimento de contrato no balcão (Check-out/Check-in) pode lançar automaticamente no caixa aberto do operador.

**Relatórios/PDF:** relatório de fechamento de caixa, extrato de movimentação.

**Permissões:** `financeiro.caixa.*` (+ `financeiro.caixa.abrir`, `financeiro.caixa.fechar`).

## 9.2 Contas a Receber

**Objetivo:** gestão de todos os valores a receber de clientes (contratos, multas repassadas, avarias cobradas, faturamento PJ).

**Campos:** título (origem: Contrato/Multa/Avaria/Avulso), cliente, valor, vencimento, forma de recebimento prevista, status (Em Aberto → Vencido → Pago Parcial → Pago → Cancelado/Estornado), parcelamento (se aplicável), boleto/link de pagamento vinculado (integração 12.1).

**Regras de negócio:**
- Geração automática a partir de: encerramento de contrato com saldo devedor, multa vinculada a cliente, avaria com responsabilidade do cliente, faturamento mensal PJ (consolidação de vários contratos em uma fatura única — 9.8).
- Régua de cobrança automatizada (Automações): notificação em D-3, D0, D+1, D+7 de atraso; bloqueio de cliente (2.1) configurável por dias de atraso.
- Baixa automática via webhook do gateway de pagamento (12.1) ou conciliação bancária (9.7).

**Relatórios/PDF:** boleto, fatura, recibo de pagamento, relatório de inadimplência, aging (0-30/31-60/61-90/90+).

**Permissões:** `financeiro.contas_receber.*` (+ `.estornar`, `.baixar_manual`).

## 9.3 Contas a Pagar

**Objetivo:** gestão de obrigações a pagar (fornecedores, OS de manutenção, comissões de vendedores/parceiros, folha/serviços administrativos).

**Campos:** título (origem: OS/Fornecedor/Comissão/Avulso), fornecedor/beneficiário, valor, vencimento, status (Em Aberto → Vencido → Pago Parcial → Pago → Cancelado), forma de pagamento (PIX, Boleto, TED, Cartão), anexo de nota fiscal do fornecedor.

**Regras de negócio:**
- Geração automática a partir de OS concluída (4.1), comissão de vendedor/parceiro fechada no mês (2.3/2.5).
- Alçada de aprovação por valor (workflow de aprovação — Automações) antes de efetivar pagamento.
- Agendamento de pagamento (data futura) com job que dispara o pagamento via integração (12.1) ou apenas lembrete.

**Relatórios/PDF:** relatório de contas a pagar por período/fornecedor/status, previsão de desembolso (fluxo de caixa projetado).

**Permissões:** `financeiro.contas_pagar.*` (+ `.aprovar`, `.efetivar_pagamento`).

## 9.4 PIX

**Objetivo:** gestão de cobranças e pagamentos via PIX (cobrança dinâmica/QR Code, chaves cadastradas, conciliação automática).

**Campos:** chave(s) PIX da empresa por filial/conta bancária, cobranças geradas (txid, valor, QR Code, status: Aguardando/Pago/Expirado), pagamentos PIX enviados (contas a pagar).

**Regras de negócio:**
- Cobrança PIX gerada automaticamente a partir de título em Contas a Receber (checkbox "gerar cobrança PIX").
- Webhook de confirmação de pagamento (integração 12.1 — PSP/banco) baixa automaticamente o título.

**Relatórios:** extrato de recebimentos PIX.

**Permissões:** `financeiro.pix.*`.

## 9.5 Cartões

**Objetivo:** gestão de transações de cartão de crédito/débito (cobrança na Reserva/Contrato e pré-autorização de caução).

**Campos:** transação (contrato/título vinculado), gateway utilizado, tipo (Débito/Crédito/Pré-autorização de caução), valor, parcelas, status (Autorizado → Capturado → Liquidado → Cancelado/Estornado), taxa da adquirente (para cálculo de custo efetivo).

**Regras de negócio:**
- Pré-autorização de caução no Check-out (6.2) sem captura imediata; captura (total/parcial) ou cancelamento no Check-in (6.3) conforme apuração final.
- Integração com adquirente/PSP (12.1) para tokenização (nunca armazenar dado de cartão cru — compliance PCI).

**Relatórios:** extrato de transações, taxas pagas às adquirentes por período.

**Permissões:** `financeiro.cartoes.*`.

## 9.6 Bancos

**Objetivo:** cadastro de contas bancárias da empresa e seus extratos.

**Campos:** banco, agência, conta, tipo, saldo atual (calculado), integração (Open Finance/API do banco, se disponível, ou importação manual de OFX/CNAB).

**Relatórios:** extrato bancário, saldo consolidado por filial/conta.

**Permissões:** `financeiro.bancos.*`.

## 9.7 Conciliação

**Objetivo:** conferência entre lançamentos internos (Contas a Receber/Pagar, Caixa, Cartões, PIX) e extratos reais (bancário, adquirente).

**Fluxo:** importação de extrato (OFX/CNAB/API) → matching automático (por valor+data+identificador) → itens conciliados automaticamente vs. pendências para conciliação manual (tela de "arrastar para casar" lançamento com extrato).

**Regras de negócio:** divergências geram alerta para o financeiro tratar (lançamento faltante, duplicidade, valor divergente).

**Relatórios:** relatório de conciliação (conciliado x pendente), divergências.

**Permissões:** `financeiro.conciliacao.*`.

## 9.8 Faturamento

**Objetivo:** consolidação de múltiplos títulos de Contas a Receber em uma única fatura (essencial para clientes PJ/frota com vários contratos no mês) e emissão de fatura periódica recorrente.

**Campos:** cliente, período de referência, títulos incluídos, valor total, data de emissão, data de vencimento, ciclo de faturamento (mensal/quinzenal, dia de fechamento).

**Regras de negócio:**
- Job mensal (Celery Beat) fecha automaticamente o ciclo de faturamento de clientes configurados como "faturado", consolidando os títulos do período em uma fatura única e gerando o respectivo documento fiscal (módulo 10).

**Relatórios/PDF:** fatura consolidada detalhada (um contrato por linha).

**Permissões:** `financeiro.faturamento.*`.

---

# 10. FISCAL

## 10.1 NFS-e (Nota Fiscal de Serviço Eletrônica)

**Objetivo:** emissão da nota fiscal de serviço referente à locação (em muitos municípios, locação de bem móvel é tributada como serviço/ISS) e demais serviços (taxas, seguros administrados pela locadora).

**Campos:** contrato/fatura de origem, tomador (cliente), município de incidência (conforme legislação local), valor do serviço, alíquota ISS, retenções (se aplicável), status (A Emitir → Enviada Prefeitura → Autorizada → Cancelada/Rejeitada), número/série, chave de acesso, link do PDF (DANFSE) e XML.

**Regras de negócio:**
- Emissão automática ao Encerrar contrato/Faturar (configurável: automática ou sob demanda), integrando com o webservice da prefeitura correspondente à filial/município (cada município tem seu próprio provedor — necessário adaptador por município, ver 10.4/12).
- Regras de retenção de impostos (ISS retido pelo tomador PJ, quando aplicável).
- Cancelamento dentro do prazo legal municipal, com justificativa obrigatória.

**Relatórios/PDF:** DANFSE, relatório de notas emitidas por período, apuração de ISS a recolher.

**Permissões:** `fiscal.nfse.*` (+ `.cancelar`).

## 10.2 NF-e (Nota Fiscal Eletrônica — produtos/mercadorias)

**Objetivo:** emissão de NF-e quando aplicável (ex.: venda de veículo baixado da frota, venda de peças/acessórios, transferência de bens entre filiais).

**Campos:** operação (Venda/Transferência/Devolução), destinatário, itens (produto/veículo, NCM, CFOP, valor, impostos ICMS/IPI conforme regime), status (A Emitir → Autorizada SEFAZ → Cancelada/Denegada), chave de acesso, DANFE, XML.

**Regras de negócio:**
- Integração com SEFAZ (via provedor/certificado digital A1, módulo 12) para autorização em tempo real.
- Venda de veículo da frota (baixa em 3.1) pode gerar NF-e automaticamente, vinculando o ativo baixado à nota.

**Relatórios/PDF:** DANFE, relatório de NF-e emitidas/canceladas.

**Permissões:** `fiscal.nfe.*` (+ `.cancelar`).

## 10.3 XML

**Objetivo:** repositório central de todos os XMLs fiscais (emitidos e recebidos de fornecedores), essencial para contabilidade/auditoria.

**Funcionalidades:** upload/importação de XML de fornecedores (para lançamento em Contas a Pagar com dados pré-preenchidos via leitura do XML), download em lote por período (para contador), validação de schema.

**Regras de negócio:** todo XML emitido (10.1/10.2) é automaticamente arquivado aqui com hash/chave, nunca sobrescrito.

**Relatórios:** exportação em lote (ZIP) por período/tipo/filial.

**Permissões:** `fiscal.xml.*`.

## 10.4 Cancelamentos

**Objetivo:** central de gestão de cancelamentos/eventos fiscais (cancelamento dentro do prazo, carta de correção, inutilização de numeração), com trilha de justificativas.

**Campos:** documento fiscal de origem, tipo de evento, motivo, data/hora, protocolo de retorno do órgão, status (Solicitado → Processado → Confirmado/Rejeitado).

**Regras de negócio:** prazo legal de cancelamento validado por tipo de documento/município/UF (parametrizável); fora do prazo, sistema orienta emissão de nota de estorno/carta de correção em vez de cancelamento direto.

**Relatórios:** relatório de cancelamentos por período/motivo.

**Permissões:** `fiscal.cancelamentos.*`.

## 10.5 Impostos

**Objetivo:** parametrização de regimes/alíquotas tributárias da empresa (por filial, já que ISS varia por município) e apuração gerencial.

**Campos:** regime tributário (Simples Nacional/Lucro Presumido/Lucro Real), alíquotas por tipo de serviço/produto/filial, retenções (IRRF, PIS/COFINS/CSLL quando aplicável a PJ tomador), vigência.

**Regras de negócio:** alíquotas usadas pelo motor de emissão (10.1/10.2) no cálculo automático dos impostos de cada documento.

**Relatórios/PDF:** apuração de impostos por período (base para guias — geração da guia em si pode ficar para integração contábil futura), relatório comparativo de carga tributária por filial.

**Permissões:** `fiscal.impostos.*` (tipicamente restrito a admin/financeiro sênior).
---

# 11. RELATÓRIOS

Central única de emissão (usa o Motor de Relatórios/PDF — seção 16). Cada submenu abaixo é uma "categoria" com relatórios pré-definidos + construtor de relatório customizado (filtros dinâmicos, seleção de colunas, agrupamento) quando possível, sempre exportável em PDF e XLSX/CSV.

## 11.1 Frota
- Frota atual (posição por status/filial/categoria), rentabilidade por veículo (receita − custos de manutenção − depreciação), ociosidade/taxa de ocupação por veículo/categoria, TCO (Custo Total de Propriedade) por veículo, idade média da frota, relatório de vencimentos de documentação.

## 11.2 Locação
- Contratos por período/status/filial/vendedor/canal, ticket médio, tempo médio de locação, taxa de renovação, taxa de no-show/cancelamento, ranking de clientes por volume, relatório de avarias e responsabilização, relatório de multas.

## 11.3 Financeiro
- DRE simplificado (receita de locação − custos operacionais − despesas), fluxo de caixa (realizado e projetado), inadimplência/aging, faturamento por filial/categoria/canal, comissões pagas (vendedores/parceiros), conciliação bancária.

## 11.4 Fiscal
- Notas emitidas/canceladas por período, apuração de impostos (ISS/ICMS conforme aplicável), relatório para contabilidade (exportação padronizada), divergências fiscais.

## 11.5 Gerencial
- Painel executivo consolidado (cruza Frota + Locação + Financeiro), comparativo entre filiais, metas x realizado (vendedores), análise de sazonalidade, projeção de demanda (base para decisão de compra/renovação de frota).

**Regras transversais dos Relatórios:**
- Todo relatório pesado roda assíncrono via Celery (fila dedicada `reports`), grava resultado no R2, notifica o usuário quando pronto (evita travar requisição HTTP).
- Relatórios podem ser agendados (recorrência diária/semanal/mensal) com envio automático por e-mail — integra com módulo 13 (Automações).
- Todo relatório gerado fica no "Histórico de Emissões" (reemitir/baixar novamente sem reprocessar, quando cache válido).

**Permissões:** `relatorios.<categoria>.view`, `relatorios.<categoria>.exportar`.

---

# 12. INTEGRAÇÕES

## 12.1 Pagamentos
**Objetivo:** conectores com gateways/adquirentes/PSPs (ex.: cartão, PIX, boleto) — arquitetura de adapter (`PaymentGatewayPort` com implementações por provedor), permitindo trocar/adicionar provedor sem alterar regra de negócio.
**Configuração:** credenciais por filial/conta (armazenadas criptografadas), webhook endpoint único (`/api/v1/webhooks/pagamentos/{provider}`) validando assinatura, mapeamento de eventos (pago/estornado/chargeback) para baixa automática em 9.2/9.4/9.5.
**Permissões:** `integracoes.pagamentos.*`.

## 12.2 Trânsito (DETRAN)
**Objetivo:** consulta de multas, situação de CNH, débitos veiculares (IPVA/licenciamento), consulta de pontuação — via provedor de dados veiculares (webservice estadual ou agregador privado homologado).
**Uso:** alimenta 6.6 (Multas), 2.2 (situação CNH), 3.7 (débitos/documentação).
**Permissões:** `integracoes.transito.*`.

## 12.3 Crédito
**Objetivo:** consulta de score/restrição de clientes (Serasa/SPC ou similar) para decisão de bloqueio/limite de crédito em 2.1, e para aprovação de faturamento PJ.
**Permissões:** `integracoes.credito.*`.

## 12.4 Telemetria
**Objetivo:** conectores com provedores de rastreamento (arquitetura adapter, similar a Pagamentos), consumindo posição/eventos e alimentando 3.8.
**Permissões:** `integracoes.telemetria.*`.

## 12.5 API Pública
**Objetivo:** documentação e gestão da API `/api/v1` exposta a terceiros (Website institucional, App, Parceiros/Marketplaces).
**Funcionalidades:** gestão de API Keys/OAuth por consumidor (com escopo e rate limit), endpoints principais expostos: disponibilidade (5.4), criação de reserva (5.1), consulta de status de contrato, webhook de eventos (reserva confirmada, contrato encerrado) para o site consumir.
**Documentação:** OpenAPI/Swagger gerado automaticamente pelo FastAPI, com página de docs interativa.
**Permissões:** `integracoes.api_publica.*` (gestão das chaves; o uso em si é autenticado por API Key/OAuth próprios do consumidor).

---

# 13. AUTOMAÇÕES

## 13.1 Regras
**Objetivo:** motor de regras de negócio configuráveis sem código (condição → ação), usado por vários módulos citados acima (bloqueio de cliente inadimplente, alerta de documentação, geração de OS preventiva, régua de cobrança).
**Modelo:** `Regra (nome, evento_gatilho, condição [DSL simples ou JSON logic], ação, ativo)`.
**Exemplos de gatilhos:** "contrato encerrado", "documento a vencer em N dias", "título vencido há N dias", "estoque abaixo do mínimo".
**Exemplos de ações:** enviar notificação, gerar tarefa, bloquear cliente/veículo, gerar OS, gerar cobrança.
**Permissões:** `automacoes.regras.*`.

## 13.2 Workflows
**Objetivo:** processos com múltiplas etapas/aprovações (ex.: aprovação de OS acima de valor-limite, aprovação de desconto acima de X%, aprovação de reserva de cliente bloqueado).
**Modelo:** etapas sequenciais/paralelas, aprovador (usuário/papel), SLA por etapa, ação em caso de timeout.
**Permissões:** `automacoes.workflows.*`.

## 13.3 Agendamentos
**Objetivo:** interface de gestão dos jobs recorrentes do Celery Beat (visão administrativa: quais rotinas existem, frequência, última execução, próxima execução, status/erro).
**Exemplos de jobs:** varredura de documentos a vencer, geração de preventivas, fechamento de faturamento mensal, cálculo de comissões, materialização de KPIs do Dashboard, disparo de campanhas agendadas, backup de relatórios agendados.
**Permissões:** `automacoes.agendamentos.*` (execução manual/forçar rodar agora — restrito a admin).

## 13.4 Histórico
**Objetivo:** log de execução de todas as regras/workflows/agendamentos (sucesso/erro, payload, tempo de execução) — essencial para depuração e confiança no sistema automatizado.
**Permissões:** `automacoes.historico.view`.

---

# 14. CONFIGURAÇÕES

## 14.1 Dados da Empresa
**Objetivo:** dados cadastrais do tenant (razão social, CNPJ matriz, logo, certificado digital para NF-e/NFS-e, configurações visuais do painel/PDFs — cor, logo em relatórios).
**Permissões:** `config.empresa.*` (admin).

## 14.2 Filiais / Unidades
**Objetivo:** CRUD de filiais/pátios/unidades operacionais (`filial_id`), cada uma com endereço, município (relevante para ISS), CNPJ próprio (se filial for CNPJ distinto) ou apenas unidade operacional do mesmo CNPJ, horário de funcionamento, numeração de documentos por filial.
**Permissões:** `config.filiais.*`.

## 14.3 Usuários
**Objetivo:** CRUD de usuários do sistema, vínculo com Papel (14.4), vínculo com filial(is) de acesso, status (ativo/inativo/bloqueado), autenticação (2FA opcional), log de acessos.
**Permissões:** `config.usuarios.*`.

## 14.4 Papéis e Permissões
**Objetivo:** RBAC — definição de papéis (Admin, Gerente, Atendente, Financeiro, Mecânico, Vendedor...) e matriz de permissões granular por módulo/ação (todas as `permission keys` citadas ao longo deste documento).
**Regras:** papéis padrão vêm pré-configurados; tenant pode customizar/criar novos papéis; permissões sempre validadas no backend (Service Layer), nunca apenas escondidas na UI.
**Permissões:** `config.papeis.*` (restrito a admin).

## 14.5 Parâmetros
**Objetivo:** central de parametrização de todas as regras configuráveis citadas nos módulos acima (valores-limite de aprovação, dias de alerta de vencimento, regra de overbooking, ciclo de faturamento padrão, política de combustível padrão, prefixos de numeração por documento, tempo de buffer entre locações, dias para bloqueio por inadimplência etc.), organizados por categoria/módulo, com valor padrão e override por filial quando aplicável.
**Permissões:** `config.parametros.*` (restrito a admin).

---

# 15. AUDITORIA

## 15.1 Trilha de Auditoria
**Objetivo:** log imutável de todas as ações relevantes do sistema (quem fez o quê, quando, de onde — IP/dispositivo, valor anterior/novo em alterações).
**Campos:** timestamp, usuário, tenant/filial, entidade afetada, ação (create/update/delete/aprovar/cancelar/emitir/login), diff (JSON before/after), IP, user-agent.
**Regras de negócio:**
- Gravação automática via hook no Service Layer/Unit of Work (não depende do desenvolvedor lembrar de logar em cada endpoint).
- Somente leitura para usuários (mesmo admin não edita/apaga registros de auditoria); retenção mínima configurável (ex.: 5 anos, atendendo legislação).
- Eventos críticos (exclusão, cancelamento de nota fiscal, reabertura de contrato, alteração de permissão) podem disparar notificação em tempo real para admin.
**Relatórios:** trilha filtrável por usuário/entidade/período/ação, exportável para compliance/auditoria externa.
**Permissões:** `auditoria.view` (tipicamente restrito a admin/compliance).
---

# 16. MOTOR DE RELATÓRIOS / EMISSÃO EM PDF (transversal a todos os módulos)

Como o requisito central do usuário é ter **muitas formas de emissão em PDF** e um sistema **funcional, robusto e automatizado**, este motor deve ser construído uma única vez e reutilizado em todo o sistema — evita duplicidade e garante identidade visual consistente.

**Arquitetura sugerida:**
- Camada `ReportService` (Clean Architecture — Application Layer) com interface única: `gerar_pdf(template_id, contexto, sincrono=False)`.
- Templates HTML (Jinja2, reaproveitando o padrão SSR já usado no painel) → renderizados para PDF via engine (ex.: WeasyPrint, que roda 100% Python/Linux sem dependência de browser headless — compatível com Docker leve; alternativa: Playwright/Chromium se precisar de CSS mais avançado, porém mais pesado).
- Templates organizados por família: Documentos Transacionais (contrato, confirmação de reserva, laudo de vistoria, recibo, DANFE/DANFSE) e Relatórios Analíticos (listagens, dashboards impressos).
- Todo PDF gerado é salvo no R2 (`/pdfs/{tenant_id}/{tipo}/{ano}/{mes}/{arquivo}.pdf`), com registro em tabela `documentos_gerados` (tipo, entidade de origem, usuário, timestamp, hash, link).
- Geração síncrona (resposta imediata) para documentos pequenos/transacionais (confirmação de reserva, recibo); geração assíncrona via Celery para relatórios pesados/lote (ex.: relatório gerencial de 500 páginas, faturamento em massa).
- Numeração/série de documentos fiscais (DANFE/DANFSE) segue regras específicas do módulo Fiscal (10), não deste motor genérico.
- Marca d'água/status visual automático (ex.: "CANCELADO", "RASCUNHO") sobreposto no PDF conforme status da entidade de origem.
- Todo template suporta: logo da empresa/filial (14.1), rodapé com dados legais, numeração de página, QR Code opcional (ex.: link de confirmação/validação do documento).
- **Assinatura digital de contrato**: campo de assinatura manuscrita capturada em canvas (Alpine.js) embutida na renderização final do PDF; opcionalmente, integração futura com provedor de assinatura eletrônica com validade jurídica (ICP-Brasil/e-CPF ou plataforma tipo Clicksign/D4Sign) — deixar a porta (`SignatureProviderPort`) desenhada desde já mesmo que a implementação inicial seja "assinatura simples em canvas".

**Lista consolidada de emissões em PDF do sistema (referência única, já detalhadas em cada módulo acima):**
Confirmação de reserva • Voucher de reserva • Cotação/orçamento • Contrato de locação • Termo de vistoria (check-out) • Termo de devolução (check-in) • Recibo de caução • Laudo de avaria • Ordem de Serviço • Ficha técnica do veículo • Relatório de vencimentos de documentação • Boleto/fatura • Recibo de pagamento • Proposta comercial • Formulário de indicação de condutor (multa) • DANFSE • DANFE • Todos os relatórios das seções 11.1–11.5 • Trilha de auditoria (exportação).

**Permissões:** herdadas do módulo de origem; ação de emissão sempre registrada na Trilha de Auditoria (15).

---

# 17. MODELO DE DADOS — ENTIDADES PRINCIPAIS (visão de alto nível para orientar as migrations)

> Lista não-exaustiva das tabelas centrais; cada uma herda `tenant_id`, `filial_id` (onde aplicável), timestamps de auditoria (ver seção 0.2).

`clientes`, `motoristas`, `parceiros`, `fornecedores`, `vendedores`, `tabelas_auxiliares`,
`veiculos`, `categorias`, `marcas`, `modelos`, `combustiveis`, `acessorios`, `veiculo_acessorios`, `documentacao_veiculo`, `telemetria_eventos`,
`ordens_servico`, `os_itens`, `planos_preventivos`, `pecas`, `estoque_movimentos`, `pneus`,
`reservas`, `cotacoes`,
`contratos`, `contrato_vistorias`, `contrato_fotos`, `multas`, `avarias`,
`funil_oportunidades`, `propostas`, `campanhas`, `cupons`, `fidelidade_pontos`,
`tabelas_tarifas`, `temporadas`, `taxas_encargos`, `protecoes`, `politicas_cancelamento`,
`caixa_sessoes`, `caixa_lancamentos`, `contas_receber`, `contas_pagar`, `transacoes_pix`, `transacoes_cartao`, `contas_bancarias`, `conciliacao_itens`, `faturas`,
`nfse`, `nfe`, `xml_arquivos`, `fiscal_eventos`, `impostos_parametros`,
`documentos_gerados` (motor de PDF),
`integracoes_config`, `api_keys`,
`automacao_regras`, `automacao_workflows`, `automacao_jobs_log`,
`empresas` (tenant), `filiais`, `usuarios`, `papeis`, `permissoes`, `papel_permissoes`, `parametros_sistema`,
`auditoria_log`.

---

# 18. ROADMAP SUGERIDO DE IMPLEMENTAÇÃO (para orientar o Cursor, fases incrementais)

1. **Fase 1 — Núcleo cadastral**: Configurações (14) → Cadastros (2) → Frota (3.1–3.7). Sem isso, nada mais funciona.
2. **Fase 2 — Tarifação e Disponibilidade**: Tarifário (8) → Reservas (5). É o motor de precificação/disponibilidade que todo o resto consome.
3. **Fase 3 — Operação de Locação**: Locações (6) completo (Contratos/Check-out/Check-in/Avarias/Multas). Aqui nasce a receita.
4. **Fase 4 — Financeiro básico**: Caixa, Contas a Receber/Pagar, Faturamento (9.1, 9.2, 9.3, 9.8) — sem isso a operação não fecha o ciclo.
5. **Fase 5 — Motor de PDF (16)** deve ser construído já na Fase 3 em paralelo (contrato/vistoria são documentos do dia 1), não deixar para o final.
6. **Fase 6 — Manutenção (4)**: Ordens de Serviço, Preventiva, Peças, Pneus.
7. **Fase 7 — Fiscal (10)**: NFS-e primeiro (locação = serviço na maioria dos municípios), depois NF-e.
8. **Fase 8 — Comercial/CRM (7)**: Funil, Propostas, Campanhas, Cupons, Fidelidade.
9. **Fase 9 — Financeiro avançado**: PIX, Cartões, Bancos, Conciliação (9.4–9.7).
10. **Fase 10 — Integrações (12)** e **Automações (13)**: conectar provedores reais (pagamento, DETRAN, crédito, telemetria) e ativar regras/workflows/jobs que dependem dos módulos anteriores já existirem.
11. **Fase 11 — Relatórios (11) consolidados e Dashboard (1)**: construídos por cima de tudo que já existe (agregações).
12. **Fase 12 — Auditoria (15)** deve ter o *hook* técnico instalado desde a Fase 1 (é transversal), mas a *tela* de consulta pode vir por último.

**Observação final:** este documento é a especificação funcional. Para cada módulo, o próximo passo técnico é: (a) desenhar o schema SQLAlchemy/Alembic, (b) definir os `permission keys`, (c) implementar Repository + Service, (d) expor rotas Web (Jinja2/HTMX) e API (`/api/v1`), (e) implementar os PDFs do módulo via `ReportService`, (f) cobrir com testes automatizados as máquinas de estado (status) de cada entidade, que são o coração da robustez pedida.
