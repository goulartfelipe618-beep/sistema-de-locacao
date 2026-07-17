# INFO-FORMS — Manual do Administrador para Testes Ponta a Ponta

**Versão:** 2.0  
**Data:** 2026-07-17  
**Público:** Administrador da plataforma (admin da empresa / superusuário)  
**Objetivo:** Guiar você, passo a passo, para **configurar, operar e validar 100% do ERP** — do cadastro inicial até encerramento financeiro e fiscal, incluindo **locação própria** e **intermediação (frota terceirizada)**.

> **Como usar:** Execute as fases **na ordem**. Marque `[x]` cada bloco concluído. Se algo falhar, anote no [Registro de defeitos](#registro-de-defeitos) e **não pule** etapas que criam dados usados depois.

---

## Sumário

1. [Antes de começar](#1-antes-de-começar)
2. [Como ler cada teste](#2-como-ler-cada-teste)
3. [Dados fictícios mestres](#3-dados-fictícios-mestres)
4. [Mapa das fases (ordem obrigatória)](#4-mapa-das-fases-ordem-obrigatória)
5. [FASE 0 — Infraestrutura e login](#fase-0--infraestrutura-e-login)
6. [FASE 1 — Configurações da plataforma](#fase-1--configurações-da-plataforma)
7. [FASE 2 — Cadastros](#fase-2--cadastros)
8. [FASE 3 — Frota própria](#fase-3--frota-própria)
9. [FASE 3B — Intermediação (locação terceirizada)](#fase-3b--intermediação-locação-terceirizada)
10. [FASE 4 — Tarifário](#fase-4--tarifário)
11. [FASE 5 — Manutenção](#fase-5--manutenção)
12. [FASE 6 — Comercial / CRM](#fase-6--comercial--crm)
13. [FASE 7 — Reservas](#fase-7--reservas)
14. [FASE 8 — Locações (contrato completo)](#fase-8--locações-contrato-completo)
15. [FASE 9 — Financeiro](#fase-9--financeiro)
16. [FASE 10 — Fiscal](#fase-10--fiscal)
17. [FASE 11 — Dashboard e Relatórios](#fase-11--dashboard-e-relatórios)
18. [FASE 12 — Integrações e API pública](#fase-12--integrações-e-api-pública)
19. [FASE 13 — Automações](#fase-13--automações)
20. [FASE 14 — Notificações](#fase-14--notificações)
21. [FASE 15 — Auditoria](#fase-15--auditoria)
22. [FASE 16 — Testes por papel (RBAC)](#fase-16--testes-por-papel-rbac)
23. [FASE 17 — Regressão automatizada](#fase-17--regressão-automatizada)
24. [FASE 18 — Cenários extras e bordas](#fase-18--cenários-extras-e-bordas)
25. [Matriz global de efeitos em cascata](#matriz-global-de-efeitos-em-cascata)
26. [Checklist por menu](#checklist-por-menu)
27. [Apêndices](#apêndices)

---

## 1. Antes de começar

### 1.1 Ambiente

| Item | Valor |
|------|-------|
| URL do painel | `http://localhost:8000` (local) ou URL da VPS |
| Health check | `/api/v1/health` e `/api/v1/health/ready` → HTTP 200 |
| Banco | PostgreSQL com migrations aplicadas |
| Comando migrations | `alembic upgrade head` |
| Seed inicial | `python -m scripts.seed` |
| Deploy Docker | `git pull && docker compose up -d --build` |

### 1.2 Usuários de teste (após seed)

| Papel | E-mail | Senha | Use para testar |
|-------|--------|-------|-----------------|
| **Administrador** | `admin@locadora.local` | `Admin@123` | Tudo — comece aqui |
| Vendedor | `vendedor@locadora.local` | `Vendedor@123` | Reservas, comercial, cotações |
| Operador | `operador@locadora.local` | `Operador@123` | Check-out/in, caixa, balcão |
| Financeiro | `financeiro@locadora.local` | `Financeiro@123` | CR/CP, fiscal, conciliação |
| Diretoria | `diretoria@locadora.local` | `Diretoria@123` | Dashboard e relatórios (leitura) |
| Auditor QA | `qa.auditor@locadora.local` | `QaAuditor@123` | Criar no PASSO 014 — só leitura |

### 1.3 Convenções de data

- **D+1** = amanhã às 10:00 (horário local)
- **D+4** = três dias após a retirada, às 10:00
- Sempre use filial **Matriz (0001)** salvo quando indicado **Campinas (0002)**

### 1.4 Documento complementar

O arquivo `teste.md` contém os mesmos passos com numeração **PASSO 000–216** para auditoria formal. Este manual (`INFO-FORMS.md`) é a versão **orientada ao administrador**, com ênfase em **efeitos em cascata** e no módulo **Intermediação**.

---

## 2. Como ler cada teste

Cada função segue este padrão:

| Bloco | Significado |
|-------|-------------|
| **Menu / URL** | Onde clicar no painel |
| **Permissão** | Código RBAC mínimo (seu admin tem todos) |
| **Como testar** | Passos numerados — faça exatamente nesta ordem |
| **Resultado esperado** | O que confirma que funcionou |
| **⚡ Efeitos em cascata** | O que muda em **outras telas** quando você cria, altera ou exclui aqui |

**Símbolos:**

- ⚡ = impacto downstream (obrigatório verificar após o teste)
- 🔒 = exclusão bloqueada por vínculo (RESTRICT)
- 👁 = preferir **inativar** em vez de excluir

---

## 3. Dados fictícios mestres

Use **sempre os mesmos valores** para reproduzir bugs e comparar execuções.

### 3.1 Cadastros e frota própria

| Entidade | Valor |
|----------|-------|
| Filial matriz | Código `0001` — Matriz — São Paulo/SP |
| Filial 2 | Código `0002` — Filial Campinas — CNPJ `44.555.666/0001-77` |
| Cliente PF | João Silva Teste · CPF `529.982.247-25` · `joao.teste@email.com` |
| Cliente PJ | Transportes Beta LTDA · CNPJ `11.444.777/0001-61` |
| Motorista | Carlos Condutor · CPF `390.533.447-05` · CNH cat. B · validade +730 dias |
| Parceiro comercial | Agência Viagem Sul · CNPJ `22.333.444/0001-55` · comissão 10% |
| Fornecedor oficina | Oficina Mecânica Norte · CNPJ `33.444.555/0001-66` |
| Veículo próprio A | Placa `TST1A23` · Chevrolet Onix · categoria Econômico |
| Veículo próprio B | Placa `TST2B34` (reserva/overbooking) |
| Tabela tarifa | `Tarifa Padrão Matriz` · diária 1–3d R$ 120 |
| Cupom | `VERAO2026` · 10% · mínimo R$ 100 |

### 3.2 Intermediação (frota terceirizada)

| Entidade | Valor |
|----------|-------|
| Locadora parceira | **Locadora Parceira Sul LTDA** · CNPJ `88.777.666/0001-55` · marcar **É locadora parceira** |
| Contato operacional | Nome `Ana Parceira` · Tel `(11) 97777-8888` · E-mail `operacao@parceirasul.com` |
| Contrato parceiro | Nº `CP-2026-001` · modelo **REPASSE** · repasse 85% · vigência hoje → +365 dias |
| Faixa preço contrato | Cliente R$ 150/dia · Repasse R$ 127,50/dia · categoria Econômico |
| Veículo terceirizado | Placa `TER3C01` · propriedade **terceirizada** · fornecedor Parceira Sul · publicar no site ✓ |

---

## 4. Mapa das fases (ordem obrigatória)

```
FASE 0  Infra + login
   ↓
FASE 1  Empresa, filiais, usuários, papéis, parâmetros
   ↓
FASE 2  Cadastros (clientes, motoristas, parceiros, fornecedores, vendedores, tabelas aux.)
   ↓
FASE 3  Frota própria (catálogo + veículos + documentação + telemetria)
   ↓
FASE 3B Intermediação ← NOVO: parceiro, contrato, veículo terceirizado, aprovação, repasse
   ↓
FASE 4  Tarifário (preço, taxas, proteções, cancelamento)
   ↓
FASE 5  Manutenção (OS, peças, pneus)
   ↓
FASE 6  Comercial (funil, proposta, campanha, cupom, fidelidade)
   ↓
FASE 7  Reservas (disponibilidade, cotação, reserva própria + terceirizada)
   ↓
FASE 8  Locações (contrato → check-out → check-in → encerramento)
   ↓
FASE 9  Financeiro (caixa, CR, CP, PIX, faturamento, repasse parceiro)
   ↓
FASE 10 Fiscal (NFS-e, NF-e, XML, impostos)
   ↓
FASE 11 Dashboard + 31 relatórios + PDFs
   ↓
FASE 12 Integrações + API pública + catálogo site
   ↓
FASE 13–15 Automações, notificações, auditoria
   ↓
FASE 16 RBAC (logar com cada papel)
   ↓
FASE 17–18 CI + cenários de borda
```

| Fase | Passos ref. (`teste.md`) | Foco admin |
|------|--------------------------|------------|
| 0 | 000–002 | Sistema no ar |
| 1 | 010–017 | Base multitenant |
| 2 | 020–027 | Domínios de negócio |
| 3 | 030–042 | Frota própria |
| **3B** | **INT-001–INT-015** | **Intermediação completa** |
| 4 | 050–055 | Motor de preço |
| 5 | 060–063 | Manutenção |
| 6 | 070–074 | CRM |
| 7 | 080–086 | Reservas |
| 8 | 090–099 | Locações |
| 9 | 100–109 | Financeiro |
| 10 | 110–115 | Fiscal |
| 11 | 120–127 | Relatórios |
| 12 | 130–136 | Integrações |
| 13–18 | 140–216 | Automação, RBAC, bordas |

---

# FASE 0 — Infraestrutura e login

### PASSO 000 — Verificar serviços

1. Abra `/api/v1/health` → JSON `"status": "ok"`.
2. Abra `/api/v1/health/ready` → `"database": true` (Redis opcional em dev).

**Resultado esperado:** HTTP 200 nos dois.

**⚡ Efeitos em cascata:** Sem banco OK, **nenhuma** fase seguinte funciona (login, seed, formulários).

---

### PASSO 001 — Seed do banco

1. No terminal: `python -m scripts.seed`
2. Confirme no log: tenant, filial 0001, permissões, papéis, admin.

**Resultado esperado:** Exit code 0.

**⚡ Efeitos em cascata:** Cria catálogo global de **permissões** e sincroniza papéis (`admin-empresa`, `gerente-filial`, `vendedor`, etc.). Se você adicionou permissões novas no código, **reexecute o seed** para papéis existentes ganharem acesso (ex.: Intermediação).

---

### PASSO 002 — Login administrador

1. Acesse `/login`
2. E-mail `admin@locadora.local` · Senha `Admin@123`
3. Clique **Entrar**

**Resultado esperado:** Redirect para `/` (Dashboard); menu lateral com **todas** as seções (Cadastros, Frota, **Intermediação**, Reservas, etc.).

**⚡ Efeitos em cascata:** Sessão + cookie CSRF ativos — necessários para **todo** formulário POST.

---

# FASE 1 — Configurações da plataforma

> **Regra:** tudo configurado aqui afeta **toda a empresa (tenant)** e, quando scoped por filial, só aquela unidade.

## 1.1 Dados da Empresa

**Menu:** Configurações → Dados da Empresa · `/configuracoes/empresa`  
**Permissão:** `configuracoes.empresa.visualizar` + editar

**Como testar:**

1. Preencha razão social `Locadora Matriz LTDA`, fantasia `Locadora Matriz`, e-mail `contato@locadoramatriz.com.br`, telefone `(11) 3000-0000`, cor primária `#1a56db`.
2. (Opcional) Faça upload de logo.
3. Clique **Salvar alterações**.

**Resultado esperado:** Mensagem de sucesso; dados persistem após F5.

**⚡ Efeitos em cascata:**

| O que você alterou | Onde verificar depois |
|--------------------|----------------------|
| Logo / cor primária | PDFs (contrato, DANFE, recibos) |
| Razão social | Cabeçalho de relatórios e NFS-e |
| Certificado A1 (se configurar) | Emissão NF-e/NFS-e reais |

---

## 1.2 Filiais / Unidades

**Menu:** Configurações → Filiais · `/configuracoes/filiais`

### Listar matriz (PASSO 011)

1. Confirme filial **0001 — Matriz** como sede.

### Criar Campinas (PASSO 012)

1. **+ Nova filial** → Código `0002`, Nome `Filial Campinas`, CNPJ `44.555.666/0001-77`, Cidade `Campinas`, UF `SP`, telefone `(19) 3200-0000`, **desmarque** sede.
2. **Salvar**.

**Resultado esperado:** Filial 0002 na listagem.

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Nova filial | Aparece em selects de Reserva, Contrato, Frota, Caixa, Tarifário, Parâmetros |
| Inativar filial 👁 | Contratos/OS abertos 🔒 bloqueiam exclusão |
| Filial errada na reserva | Disponibilidade e preço podem divergir |

---

## 1.3 Usuários e Papéis

### Usuários (PASSO 013–014)

1. **Configurações → Usuários** — confirme 5 usuários demo ativos.
2. **+ Novo:** `QA Auditor` · `qa.auditor@locadora.local` · senha `QaAuditor@123` · papel **Auditor** · filial Matriz.

### Papéis (PASSO 015)

1. **Configurações → Papéis e Permissões**
2. Abra **Gerente de Filial** → confirme permissões de **Intermediação** (config, contratos, aprovações, repasses).
3. Abra **Vendedor** → confirme reservas/comercial **sem** financeiro.

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Alterar permissões de um papel | **Todos** os usuários com aquele papel ganham/perdem menus na hora (próximo login ou refresh) |
| Desativar usuário | Sessões ativas podem persistir até expirar; novos logins bloqueados |
| Usuário sem filial | Não vê dados operacionais da filial |

---

## 1.4 Autenticação 2FA (PASSO 016)

1. **Configurações → Autenticação 2FA** → `/configuracoes/seguranca`
2. **Iniciar configuração** → veja QR → **cancele** sem confirmar (smoke test).

**⚡ Efeitos em cascata:** Se **ativar** 2FA, login exige `/login/2fa` — teste completo no PASSO 216.

---

## 1.5 Parâmetros do sistema (PASSO 017)

**Menu:** Configurações → Parâmetros · `/configuracoes/parametros`

1. Filial: **Matriz**
2. Ajuste: `reservas.overbooking_percentual` = `0`, `reservas.buffer_horas` = `2` (ou `120` minutos conforme UI)
3. **Salvar parâmetros**

**⚡ Efeitos em cascata:**

| Parâmetro | Impacto |
|-----------|---------|
| Buffer reservas | Consulta de **Disponibilidade** adiciona horas entre locações |
| Overbooking | Permite reservar além da frota física (0 = desligado) |
| Parâmetros OS | Valor acima do limite → OS **Aguardando Aprovação** |
| Numeração sequencial | Próximo número de reserva/contrato/OS |

---

# FASE 2 — Cadastros

> **Ordem interna:** Tabelas auxiliares **primeiro** → depois clientes → motoristas → parceiros → fornecedores → vendedores.

## 2.1 Tabelas Auxiliares (PASSO 020)

**Menu:** Cadastros → Tabelas Auxiliares · `/cadastros/tabelas`

1. Grupo `motivo_cancelamento` → Código `cliente_desistiu` · Descrição `Cliente desistiu` · Ordem `1`
2. **Adicionar**

**⚡ Efeitos em cascata:** Motivos aparecem em **cancelamento de reserva/contrato** e relatórios.

---

## 2.2 Clientes (PASSO 021–023)

**Menu:** Cadastros → Clientes → **+ Novo** · `/cadastros/clientes/novo`

### Cliente PF

1. Tipo **PF** · Nome `João Silva Teste` · CPF `529.982.247-25` · e-mail e celular conforme §3.1
2. Endereço: CEP `01310-100` (teste autopreenchimento ViaCEP se disponível)
3. Limite crédito R$ 5.000 · **Salvar**

### Cliente PJ (PASSO 022)

1. Tipo **PJ** · `Transportes Beta LTDA` · CNPJ `11.444.777/0001-61`

### PDFs (PASSO 023)

Na ficha do cliente PF → emitir: **Ficha cadastral**, **Extrato**, **Declaração quitação**.

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Criar cliente | Disponível em Reserva, Contrato, CR, NFS-e, CRM, API pública |
| **Bloquear** cliente 🔒 | Nova reserva exige **Aprovar cliente bloqueado** (PASSO 202) |
| Inativar 👁 | Some de comboboxes; histórico permanece |
| Excluir com reserva/contrato ativo 🔒 | **Bloqueado** — use inativar |
| Alterar limite crédito | Validação em reserva/contrato acima do limite |

---

## 2.3 Motoristas (PASSO 024)

**Menu:** Cadastros → Motoristas → **+ Novo**

1. Nome `Carlos Condutor` · CPF · CNH · categoria B · validade +730 dias
2. **Salvar**

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| CNH vencida | Reserva/contrato **rejeita** vínculo |
| Vincular na reserva | Contrato **herda** motoristas |
| Multa | Campo condutor aponta para motorista |

---

## 2.4 Parceiros comerciais (PASSO 025)

**Menu:** Cadastros → Parceiros → **+ Novo**

1. PJ `Agência Viagem Sul` · comissão 10% · PIX
2. **Salvar**

**⚡ Efeitos em cascata:** Comissão calculada no encerramento; tabela tarifária dedicada; relatório `comissoes_pagas`.

---

## 2.5 Fornecedores (PASSO 026 + base intermediação)

**Menu:** Cadastros → Fornecedores → **+ Novo**

### Fornecedor oficina (manutenção)

1. `Oficina Mecânica Norte` · CNPJ `33.444.555/0001-66` · categoria manutenção

### Locadora parceira (prepare FASE 3B)

1. **+ Novo** → `Locadora Parceira Sul LTDA` · CNPJ `88.777.666/0001-55`
2. Marque **É locadora parceira (frota terceirizada)**
3. Contato operacional: Ana · `(11) 97777-8888` · `operacao@parceirasul.com`
4. Modelo negócio padrão **REPASSE** · margem padrão 10%
5. **Salvar**

**⚡ Efeitos em cascata:**

| Tipo fornecedor | Impacto |
|-----------------|---------|
| Oficina | OS, Contas a Pagar manutenção |
| **Locadora parceira** | Contratos Intermediação, veículos terceirizados, repasse financeiro, aprovações |
| Bloquear fornecedor | CP em aberto 🔒 podem bloquear exclusão |

---

## 2.6 Vendedores (PASSO 027)

**Menu:** Cadastros → Vendedores → **+ Novo**

1. `Pedro Vendas` · filial Matriz · meta R$ 50.000
2. **Salvar**

**⚡ Efeitos em cascata:** Meta aparece em relatório `metas_vendedores`; comissão vendedor no encerramento.

---

# FASE 3 — Frota própria

> **Ordem:** Marca → Modelo → Categoria → Combustível → Acessório → Veículos → Documentação → Telemetria

## 3.1 Catálogo estrutural (PASSO 030–034)

| # | Menu | Dados mínimos | Ref |
|---|------|---------------|-----|
| Marca | Frota → Marcas | Chevrolet · Brasil | 030 |
| Modelo | Frota → Modelos | Onix · marca Chevrolet | 031 |
| Categoria | Frota → Categorias | Econômico · 5 passageiros · grupo `economico` | 032 |
| Combustível | Frota → Combustíveis | Flex · R$ 5,89/L | 033 |
| Acessório | Frota → Acessórios | Cadeirinha · R$ 25/dia · estoque 5 | 034 |

**⚡ Efeitos em cascata (catálogo):**

| Excluir/inativar | Bloqueio |
|------------------|----------|
| Categoria 🔒 | Veículos e itens de tarifa dependem |
| Marca 🔒 | Modelos dependem |
| Modelo 🔒 | Veículos dependem |
| Combustível 🔒 | Veículos dependem |

**Recomendação admin:** prefira **Inativar** 👁 em vez de excluir quando já houve locação.

---

## 3.2 Veículos próprios (PASSO 035–036)

**Menu:** Frota → Veículos → **+ Novo** · `/frota/veiculos/novo`

### Veículo A — TST1A23

1. Placa `TST1A23` · RENAVAM · chassi · ano 2023/2024 · cor Prata
2. Categoria Econômico · Marca/Modelo Chevrolet Onix · Combustível Flex
3. Propriedade **própria** · Filial Matriz · KM 15000
4. **Salvar**

### Veículo B — TST2B34

Repita com placa `TST2B34` (segundo carro para overbooking/testes de baixa).

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Criar veículo | Aparece em **Disponibilidade**, Reserva, OS, Telemetria |
| Alocar em reserva | Status → **Reservado** |
| Check-out contrato | Status → **Locado** |
| **Bloquear** veículo | Some da disponibilidade (PASSO 203) |
| **Baixar** veículo | Status terminal **Baixado** — nunca mais em reserva |
| Editar categoria | Recalcula tarifa em **novas** reservas |

---

## 3.3 Documentação veicular (PASSO 038–039)

**Menu:** Frota → Documentação → **+ Novo**

1. Veículo TST1A23 · tipo CRLV · validade futura · anexo se disponível
2. Emitir PDFs de documentação

**⚡ Efeitos em cascata:** Alertas no Dashboard; automação `documento.vencendo`; veículo pode ser **bloqueado** se vencido (regra parametrizável).

---

## 3.4 Telemetria (PASSO 040–042)

**Menu:** Frota → Telemetria → **+ Novo**

1. Dispositivo GPS no TST1A23 · provedor simulador
2. Registrar evento de posição/KM
3. Abrir **Mapa da frota** (se disponível)

**⚡ Efeitos em cascata:** KM telemetria vs KM check-out/check-in; integração **Integrações → Telemetria**.

---

# FASE 3B — Intermediação (locação terceirizada)

> **Objetivo:** testar locação **via locadora parceira** — modelos **REPASSE** e **COMISSÃO**, aprovação do parceiro, repasse financeiro e publicação no site.

## INT-001 — Configurações de intermediação

**Menu:** Intermediação → Configurações · `/intermediacao/config`  
**Permissão:** `intermediacao.config.visualizar` / editar

**Como testar:**

1. Modo da locadora: **Híbrida** (própria + terceiros)
2. Margem mínima: `10` %
3. Buffer disponibilidade: `4` horas
4. Marque: **Exigir contrato ativo com locadora parceira**
5. **Desmarque:** Confirmar intermediação automaticamente (para testar aprovação manual)
6. Marque: **Publicar veículos terceirizados no site**
7. Marque: **Priorizar frota própria na disponibilidade**
8. **Salvar configurações**
9. Clique **Sincronizar catálogo do site** (formulário separado abaixo)

**Resultado esperado:** Flash de sucesso; contador publicados/ocultos após sync.

**⚡ Efeitos em cascata:**

| Configuração | O que muda |
|--------------|------------|
| Modo **só própria** | Veículos terceirizados ignorados na operação |
| Modo **só intermediação** | Frota própria pode ser ocultada na disponibilidade |
| **Híbrida** | Ambos competem; prioridade configurable |
| Margem mínima | Reserva **rejeitada** se repasse deixar margem abaixo do mínimo |
| Buffer horas | Consulta disponibilidade adiciona folga logística para terceiros |
| Aprovação automática ON | Reserva terceirizada já nasce **confirmada pelo parceiro** |
| Aprovação automática OFF | Status **pendente_aprovacao** → bloqueia confirmar reserva |
| Publicar terceiros site | Flag `publicar_site` dos veículos terceirizados após sync |
| Priorizar frota própria | Disponibilidade lista próprios antes de terceirizados |

---

## INT-002 — Contrato com locadora parceira

**Menu:** Intermediação → Contratos Parceiros → **+ Novo** · `/intermediacao/contratos-fornecedor/novo`

**Pré-requisito:** Fornecedor **Locadora Parceira Sul** marcado como locadora parceira (FASE 2).

**Como testar:**

1. Fornecedor: Locadora Parceira Sul
2. Número `CP-2026-001` · Título `Contrato Repasse Sul 2026`
3. Modelo negócio: **REPASSE** · Tipo cálculo: **percentual_receita** ou **tabela**
4. Percentual repasse: `85` % (ou use tabela abaixo)
5. Vigência: hoje → +1 ano · Prazo pagamento: 30 dias
6. **Salvar** → status **Ativo**

### Adicionar faixa de preço (na edição do contrato)

1. Categoria **Econômico** · Vigência início hoje
2. Valor cliente diária: R$ **150,00**
3. Valor repasse diária: R$ **127,50**
4. **Adicionar faixa**

**Resultado esperado:** Contrato listado em Contratos Parceiros; faixa visível na edição.

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Contrato **inativo/expirado** | Veículos terceirizados **sem** contrato válido → reserva **falha** |
| Alterar percentual/tabela | **Novas** reservas recalculam repasse; contratos já abertos mantêm snapshot |
| Modelo **COMISSÃO** | Gera `valor_comissao` em vez de CP repasse; margem = comissão |
| Excluir contrato 🔒 | Veículos/reservas vinculadas bloqueiam |

---

## INT-003 — Veículo terceirizado

**Menu:** Frota → Veículos → **+ Novo**

1. Placa `TER3C01` · mesma categoria/marca/modelo do catálogo
2. Propriedade: **terceirizada**
3. Fornecedor: Locadora Parceira Sul
4. Contrato fornecedor: `CP-2026-001`
5. Marque **Publicar no site** · **Exige aprovação do fornecedor**
6. Proprietário: `Locadora Parceira Sul`
7. **Salvar**

**Resultado esperado:** Listagem de veículos mostra badge **terceirizada**.

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Veículo terceirizado sem fornecedor/contrato | Formulário/serviço **rejeita** |
| `publicar_site` + sync | API pública `/api/v1/public/veiculos` lista veículo |
| Alocar em reserva | Preenche campos intermediação (fornecedor, repasse, margem) |
| Veículo terceirizado | Check-out/check-in igual frota própria + lançamento repasse no encerramento |

---

## INT-004 — Indisponibilidade do parceiro

**Menu:** Intermediação → Indisponibilidades · `/intermediacao/indisponibilidades`

**Como testar:**

1. Veículo `TER3C01` · Parceiro Sul · Início agora · Fim D+2
2. Motivo: `locado_pelo_proprietario` · Marque **Remover do site**
3. **Registrar bloqueio**
4. Confirme veículo **Bloqueado** na frota
5. Clique **Encerrar** na linha da indisponibilidade

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Registrar indisponibilidade | Veículo **bloqueado** · `publicar_site=false` se sync |
| Encerrar | Veículo **disponível** · site republicado se config permitir |
| Indisponibilidade ativa | **Disponibilidade** não oferece o veículo |

---

## INT-005 — Reserva terceirizada + aprovação

**Menu:** Reservas → Nova Reserva · `/reservas/nova`

**Pré-requisito:** Config com aprovação manual (INT-001).

**Como testar:**

1. Período D+1 → D+4 · Filial Matriz
2. Consulte **Disponibilidade** — confirme `TER3C01` ou categoria com terceirizado
3. Selecione veículo **TER3C01** · Cliente João Silva
4. **Salvar** reserva
5. Abra detalhe da reserva → bloco **Intermediação** com status `pendente_aprovacao`, repasse e margem
6. Tente **Confirmar reserva** → deve **falhar** (intermediação pendente)
7. **Intermediação → Aprovações pendentes** → **Aprovar locadora parceira**
8. Volte à reserva → status intermediação `confirmado_fornecedor`
9. **Confirmar reserva** → sucesso
10. Emitir PDF **Confirmação reserva terceirizada**

**⚡ Efeitos em cascata:**

| Etapa | Impacto |
|-------|---------|
| Reserva criada | Snapshot repasse gravado (`valor_repasse_total`, `valor_margem`, JSON) |
| Pendente | Notificação in-app/e-mail/SMS ao contato operacional (se configurado) |
| Automação | Evento `intermediacao_pendente` / `intermediacao_aprovada` |
| Rejeitar aprovação | Reserva **cancelada** · status `rejeitado_fornecedor` |
| Confirmar | Veículo **Reservado** · calendário atualizado |

---

## INT-006 — Contrato e encerramento com repasse

**Como testar:**

1. Na reserva confirmada → **Gerar contrato**
2. Abra contrato → bloco **Intermediação** (parceiro, repasse, margem)
3. Execute **Check-out** → **Check-in** → **Encerramento** (FASE 8)
4. **Intermediação → Repasses / Comissões** — lançamento `em_aberto` ou pago
5. **Financeiro → Contas a Pagar** — título origem **REPASSE_LOCACAO** (se gerado)
6. Relatórios → Gerencial: `intermediacao_margem_parceiro`, `intermediacao_repasses_pendentes`

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Gerar contrato com intermediação pendente 🔒 | **Bloqueado** |
| Encerrar contrato terceirizado | CR cliente + CP repasse parceiro (modelo REPASSE) |
| Margem abaixo do mínimo | Erro já na **criação** da reserva (validação upstream) |

---

## INT-007 — Teste modelo COMISSÃO (opcional)

1. Duplique contrato parceiro com modelo **COMISSÃO** · percentual comissão 15%
2. Veículo terceirizado B ou altere contrato do TER3C01
3. Nova reserva → confirme `valor_comissao` preenchido · `valor_repasse_total` zero
4. Encerramento → lançamento reflete comissão

---

## INT-008 — API pública veículos (site)

**Menu:** Integrações → API Pública · escopo `veiculos:read`

1. Gere API Key com escopo veículos
2. Teste:

```bash
curl -H "X-API-Key: SUA_CHAVE" "http://localhost:8000/api/v1/public/veiculos"
```

**⚡ Efeitos em cascata:** Lista só veículos com `publicar_site=true` e disponíveis; sync INT-001 atualiza flags.

---

# FASE 4 — Tarifário

> **Motor de preço** — tudo aqui afeta valor de reserva, contrato e simulador.

| Passo | Menu | Ação | Ref |
|-------|------|------|-----|
| Tabela | Tarifário → Tabelas | `Tarifa Padrão Matriz` · canal balcão · diária 1–3d R$ 120 | 050 |
| Temporada | Tarifário → Temporadas | Multiplicador alta temporada | 051 |
| Taxa | Tarifário → Taxas | Taxa entrega R$ 45 fixa | 052 |
| Proteção | Tarifário → Proteções | LDW R$ 35/dia · franquia R$ 1.500 | 053 |
| Cancelamento | Tarifário → Políticas | Faixas >72h 0% · 24–72h 20% · <24h 100% | 054 |
| Simular | Tarifário → Simular Preço | Mesmos dados reserva → conferir total | 055 |

**⚡ Efeitos em cascata:**

| Alteração | Impacto |
|-----------|---------|
| Editar diária tabela (PASSO 211) | Simulador e **novas** reservas mudam; contratos abertos mantêm snapshot |
| Temporada sobreposta | Sistema aplica regra de prioridade/overlap |
| Taxa/proteção | Linhas extras na reserva/contrato |
| Política cancelamento | Valor retenção ao cancelar/no-show |
| Cupom (FASE 6) | Desconto sobre total calculado pelo tarifário |

---

# FASE 5 — Manutenção

| Passo | Menu | Fluxo | Ref |
|-------|------|-------|-----|
| Peça | Manutenção → Peças | `FILTRO-001` estoque | 060 |
| Preventiva | Manutenção → Preventiva | Plano por KM/dias | 061 |
| OS corretiva | Manutenção → OS | Abrir → itens → concluir | 062 |
| Pneu | Manutenção → Pneus | Cadastro · rodízio · descarte | 063 |

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| OS **aberta** | Veículo indisponível na consulta de reservas |
| OS concluída | Veículo disponível; estoque peças baixa; CP fornecedor |
| Valor OS > limite | Workflow aprovação (PASSO 205) |
| Preventiva vencida | Alerta Dashboard |

---

# FASE 6 — Comercial / CRM

| Passo | Menu | Ação | Ref |
|-------|------|------|-----|
| Cupom | Comercial → Cupons | `VERAO2026` 10% | 070 |
| Funil | Comercial → Funil | Nova oportunidade | 071 |
| Proposta | Comercial → Propostas | Itens · enviar · aceitar (PASSO 206) | 072 |
| Campanha | Comercial → Campanhas | E-mail/SMS simulado | 073 |
| Fidelidade | Comercial → Fidelidade | Tiers pontos | 074 |

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Aceitar proposta | Gera reserva/contrato automaticamente |
| Cupom na reserva | Desconto · uso registrado |
| Campanha | Notificações → Histórico de envios |
| Fidelidade no encerramento | Pontos creditados |

---

# FASE 7 — Reservas

| Passo | Menu | Ação | Ref |
|-------|------|------|-----|
| Disponibilidade | Reservas → Disponibilidade | Período D+1/D+4 · ver TST1A23 | 080 |
| Cotação | Reservas → Cotações | Criar · converter | 081 |
| Nova reserva | Reservas → Nova | Veículo **TST1A23** · cliente João · motorista · proteções | 082 |
| Confirmar | Detalhe reserva | Confirmar · veículo Reservado | 083 |
| Calendário | Reservas → Calendário | Evento visível | 084 |
| PDFs | Detalhe | Confirmação · voucher | 085 |
| Contrato | Detalhe | **Gerar contrato** | 086 |

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Confirmar | Status confirmada · webhook `reserva.confirmada` · veículo reservado |
| Cancelar (PASSO 200) | Política retencão · veículo liberado |
| No-show (PASSO 201) | Job ou manual · veículo liberado |
| Cliente bloqueado (PASSO 202) | Exige aprovação antes confirmar |
| Reserva terceirizada | Ver FASE 3B — fluxo paralelo |

---

# FASE 8 — Locações (contrato completo)

| Passo | Menu | Ação | Ref |
|-------|------|------|-----|
| Contrato balcão | Locações → Contratos → Novo | Sem reserva (opcional) | 090 |
| Check-out | Locações → Check-out | KM · combustível · fotos · concluir | 091 |
| PDFs | Detalhe contrato | Contrato · termo · vistoria saída | 092 |
| Renovação | Locações → Renovações | Aditivo · nova data | 093 |
| Multa | Locações → Multas | Vincular veículo/contrato | 094 |
| Avaria | Locações → Avarias | Severidade · fotos | 095 |
| Check-in | Locações → Check-in | KM · combustível · extras | 096 |
| Encerramento | Locações → Encerramentos | Contrato encerrado | 098 |
| Cancelar rascunho | Detalhe | Se existir contrato rascunho | 099 |

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Check-out | Contrato **Ativo** · veículo **Locado** · PDFs · caixa |
| Renovação | Aditivo · nova devolução · valor adicional |
| Check-in | Contrato **Encerrado** · veículo **Disponível** |
| Encerramento | Gera/atualiza **Contas a Receber** · fidelidade · repasse intermediação |
| Multa/avaria | Títulos extras · responsabilização |
| Reabrir encerramento | Permissão especial · rever financeiro |

---

# FASE 9 — Financeiro

| Passo | Menu | Ação | Ref |
|-------|------|------|-----|
| Abrir caixa | Financeiro → Caixa | Sessão filial Matriz | 100 |
| Lançamento | Caixa detalhe | Entrada/saída | 101 |
| Fechar caixa | Caixa | Conferência | 102 |
| CR manual | Financeiro → Contas a Receber | Título avulso | 103 |
| CP manual | Financeiro → Contas a Pagar | Fornecedor oficina | 104 |
| PIX | Financeiro → PIX | Chave · cobrança | 105 |
| Cartão | Financeiro → Cartões | Pré-autorização | 106 |
| Banco | Financeiro → Bancos | Conta bancária | 107 |
| Conciliação | Financeiro → Conciliação | Upload OFX | 108 |
| Faturamento | Financeiro → Faturamento | Cliente PJ · fatura mensal | 109 |

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| Encerrar contrato | CR vinculada ao contrato |
| Repasse intermediação | CP origem **REPASSE_LOCACAO** |
| Baixar CR | Conciliação · inadimplência · bloqueio cliente |
| Estornar (PASSO 212) | Reverte saldo |
| Faturamento PJ | Agrupa títulos · NFS-e em lote |

---

# FASE 10 — Fiscal

| Passo | Menu | Ação | Ref |
|-------|------|------|-----|
| Config impostos | Fiscal → Impostos | Regime · alíquotas | 110 |
| NFS-e | Fiscal → NFS-e | Emitir simulada | 111 |
| NF-e | Fiscal → NF-e | Emitir simulada | 112 |
| XML | Fiscal → XML | Importar arquivo | 113 |
| Cancelamento | Fiscal → Cancelamentos | Cancelar NFS-e teste | 114 |
| Apuração | Fiscal → Impostos → Apuração | Mês corrente | 115 |

**⚡ Efeitos em cascata:**

| Ação | Impacto |
|------|---------|
| NFS-e emitida | XML armazenado · relatório fiscal |
| Cancelamento | Status cancelado · apuração |
| Import XML | Vínculo CP fornecedor |

---

# FASE 11 — Dashboard e Relatórios

### Dashboard (PASSO 120)

**Menu:** Dashboard `/` — confira widgets após dados das fases anteriores.

### Emitir os 31 relatórios

**Menu:** Relatórios → [categoria] → Emitir

| Categoria | Códigos (emitir todos PDF) |
|-----------|----------------------------|
| **Frota** (6) | `frota_atual`, `rentabilidade_veiculo`, `ociosidade_ocupacao`, `tco_veiculo`, `idade_media_frota`, `vencimentos_documentacao` |
| **Locação** (8) | `contratos_periodo`, `ticket_medio`, `tempo_medio_locacao`, `taxa_renovacao`, `taxa_no_show_cancelamento`, `ranking_clientes`, `avarias_responsabilizacao`, `multas_relatorio` |
| **Intermediação** (2) | `intermediacao_margem_parceiro`, `intermediacao_repasses_pendentes` |
| **Financeiro** (6) | `dre_simplificado`, `fluxo_caixa`, `inadimplencia_aging`, `faturamento_segmento`, `comissoes_pagas`, `conciliacao_resumo` |
| **Fiscal** (4) | `notas_periodo`, `apuracao_impostos`, `export_contabilidade`, `divergencias_fiscais` |
| **Gerencial** (5) | `painel_executivo`, `comparativo_filiais`, `metas_vendedores`, `sazonalidade`, `projecao_demanda` |

### Agendamento (PASSO 126)

**Relatórios → Agendamentos → + Novo** — DRE mensal automático.

### Documentos PDF (PASSO 127)

**Relatórios → Documentos PDF** — confirme ≥20 emissões · re-download.

**⚡ Efeitos em cascata:** Relatórios pesados rodam via Celery; histórico em `/relatorios/historico`.

---

# FASE 12 — Integrações e API pública

| Passo | Integração | Ação | Ref |
|-------|------------|------|-----|
| Pagamentos | Integrações → Pagamentos | Simulador · testar conexão | 130 |
| DETRAN | Integrações → Trânsito | Multas · CNH · débitos | 131 |
| Crédito | Integrações → Crédito | Score cliente João | 132 |
| Telemetria | Integrações → Telemetria | Sync dispositivos | 133 |
| API pública | Integrações → API Pública | Key · webhook · curl disponibilidade/reserva | 134–136 |

**⚡ Efeitos em cascata:**

| Integração | Impacto |
|------------|---------|
| API reserva website | Reserva origem `website` · webhook dispara |
| Webhook | Log outbound · retry automações |
| Pagamento | Baixa CR automática (quando configurado) |

---

# FASE 13 — Automações

| Passo | Menu | Ação | Ref |
|-------|------|------|-----|
| Regra | Automações → Regras | Gatilho documento.vencendo | 140 |
| Workflow | Automações → Workflows | Aprovação desconto | 141 |
| Jobs | Automações → Agendamentos | Rodar agora (Beat) | 142 |
| Histórico | Automações → Histórico | Ver execuções | 143 |

**Jobs relevantes intermediação:**

- `intermediacao.sincronizar_site` — sync catálogo terceiros
- `intermediacao.lembrete_aprovacao` — lembrete reservas pendentes

**⚡ Efeitos em cascata:** Regras disparam notificações (FASE 14) e histórico imutável.

---

# FASE 14 — Notificações

| Passo | Menu | Ação | Ref |
|-------|------|------|-----|
| Inbox | Notificações → Caixa de Entrada | Marcar lidas | 150 |
| Envios | Notificações → Histórico de Envios | Campanhas e alertas | 151 |

---

# FASE 15 — Auditoria

**Menu:** Auditoria → Trilha · `/auditoria/trilha`

1. Filtre entidade `loc_contrato` · usuário admin · hoje
2. Confirme eventos check-out/check-in
3. Exporte PDF se disponível

**⚡ Efeitos em cascata:** Trilha **imutável** — não edita/deleta eventos.

---

# FASE 16 — Testes por papel (RBAC)

Faça **logout** (`/logout`) antes de cada bloco.

| Passo | Login | Deve conseguir | Não deve ver/fazer | Ref |
|-------|-------|----------------|-------------------|-----|
| Vendedor | vendedor@… | Reservas, cotações, comercial | Financeiro, config usuários | 170 |
| Operador | operador@… | Check-out/in, caixa | Papéis, fiscal completo | 171 |
| Financeiro | financeiro@… | CR/CP, fiscal, relatórios fin. | Config papéis | 172 |
| Diretoria | diretoria@… | Dashboard, relatórios | Botões criar/editar | 173 |
| Auditor QA | qa.auditor@… | Auditoria, relatórios leitura | Criar registros | 174 |

**Intermediação por papel:**

| Papel | Intermediação |
|-------|---------------|
| Admin / Gerente filial | Config, contratos, aprovar, repasses |
| Operador | Indisponibilidades, aprovar (se permissão) |
| Vendedor | Visualizar config/contratos · **não** editar repasse |
| Auditor | Somente visualizar |

---

# FASE 17 — Regressão automatizada

```bash
python -m pytest tests/ -q
python -m pytest tests/test_spec_compliance.py -v
python -m pytest tests/test_intermediacao.py -v
```

**Critério:** 100% passed (224+ testes).

Opcional Playwright: `cd e2e && npx playwright test`

Script E2E dados reais: `python -m scripts.run_teste_md_e2e`

---

# FASE 18 — Cenários extras e bordas

Execute após FASE 8 ou quando o dado existir (detalhes em `teste.md` PASSO 200–216):

| PASSO | Cenário | O que valida |
|-------|---------|--------------|
| 200 | Cancelar reserva | Política · libera veículo |
| 201 | No-show | Status · disponibilidade |
| 202 | Cliente bloqueado + aprovação | RBAC override |
| 203 | Bloquear/liberar veículo | Disponibilidade |
| 204 | Baixar veículo (venda) | Status terminal |
| 205 | OS valor alto | Workflow aprovação |
| 206–208 | Proposta/funil | CRM integrado |
| 209–210 | Peças/pneus | Estoque |
| 211 | Editar tarifa | Preço downstream |
| 212–213 | Estorno CR · cancelar NF-e | Reversões |
| 214–216 | Webhook · logout · 2FA completo | Segurança |

---

# Matriz global de efeitos em cascata

Use esta tabela quando **alterar ou excluir** qualquer registro — verifique a coluna direita **antes** de confirmar.

| Se você… | Verifique imediatamente… |
|----------|--------------------------|
| Cria **cliente** | Reserva, contrato, CR, NFS-e, CRM, API |
| **Bloqueia** cliente | Nova reserva pede aprovação |
| Cria **veículo próprio** | Disponibilidade, reserva, OS |
| Cria **veículo terceirizado** | Intermediação, contrato parceiro, site, aprovação |
| **Confirma** reserva | Veículo reservado · calendário · webhook |
| **Aprova** intermediação | Libera confirmar reserva |
| **Rejeita** intermediação | Reserva cancelada |
| **Gera contrato** | Check-out habilitado · PDF contrato |
| **Check-out** | Veículo locado · caixa · vistoria |
| **Check-in / encerra** | Veículo disponível · CR · repasse CP · fidelidade |
| Abre **OS** | Veículo indisponível |
| Conclui **OS** | Veículo disponível · estoque · CP |
| Altera **tabela tarifa** | Simulador · novas reservas (não contratos com snapshot) |
| Emite **NFS-e** | XML · apuração · relatório fiscal |
| **Sync site** intermediação | API pública veículos |
| **Seed** papéis | Menus Intermediação nos perfis |
| **Encerra indisponibilidade** | Veículo terceiro disponível · site |

### Cadeias de seleção (não pule)

```
Marca → Modelo → Veículo
Categoria → Tarifa → Preço reserva
Fornecedor parceiro → Contrato intermediação → Veículo terceirizado → Reserva → Aprovação → Contrato → Repasse
Cliente → Reserva → Contrato → Financeiro → Fiscal
Filial → Caixa · Disponibilidade · Parâmetros
UF → Município (endereços)
Retirada → Devolução (mín. +1h)
```

### Exclusão bloqueada (RESTRICT) — o que o sistema impede

| Tentativa | Bloqueado por |
|-----------|---------------|
| Excluir cliente | Reserva/contrato/fatura ativos |
| Excluir veículo | Contrato/OS/multa ativos |
| Excluir categoria/marca/modelo | Veículos vinculados |
| Excluir filial | Caixa aberto, contratos |
| Excluir contrato parceiro | Veículos/reservas terceirizadas |
| Gerar contrato | Intermediação pendente/rejeitada |

---

# Checklist por menu

Marque `[x]` quando **todos** os passos da seção estiverem OK.

| # | Seção menu | Submenus | OK |
|---|------------|----------|-----|
| 1 | Dashboard | — | [ ] |
| 2 | Cadastros | Clientes, Motoristas, Parceiros, Fornecedores, Vendedores, Tabelas | [ ] |
| 3 | Frota | Veículos, Categorias, Marcas, Modelos, Combustíveis, Acessórios, Documentação, Telemetria | [ ] |
| 4 | **Intermediação** | **Config, Contratos, Indisponibilidades, Aprovações, Repasses** | [ ] |
| 5 | Manutenção | OS, Preventiva, Corretiva, Peças, Pneus | [ ] |
| 6 | Reservas | Nova, Listagem, Calendário, Disponibilidade, Cotações | [ ] |
| 7 | Locações | Contratos, Check-out, Check-in, Renovações, Encerramentos, Multas, Avarias | [ ] |
| 8 | Comercial | Funil, Propostas, Campanhas, Cupons, Fidelidade | [ ] |
| 9 | Tarifário | Tabelas, Temporadas, Taxas, Proteções, Cancelamento, Simular | [ ] |
| 10 | Financeiro | Caixa, Receber, Pagar, PIX, Cartões, Bancos, Conciliação, Faturamento | [ ] |
| 11 | Fiscal | NFS-e, NF-e, XML, Cancelamentos, Impostos | [ ] |
| 12 | Relatórios | 6 categorias (31 relatórios) + Histórico + Agendamentos + Documentos PDF | [ ] |
| 13 | Integrações | Pagamentos, Trânsito, Crédito, Telemetria, API Pública | [ ] |
| 14 | Automações | Regras, Workflows, Agendamentos, Histórico | [ ] |
| 15 | Notificações | Inbox, Envios | [ ] |
| 16 | Configurações | Empresa, Filiais, Usuários, Papéis, 2FA, Parâmetros | [ ] |
| 17 | Auditoria | Trilha | [ ] |

**Totais:** 17 seções · 86 itens de menu folha · 31 relatórios · 26+ templates PDF · módulo Intermediação completo.

---

# Apêndices

## A — Rotas principais (admin)

| Módulo | Rotas |
|--------|-------|
| Login | `/login`, `/logout`, `/configuracoes/seguranca` |
| Cadastros | `/cadastros/clientes`, `/motoristas`, `/parceiros`, `/fornecedores`, `/vendedores`, `/tabelas` |
| Frota | `/frota/veiculos`, `/categorias`, `/marcas`, `/modelos`, `/combustiveis`, `/acessorios`, `/documentacao`, `/telemetria` |
| Intermediação | `/intermediacao/config`, `/contratos-fornecedor`, `/indisponibilidades`, `/aprovacoes`, `/repasses` |
| Reservas | `/reservas/nova`, `/reservas`, `/calendario`, `/disponibilidade`, `/cotacoes` |
| Locações | `/locacoes/contratos`, `/checkout`, `/checkin`, `/renovacoes`, `/encerramentos`, `/multas`, `/avarias` |
| Financeiro | `/financeiro/caixa`, `/receber`, `/pagar`, `/pix`, `/cartoes`, `/bancos`, `/conciliacao`, `/faturamento` |
| Fiscal | `/fiscal/nfse`, `/nfe`, `/xml`, `/cancelamentos`, `/impostos` |
| Relatórios | `/relatorios/{frota,locacao,financeiro,fiscal,gerencial}`, `/historico`, `/agendamentos` |
| Documentos | `/documentos/historico`, POST `/documentos/emitir/{template}/{id}` |

## B — Formulários web (inventário 100+)

Referência técnica de templates: 44 arquivos `*_form.html` + formulários inline em listas/detalhes (reserva, contrato, caixa, aprovações intermediação, etc.). Cada tela POST exige **CSRF token** e permissão RBAC.

Principais formulários admin para validar manualmente:

- `cliente_form`, `veiculo_form` (próprio **e** terceirizado), `fornecedor_form` (locadora parceira)
- `intermediacao/config`, `contrato_form` (contrato parceiro), `indisponibilidades_list`
- `reservas/nova`, `reservas/detalhe` (aprovação cliente **e** parceiro)
- `contrato_detalhe` (bloco intermediação), `checkout_form`, `checkin_form`
- `receber_form`, `pagar_form`, `nfse_form`, `nfe_form`

## C — PDFs emitíveis (smoke mínimo)

Emita pelo menos 1 de cada grupo durante o teste:

- Cliente: ficha, extrato, quitação
- Veículo: ficha veículo
- Reserva: confirmação (própria e **terceirizada**)
- Contrato: contrato, termo, vistoria saída/devolução, aditivo, recibo caução
- Fiscal: DANFE/DANFSE simulados

## D — Permissões Intermediação

| Código | Função |
|--------|--------|
| `intermediacao.config.visualizar/editar` | Config + sync site |
| `intermediacao.contrato.visualizar/criar/editar` | Contratos parceiros |
| `intermediacao.indisponibilidade.visualizar/criar/editar` | Bloqueios + encerrar |
| `intermediacao.reserva.aprovar` | Aprovações pendentes |
| `intermediacao.repasse.visualizar` | Repasses/comissões |

---

# Registro de defeitos

| Fase/Passo | Severidade | Descrição | Evidência (print/log) | Status |
|------------|------------|-----------|------------------------|--------|
| | | | | |

---

**Documento:** INFO-FORMS v2.0 — Manual do Administrador  
**Alinhado a:** `app/web/navigation.py`, `teste.md`, módulo `app/modules/intermediacao/`  
**Última revisão:** 2026-07-17 — inclui intermediação REPASSE/COMISSÃO, aprovações, repasses financeiros e migration Supabase 0023.
