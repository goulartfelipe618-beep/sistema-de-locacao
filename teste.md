# Plano de Testes — Smoke + Regressão E2E — ERP Locadora

**Versão:** 1.0  
**Papel do executor:** Auditor de sistemas sênior / QA manual  
**Escopo:** 100% dos menus, formulários, botões e fluxos integrados do painel web + API pública  
**Ambiente alvo:** `development` local ou Supabase (mesma base de dados do `.env`)

---

## Como usar este documento

1. Execute **cada passo na ordem numérica** — não pule etapas; muitos passos dependem de dados criados antes.
2. Marque cada passo: `[ ]` pendente · `[x]` aprovado · `[!]` falhou (anotar evidência).
3. Use o usuário indicado em cada bloco; troque de login quando solicitado.
4. **Datas dinâmicas:** onde aparecer `D+1`, use amanhã às 10:00; `D+4` = três dias após a retirada, também 10:00 (horário local `America/Sao_Paulo`).
5. Após cada **Critério de Aceite**, se falhar, pare e registre bug antes de continuar (regressão absoluta).

---

## Dados fictícios mestres (referência única)

| Entidade | Valor exato |
|----------|-------------|
| **Admin** | `admin@locadora.local` / `Admin@123` |
| **Vendedor** | `vendedor@locadora.local` / `Vendedor@123` |
| **Operador** | `operador@locadora.local` / `Operador@123` |
| **Financeiro** | `financeiro@locadora.local` / `Financeiro@123` |
| **Diretoria** | `diretoria@locadora.local` / `Diretoria@123` |
| **Filial matriz** | Código `0001` — Matriz — São Paulo/SP |
| **Filial 2 (criar)** | Código `0002` — Filial Campinas — Campinas/SP — CNPJ `44.555.666/0001-77` |
| **Cliente PF** | João Silva Teste · CPF `529.982.247-25` · `joao.teste@email.com` · `(11) 98765-4321` · CEP `01310-100` · Rua Augusta, 1000 · São Paulo/SP |
| **Cliente PJ** | Transportes Beta LTDA · CNPJ `11.444.777/0001-61` · `financeiro@transportesbeta.com` |
| **Motorista** | Carlos Condutor · CPF `390.533.447-05` · CNH `12345678901` · Cat. `B` · Validade = hoje + 730 dias |
| **Parceiro** | Agência Viagem Sul · CNPJ `22.333.444/0001-55` · Comissão 10% · PIX `viagem@sul.com` |
| **Fornecedor** | Oficina Mecânica Norte · CNPJ `33.444.555/0001-66` · Categoria `manutencao` · Prazo 30 dias |
| **Vendedor cadastro** | Pedro Vendas · `pedro.vendas@locadora.local` · Filial Matriz · Meta R$ 50.000 |
| **Marca** | Chevrolet · País `Brasil` |
| **Modelo** | Onix · Versão `1.0` · 4 portas · Tanque 44L |
| **Categoria veículo** | Econômico · 5 passageiros · Grupo tarifário `economico` |
| **Combustível** | Flex · Preço ref. R$ 5,89/L |
| **Veículo A** | Placa `TST1A23` · RENAVAM `12345678901` · Chassi `9BWZZZ377VT004251` · Ano fab/mod `2023/2024` · Cor Prata · Km 15000 |
| **Veículo B** | Placa `TST2B34` (reserva de overbooking) |
| **Acessório** | Cadeirinha Bebê · Avulso · R$ 25/dia · Estoque 5 |
| **Peça** | Código `FILTRO-001` · Filtro de óleo · Unidade `UN` |
| **Pneu** | Nº fogo `PNEU-001` · Michelin · 175/70 R14 |
| **Cupom** | Código `VERAO2026` · 10% · Mínimo R$ 100 |
| **Tabela tarifa** | `Tarifa Padrão Matriz` · Canal `balcao` · Diária 1-3d R$ 120 |
| **Proteção** | LDW Básica · R$ 35/dia · Franquia R$ 1.500 |
| **Taxa** | Taxa entrega · Fixa R$ 45 · Opcional |
| **Política cancelamento** | `Padrão Balcão` · >72h 0% · 24-72h 20% · <24h 100% |

---

# FASE 0 — Pré-requisitos e saúde do sistema

### PASSO 000 — Verificar serviços

| Campo | Detalhe |
|-------|---------|
| **Identificação** | Infraestrutura / Health checks |
| **Permissão** | Nenhuma (pré-login) |
| **Ação** | Abrir navegador em `http://localhost:8000/api/v1/health` (ou URL da VPS). Depois `http://localhost:8000/api/v1/health/ready`. |
| **Validação integração** | JSON `status: ok`; ready confirma PostgreSQL + Redis. |
| **Critério de aceite** | HTTP 200 em ambos; sem timeout. |

### PASSO 001 — Seed do banco

| Campo | Detalhe |
|-------|---------|
| **Identificação** | Script `scripts/seed.py` |
| **Ação** | No terminal: `python -m scripts.seed` |
| **Validação** | Log confirma tenant, filial 0001, admin e usuários demo. |
| **Critério de aceite** | Comando termina exit 0; login admin funciona. |

### PASSO 002 — Login administrador

| Campo | Detalhe |
|-------|---------|
| **Identificação** | Tela `/login` |
| **Permissão** | Pública → sessão autenticada |
| **Dados** | E-mail `admin@locadora.local` · Senha `Admin@123` |
| **Ação** | Clicar **Entrar** |
| **Validação** | Redirect para `/`; menu lateral completo visível. |
| **Critério de aceite** | Nome do usuário no topo; seção Configurações presente. |

---

# FASE 1 — Configurações e permissões (base de tudo)

## 1.1 Dados da Empresa

### PASSO 010 — Editar empresa

| Campo | Detalhe |
|-------|---------|
| **Menu** | Configurações → Dados da Empresa |
| **URL** | `/configuracoes/empresa` |
| **Permissão** | `configuracoes.empresa.visualizar` + editar |
| **Dados** | Razão social `Locadora Matriz LTDA` · Nome fantasia `Locadora Matriz` · E-mail `contato@locadoramatriz.com.br` · Telefone `(11) 3000-0000` · Cor primária `#1a56db` |
| **Ação** | **Salvar alterações** |
| **Validação downstream** | PDFs gerados depois exibem logo/cor; Dashboard mantém tenant. |
| **Critério de aceite** | Mensagem de sucesso; dados persistem após F5. |

## 1.2 Filiais

### PASSO 011 — Listar filial matriz

| Campo | Detalhe |
|-------|---------|
| **Menu** | Configurações → Filiais / Unidades |
| **URL** | `/configuracoes/filiais` |
| **Permissão** | `configuracoes.filial.visualizar` |
| **Ação** | Confirmar linha **0001 — Matriz** |
| **Critério de aceite** | Filial matriz listada como sede. |

