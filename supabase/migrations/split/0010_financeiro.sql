CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE fin_caixa_sessoes (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    filial_id UUID NOT NULL, 
    operador_id UUID NOT NULL, 
    status VARCHAR(10) DEFAULT 'aberta' NOT NULL, 
    aberta_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    fechada_em TIMESTAMP WITH TIME ZONE, 
    valor_abertura NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_fechamento_informado NUMERIC(14, 2), 
    valor_calculado NUMERIC(14, 2), 
    divergencia NUMERIC(14, 2), 
    observacoes TEXT, 
    CONSTRAINT pk_fin_caixa_sessoes PRIMARY KEY (id), 
    CONSTRAINT fk_fin_caixa_sessoes_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_fin_caixa_sessoes_operador_id_users FOREIGN KEY(operador_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_fin_caixa_sessoes_tenant_id ON fin_caixa_sessoes (tenant_id);

CREATE INDEX ix_fin_caixa_sessoes_tenant_status ON fin_caixa_sessoes (tenant_id, status);

CREATE INDEX ix_fin_caixa_sessoes_filial_id ON fin_caixa_sessoes (filial_id);

CREATE INDEX ix_fin_caixa_sessoes_operador_id ON fin_caixa_sessoes (operador_id);

CREATE TABLE fin_contas_bancarias (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    banco_codigo VARCHAR(10) NOT NULL, 
    banco_nome VARCHAR(120) NOT NULL, 
    agencia VARCHAR(20) NOT NULL, 
    conta VARCHAR(30) NOT NULL, 
    tipo VARCHAR(12) DEFAULT 'corrente' NOT NULL, 
    filial_id UUID, 
    saldo_atual NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    ativa BOOLEAN DEFAULT 'true' NOT NULL, 
    integracao_tipo VARCHAR(10) DEFAULT 'manual' NOT NULL, 
    CONSTRAINT pk_fin_contas_bancarias PRIMARY KEY (id), 
    CONSTRAINT fk_fin_contas_bancarias_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL
);

CREATE INDEX ix_fin_contas_bancarias_tenant_id ON fin_contas_bancarias (tenant_id);

CREATE INDEX ix_fin_contas_bancarias_tenant_ativa ON fin_contas_bancarias (tenant_id, ativa);

CREATE INDEX ix_fin_contas_bancarias_filial_id ON fin_contas_bancarias (filial_id);

CREATE TABLE fin_caixa_lancamentos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    sessao_id UUID NOT NULL, 
    tipo VARCHAR(15) NOT NULL, 
    categoria VARCHAR(80), 
    forma_pagamento VARCHAR(20) DEFAULT 'dinheiro' NOT NULL, 
    valor NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    descricao VARCHAR(255), 
    referencia_tipo VARCHAR(40), 
    referencia_id UUID, 
    created_by UUID, 
    CONSTRAINT pk_fin_caixa_lancamentos PRIMARY KEY (id), 
    CONSTRAINT fk_fin_caixa_lancamentos_sessao_id_fin_caixa_sessoes FOREIGN KEY(sessao_id) REFERENCES fin_caixa_sessoes (id) ON DELETE CASCADE, 
    CONSTRAINT fk_fin_caixa_lancamentos_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_fin_caixa_lancamentos_tenant_id ON fin_caixa_lancamentos (tenant_id);

CREATE INDEX ix_fin_caixa_lancamentos_sessao_id ON fin_caixa_lancamentos (sessao_id);

CREATE INDEX ix_fin_caixa_lancamentos_tenant_tipo ON fin_caixa_lancamentos (tenant_id, tipo);

CREATE TABLE fin_contas_receber (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    origem VARCHAR(15) DEFAULT 'avulso' NOT NULL, 
    origem_id UUID, 
    cliente_id UUID, 
    filial_id UUID NOT NULL, 
    descricao VARCHAR(255) NOT NULL, 
    valor_original NUMERIC(14, 2) NOT NULL, 
    valor_pago NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_saldo NUMERIC(14, 2) NOT NULL, 
    vencimento DATE NOT NULL, 
    forma_prevista VARCHAR(20), 
    status VARCHAR(15) DEFAULT 'em_aberto' NOT NULL, 
    parcela_num INTEGER DEFAULT '1' NOT NULL, 
    parcela_total INTEGER DEFAULT '1' NOT NULL, 
    gera_pix BOOLEAN DEFAULT 'false' NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_fin_contas_receber PRIMARY KEY (id), 
    CONSTRAINT fk_fin_contas_receber_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE SET NULL, 
    CONSTRAINT fk_fin_contas_receber_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE RESTRICT
);

CREATE INDEX ix_fin_contas_receber_tenant_id ON fin_contas_receber (tenant_id);

CREATE INDEX ix_fin_contas_receber_tenant_status ON fin_contas_receber (tenant_id, status);

CREATE INDEX ix_fin_contas_receber_cliente_id ON fin_contas_receber (cliente_id);

CREATE INDEX ix_fin_contas_receber_vencimento ON fin_contas_receber (vencimento);

CREATE UNIQUE INDEX uq_fin_contas_receber_tenant_numero_active ON fin_contas_receber (tenant_id, numero) WHERE deleted_at IS NULL;

CREATE TABLE fin_receber_baixas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    titulo_id UUID NOT NULL, 
    valor NUMERIC(14, 2) NOT NULL, 
    forma VARCHAR(20) DEFAULT 'dinheiro' NOT NULL, 
    pago_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    caixa_lancamento_id UUID, 
    estornada BOOLEAN DEFAULT 'false' NOT NULL, 
    observacao VARCHAR(255), 
    CONSTRAINT pk_fin_receber_baixas PRIMARY KEY (id), 
    CONSTRAINT fk_fin_receber_baixas_titulo_id_fin_contas_receber FOREIGN KEY(titulo_id) REFERENCES fin_contas_receber (id) ON DELETE CASCADE, 
    CONSTRAINT fk_fin_receber_baixas_caixa_lancamento_id_fin_caixa_lancamentos FOREIGN KEY(caixa_lancamento_id) REFERENCES fin_caixa_lancamentos (id) ON DELETE SET NULL
);

CREATE INDEX ix_fin_receber_baixas_tenant_id ON fin_receber_baixas (tenant_id);

CREATE INDEX ix_fin_receber_baixas_titulo_id ON fin_receber_baixas (titulo_id);

CREATE TABLE fin_contas_pagar (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    origem VARCHAR(15) DEFAULT 'avulso' NOT NULL, 
    origem_id UUID, 
    fornecedor_id UUID, 
    beneficiario_nome VARCHAR(160), 
    filial_id UUID NOT NULL, 
    descricao VARCHAR(255) NOT NULL, 
    valor_original NUMERIC(14, 2) NOT NULL, 
    valor_pago NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_saldo NUMERIC(14, 2) NOT NULL, 
    vencimento DATE NOT NULL, 
    forma_prevista VARCHAR(20), 
    status VARCHAR(15) DEFAULT 'em_aberto' NOT NULL, 
    aprovado_em TIMESTAMP WITH TIME ZONE, 
    aprovado_por UUID, 
    pagamento_agendado_em DATE, 
    nf_anexo_url VARCHAR(500), 
    observacoes TEXT, 
    CONSTRAINT pk_fin_contas_pagar PRIMARY KEY (id), 
    CONSTRAINT fk_fin_contas_pagar_fornecedor_id_fornecedores FOREIGN KEY(fornecedor_id) REFERENCES fornecedores (id) ON DELETE SET NULL, 
    CONSTRAINT fk_fin_contas_pagar_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_fin_contas_pagar_aprovado_por_users FOREIGN KEY(aprovado_por) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_fin_contas_pagar_tenant_id ON fin_contas_pagar (tenant_id);

CREATE INDEX ix_fin_contas_pagar_tenant_status ON fin_contas_pagar (tenant_id, status);

CREATE INDEX ix_fin_contas_pagar_fornecedor_id ON fin_contas_pagar (fornecedor_id);

CREATE INDEX ix_fin_contas_pagar_vencimento ON fin_contas_pagar (vencimento);

CREATE UNIQUE INDEX uq_fin_contas_pagar_tenant_numero_active ON fin_contas_pagar (tenant_id, numero) WHERE deleted_at IS NULL;

CREATE TABLE fin_pagar_baixas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    titulo_id UUID NOT NULL, 
    valor NUMERIC(14, 2) NOT NULL, 
    forma VARCHAR(20) DEFAULT 'dinheiro' NOT NULL, 
    pago_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    caixa_lancamento_id UUID, 
    conta_bancaria_id UUID, 
    observacao VARCHAR(255), 
    CONSTRAINT pk_fin_pagar_baixas PRIMARY KEY (id), 
    CONSTRAINT fk_fin_pagar_baixas_titulo_id_fin_contas_pagar FOREIGN KEY(titulo_id) REFERENCES fin_contas_pagar (id) ON DELETE CASCADE, 
    CONSTRAINT fk_fin_pagar_baixas_caixa_lancamento_id_fin_caixa_lancamentos FOREIGN KEY(caixa_lancamento_id) REFERENCES fin_caixa_lancamentos (id) ON DELETE SET NULL, 
    CONSTRAINT fk_fin_pagar_baixas_conta_bancaria_id_fin_contas_bancarias FOREIGN KEY(conta_bancaria_id) REFERENCES fin_contas_bancarias (id) ON DELETE SET NULL
);

CREATE INDEX ix_fin_pagar_baixas_tenant_id ON fin_pagar_baixas (tenant_id);

CREATE INDEX ix_fin_pagar_baixas_titulo_id ON fin_pagar_baixas (titulo_id);

CREATE TABLE fin_pix_chaves (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    filial_id UUID NOT NULL, 
    conta_bancaria_id UUID, 
    tipo VARCHAR(12) NOT NULL, 
    chave VARCHAR(140) NOT NULL, 
    ativa BOOLEAN DEFAULT 'true' NOT NULL, 
    descricao VARCHAR(200), 
    CONSTRAINT pk_fin_pix_chaves PRIMARY KEY (id), 
    CONSTRAINT fk_fin_pix_chaves_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_fin_pix_chaves_conta_bancaria_id_fin_contas_bancarias FOREIGN KEY(conta_bancaria_id) REFERENCES fin_contas_bancarias (id) ON DELETE SET NULL
);

CREATE INDEX ix_fin_pix_chaves_tenant_id ON fin_pix_chaves (tenant_id);

CREATE INDEX ix_fin_pix_chaves_tenant_ativa ON fin_pix_chaves (tenant_id, ativa);

CREATE INDEX ix_fin_pix_chaves_filial_id ON fin_pix_chaves (filial_id);

CREATE TABLE fin_pix_cobrancas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    titulo_receber_id UUID, 
    chave_id UUID, 
    txid VARCHAR(40) NOT NULL, 
    valor NUMERIC(14, 2) NOT NULL, 
    qr_code_payload TEXT NOT NULL, 
    status VARCHAR(12) DEFAULT 'aguardando' NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE, 
    pago_em TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_fin_pix_cobrancas PRIMARY KEY (id), 
    CONSTRAINT fk_fin_pix_cobrancas_titulo_receber_id_fin_contas_receber FOREIGN KEY(titulo_receber_id) REFERENCES fin_contas_receber (id) ON DELETE SET NULL, 
    CONSTRAINT fk_fin_pix_cobrancas_chave_id_fin_pix_chaves FOREIGN KEY(chave_id) REFERENCES fin_pix_chaves (id) ON DELETE SET NULL
);

