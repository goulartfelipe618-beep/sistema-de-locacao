CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE tar_tabelas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    vigencia_inicio DATE NOT NULL, 
    vigencia_fim DATE, 
    canal VARCHAR(20) DEFAULT 'todos' NOT NULL, 
    filial_id UUID, 
    parceiro_id UUID, 
    cliente_id UUID, 
    prioridade INTEGER DEFAULT '0' NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_tar_tabelas PRIMARY KEY (id), 
    CONSTRAINT fk_tar_tabelas_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL, 
    CONSTRAINT fk_tar_tabelas_parceiro_id_parceiros FOREIGN KEY(parceiro_id) REFERENCES parceiros (id) ON DELETE SET NULL, 
    CONSTRAINT fk_tar_tabelas_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE SET NULL
);

CREATE INDEX ix_tar_tabelas_tenant_id ON tar_tabelas (tenant_id);

CREATE INDEX ix_tar_tabelas_tenant_nome ON tar_tabelas (tenant_id, nome);

CREATE INDEX ix_tar_tabelas_tenant_vigencia ON tar_tabelas (tenant_id, vigencia_inicio);

CREATE INDEX ix_tar_tabelas_tenant_canal ON tar_tabelas (tenant_id, canal);

CREATE INDEX ix_tar_tabelas_tenant_prioridade ON tar_tabelas (tenant_id, prioridade);

CREATE INDEX ix_tar_tabelas_filial_id ON tar_tabelas (filial_id);

CREATE INDEX ix_tar_tabelas_parceiro_id ON tar_tabelas (parceiro_id);

CREATE INDEX ix_tar_tabelas_cliente_id ON tar_tabelas (cliente_id);

CREATE TABLE tar_tabela_itens (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    tabela_id UUID NOT NULL, 
    categoria_id UUID NOT NULL, 
    valor_1_3 NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_4_7 NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_8_15 NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_16_30 NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_mensal NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    km_livre BOOLEAN DEFAULT true NOT NULL, 
    km_incluido INTEGER, 
    valor_km_excedente NUMERIC(14, 2), 
    CONSTRAINT pk_tar_tabela_itens PRIMARY KEY (id), 
    CONSTRAINT fk_tar_tabela_itens_tabela_id_tar_tabelas FOREIGN KEY(tabela_id) REFERENCES tar_tabelas (id) ON DELETE CASCADE, 
    CONSTRAINT fk_tar_tabela_itens_categoria_id_frota_categorias FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE RESTRICT
);

CREATE INDEX ix_tar_tabela_itens_tenant_id ON tar_tabela_itens (tenant_id);

CREATE INDEX ix_tar_tabela_itens_tabela_id ON tar_tabela_itens (tabela_id);

CREATE INDEX ix_tar_tabela_itens_categoria_id ON tar_tabela_itens (categoria_id);

CREATE UNIQUE INDEX uq_tar_tabela_itens_tabela_categoria_active ON tar_tabela_itens (tenant_id, tabela_id, categoria_id) WHERE deleted_at IS NULL;

CREATE TABLE tar_temporadas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    data_inicio DATE NOT NULL, 
    data_fim DATE NOT NULL, 
    tipo_ajuste VARCHAR(30) NOT NULL, 
    valor_ajuste NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    tabela_alternativa_id UUID, 
    estadia_minima INTEGER DEFAULT '1' NOT NULL, 
    prioridade INTEGER DEFAULT '0' NOT NULL, 
    filial_id UUID, 
    categoria_id UUID, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    CONSTRAINT pk_tar_temporadas PRIMARY KEY (id), 
    CONSTRAINT fk_tar_temporadas_tabela_alternativa_id_tar_tabelas FOREIGN KEY(tabela_alternativa_id) REFERENCES tar_tabelas (id) ON DELETE SET NULL, 
    CONSTRAINT fk_tar_temporadas_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL, 
    CONSTRAINT fk_tar_temporadas_categoria_id_frota_categorias FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE SET NULL
);

CREATE INDEX ix_tar_temporadas_tenant_id ON tar_temporadas (tenant_id);

CREATE INDEX ix_tar_temporadas_tenant_periodo ON tar_temporadas (tenant_id, data_inicio, data_fim);

CREATE INDEX ix_tar_temporadas_tenant_prioridade ON tar_temporadas (tenant_id, prioridade);

CREATE INDEX ix_tar_temporadas_tabela_alternativa_id ON tar_temporadas (tabela_alternativa_id);

CREATE INDEX ix_tar_temporadas_filial_id ON tar_temporadas (filial_id);

CREATE INDEX ix_tar_temporadas_categoria_id ON tar_temporadas (categoria_id);

CREATE TABLE tar_taxas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    descricao TEXT, 
    tipo_calculo VARCHAR(20) NOT NULL, 
    valor NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    aplicacao VARCHAR(20) DEFAULT 'opcional' NOT NULL, 
    regra_codigo VARCHAR(40), 
    tributavel BOOLEAN DEFAULT true NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    CONSTRAINT pk_tar_taxas PRIMARY KEY (id)
);