### PASSO 012 — Criar filial Campinas

| Campo | Detalhe |
|-------|---------|
| **URL** | `/configuracoes/filiais/nova` |
| **Permissão** | `configuracoes.filial.criar` |
| **Dados** | Código `0002` · Nome `Filial Campinas` · CNPJ `44.555.666/0001-77` · Cidade `Campinas` · UF `SP` · Telefone `(19) 3200-0000` · Desmarcar "sede" |
| **Ação** | **Salvar** |
| **Validação** | Aparece em selects de filial em Reservas, Frota, Financeiro. |
| **Critério de aceite** | Redirect `/configuracoes/filiais`; filial 0002 visível. |

## 1.3 Usuários e papéis

### PASSO 013 — Listar usuários demo

| Campo | Detalhe |
|-------|---------|
| **Menu** | Configurações → Usuários |
| **URL** | `/configuracoes/usuarios` |
| **Permissão** | `identidade.usuario.visualizar` |
| **Ação** | Verificar 5 usuários (admin + 4 demos) |
| **Critério de aceite** | Todos `Ativo`. |

### PASSO 014 — Criar usuário auditor teste

| Campo | Detalhe |
|-------|---------|
| **URL** | `/configuracoes/usuarios/novo` |
| **Dados** | Nome `QA Auditor` · E-mail `qa.auditor@locadora.local` · Senha `QaAuditor@123` · Papel `Auditor (Somente Leitura)` · Filial Matriz |
| **Ação** | **Salvar** |
| **Validação downstream** | Login com este usuário mostra menus restritos (PASSO 900). |
| **Critério de aceite** | Usuário na listagem. |

### PASSO 015 — Papéis e permissões

| Campo | Detalhe |
|-------|---------|
| **Menu** | Configurações → Papéis e Permissões |
| **URL** | `/configuracoes/papeis` |
| **Permissão** | `identidade.papel.visualizar` |
| **Ação** | Abrir papel `Vendedor`; confirmar permissões de reservas/comercial. Repetir visualização para `Operador`, `Financeiro`, `Diretoria`. |
| **Critério de aceite** | 7 papéis sistema listados; slugs corretos. |

## 1.4 Segurança 2FA (smoke)

### PASSO 016 — Tela 2FA (sem ativar)

| Campo | Detalhe |
|-------|---------|
| **Menu** | Configurações → Autenticação 2FA |
| **URL** | `/configuracoes/seguranca` |
| **Permissão** | Qualquer usuário logado |
| **Ação** | Clicar **Iniciar configuração** → ver QR code → **Cancelar/voltar** sem confirmar |
| **Critério de aceite** | QR exibido; 2FA permanece desativado. |

## 1.5 Parâmetros do sistema

### PASSO 017 — Ajustar parâmetros operacionais

| Campo | Detalhe |
|-------|---------|
| **Menu** | Configurações → Parâmetros |
| **URL** | `/configuracoes/parametros` |
| **Permissão** | `configuracoes.parametro.visualizar` |
| **Dados** | Filial: Matriz · `reservas.overbooking_percentual` = `0` · `reservas.buffer_minutos` = `120` · Salvar |
| **Ação** | **Salvar parâmetros** |
| **Validação downstream** | Disponibilidade respeita buffer; overbooking desligado. |
| **Critério de aceite** | URL com `?ok=1`; valores persistem. |

---

# FASE 2 — Cadastros (domínios de negócio)

## 2.1 Tabelas auxiliares (primeiro — outros dependem)

### PASSO 020 — Criar item tabela auxiliar

| Campo | Detalhe |
|-------|---------|
| **Menu** | Cadastros → Tabelas Auxiliares |
| **URL** | `/cadastros/tabelas?grupo=motivo_cancelamento` |
| **Permissão** | `cadastros.tabela.visualizar` |
| **Dados** | Grupo `motivo_cancelamento` · Código `cliente_desistiu` · Descrição `Cliente desistiu` · Ordem `1` |
| **Ação** | **Adicionar** |
| **Critério de aceite** | Item na lista do grupo. |

## 2.2 Clientes

### PASSO 021 — Criar cliente PF

| Campo | Detalhe |
|-------|---------|
| **Menu** | Cadastros → Clientes → **+ Novo** |
| **URL** | `/cadastros/clientes/novo` |
| **Permissão** | `cadastros.cliente.criar` |
| **Dados** | Tipo PF · Nome `João Silva Teste` · CPF `529.982.247-25` · Status Ativo · E-mail `joao.teste@email.com` · Celular `(11) 98765-4321` · CEP `01310-100` · Endereço completo · Limite crédito `5000` |
| **Ação** | **Salvar** |
| **Validação** | Cliente aparece em combobox de Nova Reserva. |
| **Critério de aceite** | Redirect `/cadastros/clientes`; registro pesquisável. |

### PASSO 022 — Criar cliente PJ

| Campo | Detalhe |
|-------|---------|
| **Dados** | Tipo PJ · Razão `Transportes Beta LTDA` · CNPJ `11.444.777/0001-61` · E-mail `financeiro@transportesbeta.com` |
| **Ação** | **Salvar** |
| **Critério de aceite** | Dois clientes na listagem. |

### PASSO 023 — PDFs do cliente PF

| Campo | Detalhe |
|-------|---------|
| **URL** | `/cadastros/clientes/{id_joao}/editar` |
| **Ação** | Clicar **PDF Ficha** → download · **PDF Extrato** → download · **PDF Declaração Quitação** → download |
| **Validação integração** | Documentos → Histórico PDF registra 3 emissões. |
| **Critério de aceite** | 3 PDFs abrem sem erro; histórico atualizado. |

## 2.3 Motoristas

### PASSO 024 — Criar motorista

| Campo | Detalhe |
|-------|---------|
| **Menu** | Cadastros → Motoristas → **+ Novo** |
| **Permissão** | `cadastros.motorista.criar` |
| **Dados** | Nome `Carlos Condutor` · Vínculo `Terceiro` · CPF `390.533.447-05` · CNH `12345678901` · Cat. `B` · Validade +2 anos · Status `Regular` |
| **Ação** | **Salvar** |
| **Validação downstream** | Selecionável em Nova Reserva e Contrato. |
| **Critério de aceite** | Motorista listado. |

## 2.4 Parceiros

### PASSO 025 — Criar parceiro