CREATE INDEX ix_fin_pix_cobrancas_tenant_id ON fin_pix_cobrancas (tenant_id);

CREATE INDEX ix_fin_pix_cobrancas_titulo_id ON fin_pix_cobrancas (titulo_receber_id);

CREATE INDEX ix_fin_pix_cobrancas_tenant_status ON fin_pix_cobrancas (tenant_id, status);

CREATE UNIQUE INDEX uq_fin_pix_cobrancas_txid_active ON fin_pix_cobrancas (tenant_id, txid) WHERE deleted_at IS NULL;

CREATE TABLE fin_cartao_transacoes (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    contrato_id UUID, 
    titulo_receber_id UUID, 
    gateway VARCHAR(60) DEFAULT 'simulado' NOT NULL, 
    tipo VARCHAR(16) NOT NULL, 
    valor NUMERIC(14, 2) NOT NULL, 
    parcelas INTEGER DEFAULT '1' NOT NULL, 
    status VARCHAR(16) DEFAULT 'autorizado' NOT NULL, 
    taxa_adquirente NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_capturado NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    autorizacao_codigo VARCHAR(40), 
    capturado_em TIMESTAMP WITH TIME ZONE, 
    observacoes TEXT, 
    CONSTRAINT pk_fin_cartao_transacoes PRIMARY KEY (id), 
    CONSTRAINT fk_fin_cartao_transacoes_contrato_id_loc_contratos FOREIGN KEY(contrato_id) REFERENCES loc_contratos (id) ON DELETE SET NULL, 
    CONSTRAINT fk_fin_cartao_transacoes_titulo_receber_id_fin_contas_receber FOREIGN KEY(titulo_receber_id) REFERENCES fin_contas_receber (id) ON DELETE SET NULL
);

