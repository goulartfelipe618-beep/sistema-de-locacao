# INFO-FORMS — Especificação Robusta de Formulários do ERP Locadora

**Versão:** 1.0  
**Data:** 2026-07-16  
**Escopo:** 100% dos formulários web do painel administrativo (100 formulários/interações catalogados)  
**Objetivo:** Elevar formulários funcionais porém simples para formulários **intuitivos, validados, encadeados e seguros**, com máscaras, sinalização de obrigatoriedade, campos dependentes, lookups assíncronos e matriz clara de impacto entre entidades.

---

## Sumário

1. [Diagnóstico do estado atual](#1-diagnóstico-do-estado-atual)
2. [Catálogo de 38 tipos de campo (T01–T38)](#2-catálogo-de-38-tipos-de-campo-t01t38)
3. [Padrões globais de UX e layout](#3-padrões-globais-de-ux-e-layout)
4. [Matriz de dependências e impacto entre entidades](#4-matriz-de-dependências-e-impacto-entre-entidades)
5. [Inventário completo por módulo (100 formulários)](#5-inventário-completo-por-módulo-85-formulários)
6. [Especificações detalhadas — formulários prioritários](#6-especificações-detalhadas--formulários-prioritários)
7. [Motor técnico recomendado](#7-motor-técnico-recomendado)
8. [Roadmap de implementação](#8-roadmap-de-implementação)

---

## 1. Diagnóstico do estado atual

### 1.1 O que já funciona bem

- Cobertura funcional ampla: cadastro → reserva → contrato → financeiro → fiscal.
- Schemas Pydantic com validação server-side em todos os módulos.
- RBAC por rota; CSRF em mutações web.
- Alguns formulários já têm seções numeradas (ex.: Nova Reserva).
- ViaCEP parcial no cliente (autopreenchimento de endereço ao sair do CEP).

### 1.2 Lacunas identificadas (aplicar em TODOS os formulários)

| Lacuna | Impacto | Solução alvo |
|--------|---------|--------------|
| Sem asterisco/padrão visual de obrigatoriedade consistente | Usuário não sabe o mínimo para salvar | Classe `.form-label--required` + legenda no rodapé |
| Inputs sem máscara (CPF, CNPJ, placa, telefone, moeda) | Dados inconsistentes no banco | `data-mask` + normalização no submit |
| Datas sem placeholder `dd/mm/aaaa` em campos text | Confusão de formato | Máscara BR ou `type="date"` com locale |
| Selects estáticos sem busca (cliente, veículo) | Ilegível com centenas de registros | Combobox async com debounce |
| Campos dependentes não encadeados (UF→cidade, marca→modelo) | Dados incoerentes | Cascata via API + desabilitar filho até pai |
| PF/PJ mostra CPF e CNPJ juntos | Ruído visual | Toggle condicional por `person_type` |
| Sem feedback inline de erro por campo | Só alerta genérico no topo | `.form-error` abaixo do input + `aria-invalid` |
| Sem confirmação em ações destrutivas | Exclusão acidental | Modal + texto do impacto (matriz §4) |
| Valores monetários como texto livre | `1.234,56` vs `1234.56` | Tipo T15 (moeda BRL) |
| Formulários longos sem agrupamento visual | Fadiga cognitiva | Fieldsets, tabs ou accordion por seção |

### 1.3 Métricas do inventário

| Métrica | Valor |
|---------|-------|
| Templates `*_form.html` | 44 |
| Formulários de página (sem sufixo `_form`) | 4 |
| Formulários inline em listas/detalhes | 41 |
| **Total catalogado** | **100** |
| Módulos com formulários | 15 de 16 (notificações só ações) |

---

## 2. Catálogo de 38 tipos de campo (T01–T38)

Cada campo de formulário DEVE declarar: `{ tipo, id, name, label, obrigatorio, mascara, depende_de, validacao, placeholder, dica, readonly_em_edicao }`.

### 2.1 Texto e identificação

| ID | Tipo | Máscara / Formato | Placeholder | Validação | Exemplo de uso |
|----|------|-------------------|-------------|-----------|----------------|
| **T01** | Texto curto | — | — | min/max length | Nome, código |
| **T02** | Texto longo | — | — | max 2000 | Descrição, laudo |
| **T03** | Textarea | — | — | max linhas | Observações |
| **T04** | E-mail | — | `nome@empresa.com` | RFC + lowercase | email |
| **T05** | CPF | `000.000.000-00` | `000.000.000-00` | dígito verificador | PF cliente/motorista |
| **T06** | CNPJ | `00.000.000/0000-00` | `00.000.000/0000-00` | dígito verificador | PJ cliente/fornecedor |
| **T07** | CPF ou CNPJ dinâmico | T05 ou T06 | — | conforme person_type | Parceiro, fornecedor |
| **T08** | Placa Mercosul | `AAA0A00` / `AAA-0000` | `ABC1D23` | regex BR | Veículo |
| **T09** | RENAVAM | `00000000000` (11 díg.) | — | 9–11 dígitos | Veículo |
| **T10** | Chassi (VIN) | `AAAAAAAAAAAAAAAAA` | 17 chars | 17 alfanum. | Veículo |
| **T11** | Telefone fixo | `(00) 0000-0000` | — | 10 dígitos | telefone |
| **T12** | Celular | `(00) 00000-0000` | — | 11 dígitos | celular |
| **T13** | CEP | `00000-000` | `00000-000` | 8 dígitos + ViaCEP | Endereço |
| **T14** | UF | select 27 UFs | — | enum IBGE | uf |
| **T15** | Moeda BRL | `R$ 0.000,00` | `R$ 0,00` | ≥ 0, 2 decimais | valores financeiros |
| **T16** | Percentual | `0,00 %` | `0,00` | 0–100 | comissão, alíquota |
| **T17** | Inteiro | `0` | — | min/max | KM, ano, prioridade |
| **T18** | Ano | `0000` | `2026` | 1980–2100 | ano fabricação |
| **T19** | Chave PIX | tipo detectado | — | CPF/CNPJ/email/phone/EVP | pix_chave |
| **T20** | Código alfanum. | `AAAA-0000` | — | uppercase | cupom, pneu |

### 2.2 Datas e horários

| ID | Tipo | Máscara / Formato | Placeholder | Validação | Exemplo |
|----|------|-------------------|-------------|-----------|---------|
| **T21** | Data | `dd/mm/aaaa` | `dd/mm/aaaa` | data válida | vencimento |
| **T22** | Data-hora | `dd/mm/aaaa HH:mm` | — | retirada ≤ devolução | reserva |
| **T23** | Data-hora local HTML | `datetime-local` | — | timezone tenant | retirada_em |
| **T24** | Hora | `HH:mm` | `08:00` | 00:00–23:59 | agendamento |
| **T25** | Período (início/fim) | par T21/T22 | — | fim ≥ início | vigência tabela |
| **T26** | Data relativa | presets | — | — | "Hoje", "+7 dias" (atalhos) |

### 2.3 Seleção e relacionamentos

| ID | Tipo | Comportamento | API / Fonte | Exemplo |
|----|------|---------------|-------------|---------|
| **T27** | Select estático | enum fixo | — | status, tipo |
| **T28** | Select FK simples | lista curta (<30) | GET cache | categoria frota |
| **T29** | Combobox async | busca + paginação | `/api/v1/cadastros/clientes?search=` | cliente |
| **T30** | Select encadeado | desabilita até pai | `/api/v1/frota/modelos?marca_id=` | marca→modelo |
| **T31** | UF → Município IBGE | cascata | `/api/v1/util/ibge/ufs` + `/municipios/{uf}` | endereço |
| **T32** | Multi-select | chips + busca | — | motoristas reserva |
| **T33** | Checkbox único | boolean | — | tributável, gera_pix |
| **T34** | Checkbox grupo | array | — | proteções, taxas |
| **T35** | Radio grupo | enum visual | — | person_type PF/PJ |
| **T36** | Toggle switch | boolean estilizado | — | is_active |
| **T37** | Autocomplete entidade | criação rápida inline | modal "Cadastrar cliente" | cliente novo na reserva |
| **T38** | Upload arquivo | drag-drop + validação MIME | — | XML fiscal, certificado A1 |

### 2.4 Tipos compostos / avançados (recomendados)

| ID | Tipo | Descrição |
|----|------|-----------|
| **T39** | Repeater (lista dinâmica) | Itens de proposta, faixas cancelamento, alíquotas imposto |
| **T40** | Endereço composto | CEP + logradouro + número + compl + bairro + UF + cidade (T13+T31) |
| **T41** | Money range | faixa min/max desconto |
| **T42** | KM + combustível par | checkout/checkin (slider 0–8) |
| **T43** | JSON editor | condicao_json automações (modo avançado) |
| **T44** | Color picker | brand_primary_color empresa |
| **T45** | Password + strength | senha usuário, certificado A1 |

---

## 3. Padrões globais de UX e layout

### 3.1 Obrigatoriedade

```html
<label class="form-label form-label--required" for="nome">
  Nome / Razão Social
</label>
```

- Asterisco vermelho `*` após label de campos obrigatórios.
- Legenda fixa no rodapé do formulário: `* Campos obrigatórios`.
- Campos condicionalmente obrigatórios: classe `form-label--required-when` + tooltip explicando a regra.
- Server: manter validação Pydantic; client: HTML5 `required` + validação JS antes do submit.

### 3.2 Máscaras e normalização

| Entrada usuário | Armazenamento DB | Biblioteca sugerida |
|-----------------|------------------|---------------------|
| `123.456.789-00` | `12345678900` | IMask.js ou Cleave.js |
| `R$ 1.234,56` | `Decimal("1234.56")` | IMask Number |
| `13/07/2026` | `date(2026,7,13)` | flatpickr pt-BR |
| `(11) 98765-4321` | `11987654321` | IMask |

**Regra:** máscara na exibição; normalização no `submit` (hidden fields ou JS no handler).

### 3.3 Layout por complexidade

| Complexidade | Layout | Exemplos |
|--------------|--------|----------|
| Simples (≤8 campos) | Card único, grid 2 colunas | Marca, combustível |
| Médio (9–20) | Fieldsets com título | Motorista, parceiro |
| Complexo (21+) | Tabs ou accordion numerado | Reserva, veículo, contrato |
| Wizard transacional | Stepper 1→N + resumo | Reserva → contrato |

### 3.4 Fieldsets padrão (nomenclatura)

1. **Identificação** — nome, documento, status  
2. **Contato** — e-mail, telefones  
3. **Endereço** — CEP, logradouro, UF/cidade  
4. **Comercial** — limites, comissões, categorias  
5. **Operacional** — FKs de negócio  
6. **Financeiro** — valores, vencimentos  
7. **Observações** — textarea full-width  

### 3.5 Feedback e estados

| Estado | Visual |
|--------|--------|
| Vazio | placeholder + dica `.form-help` |
| Foco | borda `--primary` |
| Válido | ícone ✓ discreto (opcional) |
| Inválido | borda vermelha + `.form-error` + `aria-describedby` |
| Desabilitado | opacity 0.6 + cursor not-allowed |
| Carregando lookup | spinner no select + "Buscando..." |
| Readonly (edição) | fundo cinza — CPF após criação |

### 3.6 Ações do formulário

- **Salvar** (primary) — valida e submete.
- **Salvar e continuar** — permanece na edição (formulários longos).
- **Cancelar** — link; confirma se `dirty`.
- **Excluir** — vermelho, separado, com modal de impacto (§4).

---

## 4. Matriz de dependências e impacto entre entidades

### 4.1 Legenda `ondelete`

| Código | Significado | Ação na UI ao excluir/inativar |
|--------|-------------|--------------------------------|
| **R** | RESTRICT — bloqueia exclusão | Modal: "Existem N contratos/reservas vinculados" |
| **C** | CASCADE — exclui filhos | Aviso: "Excluirá também X registros" |
| **S** | SET NULL — desvincula | Aviso: "Referências ficarão vazias em Y registros" |
| **I** | Inativação lógica (soft delete) | Preferir inativar vs excluir |

### 4.2 Entidades cadastrais → impacto downstream

#### Cliente (`clientes`)

| Vinculado em | ondelete | Impacto ao excluir/inativar/bloquear |
|--------------|----------|--------------------------------------|
| Reserva | R | Não pode excluir com reserva ativa |
| Contrato | R | Idem |
| Conta a Receber | S | Títulos ficam sem cliente |
| Fatura | R | Bloqueia exclusão |
| NFS-e / NFe destinatário | S | Notas mantidas, sem FK cliente |
| Oportunidade CRM | S | Funil perde vínculo |
| Tabela preço dedicada | S | Tarifa perde cliente |
| Fidelidade | C | Conta pontos excluída |
| Faturamento config | C | Config removida |

**Regras UI:**
- Bloquear cliente (`blacklist=true`) → aviso em Nova Reserva/Contrato; permitir override com permissão `cadastros.cliente.bloquear`.
- Inativar → ocultar de comboboxes; manter histórico.

#### Motorista (`motoristas`)

| Vinculado em | ondelete | Impacto |
|--------------|----------|---------|
| ReservaMotorista | R | Não excluir se vinculado a reserva/contrato ativo |
| Multa (condutor) | S | Multa perde motorista |
| Consulta DETRAN | — | Apenas leitura |

**Regras UI:**
- Ao selecionar motorista na reserva: validar CNH válida + categoria compatível com veículo.
- Vínculo `funcionario` vs `terceiro`: se terceiro, exigir CPF.

#### Parceiro / Vendedor / Fornecedor

| Entidade | Bloqueio exclusão quando |
|----------|--------------------------|
| Parceiro | Reservas/contratos/tabelas com parceiro_id |
| Vendedor | Oportunidades abertas |
| Fornecedor | OS abertas, contas a pagar em aberto |

#### Veículo (`frota_veiculos`)

| Vinculado | ondelete | Impacto |
|-----------|----------|---------|
| Reserva (alocado) | S | Libera slot |
| Contrato ativo | R | Não excluir |
| Documentação | C | Remove docs |
| Telemetria | C | Remove device/events |
| OS | R | OS aberta bloqueia baixa |
| Multa | R | — |
| Manutenção pneus | S | — |

**Baixa de veículo:** form dedicado; status terminal; não aparece em disponibilidade.

#### Categoria / Marca / Modelo / Combustível (catálogo frota)

| Entidade | ondelete | Impacto |
|----------|----------|---------|
| Categoria | R | Veículos e tarifas dependem |
| Marca | R | Modelos dependem |
| Modelo | R | Veículos dependem |
| Combustível | R | Veículos dependem |
| Acessório | R | Vínculo veículo-acessório |

**UI:** inativar (`status=inactive`) em vez de excluir quando houver histórico.

### 4.3 Cadeias de seleção obrigatórias (UX)

```
Marca (T30) ──► Modelo (filtrado por marca_id)
UF (T14)    ──► Município IBGE (T31)
CEP (T13)   ──► Endereço auto (ViaCEP) + focus número
Categoria   ──► Veículos disponíveis (reserva/contrato)
Cliente     ──► Limite crédito, blacklist, faturamento config
Filial ret. ──► Filial dev. (sugerir igual; one-way destaca)
Retirada    ──► Devolução (min +1h); dispara disponibilidade
person_type ──► CPF XOR CNPJ visível
tipo OS     ──► Campos corretiva vs preventiva
```

### 4.4 Matriz resumida — exclusão bloqueada (RESTRICT)

| Se tentar excluir… | Bloqueado por… |
|--------------------|----------------|
| Cliente | Reserva/contrato/fatura ativos |
| Motorista | Reserva/contrato com motorista |
| Veículo | Contrato/OS/multa ativos |
| Categoria frota | Veículos, itens tarifário |
| Marca/Modelo | Veículos |
| Filial | Caixa aberto, títulos, contratos |
| Usuário | Caixa sessão RESTRICT; reatribuir papéis |
| Papel sistema | Usuários vinculados |

---

## 5. Inventário completo por módulo (100 formulários)

Cada entrada: **ID** | **Rota** | **Template** | **Melhorias obrigatórias**

### 5.1 Cadastros (8)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| CAD-01 | `/cadastros/clientes/novo\|editar` | `cliente_form.html` | §6.1 — PF/PJ toggle, máscaras, IBGE, combobox |
| CAD-02 | POST bloquear | inline | Modal + motivo obrigatório |
| CAD-03 | POST `/cadastros/tabelas` | `tabelas_list.html` | Validar slug único por grupo |
| CAD-04 | `/cadastros/motoristas/novo\|editar` | `motorista_form.html` | §6.2 |
| CAD-05 | `/cadastros/parceiros/novo\|editar` | `parceiro_form.html` | §6.3 |
| CAD-06 | `/cadastros/fornecedores/novo\|editar` | `fornecedor_form.html` | CNPJ mask, categoria async |
| CAD-07 | `/cadastros/vendedores/novo\|editar` | `vendedor_form.html` | Filial + meta com máscara moeda |
| CAD-08 | GET `/cadastros/cep/{cep}` | API | Manter; expandir para IBGE |

### 5.2 Frota (16)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| FRO-01 | `/frota/veiculos/novo\|editar` | `veiculo_form.html` | §6.4 |
| FRO-02–06 | ações veículo | inline | Modais confirmação |
| FRO-07 | `/frota/categorias/novo\|editar` | `categoria_form.html` | Capacidades numéricas T17 |
| FRO-08 | `/frota/marcas/novo\|editar` | `marca_form.html` | Nome único case-insensitive |
| FRO-09 | `/frota/combustiveis/novo\|editar` | `combustivel_form.html` | Simples |
| FRO-10 | `/frota/modelos/novo\|editar` | `modelo_form.html` | Marca→categoria cascata |
| FRO-11 | `/frota/acessorios/novo\|editar` | `acessorio_form.html` | valor_diaria T15, estoque T17 |
| FRO-12 | `/frota/documentacao/novo\|editar` | `documento_form.html` | Alerta vencimento, veículo combobox |
| FRO-13 | `/frota/telemetria/novo\|editar` | `telemetria_form.html` | Veículo combobox, provedor enum |
| FRO-14 | POST telemetria evento | inline | lat/long T17 decimal |

### 5.3 Reservas (3)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| RES-01 | `/reservas/nova` | `nova.html` | §6.5 — wizard completo |
| RES-02 | `/reservas/cotacoes/novo` | `cotacao_form.html` | Similar RES-01 simplificado |
| RES-03 | POST converter cotação | inline | Herdar campos + validar cliente |

### 5.4 Locações (8)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| LOC-01 | `/locacoes/contratos/novo` | `contrato_form.html` | §6.6 |
| LOC-02 | checkout | `checkout_form.html` | KM T17, combustível slider T42, fotos T38 |
| LOC-03 | checkin | `checkin_form.html` | Avaria condicional, caução T15 |
| LOC-04 | renovações | `renovacoes.html` | Contrato combobox + nova data T22 |
| LOC-05 | multas | `multa_form.html` | Veículo→contrato auto por data |
| LOC-06 | avarias | `avaria_form.html` | Severidade enum visual |
| LOC-07 | POST responsabilidade | inline | Confirma impacto financeiro |

### 5.5 Manutenção (15)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| MAN-01 | OS novo/editar/corretiva | `os_form.html` | Veículo combobox, repeater itens T39 |
| MAN-02–06 | OS ações/itens/fotos | inline | Validação valor > limite → workflow |
| MAN-07 | preventiva | `preventiva_form.html` | Intervalo km/dias par |
| MAN-08 | peça | `peca_form.html` | Código único, estoque mínimo |
| MAN-09–14 | pneu ações | inline + `pneu_form.html` | Posição enum por eixo |

### 5.6 Tarifário (9)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| TAR-01 | tabelas | `tabela_form.html` | §6.7 — repeater itens por categoria |
| TAR-02 | temporadas | `temporada_form.html` | Multiplicador T16, overlap validação |
| TAR-03 | taxas | `taxa_form.html` | §6.8 |
| TAR-04 | proteções | `protecao_form.html` | Franquia T15, multi categoria |
| TAR-05 | cancelamento | `politica_form.html` | Repeater faixas T39 |
| TAR-06 | simular | `simular.html` | Read-only resultado HTMX |

### 5.7 Financeiro (14)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| FIN-01 | receber novo | `receber_form.html` | §6.9 |
| FIN-02 | pagar novo | `pagar_form.html` | Fornecedor combobox |
| FIN-03 | cartão | `cartao_form.html` | Parcelas T17, link título |
| FIN-04 | banco | `banco_form.html` | Agência/conta máscara |
| FIN-05–08 | caixa/pix | inline | Sessão única aberta por filial |
| FIN-09–11 | conciliação/faturamento | inline | Upload OFX T38 |

### 5.8 Fiscal (7)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| FIS-01 | nfse | `nfse_form.html` | Município IBGE T31, valores T15 |
| FIS-02 | nfe | `nfe_form.html` | Destinatário auto de cliente |
| FIS-03 | cancelamentos | `cancelamentos_form.html` | Justificativa min 15 chars |
| FIS-04 | impostos | `impostos_form.html` | Repeater alíquotas |
| FIS-05 | xml import | `xml_import.html` | Drag-drop T38 |

### 5.9 Comercial (9)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| COM-01 | funil novo | kanban inline | Cliente combobox |
| COM-02 | proposta | `proposta_form.html` | Repeater itens T39 |
| COM-03 | campanha | `campanha_form.html` | Canal enum, preview mensagem |
| COM-04 | cupom | `cupom_form.html` | Código uppercase T20 |
| COM-05–07 | fidelidade | inline | Tier repeater |

### 5.10 Identity (2)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| IDN-01 | usuários | `user_form.html` | Senha strength T45, roles checklist |
| IDN-02 | papéis | `role_form.html` | Matriz permissões agrupada |

### 5.11 Tenants (2)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| TEN-01 | empresa | `company.html` | Logo T38, cert A1 T45, color T44 |
| TEN-02 | filiais | `filial_form.html` | CNPJ T06, UF/cidade T31 |

### 5.12 Integrações (6)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| INT-01 | configs | `_config_section.html` | Secret masked, test connection btn |
| INT-02–04 | api keys/webhooks | inline | Escopos checklist |
| INT-05–07 | consultas | inline | Resultado em card, não form |

### 5.13 Automações (2)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| AUT-01 | regras | inline | Builder condição visual + JSON T43 |
| AUT-02 | workflows | inline | Drag etapas |

### 5.14 Relatórios (2)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| REL-01 | agendamentos | `agendamento_form.html` | E-mails múltiplos T04, cron humanizado |
| REL-02 | emitir | `emitir_form.html` | Período presets T26 |

### 5.15 Parâmetros (1)

| ID | Rota | Template | Melhorias |
|----|------|----------|-----------|
| PAR-01 | parametros | `list.html` | Agrupar por categoria; filial scope toggle |

---

## 6. Especificações detalhadas — formulários prioritários

### 6.1 CAD-01 — Cliente (Novo/Editar)

**Layout alvo:** Tabs → [Dados] [Endereço] [Comercial] [Observações]

| Campo | Tipo | Obrig. | Máscara | Dependência | Validação extra |
|-------|------|--------|---------|-------------|-----------------|
| person_type | T35 | Sim | — | — | PF ou PJ |
| status | T27 | Sim | — | — | blocked exige motivo em ação separada |
| nome | T01 | Sim | — | — | min 2 |
| nome_fantasia | T01 | Não | — | visível se PJ | — |
| cpf | T05 | Sim se PF | CPF | oculto se PJ | único tenant |
| cnpj | T06 | Sim se PJ | CNPJ | oculto se PF | único tenant |
| email | T04 | Não | — | — | — |
| telefone | T11 | Não | phone | — | — |
| celular | T12 | Não | phone | — | — |
| cep | T13 | Não | CEP | blur→ViaCEP | — |
| endereco | T01 | Não | — | auto ViaCEP | — |
| numero | T01 | Não | — | focus após CEP | — |
| complemento | T01 | Não | — | auto ViaCEP | — |
| bairro | T01 | Não | — | auto ViaCEP | — |
| uf | T14 | Não | — | → município IBGE | — |
| cidade | T31 | Não | — | depende UF | IBGE nome |
| categoria_codigo | T28 | Não | — | — | tabela auxiliar |
| limite_credito | T15 | Não | BRL | — | ≥ 0 |
| observacoes | T03 | Não | — | — | — |

**Pré-preenchimento:** limite_credito `R$ 0,00`; status `Ativo`; person_type `PF`.

**Impacto:** ver §4.2 Cliente.

---

### 6.2 CAD-04 — Motorista

| Campo | Tipo | Obrig. | Máscara | Dependência |
|-------|------|--------|---------|-------------|
| nome | T01 | Sim | — | — |
| vinculo | T27 | Sim | — | terceiro→CPF obrig. |
| status | T27 | Sim | — | — |
| cpf | T05 | Sim (create) | CPF | readonly edit |
| email | T04 | Não | — | — |
| celular | T12 | Não | phone | — |
| cnh_numero | T01 | Sim | — | — |
| cnh_categoria | T28 | Sim | — | tabela auxiliar |
| cnh_validade | T21 | Sim | date | alerta se < 30d |
| cnh_status | T27 | Sim | — | auto `vencida` se data passada |
| observacoes | T03 | Não | — | — |

**Encadeamento reserva:** ao selecionar motorista, exibir badge CNH categoria + validade.

---

### 6.3 CAD-05 — Parceiro

| Campo | Tipo | Obrig. | Máscara | Dependência |
|-------|------|--------|---------|-------------|
| person_type | T35 | Sim | — | CPF XOR CNPJ |
| nome | T01 | Sim | — | — |
| tipo (parceria) | T27 | Sim | — | — |
| comissao_percentual | T16 | Não | % | — |
| comissao_valor_fixo | T15 | Não | BRL | — |
| pix_chave | T19 | Não | auto | — |

---

### 6.4 FRO-01 — Veículo

**Layout:** Tabs → [Identificação] [Classificação] [Financeiro] [Operação] [Acessórios*]

| Campo | Tipo | Obrig. | Máscara |
|-------|------|--------|---------|
| placa | T08 | Sim | Mercosul |
| renavam | T09 | Não | 11 dígitos |
| chassi | T10 | Não | VIN |
| ano_fabricacao | T18 | Sim | — |
| ano_modelo | T18 | Sim | ≥ ano_fab |
| cor | T01 | Não | — |
| categoria_id | T28 | Sim | — |
| marca_id | T28 | Sim | → filtra modelo |
| modelo_id | T30 | Sim | depende marca |
| combustivel_id | T28 | Sim | — |
| filial_id | T28 | Não | — |
| propriedade | T27 | Sim | — |
| data_compra | T21 | Não | — |
| valor_aquisicao | T15 | Não | BRL |
| valor_fipe | T15 | Não | BRL |
| valor_mercado | T15 | Não | BRL |
| km_inicial / km_atual | T17 | Não | — |
| nivel_combustivel | T42 | Não | slider 0–8 |

**Pré-preenchimento:** propriedade `própria`; nivel_combustivel `8`; ano corrente nos anos.

---

### 6.5 RES-01 — Nova Reserva (Wizard)

**Stepper 6 passos:**

1. **Período e filiais** — retirada/devolução T22; botão "Consultar disponibilidade" inline HTMX.
2. **Disponibilidade** — tabela readonly; clique categoria pré-seleciona passo 3.
3. **Categoria e veículo** — veículo filtrado por categoria + disponibilidade.
4. **Cliente e motoristas** — cliente T29; motoristas T32; validar blacklist.
5. **Opcionais** — proteções T34; taxas T34; acessórios qty.
6. **Pagamento** — forma, cupom T20, desconto T15, recalcular preço HTMX.

**Dependências críticas:**
- `devolucao_em` > `retirada_em` (min 1h).
- Cliente bloqueado → modal aprovação (`requer_aprovacao`).
- Cupom validado async antes submit.

---

### 6.6 LOC-01 — Novo Contrato

Espelha RES-01 + campos:
- `caucao` T15
- `clausulas_combustivel` T27
- `condicao` pagamento
- Origem reserva (readonly se convertido)

---

### 6.7 TAR-01 — Tabela de Tarifas

| Campo | Tipo | Obrig. |
|-------|------|--------|
| nome | T01 | Sim |
| vigencia_inicio/fim | T25 | Sim |
| canal | T27 | Sim |
| filial/parceiro/cliente | T28/T29 | Não (prioridade) |
| prioridade | T17 | Sim (default 0) |
| itens[] | T39 | Sim ≥1 categoria |

**Repeater item:** categoria_id, valor_1_3, valor_4_7, valor_8_14, valor_15_29, valor_mensal, km_livre.

---

### 6.8 TAR-03 — Nova Taxa

| Campo | Tipo | Obrig. | Máscara |
|-------|------|--------|---------|
| codigo | T20 | Sim | uppercase |
| nome | T01 | Sim | — |
| tipo_calculo | T27 | Sim | fixo/diario/percentual |
| valor | T15/T16 | Sim | conforme tipo |
| aplicacao | T27 | Sim | — |
| codigo_regra | T01 | Não | one_way, condutor_adicional |
| tributavel | T33 | Não | default true |
| descricao | T03 | Não | — |

**Condicional:** se `tipo=percentual` → máscara T16; se `fixo/diario` → T15.

---

### 6.9 FIN-01 — Título a Receber

| Campo | Tipo | Obrig. | Máscara |
|-------|------|--------|---------|
| filial_id | T28 | Sim | — |
| cliente_id | T29 | Não | combobox |
| descricao | T01 | Sim | — |
| valor_original | T15 | Sim | BRL |
| vencimento | T21 | Sim | default +30d |
| forma_prevista | T27 | Não | enum formas |
| gera_pix | T33 | Não | se marcado → job PIX |
| observacoes | T03 | Não | — |

**Pré-preenchimento:** vencimento = hoje + 30 dias; valor `R$ 0,00`.

---

## 7. Motor técnico recomendado

### 7.1 Arquivos JS compartilhados (criar em `app/web/static/js/`)

| Arquivo | Responsabilidade |
|---------|------------------|
| `form-core.js` | Required labels, dirty check, submit disable |
| `form-masks.js` | T05–T20, T15–T16 via IMask |
| `form-lookups.js` | Combobox async, debounce 300ms |
| `form-cascade.js` | marca→modelo, UF→cidade |
| `form-viacep.js` | CEP blur (existente, generalizar) |
| `form-ibge.js` | `/api/v1/util/ibge/*` |
| `form-validate.js` | CPF/CNPJ dígitos, datas, períodos |
| `form-impact.js` | Modal exclusão com matriz §4 |

### 7.2 Endpoints API a criar

```
GET  /api/v1/util/ibge/ufs
GET  /api/v1/util/ibge/municipios/{uf}
GET  /api/v1/cadastros/clientes?search=&page=
GET  /api/v1/frota/modelos?marca_id=
GET  /api/v1/frota/veiculos/disponiveis?categoria_id=&inicio=&fim=
GET  /api/v1/cadastros/clientes/{id}/impacto-exclusao
```

### 7.3 Macros Jinja (criar `templates/macros/forms.html`)

```jinja
{% macro field_label(text, required=false) %}
  <label class="form-label{% if required %} form-label--required{% endif %}">{{ text }}</label>
{% endmacro %}

{% macro field_error(name) %}
  <div class="form-error" id="error-{{ name }}" role="alert"></div>
{% endmacro %}
```

### 7.4 CSS (`app.css` additions)

```css
.form-label--required::after { content: " *"; color: var(--danger); }
.form-error { color: var(--danger); font-size: 0.85rem; margin-top: 4px; }
.form-input.is-invalid { border-color: var(--danger); }
.form-fieldset { border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.form-fieldset legend { font-weight: 600; padding: 0 8px; }
```

---

## 8. Roadmap de implementação

### Fase 1 — Fundação (1 sprint)
- [ ] Macros + CSS global obrigatoriedade/erro
- [ ] `form-masks.js` para CPF, CNPJ, telefone, CEP, moeda, placa
- [ ] API IBGE UF/município
- [ ] Estender ViaCEP para todos forms com endereço

### Fase 2 — Cadastros + Frota (1 sprint)
- [ ] CAD-01 a CAD-07 conforme §6
- [ ] FRO-01 cascata marca→modelo
- [ ] Combobox async clientes/veículos

### Fase 3 — Operacional (1 sprint)
- [ ] RES-01 wizard + validações
- [ ] LOC-01/02/03 checkout/checkin
- [ ] Impacto exclusão modals

### Fase 4 — Comercial + Tarifário + Financeiro (1 sprint)
- [ ] TAR-01 repeater itens
- [ ] FIN-01/02 máscaras moeda/data
- [ ] COM-02 proposta repeater

### Fase 5 — Fiscal + Integrações + Restantes (1 sprint)
- [ ] FIS-* IBGE município NFS-e
- [ ] INT test connection
- [ ] AUT builder visual
- [ ] PAR-01 agrupamento

### Fase 6 — Polimento
- [ ] Testes E2E Playwright por formulário crítico
- [ ] Documentação inline `.form-help` em 100% campos não óbvios
- [ ] Acessibilidade WCAG (aria, tabindex, labels)

---

## Apêndice A — Checklist por formulário (aplicar em todos os 100)

- [ ] Legenda `* Campos obrigatórios` presente
- [ ] Cada campo obrigatório com `form-label--required`
- [ ] Máscaras aplicadas conforme tipo T01–T45
- [ ] Placeholders em datas/documentos
- [ ] Campos condicionais implementados
- [ ] Combobox async para FKs com >30 registros
- [ ] Validação client antes submit
- [ ] Erros inline por campo (não só alerta topo)
- [ ] Seções/fieldsets para forms >12 campos
- [ ] Modal de impacto antes excluir/inativar
- [ ] Pré-preenchimento de defaults sensatos
- [ ] `form-help` em campos não óbvios
- [ ] CSRF token presente
- [ ] Cancelar confirma se dirty

---

## Apêndice B — Mapeamento schema ↔ template

| Módulo | Schemas |
|--------|---------|
| cadastros | `schemas.py`, `schemas_extra.py` |
| frota | `frota/schemas.py` |
| reservas | `reservas/schemas.py` |
| locacoes | `locacoes/schemas.py` |
| manutencao | `manutencao/schemas.py` |
| tarifario | `tarifario/schemas.py` |
| financeiro | `financeiro/schemas.py` |
| fiscal | `fiscal/schemas.py` |
| comercial | `comercial/schemas.py` |
| identity | `identity/schemas.py` |
| tenants | `tenants/schemas.py` |
| integracoes | `integracoes/schemas.py` |
| automacoes | `automacoes/schemas.py` |
| relatorios | `relatorios/schemas.py` |
| parametros | `parametros/schemas.py` |

**Regra:** todo campo no template deve existir no schema Create/Update; campos só-leitura na edição devem estar documentados.

---

## Apêndice C — Referência rápida de máscaras BR

| Campo | Máscara entrada | Exemplo |
|-------|-----------------|---------|
| CPF | `999.999.999-99` | 123.456.789-09 |
| CNPJ | `99.999.999/9999-99` | 12.345.678/0001-90 |
| CEP | `99999-999` | 01310-100 |
| Telefone | `(99) 9999-9999` | (11) 3456-7890 |
| Celular | `(99) 99999-9999` | (11) 98765-4321 |
| Placa | `AAA9*99` | ABC1D23 |
| Data | `99/99/9999` | 16/07/2026 |
| Moeda | `R$ 999.999,99` | R$ 1.234,56 |
| Percentual | `999,99 %` | 10,50 % |

---

## Apêndice D — Lista canônica de arquivos de formulário (100% do codebase)

### D.1 Templates dedicados `*_form.html` (44 arquivos)

| # | Arquivo | ID doc |
|---|---------|--------|
| 1 | `cadastros/cliente_form.html` | CAD-01 |
| 2 | `cadastros/motorista_form.html` | CAD-04 |
| 3 | `cadastros/parceiro_form.html` | CAD-05 |
| 4 | `cadastros/fornecedor_form.html` | CAD-06 |
| 5 | `cadastros/vendedor_form.html` | CAD-07 |
| 6 | `frota/veiculo_form.html` | FRO-01 |
| 7 | `frota/categoria_form.html` | FRO-07 |
| 8 | `frota/marca_form.html` | FRO-08 |
| 9 | `frota/combustivel_form.html` | FRO-09 |
| 10 | `frota/modelo_form.html` | FRO-10 |
| 11 | `frota/acessorio_form.html` | FRO-11 |
| 12 | `frota/documento_form.html` | FRO-12 |
| 13 | `frota/telemetria_form.html` | FRO-13 |
| 14 | `reservas/cotacao_form.html` | RES-02 |
| 15 | `locacoes/contrato_form.html` | LOC-01 |
| 16 | `locacoes/checkout_form.html` | LOC-02 |
| 17 | `locacoes/checkin_form.html` | LOC-03 |
| 18 | `locacoes/multa_form.html` | LOC-05 |
| 19 | `locacoes/avaria_form.html` | LOC-06 |
| 20 | `manutencao/os_form.html` | MAN-01 |
| 21 | `manutencao/preventiva_form.html` | MAN-07 |
| 22 | `manutencao/peca_form.html` | MAN-08 |
| 23 | `manutencao/pneu_form.html` | MAN-09 |
| 24 | `tarifario/tabela_form.html` | TAR-01 |
| 25 | `tarifario/temporada_form.html` | TAR-02 |
| 26 | `tarifario/taxa_form.html` | TAR-03 |
| 27 | `tarifario/protecao_form.html` | TAR-04 |
| 28 | `tarifario/politica_form.html` | TAR-05 |
| 29 | `financeiro/receber_form.html` | FIN-01 |
| 30 | `financeiro/pagar_form.html` | FIN-02 |
| 31 | `financeiro/cartao_form.html` | FIN-03 |
| 32 | `financeiro/banco_form.html` | FIN-04 |
| 33 | `fiscal/nfse_form.html` | FIS-01 |
| 34 | `fiscal/nfe_form.html` | FIS-02 |
| 35 | `fiscal/cancelamentos_form.html` | FIS-03 |
| 36 | `fiscal/impostos_form.html` | FIS-04 |
| 37 | `comercial/proposta_form.html` | COM-02 |
| 38 | `comercial/campanha_form.html` | COM-03 |
| 39 | `comercial/cupom_form.html` | COM-04 |
| 40 | `identity/user_form.html` | IDN-01 |
| 41 | `identity/role_form.html` | IDN-02 |
| 42 | `tenants/filial_form.html` | TEN-02 |
| 43 | `relatorios/agendamento_form.html` | REL-01 |
| 44 | `relatorios/emitir_form.html` | REL-02 |

### D.2 Páginas de formulário sem sufixo `_form` (12)

| # | Arquivo | ID | Melhorias-chave |
|---|---------|-----|-----------------|
| 45 | `reservas/nova.html` | RES-01 | Wizard 6 passos §6.5 |
| 46 | `tenants/company.html` | TEN-01 | Certificado A1 T45, logo T38 |
| 47 | `fiscal/xml_import.html` | FIS-05 | Drag-drop T38, validação XML |
| 48 | `tarifario/simular.html` | TAR-06 | Período T25, resultado HTMX |
| 49 | `locacoes/renovacoes.html` | LOC-04 | Contrato combobox + nova data |
| 50 | `locacoes/encerramentos.html` | LOC-08 | Filtro contrato + confirmação |
| 51 | `fiscal/impostos_apuracao.html` | FIS-06 | Período competência T21 |
| 52 | `comercial/fidelidade.html` | COM-05 | Repeater tiers T39 |
| 53 | `financeiro/conciliacao.html` | FIN-10 | Upload OFX T38 |
| 54 | `reservas/disponibilidade.html` | RES-04 | Filtros período/filial T22 |
| 55 | `integracoes/_config_section.html` | INT-01 | Secrets masked, test btn |
| 56 | `parametros/list.html` | PAR-01 | Edição inline por grupo |

### D.3 Autenticação e segurança (4)

| # | Arquivo | Melhorias |
|---|---------|-----------|
| 57 | `identity/login.html` | E-mail T04, senha T45, link 2FA |
| 58 | `identity/login_2fa.html` | Código 6 dígitos T17, recovery |
| 59 | `identity/twofa_setup.html` | QR readonly, backup codes |
| 60 | `identity/users_list.html` | Filtro busca + reset senha inline |

### D.4 Formulários inline em listas e detalhes (40)

Inclui filtros, baixas, aprovações e ações em: `clientes_list`, `tabelas_list`, `veiculos_list`, `documentacao_list`, `reservas/list`, `cotacoes_list`, `calendario`, `detalhe` (reserva), `contratos_list`, `contrato_detalhe`, `multas_list`, `avarias_list`, `os_list`, `pecas_list`, `pneus_list`, `receber_list`, `receber_detalhe`, `pagar_detalhe`, `caixa_list`, `caixa_detalhe`, `fatura_detalhe`, `faturamento_list`, `pix_list`, `cartoes_list`, `nfse_detalhe`, `nfe_detalhe`, `xml_list`, `funil_kanban`, `funil_detalhe`, `proposta_detalhe`, `campanha_detalhe`, `regras_list`, `workflows_list`, `agendamentos_list`, `api_publica`, `credito`, `transito`, `audit/trail`, `notificacoes/inbox`, `dashboard/home`.

**Total catalogado: 100 formulários/interações de entrada de dados.**

---

## Apêndice E — Fluxos de atribuição entre entidades

### E.1 Motorista → Reserva → Contrato

Cadastro motorista → seleção na reserva (N:N RESTRICT) → contrato herda motoristas → multa vincula condutor.

### E.2 Cliente → Financeiro → Fiscal

Cliente → contrato gera títulos → fatura mensal → NFS-e destinatário automático → bloqueio se inadimplente.

### E.3 Veículo → Manutenção → Disponibilidade

OS aberta indisponibiliza veículo na consulta de reservas; encerramento OS restaura disponibilidade.

### E.4 Preferir inativar vs excluir

| Entidade | Ação recomendada |
|----------|------------------|
| Cliente/motorista com histórico | Inativar |
| Veículo vendido | Baixa (status terminal) |
| Catálogo frota | Inativar |
| Usuário | Desativar |

---

*Documento gerado a partir do inventário completo do codebase (100 formulários/interações, 16 módulos). Implementação código a partir da Fase 1 do Roadmap §8.*