| Campo | Detalhe |
|-------|---------|
| **Menu** | Cadastros → Parceiros → **+ Novo** |
| **Dados** | PJ · Nome `Agência Viagem Sul` · CNPJ `22.333.444/0001-55` · Tipo `Indicação` · Comissão 10% · PIX `viagem@sul.com` |
| **Ação** | **Salvar** |
| **Critério de aceite** | Parceiro ativo na listagem. |

## 2.5 Fornecedores

### PASSO 026 — Criar fornecedor

| Campo | Detalhe |
|-------|---------|
| **Menu** | Cadastros → Fornecedores → **+ Novo** |
| **Dados** | Nome `Oficina Mecânica Norte` · CNPJ `33.444.555/0001-66` · Categoria manutenção · Prazo pagamento `30` · E-mail `oficina@norte.com` |
| **Ação** | **Salvar** |
| **Validação downstream** | Disponível em OS e Contas a Pagar. |
| **Critério de aceite** | Fornecedor listado. |

## 2.6 Vendedores

### PASSO 027 — Criar vendedor

| Campo | Detalhe |
|-------|---------|
| **Menu** | Cadastros → Vendedores → **+ Novo** |
| **Dados** | Nome `Pedro Vendas` · E-mail `pedro.vendas@locadora.local` · Filial Matriz · Comissão 5% · Meta faturamento `50000` · Meta contratos `20` |
| **Ação** | **Salvar** |
| **Critério de aceite** | Vendedor vinculado à filial Matriz. |

---

# FASE 3 — Frota

## 3.1 Estrutura (marca → modelo → categoria → combustível)

### PASSO 030 — Marca Chevrolet

| Menu | Frota → Marcas → **+ Novo** |
| Dados | Nome `Chevrolet` · País `Brasil` · Status Ativo |
| Ação | **Salvar** |

### PASSO 031 — Modelo Onix

| Menu | Frota → Modelos → **+ Novo** |
| Dados | Marca Chevrolet · Nome `Onix` · Versão `1.0` · Categoria padrão Econômico · Portas `4` · Tanque `44` |
| Ação | **Salvar** |

### PASSO 032 — Categoria Econômico

| Menu | Frota → Categorias → **+ Novo** |
| Dados | Nome `Econômico` · Passageiros `5` · Grupo tarifário `economico` · Ordem `1` |
| Ação | **Salvar** |

### PASSO 033 — Combustível Flex

| Menu | Frota → Combustíveis → **+ Novo** |
| Dados | Nome `Flex` · Unidade `litro` · Preço ref. `5.89` |
| Ação | **Salvar** |

### PASSO 034 — Acessório cadeirinha

| Menu | Frota → Acessórios → **+ Novo** |
| Dados | Nome `Cadeirinha Bebê` · Tipo `avulso` · Valor diária `25` · Estoque `5` |
| Ação | **Salvar** |

## 3.2 Veículos

### PASSO 035 — Veículo TST1A23

| Campo | Detalhe |
|-------|---------|
| **Menu** | Frota → Veículos → **+ Novo** |
| **Dados** | Placa `TST1A23` · RENAVAM `12345678901` · Chassi `9BWZZZ377VT004251` · Anos `2023/2024` · Cor Prata · Marca/Modelo/Categoria/Combustível/Filial Matriz · Propriedade própria · Km atual `15000` · Combustível nível `8` |
| **Ação** | **Salvar** |
| **Validação** | Status inicial `Disponível`; aparece em Disponibilidade. |
| **Critério de aceite** | Veículo na listagem com placa correta. |

### PASSO 036 — Veículo TST2B34 (segundo)

| Dados | Placa `TST2B34` · demais campos iguais ao PASSO 035 |
| **Critério de aceite** | 2 veículos Econômico na Matriz. |

### PASSO 037 — PDF ficha veículo

| Ação | Editar TST1A23 → **PDF Ficha** |
| Validação | Documentos/historico + Frota relatórios futuros. |

## 3.3 Documentação veicular

### PASSO 038 — CRLV veículo A

| Menu | Frota → Documentação → **+ Novo** |
| Dados | Veículo TST1A23 · Tipo `CRLV` · Número `CRLV-2026-001` · Validade = hoje + 365 dias · Status regular |
| Ação | **Salvar** |

### PASSO 039 — PDFs documentação

| Ação | Na listagem: **PDF Vencimentos** · **PDF Certidão Regularidade** |
| Critério | Certidão mostra frota regular (sem vencidos). |

## 3.4 Telemetria

### PASSO 040 — Dispositivo GPS TST1A23

| Menu | Frota → Telemetria → **+ Novo Dispositivo** |
| Dados | Veículo TST1A23 · Provedor `Suntech` · Equipamento `EQ-001` · Status `online` · Lat `-23.5505` · Lng `-46.6333` · Km telemetria `15000` |
| Ação | **Salvar dispositivo** |

### PASSO 041 — Registrar evento

| URL | `/frota/telemetria/{veiculo_id}` |
| Dados | Tipo `excesso_velocidade` · Descrição `Teste auditoria` · Velocidade `95` |
| Ação | **Registrar evento** |

### PASSO 042 — Mapa da frota

| Menu | Frota → Telemetria → **Mapa da Frota** |
| URL | `/frota/telemetria/mapa` |
| Ação | Confirmar pin em São Paulo para TST1A23 |
| Critério | Mapa Leaflet carrega; popup com placa. |

---

# FASE 4 — Tarifário (motor de preço)

### PASSO 050 — Tabela de tarifas

| Menu | Tarifário → Tabelas → **+ Novo** |
| Dados | Nome `Tarifa Padrão Matriz` · Vigência início hoje · Canal `balcao` · Filial Matriz · Item categoria Econômico: 1-3d `120` · 4-7d `110` · 8-15d `100` · Km livre |
| Ação | **Criar tabela** |

### PASSO 051 — Temporada alta

| Menu | Tarifário → Temporadas → **+ Novo** |
| Dados | Nome `Alta Temporada Teste` · Início/fim abrangendo D+1 a D+4 · Ajuste percentual `10%` · Categoria Econômico |
| Ação | **Salvar** |

### PASSO 052 — Taxa entrega

| Menu | Tarifário → Taxas → **+ Novo** |
| Dados | Nome `Taxa entrega` · Cálculo fixo `45` · Aplicação `opcional` |
| Ação | **Salvar** |

### PASSO 053 — Proteção LDW

| Menu | Tarifário → Proteções → **+ Novo** |
| Dados | Nome `LDW Básica` · Valor diária `35` · Franquia `1500` |
| Ação | **Salvar** |

### PASSO 054 — Política cancelamento

| Menu | Tarifário → Cancelamento → **+ Novo** |
| Dados | Nome `Padrão Balcão` · Canal balcão · Faixa 1: >72h retenção 0% · Faixa 2: 24-72h 20% · Faixa 3: <24h 100% |
| Ação | **Salvar** + adicionar faixas |

