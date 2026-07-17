CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE parametros_sistema (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    filial_id UUID, 
    chave VARCHAR(120) NOT NULL, 
    valor TEXT NOT NULL, 
    CONSTRAINT pk_parametros_sistema PRIMARY KEY (id), 
    CONSTRAINT fk_parametros_sistema_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE CASCADE, 
    CONSTRAINT fk_parametros_sistema_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
);

CREATE INDEX ix_parametros_sistema_tenant ON parametros_sistema (tenant_id);

CREATE INDEX ix_parametros_sistema_chave ON parametros_sistema (chave);

CREATE INDEX ix_parametros_sistema_filial_id ON parametros_sistema (filial_id);

CREATE UNIQUE INDEX uq_parametros_tenant_chave ON parametros_sistema (tenant_id, chave) WHERE filial_id IS NULL AND deleted_at IS NULL;

CREATE UNIQUE INDEX uq_parametros_filial_chave ON parametros_sistema (tenant_id, filial_id, chave) WHERE filial_id IS NOT NULL AND deleted_at IS NULL;

ALTER TABLE parametros_sistema ENABLE ROW LEVEL SECURITY;

ALTER TABLE parametros_sistema FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON parametros_sistema
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0016_parametros' WHERE alembic_version.version_num = '0015_automacoes';

INSERT INTO alembic_version (version_num) VALUES ('0016_parametros') ON CONFLICT (version_num) DO NOTHING;
