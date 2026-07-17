CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE documentos_gerados (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    filial_id UUID, 
    user_id UUID, 
    template_id VARCHAR(60) NOT NULL, 
    titulo VARCHAR(200) NOT NULL, 
    familia VARCHAR(15) NOT NULL, 
    entidade_tipo VARCHAR(40), 
    entidade_id UUID, 
    status VARCHAR(15) DEFAULT 'pendente' NOT NULL, 
    sincrono BOOLEAN DEFAULT true NOT NULL, 
    watermark VARCHAR(40), 
    storage_key VARCHAR(500), 
    conteudo_inline BYTEA, 
    content_type VARCHAR(100) DEFAULT 'application/pdf' NOT NULL, 
    tamanho_bytes INTEGER, 
    hash_sha256 VARCHAR(64), 
    erro_mensagem TEXT, 
    iniciado_em TIMESTAMP WITH TIME ZONE, 
    concluido_em TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_documentos_gerados PRIMARY KEY (id), 
    CONSTRAINT fk_documentos_gerados_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL, 
    CONSTRAINT fk_documentos_gerados_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT fk_documentos_gerados_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_documentos_gerados_tenant_status ON documentos_gerados (tenant_id, status);

CREATE INDEX ix_documentos_gerados_tenant_template ON documentos_gerados (tenant_id, template_id);

CREATE INDEX ix_documentos_gerados_entidade ON documentos_gerados (entidade_tipo, entidade_id);

CREATE INDEX ix_documentos_gerados_user_id ON documentos_gerados (user_id);

ALTER TABLE documentos_gerados ENABLE ROW LEVEL SECURITY;

ALTER TABLE documentos_gerados FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON documentos_gerados
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0017_documentos' WHERE alembic_version.version_num = '0016_parametros';

INSERT INTO alembic_version (version_num) VALUES ('0017_documentos') ON CONFLICT (version_num) DO NOTHING;