### PASSO 055 — Simulador de preço

| Menu | Tarifário → Simular Preço |
| Dados | Filial Matriz · Categoria Econômico · Retirada D+1 10:00 · Devolução D+4 10:00 · Canal balcao · Proteção LDW · Taxa entrega |
| Ação | **Calcular cotação** |
| Validação | Total > 0; breakdown exibe diárias + taxas + proteção. |
| Critério | Valor coerente (~3 diárias × tarifa + extras). |

---

# FASE 5 — Manutenção

### PASSO 060 — Peça estoque

| Menu | Manutenção → Peças → **+ Novo** |
| Dados | Código `FILTRO-001` · Nome `Filtro de óleo` · Unidade `UN` · Custo médio `35` |
| Ação | **Salvar** → aba Estoque → Entrada: Filial Matriz · Qtd `10` · Custo `35` |

### PASSO 061 — Plano preventivo

| Menu | Manutenção → Preventiva → **+ Novo** |
| Dados | Nome `Revisão 10.000 km` · Intervalo km `10000` · Intervalo meses `6` · Checklist `Óleo, Filtro` · Automático |
| Ação | **Salvar** → Vincular veículo TST1A23 |

### PASSO 062 — OS corretiva (fluxo completo)

| Menu | Manutenção → Corretiva → **+ Novo** |
| Dados | Veículo TST1A23 · Fornecedor Oficina Norte · Km entrada `15000` · Causa `desgaste` · Responsável `locadora` |
| Ação | **Salvar** → na OS: adicionar item mão de obra `Troca filtro` R$ 80 · peça FILTRO-001 qtd 1 · **Mudar status** → Em Execução → **Concluir** km saída `15001` |
| Validação | Veículo volta `Disponível`; estoque peça -1; Contas a Pagar pode ter título automático. |
| Critério | OS status `Concluída`; **PDF OS** baixa. |

### PASSO 063 — Pneu

| Menu | Manutenção → Pneus → **+ Novo** |
| Dados | Nº fogo `PNEU-001` · Marca `Michelin` · Medida `175/70 R14` · Vida útil km `40000` |
| Ação | **Salvar** → **Instalar** em TST1A23 posição `DD` km `15001` |

---

# FASE 6 — Comercial / CRM (antes das reservas promocionais)

### PASSO 070 — Cupom

| Menu | Comercial → Cupons → **+ Novo** |
| Dados | Código `VERAO2026` · Tipo percentual · Valor `10` · Mínimo `100` · Validade +90 dias · Limite total `100` |
| Ação | **Salvar Cupom** |

### PASSO 071 — Funil — nova oportunidade

| Menu | Comercial → Funil → **+ Nova Oportunidade** |
| Dados | Título `Locação fim de semana` · Cliente João Silva · Vendedor Pedro · Valor estimado `500` · Origem `Telefone` |
| Ação | Salvar → abrir card → **Mover** para `Qualificação` → **Registrar Interação** tipo ligação |

### PASSO 072 — Proposta comercial

| Menu | Comercial → Propostas → **+ Nova** |
| Dados | Cliente Transportes Beta · Validade +15 dias · Item: Categoria Econômico · Qtd 2 · 30 dias · Valor unit. `110` |
| Ação | **Salvar** → **Enviar** → **PDF Proposta** |

### PASSO 073 — Campanha

| Menu | Comercial → Campanhas → **+ Nova** |
| Dados | Nome `Promo Verão` · Canal e-mail · Público todos · Desconto 5% · Início hoje · Fim +30 dias |
| Ação | **Salvar** → **Ativar** → **Disparar** (simulador) |

### PASSO 074 — Fidelidade

| Menu | Comercial → Fidelidade |
| Dados | Regra: 10 pontos/diária · 100 pontos = R$ 10 · Tier Bronze 0 pts |
| Ação | **Salvar Regra** · **+ Adicionar Tier** |

---

# FASE 7 — Reservas (fluxo operacional principal)

### PASSO 080 — Consultar disponibilidade

| Menu | Reservas → Disponibilidade |
| Dados | Filial Matriz · D+1 10:00 → D+4 10:00 · Categoria Econômico |
| Critério | Mostra ≥1 veículo livre (TST1A23/TST2B34). |

### PASSO 081 — Cotação

| Menu | Reservas → Cotações → **+ Novo** |
| Dados | Mesmas datas · Cliente João · Categoria Econômico · Canal balcão · Validade 24h |
| Ação | **Simular preço** → **Salvar cotação** → **PDF** → **Converter em reserva** (forma pagamento `cartao`) |
| Validação | Funil CRM pode ter oportunidade ligada; cotação status convertida. |
| Critério | Redirect reserva criada. |

### PASSO 082 — Nova reserva manual (segunda reserva)

| Menu | Reservas → Nova Reserva |
| Dados | Filial Matriz retirada/devolução · D+5 10:00 → D+8 10:00 · Origem balcão · Categoria Econômico · Veículo TST2B34 garantido · Cliente João · Motorista Carlos · Proteção LDW · Cupom `VERAO2026` · Pagamento `pix` |
| Ação | **Criar reserva (pendente)** |
| Validação | Preview HTMX de preço antes de salvar; cupom aplicado. |
| Critério | Reserva status `Pendente`; número RES- gerado. |

### PASSO 083 — Confirmar reserva

| URL | `/reservas/{id}` |
| Ação | **Confirmar** |
| Validação | Veículo TST2B34 → status `Reservado`; calendário mostra bloco. |
| Critério | Status `Confirmada`. |

### PASSO 084 — Calendário

| Menu | Reservas → Calendário |
| Ação | Filtrar filial Matriz · localizar reserva · (opcional) **Realocar** para TST1A23 se TST2B34 conflitar — validar alerta de conflito |
| Critério | Eventos coloridos por status visíveis. |

### PASSO 085 — PDFs reserva

| Ação | **PDF Confirmação** · **PDF Voucher** |
| Validação | Documentos/historico. |

### PASSO 086 — Gerar contrato da reserva

| Ação | **Gerar contrato** |
| Validação | Redirect `/locacoes/contratos/{id}`; contrato `Aguardando Check-out`. |
| Critério | Contrato vinculado à reserva. |

---

# FASE 8 — Locações (contrato → check-out → check-in → encerramento)

### PASSO 090 — Contrato balcão (sem reserva)

| Menu | Locações → Contratos → **+ Novo** |
| Dados | Cliente PJ Transportes Beta · TST1A23 · D+10 → D+13 · Motorista Carlos · Caução `800` · Forma `faturado` |
| Ação | **Criar contrato** |
| Critério | Contrato `Rascunho` ou `Aguardando Check-out`. |

