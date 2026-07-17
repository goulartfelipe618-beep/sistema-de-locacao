CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE man_pecas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    codigo VARCHAR(60) NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    categoria_codigo VARCHAR(60), 
    unidade VARCHAR(10) DEFAULT 'UN' NOT NULL, 
    custo_medio NUMERIC(14, 4) DEFAULT '0' NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    CONSTRAINT pk_man_pecas PRIMARY KEY (id)
);

CREATE INDEX ix_man_pecas_tenant_id ON man_pecas (tenant_id);

CREATE INDEX ix_man_pecas_tenant_nome ON man_pecas (tenant_id, nome);

CREATE UNIQUE INDEX uq_man_pecas_tenant_codigo_active ON man_pecas (tenant_id, codigo) WHERE deleted_at IS NULL;

CREATE TABLE man_planos_preventivos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    descricao TEXT, 
    categoria_id UUID, 
    modelo_id UUID, 
    intervalo_km INTEGER, 
    intervalo_meses INTEGER, 
    fornecedor_sugerido_id UUID, 
    custo_estimado NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    automatico BOOLEAN DEFAULT true NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    CONSTRAINT pk_man_planos_preventivos PRIMARY KEY (id), 
    CONSTRAINT fk_man_planos_preventivos_categoria_id_frota_categorias FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE SET NULL, 
    CONSTRAINT fk_man_planos_preventivos_modelo_id_frota_modelos FOREIGN KEY(modelo_id) REFERENCES frota_modelos (id) ON DELETE SET NULL, 
    CONSTRAINT fk_man_planos_preventivos_fornecedor_sugerido_id_fornecedores FOREIGN KEY(fornecedor_sugerido_id) REFERENCES fornecedores (id) ON DELETE SET NULL
);

CREATE INDEX ix_man_planos_preventivos_tenant_id ON man_planos_preventivos (tenant_id);

CREATE INDEX ix_man_planos_preventivos_categoria_id ON man_planos_preventivos (categoria_id);

CREATE INDEX ix_man_planos_preventivos_modelo_id ON man_planos_preventivos (modelo_id);

CREATE INDEX ix_man_planos_preventivos_fornecedor_sugerido_id ON man_planos_preventivos (fornecedor_sugerido_id);

CREATE INDEX ix_man_planos_preventivos_tenant_nome ON man_planos_preventivos (tenant_id, nome);

CREATE TABLE man_plano_checklist (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    plano_id UUID NOT NULL, 
    item_descricao VARCHAR(500) NOT NULL, 
    ordem INTEGER DEFAULT '0' NOT NULL, 
    CONSTRAINT pk_man_plano_checklist PRIMARY KEY (id), 
    CONSTRAINT fk_man_plano_checklist_plano_id_man_planos_preventivos FOREIGN KEY(plano_id) REFERENCES man_planos_preventivos (id) ON DELETE CASCADE
);

CREATE INDEX ix_man_plano_checklist_tenant_id ON man_plano_checklist (tenant_id);

CREATE INDEX ix_man_plano_checklist_plano_id ON man_plano_checklist (plano_id);

CREATE INDEX ix_man_plano_checklist_plano_ordem ON man_plano_checklist (plano_id, ordem);

CREATE TABLE man_veiculo_planos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    veiculo_id UUID NOT NULL, 
    plano_id UUID NOT NULL, 
    km_ultima_execucao INTEGER, 
    data_ultima_execucao DATE, 
    CONSTRAINT pk_man_veiculo_planos PRIMARY KEY (id), 
    CONSTRAINT fk_man_veiculo_planos_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE CASCADE, 
    CONSTRAINT fk_man_veiculo_planos_plano_id_man_planos_preventivos FOREIGN KEY(plano_id) REFERENCES man_planos_preventivos (id) ON DELETE CASCADE
);

CREATE INDEX ix_man_veiculo_planos_tenant_id ON man_veiculo_planos (tenant_id);

