CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE auto_regras (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(120) NOT NULL, 
    descricao TEXT, 
    evento_gatilho VARCHAR(30) NOT NULL, 
    condicao_json TEXT DEFAULT '{}' NOT NULL, 
    acao_tipo VARCHAR(20) NOT NULL, 
    acao_params_json TEXT DEFAULT '{}' NOT NULL, 
    ativo BOOLEAN DEFAULT true NOT NULL, 
    prioridade INTEGER DEFAULT '100' NOT NULL, 
    ultima_execucao_em TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_auto_regras PRIMARY KEY (id)
);

CREATE INDEX ix_auto_regras_tenant_ativo ON auto_regras (tenant_id, ativo);

CREATE TABLE auto_workflows (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    codigo VARCHAR(60) NOT NULL, 
    nome VARCHAR(120) NOT NULL, 
    descricao TEXT, 
    ativo BOOLEAN DEFAULT true NOT NULL, 
    CONSTRAINT pk_auto_workflows PRIMARY KEY (id)
);

CREATE INDEX ix_auto_workflows_tenant_codigo ON auto_workflows (tenant_id, codigo);

CREATE TABLE auto_workflow_etapas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    ordem INTEGER NOT NULL, 
    nome VARCHAR(120) NOT NULL, 
    aprovador_papel_slug VARCHAR(60), 
    aprovador_user_id UUID, 
    sla_horas INTEGER DEFAULT '24' NOT NULL, 
    timeout_acao VARCHAR(15) DEFAULT 'escalar' NOT NULL, 
    CONSTRAINT pk_auto_workflow_etapas PRIMARY KEY (id), 
    CONSTRAINT fk_auto_wf_etapa_wf_id FOREIGN KEY(workflow_id) REFERENCES auto_workflows (id) ON DELETE CASCADE, 
    CONSTRAINT fk_auto_wf_etapa_user_id FOREIGN KEY(aprovador_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_auto_wf_etapa_workflow_ordem ON auto_workflow_etapas (workflow_id, ordem);

CREATE TABLE auto_workflow_instancias (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    etapa_atual_id UUID, 
    entidade_tipo VARCHAR(40) NOT NULL, 
    entidade_id UUID NOT NULL, 
    status VARCHAR(15) DEFAULT 'pendente' NOT NULL, 
    contexto_json TEXT DEFAULT '{}' NOT NULL, 
    iniciado_em TIMESTAMP WITH TIME ZONE, 
    concluido_em TIMESTAMP WITH TIME ZONE, 
    etapa_vence_em TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_auto_workflow_instancias PRIMARY KEY (id), 
    CONSTRAINT fk_auto_wf_inst_wf_id FOREIGN KEY(workflow_id) REFERENCES auto_workflows (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_auto_wf_inst_etapa_id FOREIGN KEY(etapa_atual_id) REFERENCES auto_workflow_etapas (id) ON DELETE SET NULL
);

CREATE INDEX ix_auto_wf_inst_tenant_status ON auto_workflow_instancias (tenant_id, status);

CREATE TABLE auto_workflow_aprovacoes (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    instancia_id UUID NOT NULL, 
    etapa_id UUID NOT NULL, 
    user_id UUID, 
    status VARCHAR(12) DEFAULT 'pendente' NOT NULL, 
    comentario TEXT, 
    decidido_em TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_auto_workflow_aprovacoes PRIMARY KEY (id), 
    CONSTRAINT fk_auto_wf_aprov_inst_id FOREIGN KEY(instancia_id) REFERENCES auto_workflow_instancias (id) ON DELETE CASCADE, 
    CONSTRAINT fk_auto_wf_aprov_etapa_id FOREIGN KEY(etapa_id) REFERENCES auto_workflow_etapas (id) ON DELETE CASCADE, 
    CONSTRAINT fk_auto_wf_aprov_user_id FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE auto_execucoes (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    tipo VARCHAR(12) NOT NULL, 
    referencia_id UUID, 
    referencia_codigo VARCHAR(120), 
    evento VARCHAR(60), 
    status VARCHAR(12) DEFAULT 'pendente' NOT NULL, 
    payload_json TEXT DEFAULT '{}' NOT NULL, 
    resultado_json TEXT, 
    erro_mensagem TEXT, 
    duracao_ms INTEGER, 
    iniciado_em TIMESTAMP WITH TIME ZONE, 
    concluido_em TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_auto_execucoes PRIMARY KEY (id)
);

CREATE INDEX ix_auto_exec_tenant_tipo ON auto_execucoes (tenant_id, tipo);

CREATE INDEX ix_auto_exec_tenant_status ON auto_execucoes (tenant_id, status);

ALTER TABLE auto_regras ENABLE ROW LEVEL SECURITY;

ALTER TABLE auto_regras FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON auto_regras
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE auto_workflows ENABLE ROW LEVEL SECURITY;

ALTER TABLE auto_workflows FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON auto_workflows
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE auto_workflow_etapas ENABLE ROW LEVEL SECURITY;

ALTER TABLE auto_workflow_etapas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON auto_workflow_etapas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE auto_workflow_instancias ENABLE ROW LEVEL SECURITY;

ALTER TABLE auto_workflow_instancias FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON auto_workflow_instancias
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE auto_workflow_aprovacoes ENABLE ROW LEVEL SECURITY;

ALTER TABLE auto_workflow_aprovacoes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON auto_workflow_aprovacoes
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE auto_execucoes ENABLE ROW LEVEL SECURITY;

ALTER TABLE auto_execucoes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON auto_execucoes
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0015_automacoes' WHERE alembic_version.version_num = '0014_integracoes';

INSERT INTO alembic_version (version_num) VALUES ('0015_automacoes') ON CONFLICT (version_num) DO NOTHING;