### PASSO 091 — Check-out completo

| Menu | Locações → Check-out → selecionar contrato da reserva (PASSO 086) |
| Dados | Km `15200` · Combustível `8` · Checklist linhas: `Pneus OK` / `Documentos OK` · Fotos: preencher keys fictícias `foto/frente.jpg` etc. · Marcar **Caução confirmada** · Desenhar **assinatura** no canvas |
| Ação | **Concluir check-out** |
| Validação | Contrato `Ativo`; veículo `Locado`; reserva `Check-out Realizado`; assinatura no PDF contrato. |
| Critério | Redirect detalhe contrato com checkout_em preenchido. |

### PASSO 092 — PDFs contrato pós-checkout

| Ação | **PDF Contrato** · **PDF Termo Responsabilidade** · **PDF Vistoria Saída** · **PDF Recibo Caução** |
| Critério | Assinatura visível no PDF contrato/termo. |

### PASSO 093 — Renovação (aditivo)

| Menu | Locações → Renovações |
| Dados | Contrato ativo do PASSO 086 · Nova devolução = devolução original + 2 dias |
| Ação | **Preview** → **Confirmar renovação** |
| Validação | Aditivo na ficha contrato · **PDF Aditivo** · devolução_prevista_em atualizada. |
| Critério | Versão contrato incrementada. |

### PASSO 094 — Multa de trânsito

| Menu | Locações → Multas → **+ Novo** |
| Dados | Veículo TST2B34 · AIT `AIT-2026-99999` · Código `745-5` · Órgão `DETRAN-SP` · Data/hora durante contrato ativo · Valor `195.23` · Taxa admin `30` |
| Ação | **Salvar** → **Vincular** ao contrato → **Notificado** → **PDF Condutor** |
| Validação | Contas a Receber pode receber título; dashboard alertas. |
| Critério | Status `Vinculada` / `Notificado`. |

### PASSO 095 — Avaria

| Menu | Locações → Avarias → **+ Novo** |
| Dados | Veículo TST2B34 · Contrato ativo · Origem `checkin` · Localização `Para-choque traseiro` · Severidade `leve` · Valor reparo `350` |
| Ação | **Salvar** → **Responsabilidade** = `cliente` → **Gerar OS** → **Encerrar** · **PDF Laudo** |
| Validação | OS corretiva criada; título a receber possível. |
| Critério | Avaria status `Encerrada`. |

### PASSO 096 — Check-in e encerramento

| Menu | Locações → Check-in → contrato PASSO 086 |
| Dados | Km entrada `15450` · Combustível `6` · Atraso `0` · Km excedente `0` · Caução retida `0` · Caução devolvida `800` · Checklist e fotos · (opcional) avaria leve no formulário |
| Ação | **Concluir check-in** |
| Validação | Contrato `Encerrado`; veículo `Disponível`; financeiro gera saldo; fidelidade pontua cliente. |
| Critério | checkin_em preenchido; valor_final calculado. |

### PASSO 097 — PDFs check-in

| Ação | **PDF Devolução** |
| Critério | PDF abre com km/combustível final. |

### PASSO 098 — Encerramentos

| Menu | Locações → Encerramentos |
| Ação | Filtrar contrato encerrado · verificar pendência financeira · se houver, listar |
| Critério | Contrato aparece no histórico. |

### PASSO 099 — Cancelar contrato rascunho (se existir)

| Ação | Contrato PASSO 090 ainda não check-out → **Cancelar** motivo `Teste cancelamento` |
| Critério | Status `Cancelado`; veículo permanece disponível. |

---

# FASE 9 — Financeiro

### PASSO 100 — Abrir caixa

| Menu | Financeiro → Caixa |
| Usuário | `operador@locadora.local` ou admin |
| Dados | Filial Matriz · Abertura R$ `200` |
| Ação | **Abrir Caixa** |

### PASSO 101 — Lançamento caixa

| URL | `/financeiro/caixa/{sessao_id}` |
| Dados | Tipo `entrada` · Forma `dinheiro` · Valor `150` · Categoria `Recebimento balcão` · Descrição `Teste smoke` |
| Ação | **Lançar** |

### PASSO 102 — Fechar caixa

| Dados | Valor informado = saldo calculado (200+150=350) |
| Ação | **Fechar Caixa** → **PDF Fechamento de Caixa** |
| Critério | Status sessão `Fechada`; divergência R$ 0. |

### PASSO 103 — Conta a receber manual

| Menu | Financeiro → Contas a Receber → **+ Novo** |
| Dados | Filial Matriz · Cliente João · Descrição `Cobrança teste` · Valor `250` · Vencimento D+7 · Gerar PIX marcado |
| Ação | **Salvar** → detalhe → **Gerar PIX** → **Baixar** valor total forma PIX · **PDF Recibo** |
| Validação | PIX tela atualizada; título `Pago`. |
| Critério | Saldo caixa/ref conciliação coerentes. |

### PASSO 104 — Conta a pagar

| Menu | Financeiro → Contas a Pagar → **+ Novo** |
| Dados | Fornecedor Oficina Norte · Valor `350` · Vencimento D+14 · Descrição `OS teste` |
| Ação | **Salvar** → **Aprovar Pagamento** → **Pagar** |
| Critério | Status `Pago`. |

### PASSO 105 — PIX chave

| Menu | Financeiro → PIX |
| Dados | Filial Matriz · Tipo `email` · Chave `pix@locadoramatriz.com.br` |
| Ação | **Cadastrar Chave** |

### PASSO 106 — Cartão pré-autorização

| Menu | Financeiro → Cartões → **+ Novo** |
| Dados | Contrato ativo · Tipo `pre_autorizacao` · Valor `800` · Parcelas `1` |
| Ação | **Autorizar** → depois **Capturar** parcial `200` → **Estornar** restante (ou **Cancelar**) |
| Critério | Status transição correta. |

### PASSO 107 — Conta bancária

| Menu | Financeiro → Bancos → **+ Novo** |
| Dados | Filial Matriz · Banco `341` Itaú · Agência `1234` · Conta `56789-0` · Tipo `corrente` |
| Ação | **Salvar** |

### PASSO 108 — Conciliação

| Menu | Financeiro → Conciliação |
| Ação | **Importar** extrato fictício (colar OFX/CSV de teste se disponível) → **Vincular** linha a título do PASSO 103 |
| Critério | Item marcado conciliado. |

### PASSO 109 — Faturamento PJ

| Menu | Financeiro → Faturamento |
| Dados | Config cliente Transportes Beta · ciclo mensal · dia fechamento `25` |
| Ação | **Salvar Configuração** → **Consolidar** período corrente → **Emitir Fatura** → **PDF Boleto/Fatura** |
| Validação | NFS-e pode ser disparada se configurado. |
| Critério | Fatura status emitida. |

