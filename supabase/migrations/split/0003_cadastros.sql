CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE tabelas_auxiliares (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    grupo VARCHAR(60) NOT NULL, 
    codigo VARCHAR(60) NOT NULL, 
    descricao VARCHAR(200) NOT NULL, 
    ativo BOOLEAN DEFAULT true NOT NULL, 
    ordem INTEGER DEFAULT '0' NOT NULL, 
    sistema BOOLEAN DEFAULT false NOT NULL, 
    CONSTRAINT pk_tabelas_auxiliares PRIMARY KEY (id), 
    CONSTRAINT uq_tabelas_auxiliares_tenant_grupo_codigo UNIQUE (tenant_id, grupo, codigo)
);

CREATE INDEX ix_tabelas_auxiliares_tenant_id ON tabelas_auxiliares (tenant_id);

CREATE INDEX ix_tabelas_auxiliares_grupo ON tabelas_auxiliares (grupo);

CREATE INDEX ix_tabelas_auxiliares_tenant_grupo ON tabelas_auxiliares (tenant_id, grupo);

CREATE TABLE clientes (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    filial_id UUID, 
    person_type VARCHAR(5) NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    nome_fantasia VARCHAR(200), 
    cpf VARCHAR(11), 
    cnpj VARCHAR(14), 
    rg VARCHAR(20), 
    ie VARCHAR(30), 
    data_nascimento DATE, 
    estado_civil VARCHAR(40), 
    profissao VARCHAR(100), 
    representante_legal VARCHAR(200), 
    email VARCHAR(255), 
    telefone VARCHAR(20), 
    celular VARCHAR(20), 
    whatsapp BOOLEAN DEFAULT false NOT NULL, 
    cep VARCHAR(8), 
    endereco VARCHAR(255), 
    numero VARCHAR(20), 
    complemento VARCHAR(100), 
    bairro VARCHAR(100), 
    cidade VARCHAR(100), 
    uf VARCHAR(2), 
    categoria_codigo VARCHAR(60), 
    limite_credito NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    blacklist BOOLEAN DEFAULT false NOT NULL, 
    motivo_bloqueio VARCHAR(255), 
    observacoes TEXT, 
    CONSTRAINT pk_clientes PRIMARY KEY (id), 
    CONSTRAINT fk_clientes_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL
);

CREATE INDEX ix_clientes_tenant_id ON clientes (tenant_id);

CREATE INDEX ix_clientes_filial_id ON clientes (filial_id);

CREATE INDEX ix_clientes_tenant_nome ON clientes (tenant_id, nome);

CREATE UNIQUE INDEX uq_clientes_tenant_cpf_active ON clientes (tenant_id, cpf) WHERE deleted_at IS NULL AND cpf IS NOT NULL;

CREATE UNIQUE INDEX uq_clientes_tenant_cnpj_active ON clientes (tenant_id, cnpj) WHERE deleted_at IS NULL AND cnpj IS NOT NULL;

ALTER TABLE tabelas_auxiliares ENABLE ROW LEVEL SECURITY;

ALTER TABLE tabelas_auxiliares FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON tabelas_auxiliares
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;

ALTER TABLE clientes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON clientes
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0003_cadastros' WHERE alembic_version.version_num = '0002_foundation_hardening';

INSERT INTO alembic_version (version_num) VALUES ('0003_cadastros') ON CONFLICT (version_num) DO NOTHING;
