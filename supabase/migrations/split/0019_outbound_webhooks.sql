CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE int_outbound_webhooks (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    filial_id UUID, 
    nome VARCHAR(120) NOT NULL, 
    url VARCHAR(500) NOT NULL, 
    eventos_json TEXT DEFAULT '[]' NOT NULL, 
    secret_cripto TEXT, 
    ativo BOOLEAN DEFAULT true NOT NULL, 
    ultimo_disparo_em TIMESTAMP WITH TIME ZONE, 
    ultimo_erro TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_int_outbound_webhooks PRIMARY KEY (id), 
    CONSTRAINT fk_int_outbound_webhooks_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT fk_int_outbound_webhooks_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL
);

CREATE INDEX ix_int_outbound_tenant ON int_outbound_webhooks (tenant_id);

UPDATE alembic_version SET version_num='0019_outbound_webhooks' WHERE alembic_version.version_num = '0018_tenant_branding';

INSERT INTO alembic_version (version_num) VALUES ('0019_outbound_webhooks') ON CONFLICT (version_num) DO NOTHING;
