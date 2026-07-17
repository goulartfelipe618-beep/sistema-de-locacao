CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE int_provedor_configs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    filial_id UUID, 
    tipo VARCHAR(15) NOT NULL, 
    provedor VARCHAR(60) NOT NULL, 
    nome VARCHAR(120) NOT NULL, 
    credenciais_cripto TEXT, 
    webhook_secret_cripto TEXT, 
    webhook_token VARCHAR(64) NOT NULL, 
    config_json TEXT DEFAULT '{}' NOT NULL, 
    status VARCHAR(10) DEFAULT 'ativo' NOT NULL, 
    ultimo_sync_em TIMESTAMP WITH TIME ZONE, 
    ultimo_erro TEXT, 
    CONSTRAINT pk_int_provedor_configs PRIMARY KEY (id), 
    CONSTRAINT fk_int_prov_cfg_filial_id FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL
);

CREATE INDEX ix_int_prov_cfg_tenant_tipo ON int_provedor_configs (tenant_id, tipo);

CREATE UNIQUE INDEX ix_int_prov_cfg_webhook_token ON int_provedor_configs (webhook_token);

CREATE TABLE int_webhook_eventos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    config_id UUID, 
    provedor VARCHAR(60) NOT NULL, 
    evento_tipo VARCHAR(60) NOT NULL, 
    payload_json TEXT DEFAULT '{}' NOT NULL, 
    assinatura_valida BOOLEAN DEFAULT false NOT NULL, 
    status VARCHAR(12) DEFAULT 'recebido' NOT NULL, 
    processado_em TIMESTAMP WITH TIME ZONE, 
    erro_mensagem TEXT, 
    CONSTRAINT pk_int_webhook_eventos PRIMARY KEY (id), 
    CONSTRAINT fk_int_webhook_cfg_id FOREIGN KEY(config_id) REFERENCES int_provedor_configs (id) ON DELETE SET NULL
);

CREATE INDEX ix_int_webhook_tenant_status ON int_webhook_eventos (tenant_id, status);

CREATE TABLE int_consultas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    config_id UUID, 
    tipo VARCHAR(20) NOT NULL, 
    referencia_tipo VARCHAR(40), 
    referencia_id UUID, 
    request_json TEXT DEFAULT '{}' NOT NULL, 
    response_json TEXT, 
    status VARCHAR(10) DEFAULT 'sucesso' NOT NULL, 
    erro_mensagem TEXT, 
    CONSTRAINT pk_int_consultas PRIMARY KEY (id), 
    CONSTRAINT fk_int_consulta_cfg_id FOREIGN KEY(config_id) REFERENCES int_provedor_configs (id) ON DELETE SET NULL
);

CREATE INDEX ix_int_consultas_tenant_tipo ON int_consultas (tenant_id, tipo);

CREATE TABLE int_api_keys (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(120) NOT NULL, 
    key_prefix VARCHAR(12) NOT NULL, 
    key_hash VARCHAR(128) NOT NULL, 
    scopes_json TEXT DEFAULT '[]' NOT NULL, 
    rate_limit_por_minuto INTEGER DEFAULT '60' NOT NULL, 
    ativo BOOLEAN DEFAULT true NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE, 
    ultimo_uso_em TIMESTAMP WITH TIME ZONE, 
    criado_por_id UUID, 
    CONSTRAINT pk_int_api_keys PRIMARY KEY (id), 
    CONSTRAINT fk_int_api_key_user_id FOREIGN KEY(criado_por_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_int_api_keys_prefix ON int_api_keys (key_prefix);

ALTER TABLE int_provedor_configs ENABLE ROW LEVEL SECURITY;

ALTER TABLE int_provedor_configs FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON int_provedor_configs
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE int_webhook_eventos ENABLE ROW LEVEL SECURITY;

ALTER TABLE int_webhook_eventos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON int_webhook_eventos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE int_consultas ENABLE ROW LEVEL SECURITY;

ALTER TABLE int_consultas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON int_consultas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE int_api_keys ENABLE ROW LEVEL SECURITY;

ALTER TABLE int_api_keys FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON int_api_keys
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0014_integracoes' WHERE alembic_version.version_num = '0013_relatorios';

INSERT INTO alembic_version (version_num) VALUES ('0014_integracoes') ON CONFLICT (version_num) DO NOTHING;
