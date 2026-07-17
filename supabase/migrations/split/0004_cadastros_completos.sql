CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE motoristas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    cliente_id UUID, 
    vinculo VARCHAR(20) DEFAULT 'terceiro' NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    cpf VARCHAR(11), 
    data_nascimento DATE, 
    email VARCHAR(255), 
    telefone VARCHAR(20), 
    celular VARCHAR(20), 
    cnh_numero VARCHAR(20), 
    cnh_categoria VARCHAR(10), 
    cnh_emissao DATE, 
    cnh_validade DATE, 
    cnh_orgao VARCHAR(60), 
    cnh_status VARCHAR(20) DEFAULT 'regular' NOT NULL, 
    cnh_pontuacao INTEGER, 
    cnh_frente_key VARCHAR(500), 
    cnh_verso_key VARCHAR(500), 
    observacoes TEXT, 
    CONSTRAINT pk_motoristas PRIMARY KEY (id), 
    CONSTRAINT fk_motoristas_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE SET NULL
);

CREATE INDEX ix_motoristas_tenant_id ON motoristas (tenant_id);

CREATE INDEX ix_motoristas_cliente_id ON motoristas (cliente_id);

CREATE INDEX ix_motoristas_tenant_nome ON motoristas (tenant_id, nome);

CREATE UNIQUE INDEX uq_motoristas_tenant_cpf_active ON motoristas (tenant_id, cpf) WHERE deleted_at IS NULL AND cpf IS NOT NULL;

CREATE UNIQUE INDEX uq_motoristas_tenant_cnh_active ON motoristas (tenant_id, cnh_numero) WHERE deleted_at IS NULL AND cnh_numero IS NOT NULL;

CREATE TABLE parceiros (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    person_type VARCHAR(5) NOT NULL, 
    tipo VARCHAR(20) DEFAULT 'indicacao' NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    nome_fantasia VARCHAR(200), 
    cpf VARCHAR(11), 
    cnpj VARCHAR(14), 
    email VARCHAR(255), 
    telefone VARCHAR(20), 
    comissao_percentual NUMERIC(7, 4) DEFAULT '0' NOT NULL, 
    comissao_valor_fixo NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    banco VARCHAR(100), 
    agencia VARCHAR(20), 
    conta VARCHAR(30), 
    pix_chave VARCHAR(140), 
    vigencia_inicio DATE, 
    vigencia_fim DATE, 
    observacoes TEXT, 
    CONSTRAINT pk_parceiros PRIMARY KEY (id)
);

CREATE INDEX ix_parceiros_tenant_id ON parceiros (tenant_id);

CREATE INDEX ix_parceiros_tenant_nome ON parceiros (tenant_id, nome);

CREATE UNIQUE INDEX uq_parceiros_tenant_cpf_active ON parceiros (tenant_id, cpf) WHERE deleted_at IS NULL AND cpf IS NOT NULL;

CREATE UNIQUE INDEX uq_parceiros_tenant_cnpj_active ON parceiros (tenant_id, cnpj) WHERE deleted_at IS NULL AND cnpj IS NOT NULL;

CREATE TABLE fornecedores (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    nome_fantasia VARCHAR(200), 
    cnpj VARCHAR(14), 
    ie VARCHAR(30), 
    categoria_codigo VARCHAR(60), 
    email VARCHAR(255), 
    telefone VARCHAR(20), 
    celular VARCHAR(20), 
    cep VARCHAR(8), 
    endereco VARCHAR(255), 
    numero VARCHAR(20), 
    complemento VARCHAR(100), 
    bairro VARCHAR(100), 
    cidade VARCHAR(100), 
    uf VARCHAR(2), 
    banco VARCHAR(100), 
    agencia VARCHAR(20), 
    conta VARCHAR(30), 
    pix_chave VARCHAR(140), 
    prazo_pagamento_dias INTEGER DEFAULT '30' NOT NULL, 
    desconto_percentual NUMERIC(7, 4) DEFAULT '0' NOT NULL, 
    rating INTEGER, 
    bloqueado BOOLEAN DEFAULT false NOT NULL, 
    motivo_bloqueio VARCHAR(255), 
    observacoes TEXT, 
    CONSTRAINT pk_fornecedores PRIMARY KEY (id)
);

CREATE INDEX ix_fornecedores_tenant_id ON fornecedores (tenant_id);

CREATE INDEX ix_fornecedores_tenant_nome ON fornecedores (tenant_id, nome);

CREATE UNIQUE INDEX uq_fornecedores_tenant_cnpj_active ON fornecedores (tenant_id, cnpj) WHERE deleted_at IS NULL AND cnpj IS NOT NULL;

CREATE TABLE vendedores (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    usuario_id UUID, 
    filial_id UUID, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    email VARCHAR(255), 
    telefone VARCHAR(20), 
    meta_contratos_mes INTEGER DEFAULT '0' NOT NULL, 
    meta_faturamento_mes NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    comissao_percentual NUMERIC(7, 4) DEFAULT '0' NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_vendedores PRIMARY KEY (id), 
    CONSTRAINT fk_vendedores_usuario_id_users FOREIGN KEY(usuario_id) REFERENCES users (id) ON DELETE SET NULL, 
    CONSTRAINT fk_vendedores_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL
);

CREATE INDEX ix_vendedores_tenant_id ON vendedores (tenant_id);

CREATE INDEX ix_vendedores_usuario_id ON vendedores (usuario_id);

CREATE INDEX ix_vendedores_filial_id ON vendedores (filial_id);

CREATE INDEX ix_vendedores_tenant_nome ON vendedores (tenant_id, nome);

CREATE UNIQUE INDEX uq_vendedores_tenant_usuario_active ON vendedores (tenant_id, usuario_id) WHERE deleted_at IS NULL AND usuario_id IS NOT NULL;

ALTER TABLE motoristas ENABLE ROW LEVEL SECURITY;

ALTER TABLE motoristas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON motoristas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE parceiros ENABLE ROW LEVEL SECURITY;

ALTER TABLE parceiros FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON parceiros
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fornecedores ENABLE ROW LEVEL SECURITY;

ALTER TABLE fornecedores FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fornecedores
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE vendedores ENABLE ROW LEVEL SECURITY;

ALTER TABLE vendedores FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON vendedores
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0004_cadastros_completos' WHERE alembic_version.version_num = '0003_cadastros';

INSERT INTO alembic_version (version_num) VALUES ('0004_cadastros_completos') ON CONFLICT (version_num) DO NOTHING;
