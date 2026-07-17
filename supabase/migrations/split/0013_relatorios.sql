CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE rel_emissoes (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    user_id UUID, 
    categoria VARCHAR(15) NOT NULL, 
    relatorio_codigo VARCHAR(60) NOT NULL, 
    titulo VARCHAR(200) NOT NULL, 
    parametros_json TEXT DEFAULT '{}' NOT NULL, 
    formato VARCHAR(10) NOT NULL, 
    status VARCHAR(15) DEFAULT 'pendente' NOT NULL, 
    pesado BOOLEAN DEFAULT false NOT NULL, 
    storage_key VARCHAR(500), 
    conteudo_inline BYTEA, 
    content_type VARCHAR(100), 
    tamanho_bytes INTEGER, 
    hash_sha256 VARCHAR(64), 
    erro_mensagem TEXT, 
    iniciado_em TIMESTAMP WITH TIME ZONE, 
    concluido_em TIMESTAMP WITH TIME ZONE, 
    cache_valido_ate TIMESTAMP WITH TIME ZONE, 
    linhas_count INTEGER, 
    CONSTRAINT pk_rel_emissoes PRIMARY KEY (id), 
    CONSTRAINT fk_rel_emissoes_user_id FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_rel_emissoes_tenant_id ON rel_emissoes (tenant_id);

CREATE INDEX ix_rel_emissoes_tenant_status ON rel_emissoes (tenant_id, status);

CREATE TABLE rel_agendamentos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    user_id UUID, 
    nome VARCHAR(200) NOT NULL, 
    categoria VARCHAR(15) NOT NULL, 
    relatorio_codigo VARCHAR(60) NOT NULL, 
    parametros_json TEXT DEFAULT '{}' NOT NULL, 
    formato VARCHAR(10) DEFAULT 'pdf' NOT NULL, 
    recorrencia VARCHAR(10) NOT NULL, 
    hora_execucao VARCHAR(5) DEFAULT '08:00' NOT NULL, 
    dia_semana INTEGER, 
    dia_mes INTEGER, 
    email_destinatarios TEXT, 
    ativo BOOLEAN DEFAULT true NOT NULL, 
    ultima_execucao_em TIMESTAMP WITH TIME ZONE, 
    proxima_execucao_em TIMESTAMP WITH TIME ZONE, 
    ultima_emissao_id UUID, 
    CONSTRAINT pk_rel_agendamentos PRIMARY KEY (id), 
    CONSTRAINT fk_rel_agend_user_id FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, 
    CONSTRAINT fk_rel_agend_emissao_id FOREIGN KEY(ultima_emissao_id) REFERENCES rel_emissoes (id) ON DELETE SET NULL
);

CREATE INDEX ix_rel_agendamentos_tenant_id ON rel_agendamentos (tenant_id);

ALTER TABLE rel_emissoes ENABLE ROW LEVEL SECURITY;

ALTER TABLE rel_emissoes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON rel_emissoes
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE rel_agendamentos ENABLE ROW LEVEL SECURITY;

ALTER TABLE rel_agendamentos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON rel_agendamentos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0013_relatorios' WHERE alembic_version.version_num = '0012_fiscal';

INSERT INTO alembic_version (version_num) VALUES ('0013_relatorios') ON CONFLICT (version_num) DO NOTHING;