CREATE INDEX ix_man_veiculo_planos_veiculo_id ON man_veiculo_planos (veiculo_id);

CREATE INDEX ix_man_veiculo_planos_plano_id ON man_veiculo_planos (plano_id);

CREATE UNIQUE INDEX uq_man_veiculo_planos_active ON man_veiculo_planos (tenant_id, veiculo_id, plano_id) WHERE deleted_at IS NULL;

CREATE TABLE man_ordens_servico (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    veiculo_id UUID NOT NULL, 
    tipo VARCHAR(15) NOT NULL, 
    origem VARCHAR(20) DEFAULT 'manual' NOT NULL, 
    status VARCHAR(25) DEFAULT 'aberta' NOT NULL, 
    fornecedor_id UUID, 
    filial_id UUID, 
    plano_preventivo_id UUID, 
    km_entrada INTEGER, 
    km_saida INTEGER, 
    data_abertura DATE NOT NULL, 
    data_previsao DATE, 
    data_conclusao DATE, 
    custo_mao_obra NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    custo_pecas NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    custo_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    requer_aprovacao BOOLEAN DEFAULT false NOT NULL, 
    aprovado_em TIMESTAMP WITH TIME ZONE, 
    aprovado_por_user_id UUID, 
    garantia_dias INTEGER, 
    garantia_km INTEGER, 
    status_veiculo_anterior VARCHAR(20), 
    causa VARCHAR(15), 
    responsavel_custo VARCHAR(15), 
    observacoes TEXT, 
    CONSTRAINT pk_man_ordens_servico PRIMARY KEY (id), 
    CONSTRAINT fk_man_ordens_servico_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_man_ordens_servico_fornecedor_id_fornecedores FOREIGN KEY(fornecedor_id) REFERENCES fornecedores (id) ON DELETE SET NULL, 
    CONSTRAINT fk_man_ordens_servico_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL, 
    CONSTRAINT fk_man_os_plano_prev_id FOREIGN KEY(plano_preventivo_id) REFERENCES man_planos_preventivos (id) ON DELETE SET NULL, 
    CONSTRAINT fk_man_ordens_servico_aprovado_por_user_id_users FOREIGN KEY(aprovado_por_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_man_ordens_servico_tenant_id ON man_ordens_servico (tenant_id);

CREATE INDEX ix_man_ordens_servico_veiculo_id ON man_ordens_servico (veiculo_id);

CREATE INDEX ix_man_ordens_servico_fornecedor_id ON man_ordens_servico (fornecedor_id);

CREATE INDEX ix_man_ordens_servico_filial_id ON man_ordens_servico (filial_id);

CREATE INDEX ix_man_ordens_servico_plano_preventivo_id ON man_ordens_servico (plano_preventivo_id);

CREATE INDEX ix_man_ordens_servico_aprovado_por_user_id ON man_ordens_servico (aprovado_por_user_id);

CREATE INDEX ix_man_ordens_servico_tenant_status ON man_ordens_servico (tenant_id, status);

CREATE INDEX ix_man_ordens_servico_tenant_veiculo ON man_ordens_servico (tenant_id, veiculo_id);

CREATE INDEX ix_man_ordens_servico_tenant_tipo ON man_ordens_servico (tenant_id, tipo);

CREATE UNIQUE INDEX uq_man_ordens_servico_tenant_numero_active ON man_ordens_servico (tenant_id, numero) WHERE deleted_at IS NULL;

CREATE TABLE man_os_itens (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    os_id UUID NOT NULL, 
    tipo_item VARCHAR(15) NOT NULL, 
    descricao VARCHAR(500) NOT NULL, 
    peca_id UUID, 
    quantidade NUMERIC(12, 3) DEFAULT '1' NOT NULL, 
    valor_unitario NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_man_os_itens PRIMARY KEY (id), 
    CONSTRAINT fk_man_os_itens_os_id_man_ordens_servico FOREIGN KEY(os_id) REFERENCES man_ordens_servico (id) ON DELETE CASCADE, 
    CONSTRAINT fk_man_os_itens_peca_id_man_pecas FOREIGN KEY(peca_id) REFERENCES man_pecas (id) ON DELETE SET NULL
);

CREATE INDEX ix_man_os_itens_tenant_id ON man_os_itens (tenant_id);

CREATE INDEX ix_man_os_itens_os_id ON man_os_itens (os_id);

CREATE INDEX ix_man_os_itens_peca_id ON man_os_itens (peca_id);

CREATE TABLE man_os_fotos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    os_id UUID NOT NULL, 
    storage_key VARCHAR(500) NOT NULL, 
    legenda VARCHAR(255), 
    fase VARCHAR(20), 
    ordem INTEGER DEFAULT '0' NOT NULL, 
    CONSTRAINT pk_man_os_fotos PRIMARY KEY (id), 
    CONSTRAINT fk_man_os_fotos_os_id_man_ordens_servico FOREIGN KEY(os_id) REFERENCES man_ordens_servico (id) ON DELETE CASCADE
);

CREATE INDEX ix_man_os_fotos_tenant_id ON man_os_fotos (tenant_id);

CREATE INDEX ix_man_os_fotos_os_id ON man_os_fotos (os_id);

CREATE INDEX ix_man_os_fotos_os_ordem ON man_os_fotos (os_id, ordem);

CREATE TABLE man_estoque_pecas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    peca_id UUID NOT NULL, 
    filial_id UUID NOT NULL, 
    quantidade_atual NUMERIC(12, 3) DEFAULT '0' NOT NULL, 
    quantidade_minima NUMERIC(12, 3) DEFAULT '0' NOT NULL, 
    quantidade_maxima NUMERIC(12, 3), 
    localizacao VARCHAR(100), 
    CONSTRAINT pk_man_estoque_pecas PRIMARY KEY (id), 
    CONSTRAINT fk_man_estoque_pecas_peca_id_man_pecas FOREIGN KEY(peca_id) REFERENCES man_pecas (id) ON DELETE CASCADE, 
    CONSTRAINT fk_man_estoque_pecas_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE RESTRICT
);

