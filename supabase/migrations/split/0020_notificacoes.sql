CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE notificacoes (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    user_id UUID, 
    titulo VARCHAR(200) NOT NULL, 
    mensagem TEXT NOT NULL, 
    link VARCHAR(500), 
    lida BOOLEAN DEFAULT false NOT NULL, 
    lida_em TIMESTAMP WITH TIME ZONE, 
    evento VARCHAR(80), 
    referencia_tipo VARCHAR(80), 
    referencia_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_notificacoes PRIMARY KEY (id), 
    CONSTRAINT fk_notificacoes_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT fk_notificacoes_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_notificacoes_tenant_user ON notificacoes (tenant_id, user_id);

CREATE INDEX ix_notificacoes_tenant_lida ON notificacoes (tenant_id, lida);

CREATE TABLE notificacao_envios (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    notificacao_id UUID, 
    canal VARCHAR(20) NOT NULL, 
    destino VARCHAR(255) NOT NULL, 
    assunto VARCHAR(255), 
    corpo TEXT NOT NULL, 
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL, 
    erro_mensagem TEXT, 
    enviado_em TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_notificacao_envios PRIMARY KEY (id), 
    CONSTRAINT fk_notificacao_envios_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT fk_notificacao_envios_notificacao_id_notificacoes FOREIGN KEY(notificacao_id) REFERENCES notificacoes (id) ON DELETE SET NULL
);

CREATE INDEX ix_notificacao_envios_tenant ON notificacao_envios (tenant_id);

UPDATE alembic_version SET version_num='0020_notificacoes' WHERE alembic_version.version_num = '0019_outbound_webhooks';

INSERT INTO alembic_version (version_num) VALUES ('0020_notificacoes') ON CONFLICT (version_num) DO NOTHING;