CREATE INDEX ix_fin_cartao_transacoes_tenant_id ON fin_cartao_transacoes (tenant_id);

CREATE INDEX ix_fin_cartao_transacoes_tenant_status ON fin_cartao_transacoes (tenant_id, status);

CREATE INDEX ix_fin_cartao_transacoes_contrato_id ON fin_cartao_transacoes (contrato_id);

CREATE INDEX ix_fin_cartao_transacoes_titulo_id ON fin_cartao_transacoes (titulo_receber_id);

CREATE TABLE fin_extrato_linhas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    conta_id UUID NOT NULL, 
    data_movimento DATE NOT NULL, 
    descricao VARCHAR(255) NOT NULL, 
    valor NUMERIC(14, 2) NOT NULL, 
    tipo VARCHAR(1) NOT NULL, 
    identificador_externo VARCHAR(80), 
    status_conciliacao VARCHAR(12) DEFAULT 'pendente' NOT NULL, 
    match_titulo_tipo VARCHAR(20), 
    match_titulo_id UUID, 
    CONSTRAINT pk_fin_extrato_linhas PRIMARY KEY (id), 
    CONSTRAINT fk_fin_extrato_linhas_conta_id_fin_contas_bancarias FOREIGN KEY(conta_id) REFERENCES fin_contas_bancarias (id) ON DELETE CASCADE
);