CREATE INDEX ix_man_estoque_pecas_tenant_id ON man_estoque_pecas (tenant_id);

CREATE INDEX ix_man_estoque_pecas_peca_id ON man_estoque_pecas (peca_id);

CREATE INDEX ix_man_estoque_pecas_filial_id ON man_estoque_pecas (filial_id);

CREATE UNIQUE INDEX uq_man_estoque_pecas_active ON man_estoque_pecas (tenant_id, peca_id, filial_id) WHERE deleted_at IS NULL;

CREATE TABLE man_estoque_movimentos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    peca_id UUID NOT NULL, 
    filial_id UUID NOT NULL, 
    filial_destino_id UUID, 
    tipo VARCHAR(15) NOT NULL, 
    quantidade NUMERIC(12, 3) NOT NULL, 
    custo_unitario NUMERIC(14, 4) DEFAULT '0' NOT NULL, 
    os_id UUID, 
    observacoes TEXT, 
    ocorrido_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_man_estoque_movimentos PRIMARY KEY (id), 
    CONSTRAINT fk_man_estoque_movimentos_peca_id_man_pecas FOREIGN KEY(peca_id) REFERENCES man_pecas (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_man_estoque_movimentos_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_man_estoque_movimentos_filial_destino_id_filiais FOREIGN KEY(filial_destino_id) REFERENCES filiais (id) ON DELETE SET NULL, 
    CONSTRAINT fk_man_estoque_movimentos_os_id_man_ordens_servico FOREIGN KEY(os_id) REFERENCES man_ordens_servico (id) ON DELETE SET NULL
);

CREATE INDEX ix_man_estoque_movimentos_tenant_id ON man_estoque_movimentos (tenant_id);