---

# FASE 10 — Fiscal

### PASSO 110 — Config impostos

| Menu | Fiscal → Impostos → **+ Novo** |
| Dados | Filial Matriz · Regime `Simples Nacional` · Vigência início hoje · NFSe automática desmarcada |
| Ação | **Salvar** → adicionar alíquota ISS `5%` serviço locação |

### PASSO 111 — NFS-e

| Menu | Fiscal → NFS-e → **+ Novo** |
| Dados | Cliente João · Valor serviço `400` · Discriminação `Locação veículo` · Município SP · Alíquota `5` |
| Ação | **Salvar** → **Emitir** (simulador) → **PDF DANFSE** |
| Critério | Status `Autorizada`; XML arquivado. |

### PASSO 112 — NF-e

| Menu | Fiscal → NF-e → **+ Novo** |
| Dados | Cliente João · Operação venda · Item descrição `Peça teste` · NCM `84212300` · Qtd 1 · Valor `100` |
| Ação | **Salvar** → **Autorizar (SEFAZ)** simulador → **PDF DANFE** |

### PASSO 113 — Importar XML

| Menu | Fiscal → XML → **Importar** |
| Dados | Filial Matriz · Nome `nf-teste.xml` · Colar XML fictício válido |
| Ação | **Importar XML** |

### PASSO 114 — Cancelamento fiscal

| Menu | Fiscal → Cancelamentos → **+ Novo** |
| Dados | Documento NFS-e do PASSO 111 · Tipo cancelamento · Motivo `Teste auditoria` |
| Ação | **Registrar e processar** |

### PASSO 115 — Apuração impostos

| Menu | Fiscal → Impostos → link **Apuração** |
| Ação | Período mês corrente |
| Critério | Tabela ISS/ICMS exibida. |

---

# FASE 11 — Dashboard e Relatórios

### PASSO 120 — Dashboard KPIs

| Menu | Dashboard `/` |
| Usuários | Admin · depois `diretoria@locadora.local` |
| Ação | Verificar widgets: Frota · Reservas · Locações · Financeiro · Manutenção · Comercial · Alertas |
| Validação | KPIs refletem dados criados (≥1 contrato, ≥1 veículo locado ou disponível). |
| Critério | Sem erro 500; números > 0 onde aplicável. |

### PASSO 121 — Relatórios Frota (6)

| Menu | Relatórios → Frota |
| Para cada código | `frota_atual`, `rentabilidade_veiculo`, `ociosidade_ocupacao`, `tco_veiculo`, `idade_media_frota`, `vencimentos_documentacao` |
| Dados comuns | Filial Matriz · Período mês corrente · Formato PDF |
| Ação | **Emitir relatório** → aguardar → download |
| Critério | 6 emissões concluídas em `/relatorios/historico`. |

### PASSO 122 — Relatórios Locação (8)

| Códigos | `contratos_periodo`, `ticket_medio`, `tempo_medio_locacao`, `taxa_renovacao`, `taxa_no_show_cancelamento`, `ranking_clientes`, `avarias_responsabilizacao`, `multas_relatorio` |
| Critério | 8 PDFs gerados. |

### PASSO 123 — Relatórios Financeiro (6)

| Códigos | `dre_simplificado`, `fluxo_caixa`, `inadimplencia_aging`, `faturamento_segmento`, `comissoes_pagas`, `conciliacao_resumo` |

### PASSO 124 — Relatórios Fiscal (4)

| Códigos | `notas_periodo`, `apuracao_impostos`, `export_contabilidade`, `divergencias_fiscais` |

### PASSO 125 — Relatórios Gerencial (5)

| Códigos | `painel_executivo`, `comparativo_filiais`, `metas_vendedores`, `sazonalidade`, `projecao_demanda` |

### PASSO 126 — Agendamento relatório

| Menu | Relatórios → Agendamentos → **+ Novo** |
| Dados | Nome `DRE Mensal Auto` · Categoria financeiro · Relatório `dre_simplificado` · Recorrência mensal · E-mail admin |
| Ação | **Salvar** |

### PASSO 127 — Histórico documentos PDF

| Menu | Relatórios → Documentos PDF (`/documentos/historico`) |
| Ação | Confirmar ≥20 registros de PDFs emitidos nos passos anteriores · baixar 1 novamente |
| Critério | Re-download funciona (cache válido). |

---

# FASE 12 — Integrações

### PASSO 130 — Pagamentos (simulador)

| Menu | Integrações → Pagamentos |
| Dados | Nome `Pagamento Simulador` · Provedor `simulador` · API Key `test-key-smoke` |
| Ação | **Salvar conector** → **Testar conexão** (botão JS) |
| Critério | Toast/alerta sucesso. |

### PASSO 131 — Trânsito DETRAN simulado

| Menu | Integrações → Trânsito |
| Ação | **Consultar multas** veículo TST1A23 · **Consultar CNH** motorista Carlos · **Consultar débitos** veículo |
| Critério | Resultado simulado exibido (sem erro). |

### PASSO 132 — Crédito

| Menu | Integrações → Crédito |
| Ação | **Consultar crédito** cliente João |
| Critério | Score simulado retornado. |

### PASSO 133 — Telemetria integração

| Menu | Integrações → Telemetria |
| Ação | Salvar conector simulador → **Sincronizar telemetria agora** |
| Validação | Frota → Telemetria km/posição atualizados ou log sem erro. |

### PASSO 134 — API Pública

| Menu | Integrações → API Pública |
| Dados API Key | Nome `Site Institucional` · Escopos `disponibilidade:read`, `reservas:write`, `contratos:read` |
| Ação | **Gerar API Key** → copiar chave exibida **uma vez** |
| Dados Webhook | Nome `Site Hook` · URL `https://webhook.site/unique-id` · Eventos `reserva.confirmada`, `contrato.encerrado` |
| Ação | **Cadastrar webhook** |

### PASSO 135 — Teste API disponibilidade (curl)

```bash
curl -H "X-API-Key: SUA_CHAVE" \
  "http://localhost:8000/api/v1/public/disponibilidade?filial_id=FILIAL_UUID&retirada_em=2026-08-01T10:00:00&devolucao_em=2026-08-04T10:00:00"
```

| Critério | HTTP 200 · JSON com `livres` ≥ 1. |

### PASSO 136 — Teste API criar reserva (curl)

```bash
curl -X POST -H "X-API-Key: SUA_CHAVE" -H "Content-Type: application/json" \
  -d '{"filial_retirada_id":"...","filial_devolucao_id":"...","retirada_em":"...","devolucao_em":"...","categoria_id":"...","cliente_id":"...","origem":"website"}' \
  http://localhost:8000/api/v1/public/reservas
```