CREATE INDEX ix_fin_extrato_linhas_tenant_id ON fin_extrato_linhas (tenant_id);

CREATE INDEX ix_fin_extrato_linhas_conta_id ON fin_extrato_linhas (conta_id);

CREATE INDEX ix_fin_extrato_linhas_tenant_status ON fin_extrato_linhas (tenant_id, status_conciliacao);

CREATE INDEX ix_fin_extrato_linhas_data_movimento ON fin_extrato_linhas (data_movimento);

CREATE TABLE fin_faturamento_configs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    cliente_id UUID NOT NULL, 
    ciclo VARCHAR(12) DEFAULT 'mensal' NOT NULL, 
    dia_fechamento INTEGER DEFAULT '1' NOT NULL, 
    ativo BOOLEAN DEFAULT 'true' NOT NULL, 
    CONSTRAINT pk_fin_faturamento_configs PRIMARY KEY (id), 
    CONSTRAINT fk_fin_faturamento_configs_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
);

CREATE INDEX ix_fin_faturamento_configs_tenant_id ON fin_faturamento_configs (tenant_id);

CREATE INDEX ix_fin_faturamento_configs_cliente_id ON fin_faturamento_configs (cliente_id);

CREATE UNIQUE INDEX uq_fin_faturamento_configs_cliente_active ON fin_faturamento_configs (tenant_id, cliente_id) WHERE deleted_at IS NULL;