CREATE INDEX ix_man_estoque_movimentos_peca_id ON man_estoque_movimentos (peca_id);

CREATE INDEX ix_man_estoque_movimentos_filial_id ON man_estoque_movimentos (filial_id);

CREATE INDEX ix_man_estoque_movimentos_filial_destino_id ON man_estoque_movimentos (filial_destino_id);

CREATE INDEX ix_man_estoque_movimentos_os_id ON man_estoque_movimentos (os_id);

CREATE INDEX ix_man_estoque_movimentos_peca_ocorrido ON man_estoque_movimentos (peca_id, ocorrido_em);

CREATE TABLE man_pneus (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero_fogo VARCHAR(50) NOT NULL, 
    marca VARCHAR(100) NOT NULL, 
    modelo VARCHAR(100), 
    medida VARCHAR(30) NOT NULL, 
    veiculo_id UUID, 
    posicao VARCHAR(10), 
    km_instalacao INTEGER, 
    km_atual INTEGER, 
    vida_util_km INTEGER, 
    sulco_mm NUMERIC(4, 2), 
    status VARCHAR(15) DEFAULT 'novo' NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_man_pneus PRIMARY KEY (id), 
    CONSTRAINT fk_man_pneus_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE SET NULL
);

CREATE INDEX ix_man_pneus_tenant_id ON man_pneus (tenant_id);

CREATE INDEX ix_man_pneus_veiculo_id ON man_pneus (veiculo_id);

CREATE INDEX ix_man_pneus_tenant_status ON man_pneus (tenant_id, status);

CREATE UNIQUE INDEX uq_man_pneus_tenant_numero_fogo_active ON man_pneus (tenant_id, numero_fogo) WHERE deleted_at IS NULL;

CREATE TABLE man_pneu_historico (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    pneu_id UUID NOT NULL, 
    veiculo_id UUID, 
    posicao VARCHAR(10), 
    km_evento INTEGER, 
    tipo_evento VARCHAR(20) NOT NULL, 
    observacoes TEXT, 
    ocorrido_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_man_pneu_historico PRIMARY KEY (id), 
    CONSTRAINT fk_man_pneu_historico_pneu_id_man_pneus FOREIGN KEY(pneu_id) REFERENCES man_pneus (id) ON DELETE CASCADE, 
    CONSTRAINT fk_man_pneu_historico_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE SET NULL
);

CREATE INDEX ix_man_pneu_historico_tenant_id ON man_pneu_historico (tenant_id);

CREATE INDEX ix_man_pneu_historico_pneu_id ON man_pneu_historico (pneu_id);

CREATE INDEX ix_man_pneu_historico_veiculo_id ON man_pneu_historico (veiculo_id);

CREATE INDEX ix_man_pneu_historico_pneu_ocorrido ON man_pneu_historico (pneu_id, ocorrido_em);

ALTER TABLE man_pecas ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_pecas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_pecas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE man_planos_preventivos ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_planos_preventivos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_planos_preventivos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE man_plano_checklist ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_plano_checklist FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_plano_checklist
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE man_veiculo_planos ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_veiculo_planos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_veiculo_planos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE man_ordens_servico ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_ordens_servico FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_ordens_servico
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE man_os_itens ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_os_itens FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_os_itens
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE man_os_fotos ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_os_fotos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_os_fotos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE man_estoque_pecas ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_estoque_pecas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_estoque_pecas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE man_estoque_movimentos ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_estoque_movimentos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_estoque_movimentos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE man_pneus ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_pneus FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_pneus
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE man_pneu_historico ENABLE ROW LEVEL SECURITY;

ALTER TABLE man_pneu_historico FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON man_pneu_historico
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0006_manutencao' WHERE alembic_version.version_num = '0005_frota';

INSERT INTO alembic_version (version_num) VALUES ('0006_manutencao') ON CONFLICT (version_num) DO NOTHING;