CREATE INDEX ix_tar_taxas_tenant_id ON tar_taxas (tenant_id);

CREATE INDEX ix_tar_taxas_tenant_nome ON tar_taxas (tenant_id, nome);

CREATE TABLE tar_protecoes (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    descricao TEXT, 
    valor_diaria NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    franquia NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    fornecedor_id UUID, 
    exclusoes TEXT, 
    obrigatoria BOOLEAN DEFAULT false NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    CONSTRAINT pk_tar_protecoes PRIMARY KEY (id), 
    CONSTRAINT fk_tar_protecoes_fornecedor_id_fornecedores FOREIGN KEY(fornecedor_id) REFERENCES fornecedores (id) ON DELETE SET NULL
);

CREATE INDEX ix_tar_protecoes_tenant_id ON tar_protecoes (tenant_id);

CREATE INDEX ix_tar_protecoes_tenant_nome ON tar_protecoes (tenant_id, nome);

CREATE INDEX ix_tar_protecoes_fornecedor_id ON tar_protecoes (fornecedor_id);

CREATE TABLE tar_protecao_categorias (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    protecao_id UUID NOT NULL, 
    categoria_id UUID NOT NULL, 
    CONSTRAINT pk_tar_protecao_categorias PRIMARY KEY (id), 
    CONSTRAINT fk_tar_protecao_categorias_protecao_id_tar_protecoes FOREIGN KEY(protecao_id) REFERENCES tar_protecoes (id) ON DELETE CASCADE, 
    CONSTRAINT fk_tar_protecao_categorias_categoria_id_frota_categorias FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE RESTRICT
);

CREATE INDEX ix_tar_protecao_categorias_tenant_id ON tar_protecao_categorias (tenant_id);

CREATE INDEX ix_tar_protecao_categorias_protecao_id ON tar_protecao_categorias (protecao_id);

CREATE INDEX ix_tar_protecao_categorias_categoria_id ON tar_protecao_categorias (categoria_id);

CREATE UNIQUE INDEX uq_tar_protecao_categorias_active ON tar_protecao_categorias (tenant_id, protecao_id, categoria_id) WHERE deleted_at IS NULL;

CREATE TABLE tar_politicas_cancelamento (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    canal VARCHAR(20) DEFAULT 'todos' NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    descricao TEXT, 
    CONSTRAINT pk_tar_politicas_cancelamento PRIMARY KEY (id)
);

CREATE INDEX ix_tar_politicas_cancelamento_tenant_id ON tar_politicas_cancelamento (tenant_id);

CREATE INDEX ix_tar_politicas_cancelamento_tenant_nome ON tar_politicas_cancelamento (tenant_id, nome);

CREATE TABLE tar_politica_faixas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    politica_id UUID NOT NULL, 
    horas_antes_min INTEGER DEFAULT '0' NOT NULL, 
    horas_antes_max INTEGER, 
    tipo_retencao VARCHAR(20) NOT NULL, 
    valor_retencao NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    ordem INTEGER DEFAULT '0' NOT NULL, 
    CONSTRAINT pk_tar_politica_faixas PRIMARY KEY (id), 
    CONSTRAINT fk_tar_politica_faixas_politica_id_tar_politicas_cancelamento FOREIGN KEY(politica_id) REFERENCES tar_politicas_cancelamento (id) ON DELETE CASCADE
);

CREATE INDEX ix_tar_politica_faixas_tenant_id ON tar_politica_faixas (tenant_id);

CREATE INDEX ix_tar_politica_faixas_politica_id ON tar_politica_faixas (politica_id);

CREATE INDEX ix_tar_politica_faixas_politica_ordem ON tar_politica_faixas (politica_id, ordem);

ALTER TABLE tar_tabelas ENABLE ROW LEVEL SECURITY;

ALTER TABLE tar_tabelas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON tar_tabelas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE tar_tabela_itens ENABLE ROW LEVEL SECURITY;

ALTER TABLE tar_tabela_itens FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON tar_tabela_itens
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE tar_temporadas ENABLE ROW LEVEL SECURITY;

ALTER TABLE tar_temporadas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON tar_temporadas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE tar_taxas ENABLE ROW LEVEL SECURITY;

ALTER TABLE tar_taxas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON tar_taxas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE tar_protecoes ENABLE ROW LEVEL SECURITY;

ALTER TABLE tar_protecoes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON tar_protecoes
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE tar_protecao_categorias ENABLE ROW LEVEL SECURITY;

ALTER TABLE tar_protecao_categorias FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON tar_protecao_categorias
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE tar_politicas_cancelamento ENABLE ROW LEVEL SECURITY;

ALTER TABLE tar_politicas_cancelamento FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON tar_politicas_cancelamento
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE tar_politica_faixas ENABLE ROW LEVEL SECURITY;

ALTER TABLE tar_politica_faixas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON tar_politica_faixas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0007_tarifario' WHERE alembic_version.version_num = '0006_manutencao';

INSERT INTO alembic_version (version_num) VALUES ('0007_tarifario') ON CONFLICT (version_num) DO NOTHING;
