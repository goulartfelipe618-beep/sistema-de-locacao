CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE intermediacao_configs (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL,
    modo_operacao VARCHAR(20) DEFAULT 'hibrida' NOT NULL,
    exige_contrato_fornecedor BOOLEAN DEFAULT true NOT NULL,
    aprovar_reserva_automaticamente BOOLEAN DEFAULT false NOT NULL,
    publicar_terceiros_site BOOLEAN DEFAULT true NOT NULL,
    margem_minima_percentual NUMERIC(7, 4) DEFAULT '10' NOT NULL,
    buffer_disponibilidade_horas INTEGER DEFAULT 4 NOT NULL,
    priorizar_frota_propria BOOLEAN DEFAULT true NOT NULL,
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_intermediacao_configs PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_intermediacao_configs_tenant_active ON intermediacao_configs (tenant_id) WHERE deleted_at IS NULL;

CREATE TABLE fornecedor_contratos_locacao (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL,
    fornecedor_id UUID NOT NULL,
    numero VARCHAR(30) NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'rascunho' NOT NULL,
    modelo_negocio VARCHAR(20) DEFAULT 'repasse' NOT NULL,
    tipo_calculo VARCHAR(25) DEFAULT 'percentual_receita' NOT NULL,
    percentual_repasse NUMERIC(7, 4),
    percentual_comissao NUMERIC(7, 4),
    valor_diaria_repasse NUMERIC(14, 2),
    margem_minima_percentual NUMERIC(7, 4),
    prazo_pagamento_dias INTEGER DEFAULT 30 NOT NULL,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE,
    km_livre_dia INTEGER,
    valor_km_excedente NUMERIC(14, 2),
    seguro_incluso BOOLEAN DEFAULT false NOT NULL,
    documento_storage_key VARCHAR(500),
    clausulas TEXT,
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_fornecedor_contratos_locacao PRIMARY KEY (id),
    CONSTRAINT fk_fornecedor_contratos_locacao_fornecedor_id_fornecedores FOREIGN KEY(fornecedor_id) REFERENCES fornecedores (id) ON DELETE RESTRICT
);

CREATE INDEX ix_fornecedor_contratos_locacao_fornecedor ON fornecedor_contratos_locacao (fornecedor_id);

CREATE UNIQUE INDEX uq_fornecedor_contratos_locacao_numero_active ON fornecedor_contratos_locacao (tenant_id, numero) WHERE deleted_at IS NULL;

CREATE TABLE fornecedor_contratos_precos (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL,
    contrato_fornecedor_id UUID NOT NULL,
    categoria_id UUID,
    filial_id UUID,
    vigencia_inicio DATE NOT NULL,
    vigencia_fim DATE,
    hora_inicio TIME,
    hora_fim TIME,
    dias_minimos INTEGER DEFAULT 1 NOT NULL,
    dias_maximos INTEGER,
    valor_cliente_diaria NUMERIC(14, 2) DEFAULT '0' NOT NULL,
    valor_repasse_diaria NUMERIC(14, 2) DEFAULT '0' NOT NULL,
    valor_hora_extra_cliente NUMERIC(14, 2),
    valor_hora_extra_repasse NUMERIC(14, 2),
    percentual_comissao NUMERIC(7, 4),
    taxa_entrega NUMERIC(14, 2),
    prioridade INTEGER DEFAULT 0 NOT NULL,
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_fornecedor_contratos_precos PRIMARY KEY (id),
    CONSTRAINT fk_fornecedor_contratos_precos_contrato_fornecedor_id FOREIGN KEY(contrato_fornecedor_id) REFERENCES fornecedor_contratos_locacao (id) ON DELETE CASCADE,
    CONSTRAINT fk_fornecedor_contratos_precos_categoria_id FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE SET NULL,
    CONSTRAINT fk_fornecedor_contratos_precos_filial_id FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL
);

ALTER TABLE fornecedores ADD COLUMN locadora_parceira BOOLEAN DEFAULT false NOT NULL;

ALTER TABLE fornecedores ADD COLUMN modelo_negocio_padrao VARCHAR(20);

ALTER TABLE fornecedores ADD COLUMN contato_operacional_nome VARCHAR(200);

ALTER TABLE fornecedores ADD COLUMN contato_operacional_telefone VARCHAR(20);

ALTER TABLE fornecedores ADD COLUMN contato_operacional_email VARCHAR(255);

ALTER TABLE fornecedores ADD COLUMN margem_padrao_percentual NUMERIC(7, 4);

ALTER TABLE frota_veiculos ADD COLUMN contrato_fornecedor_id UUID;

ALTER TABLE frota_veiculos ADD COLUMN publicar_site BOOLEAN DEFAULT true NOT NULL;

ALTER TABLE frota_veiculos ADD COLUMN exige_aprovacao_fornecedor BOOLEAN DEFAULT true NOT NULL;

ALTER TABLE frota_veiculos ADD CONSTRAINT fk_frota_veiculos_contrato_fornecedor FOREIGN KEY(contrato_fornecedor_id) REFERENCES fornecedor_contratos_locacao (id) ON DELETE SET NULL;

ALTER TABLE res_reservas ADD COLUMN fornecedor_id UUID;

ALTER TABLE res_reservas ADD COLUMN contrato_fornecedor_id UUID;

ALTER TABLE res_reservas ADD COLUMN modelo_negocio_terceiro VARCHAR(20);

ALTER TABLE res_reservas ADD COLUMN intermediacao_status VARCHAR(25) DEFAULT 'nao_aplicavel' NOT NULL;

ALTER TABLE res_reservas ADD COLUMN valor_repasse_total NUMERIC(14, 2);

ALTER TABLE res_reservas ADD COLUMN valor_margem NUMERIC(14, 2);

ALTER TABLE res_reservas ADD COLUMN valor_comissao NUMERIC(14, 2);

ALTER TABLE res_reservas ADD COLUMN repasse_snapshot TEXT;

ALTER TABLE res_reservas ADD CONSTRAINT fk_res_reservas_fornecedor FOREIGN KEY(fornecedor_id) REFERENCES fornecedores (id) ON DELETE SET NULL;

ALTER TABLE res_reservas ADD CONSTRAINT fk_res_reservas_contrato_fornecedor FOREIGN KEY(contrato_fornecedor_id) REFERENCES fornecedor_contratos_locacao (id) ON DELETE SET NULL;

ALTER TABLE loc_contratos ADD COLUMN fornecedor_id UUID;

ALTER TABLE loc_contratos ADD COLUMN contrato_fornecedor_id UUID;

ALTER TABLE loc_contratos ADD COLUMN modelo_negocio_terceiro VARCHAR(20);

ALTER TABLE loc_contratos ADD COLUMN intermediacao_status VARCHAR(25) DEFAULT 'nao_aplicavel' NOT NULL;

ALTER TABLE loc_contratos ADD COLUMN valor_repasse_total NUMERIC(14, 2);

ALTER TABLE loc_contratos ADD COLUMN valor_margem NUMERIC(14, 2);

ALTER TABLE loc_contratos ADD COLUMN valor_comissao NUMERIC(14, 2);

ALTER TABLE loc_contratos ADD COLUMN repasse_snapshot TEXT;

ALTER TABLE loc_contratos ADD CONSTRAINT fk_loc_contratos_fornecedor FOREIGN KEY(fornecedor_id) REFERENCES fornecedores (id) ON DELETE SET NULL;

ALTER TABLE loc_contratos ADD CONSTRAINT fk_loc_contratos_contrato_fornecedor FOREIGN KEY(contrato_fornecedor_id) REFERENCES fornecedor_contratos_locacao (id) ON DELETE SET NULL;

CREATE TABLE frota_indisponibilidade_terceiro (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL,
    veiculo_id UUID NOT NULL,
    fornecedor_id UUID NOT NULL,
    inicio_em TIMESTAMP WITH TIME ZONE NOT NULL,
    fim_em TIMESTAMP WITH TIME ZONE,
    motivo VARCHAR(30) DEFAULT 'locado_pelo_proprietario' NOT NULL,
    sincronizar_site BOOLEAN DEFAULT true NOT NULL,
    registrado_por_id UUID,
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_frota_indisponibilidade_terceiro PRIMARY KEY (id),
    CONSTRAINT fk_frota_indisponibilidade_terceiro_veiculo_id FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE CASCADE,
    CONSTRAINT fk_frota_indisponibilidade_terceiro_fornecedor_id FOREIGN KEY(fornecedor_id) REFERENCES fornecedores (id) ON DELETE RESTRICT,
    CONSTRAINT fk_frota_indisponibilidade_terceiro_registrado_por_id FOREIGN KEY(registrado_por_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE loc_repasse_lancamentos (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL,
    contrato_id UUID NOT NULL,
    reserva_id UUID,
    fornecedor_id UUID NOT NULL,
    contrato_fornecedor_id UUID,
    modelo_negocio VARCHAR(20) NOT NULL,
    valor_cliente NUMERIC(14, 2) DEFAULT '0' NOT NULL,
    valor_repasse NUMERIC(14, 2) DEFAULT '0' NOT NULL,
    valor_margem NUMERIC(14, 2) DEFAULT '0' NOT NULL,
    valor_comissao NUMERIC(14, 2) DEFAULT '0' NOT NULL,
    conta_pagar_id UUID,
    conta_receber_id UUID,
    vencimento DATE,
    status VARCHAR(20) DEFAULT 'em_aberto' NOT NULL,
    repasse_snapshot TEXT DEFAULT '{}' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_loc_repasse_lancamentos PRIMARY KEY (id),
    CONSTRAINT fk_loc_repasse_lancamentos_contrato_id FOREIGN KEY(contrato_id) REFERENCES loc_contratos (id) ON DELETE CASCADE,
    CONSTRAINT fk_loc_repasse_lancamentos_reserva_id FOREIGN KEY(reserva_id) REFERENCES res_reservas (id) ON DELETE SET NULL,
    CONSTRAINT fk_loc_repasse_lancamentos_fornecedor_id FOREIGN KEY(fornecedor_id) REFERENCES fornecedores (id) ON DELETE RESTRICT,
    CONSTRAINT fk_loc_repasse_lancamentos_contrato_fornecedor_id FOREIGN KEY(contrato_fornecedor_id) REFERENCES fornecedor_contratos_locacao (id) ON DELETE SET NULL,
    CONSTRAINT fk_loc_repasse_lancamentos_conta_pagar_id FOREIGN KEY(conta_pagar_id) REFERENCES fin_contas_pagar (id) ON DELETE SET NULL,
    CONSTRAINT fk_loc_repasse_lancamentos_conta_receber_id FOREIGN KEY(conta_receber_id) REFERENCES fin_contas_receber (id) ON DELETE SET NULL
);

ALTER TABLE intermediacao_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE intermediacao_configs FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON intermediacao_configs
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fornecedor_contratos_locacao ENABLE ROW LEVEL SECURITY;
ALTER TABLE fornecedor_contratos_locacao FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON fornecedor_contratos_locacao
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fornecedor_contratos_precos ENABLE ROW LEVEL SECURITY;
ALTER TABLE fornecedor_contratos_precos FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON fornecedor_contratos_precos
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_indisponibilidade_terceiro ENABLE ROW LEVEL SECURITY;
ALTER TABLE frota_indisponibilidade_terceiro FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON frota_indisponibilidade_terceiro
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE loc_repasse_lancamentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE loc_repasse_lancamentos FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON loc_repasse_lancamentos
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0023_intermediacao' WHERE alembic_version.version_num = '0022_remove_whatsapp_redes';

INSERT INTO alembic_version (version_num) VALUES ('0023_intermediacao') ON CONFLICT (version_num) DO NOTHING;