CREATE TABLE fin_faturas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    cliente_id UUID NOT NULL, 
    periodo_inicio DATE NOT NULL, 
    periodo_fim DATE NOT NULL, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    emitida_em TIMESTAMP WITH TIME ZONE, 
    vencimento DATE, 
    status VARCHAR(12) DEFAULT 'rascunho' NOT NULL, 
    conta_receber_id UUID, 
    CONSTRAINT pk_fin_faturas PRIMARY KEY (id), 
    CONSTRAINT fk_fin_faturas_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_fin_faturas_conta_receber_id_fin_contas_receber FOREIGN KEY(conta_receber_id) REFERENCES fin_contas_receber (id) ON DELETE SET NULL
);

CREATE INDEX ix_fin_faturas_tenant_id ON fin_faturas (tenant_id);

CREATE INDEX ix_fin_faturas_tenant_status ON fin_faturas (tenant_id, status);

CREATE INDEX ix_fin_faturas_cliente_id ON fin_faturas (cliente_id);

CREATE UNIQUE INDEX uq_fin_faturas_tenant_numero_active ON fin_faturas (tenant_id, numero) WHERE deleted_at IS NULL;

CREATE TABLE fin_fatura_titulos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    fatura_id UUID NOT NULL, 
    titulo_receber_id UUID NOT NULL, 
    CONSTRAINT pk_fin_fatura_titulos PRIMARY KEY (id), 
    CONSTRAINT fk_fin_fatura_titulos_fatura_id_fin_faturas FOREIGN KEY(fatura_id) REFERENCES fin_faturas (id) ON DELETE CASCADE, 
    CONSTRAINT fk_fin_fatura_titulos_titulo_receber_id_fin_contas_receber FOREIGN KEY(titulo_receber_id) REFERENCES fin_contas_receber (id) ON DELETE CASCADE
);

CREATE INDEX ix_fin_fatura_titulos_tenant_id ON fin_fatura_titulos (tenant_id);

CREATE INDEX ix_fin_fatura_titulos_fatura_id ON fin_fatura_titulos (fatura_id);

CREATE UNIQUE INDEX uq_fin_fatura_titulos_active ON fin_fatura_titulos (tenant_id, fatura_id, titulo_receber_id) WHERE deleted_at IS NULL;

ALTER TABLE fin_caixa_sessoes ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_caixa_sessoes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_caixa_sessoes
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_contas_bancarias ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_contas_bancarias FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_contas_bancarias
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_caixa_lancamentos ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_caixa_lancamentos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_caixa_lancamentos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_contas_receber ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_contas_receber FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_contas_receber
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_receber_baixas ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_receber_baixas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_receber_baixas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_contas_pagar ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_contas_pagar FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_contas_pagar
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_pagar_baixas ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_pagar_baixas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_pagar_baixas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_pix_chaves ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_pix_chaves FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_pix_chaves
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_pix_cobrancas ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_pix_cobrancas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_pix_cobrancas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_cartao_transacoes ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_cartao_transacoes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_cartao_transacoes
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_extrato_linhas ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_extrato_linhas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_extrato_linhas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_faturamento_configs ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_faturamento_configs FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_faturamento_configs
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_faturas ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_faturas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_faturas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fin_fatura_titulos ENABLE ROW LEVEL SECURITY;

ALTER TABLE fin_fatura_titulos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fin_fatura_titulos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0010_financeiro' WHERE alembic_version.version_num = '0009_locacoes';

INSERT INTO alembic_version (version_num) VALUES ('0010_financeiro') ON CONFLICT (version_num) DO NOTHING;