| Critério | HTTP 201 · corpo com `numero` e `status`. |

---

# FASE 13 — Automações

### PASSO 140 — Regra automação

| Menu | Automações → Regras → **+ Novo** |
| Dados | Nome `Alerta doc vencendo` · Gatilho `documento.vencendo` · Condição `{"op":"always"}` · Ação `notificar` · Ativa |
| Ação | **Salvar** → **Executar** manual |
| Validação | Automações → Histórico registra execução. |

### PASSO 141 — Workflow

| Menu | Automações → Workflows → **+ Novo** |
| Dados | Código `aprovacao_desconto` · Nome `Aprovação desconto` |
| Ação | **Criar workflow** |

### PASSO 142 — Agendamentos Celery Beat

| Menu | Automações → Agendamentos |
| Ação | Para cada job listado (`dashboard.materializar_kpis`, `reservas.processar_no_show`, `financeiro.marcar_vencidos`, etc.): clicar **Rodar agora** |
| Validação | Histórico sem erro crítico. |
| Critério | Execuções registradas. |

### PASSO 143 — Histórico automações

| Menu | Automações → Histórico |
| Critério | Lista execuções PASSO 140-142. |

---

# FASE 14 — Notificações

### PASSO 150 — Inbox

| Menu | Notificações → Caixa de Entrada |
| Ação | Se houver não lidas: abrir → **Marcar lida** → **Marcar todas como lidas** |
| Critério | Contador zerado. |

### PASSO 151 — Envios

| Menu | Notificações → Histórico de Envios |
| Critério | Campanha PASSO 073 e regras aparecem (simulador log). |

---

# FASE 15 — Auditoria

### PASSO 160 — Trilha de auditoria

| Menu | Auditoria → Trilha de Auditoria |
| Ação | Filtrar entidade `loc_contrato` · usuário admin · período hoje |
| Validação | Eventos dos PASSOS 091, 096 visíveis (checkout/checkin). |
| Ação | Exportar PDF auditoria se botão disponível |
| Critério | Log imutável; sem editar/deletar. |

---

# FASE 16 — Testes de regressão por papel (RBAC)

Execute logout (`/logout`) antes de cada bloco.

### PASSO 170 — Vendedor

| Login | `vendedor@locadora.local` / `Vendedor@123` |
| Deve ver | Dashboard, Cadastros (parcial), Reservas, Cotações, Comercial, Tarifário simular |
| Não deve ver | Financeiro, Fiscal, Configurações usuários |
| Ação smoke | Criar cotação → converter · tentar abrir `/financeiro/caixa` (esperado 403 ou redirect) |
| Critério | Menu filtrado; operações comerciais OK. |

### PASSO 171 — Operador

| Login | `operador@locadora.local` / `Operador@123` |
| Deve ver | Locações check-out/in, Reservas, Caixa, Frota leitura |
| Ação smoke | Listar check-out · abrir caixa (se permissão) |
| Critério | Fluxo balcão operacional. |

### PASSO 172 — Financeiro

| Login | `financeiro@locadora.local` / `Financeiro@123` |
| Deve ver | Todo Financeiro, Fiscal, Relatórios financeiro/fiscal |
| Ação smoke | Listar receber/pagar · emitir NFS-e |
| Critério | Sem acesso a Config papéis. |

### PASSO 173 — Diretoria

| Login | `diretoria@locadora.local` / `Diretoria@123` |
| Deve ver | Dashboard, Relatórios (todos), leitura gerencial |
| Não deve ver | Formulários de criar/editar (botões ausentes) |
| Critério | Somente leitura + export. |

### PASSO 174 — Auditor QA

| Login | `qa.auditor@locadora.local` / `QaAuditor@123` |
| Critério | Visualiza auditoria + relatórios; não cria registros. |

---

# FASE 17 — Regressão automatizada (complemento CI)

### PASSO 180 — Suite pytest

```bash
python -m pytest tests/ -q
```

| Critério | 100% passed (215+ testes). |

### PASSO 181 — Testes E2E Playwright (se Node instalado)

```bash
cd e2e && npm ci && npx playwright test
```

| Critério | Fluxos críticos UI passam. |

### PASSO 182 — Teste conformidade spec

```bash
python -m pytest tests/test_spec_compliance.py -v
```

| Critério | Menus implementados + catálogo PDF completo. |

---

# FASE 18 — Matriz de dependências downstream (referência rápida)

| Ação upstream | Verificar downstream |
|---------------|---------------------|
| Criar cliente | Reserva, Contrato, Receber, NFS-e, CRM |
| Criar veículo | Disponibilidade, Reserva, OS, Telemetria |
| Confirmar reserva | Veículo `Reservado`, Calendário, Webhook outbound |
| Check-out | Contrato `Ativo`, Veículo `Locado`, Caixa, PDFs |
| Check-in | Contrato `Encerrado`, Veículo `Disponível`, Receber, Fidelidade |
| OS concluída | Veículo disponível, Estoque peças, Contas pagar |
| Baixa receber | Conciliação, Declaração quitação, Dashboard financeiro |
| Emitir NFS-e | XML, Relatório fiscal, Fiscal apuração |
| Cupom usado | Relatório comercial, valor reserva menor |
| API reserva | Webhook `reserva.confirmada`, listagem Reservas origem website |

---

# Controle de execução

| Fase | Passos | Total | Concluídos |
|------|--------|-------|------------|
| 0 Pré-requisitos | 000-002 | 3 | |
| 1 Configurações | 010-017 | 8 | |
| 2 Cadastros | 020-027 | 8 | |
| 3 Frota | 030-042 | 13 | |
| 4 Tarifário | 050-055 | 6 | |
| 5 Manutenção | 060-063 | 4 | |
| 6 Comercial | 070-074 | 5 | |
| 7 Reservas | 080-086 | 7 | |
| 8 Locações | 090-099 | 10 | |
| 9 Financeiro | 100-109 | 10 | |
| 10 Fiscal | 110-115 | 6 | |
| 11 Dashboard/Relatórios | 120-127 | 8 | |
| 12 Integrações | 130-136 | 7 | |
| 13 Automações | 140-143 | 4 | |
| 14 Notificações | 150-151 | 2 | |
| 15 Auditoria | 160 | 1 | |
| 16 RBAC | 170-174 | 5 | |
| 17 CI + Apêndice | 180-182, 200-216 | 20 | |
| **TOTAL** | | **130 passos** | |

---

# APÊNDICE A — Passos granulares adicionais (completude absoluta)

Execute após a Fase 8 ou em paralelo quando o dado existir.

### PASSO 200 — Reserva: cancelar

| URL | `/reservas/{id}` reserva PASSO 082 (se ainda confirmada e não convertida) ou criar reserva descartável |
| Ação | Preencher motivo `Teste cancelamento` → **Cancelar** |
| Validação | Veículo liberado; política cancelamento aplicada; status `Cancelada`. |

### PASSO 201 — Reserva: no-show

| Pré-requisito | Reserva confirmada com retirada_em no passado (ajustar data via admin ou aguardar job `reservas.processar_no_show`) |
| Ação | **No-show** manual na tela da reserva |
| Validação | Status `No-show`; veículo disponível. |

### PASSO 202 — Cliente bloqueado + aprovação

| Ação | Cadastros → Cliente João → **Bloquear** motivo `Inadimplência teste` |
| Nova reserva | Tentar criar reserva → deve exigir **Aprovar cliente bloqueado** |
| Ação | **Aprovar** com permissão admin |
| Critério | Reserva criada apesar do bloqueio. |

### PASSO 203 — Veículo bloquear e liberar

| URL | `/frota/veiculos/{id}/editar` TST1A23 |
| Ação | **Bloquear** motivo `Documentação pendente teste` → status `Bloqueado` |
| Validação | Disponibilidade não lista veículo |
| Ação | **Liberar** motivo `Regularizado teste` → status `Disponível` |

### PASSO 204 — Veículo baixar (venda)

| Veículo | Usar TST2B34 se disponível |
| Ação | **Baixar** · Motivo `Venda` · Destinatário `Comprador Teste` · Doc `111.222.333-44` · Valor `45000` |
| Validação | Status `Baixado`; NF-e venda pode ser emitida (PASSO 112). |

### PASSO 205 — OS: fluxo aprovação valor alto

| Ação | Criar OS corretiva valor total > limite parâmetro → **Aguardando Aprovação** → **Aprovar** → concluir |
| Critério | Workflow respeitado; histórico status OS. |

### PASSO 206 — Proposta: aceitar e gerar reserva

| URL | Proposta PASSO 072 |
| Ação | **Aceitar** → verificar reserva/contrato gerado automaticamente |
| Critério | Proposta status `Aceita`. |

### PASSO 207 — Proposta: recusar e revisão

| Nova proposta descartável | **Recusar** · criar **Nova Revisão** versão 2 |
| Critério | Histórico versões visível. |

### PASSO 208 — Funil: marcar perdido

| Oportunidade PASSO 071 | **Marcar Perdido** · Motivo `Preço` |
| Critério | Card na coluna Perdido. |

### PASSO 209 — Estoque peça: saída e ajuste

| Menu | Manutenção → Peças → Estoque |
| Ação | Saída qtd 1 · Ajuste inventário qtd -1 com observação `Ajuste teste` |
| Critério | Saldo correto. |

### PASSO 210 — Pneu: rodízio e descarte

| Pneu PNEU-001 | **Rodízio** posição `DE` · **Inspecionar** sulco `4.5` mm · **Descartar** motivo `Desgaste` (usar pneu descartável se necessário) |

### PASSO 211 — Tarifário: editar item tabela

| URL | `/tarifario/tabelas/{id}/editar` |
| Ação | Alterar diária 1-3d para `125` → **Salvar alterações** → Simular preço PASSO 055 e confirmar valor atualizado |

### PASSO 212 — Financeiro: estornar recebimento

| Título pago PASSO 103 | **Estornar** · confirmar |
| Critério | Status estornado; saldo revertido. |

### PASSO 213 — Fiscal: cancelar NF-e

| NF-e PASSO 112 | **Cancelar NF-e** · motivo `Teste` |
| Critério | DANFE com watermark CANCELADO se reemitido. |

### PASSO 214 — Integrações: excluir webhook

| API Pública | **Excluir** webhook PASSO 134 |
| Critério | Lista webhooks vazia ou sem o item. |

### PASSO 215 — Logout e sessão

| Ação | Navbar → **Sair** (/logout) |
| Validação | Redirect `/login`; rotas protegidas inacessíveis sem login. |

### PASSO 216 — Login 2FA (opcional completo)

| Repetir PASSO 016 | Escanear QR com app autenticador → **Ativar 2FA** → logout → login → `/login/2fa` com código TOTP |
| Critério | Login só completa com 2FA. |

---

# APÊNDICE B — Checklist por menu (marque quando todos passos da seção OK)

| # | Menu | Submenus | Smoke OK |
|---|------|----------|----------|
| 1 | Dashboard | — | [ ] |
| 2 | Cadastros | Clientes, Motoristas, Parceiros, Fornecedores, Vendedores, Tabelas | [ ] |
| 3 | Frota | Veículos, Categorias, Marcas, Modelos, Combustíveis, Acessórios, Documentação, Telemetria, Mapa | [ ] |
| 4 | Manutenção | OS, Preventiva, Corretiva, Peças, Pneus | [ ] |
| 5 | Reservas | Nova, Listagem, Calendário, Disponibilidade, Cotações | [ ] |
| 6 | Locações | Contratos, Check-out, Check-in, Renovações, Encerramentos, Multas, Avarias | [ ] |
| 7 | Comercial | Funil, Propostas, Campanhas, Cupons, Fidelidade | [ ] |
| 8 | Tarifário | Tabelas, Temporadas, Taxas, Proteções, Cancelamento, Simular | [ ] |
| 9 | Financeiro | Caixa, Receber, Pagar, PIX, Cartões, Bancos, Conciliação, Faturamento | [ ] |
| 10 | Fiscal | NFS-e, NF-e, XML, Cancelamentos, Impostos | [ ] |
| 11 | Relatórios | 5 categorias + Histórico + Agendamentos + Documentos PDF | [ ] |
| 12 | Integrações | Pagamentos, Trânsito, Crédito, Telemetria, API Pública | [ ] |
| 13 | Automações | Regras, Workflows, Agendamentos, Histórico | [ ] |
| 14 | Notificações | Inbox, Envios | [ ] |
| 15 | Configurações | Empresa, Filiais, Usuários, Papéis, 2FA, Parâmetros | [ ] |
| 16 | Auditoria | Trilha | [ ] |

**Total menus/submenus:** 16 seções · 81 itens de menu folha · 26 templates PDF · 29 relatórios · 3 endpoints API pública.

---

# Registro de defeitos (preencher durante execução)

| Passo | Severidade | Descrição | Evidência | Status |
|-------|------------|-----------|-----------|--------|
| | | | | |

---

**Documento gerado para:** ERP Locadora — repositório `sistema de locação`  
**Última revisão:** alinhado aos menus e rotas de `app/web/navigation.py` e formulários web atuais.
