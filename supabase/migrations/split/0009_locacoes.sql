CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE loc_contratos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    versao INTEGER DEFAULT '1' NOT NULL, 
    status VARCHAR(25) DEFAULT 'rascunho' NOT NULL, 
    reserva_id UUID, 
    cliente_id UUID NOT NULL, 
    veiculo_id UUID NOT NULL, 
    categoria_id UUID NOT NULL, 
    filial_retirada_id UUID NOT NULL, 
    filial_devolucao_id UUID NOT NULL, 
    retirada_prevista_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    devolucao_prevista_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    checkout_em TIMESTAMP WITH TIME ZONE, 
    checkin_em TIMESTAMP WITH TIME ZONE, 
    km_saida INTEGER, 
    km_entrada INTEGER, 
    combustivel_saida INTEGER, 
    combustivel_entrada INTEGER, 
    diaria_unitaria NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    dias INTEGER DEFAULT '1' NOT NULL, 
    subtotal NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    total_taxas NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    total_protecoes NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    total_acessorios NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    desconto NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    caucao NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    ajustes_checkin NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_final NUMERIC(14, 2), 
    forma_pagamento VARCHAR(60), 
    condicao VARCHAR(25) DEFAULT 'avista' NOT NULL, 
    pricing_snapshot TEXT DEFAULT '{}' NOT NULL, 
    politica_snapshot TEXT, 
    clausulas_combustivel TEXT, 
    assinatura_tipo VARCHAR(20), 
    assinatura_key VARCHAR(500), 
    pendencia_financeira BOOLEAN DEFAULT 'false' NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_loc_contratos PRIMARY KEY (id), 
    CONSTRAINT ck_loc_contratos_ck_loc_contratos_combustivel_saida CHECK (combustivel_saida IS NULL OR (combustivel_saida >= 0 AND combustivel_saida <= 8)), 
    CONSTRAINT ck_loc_contratos_ck_loc_contratos_combustivel_entrada CHECK (combustivel_entrada IS NULL OR (combustivel_entrada >= 0 AND combustivel_entrada <= 8)), 
    CONSTRAINT fk_loc_contratos_reserva_id_res_reservas FOREIGN KEY(reserva_id) REFERENCES res_reservas (id) ON DELETE SET NULL, 
    CONSTRAINT fk_loc_contratos_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_loc_contratos_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_loc_contratos_categoria_id_frota_categorias FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_loc_contratos_filial_retirada_id_filiais FOREIGN KEY(filial_retirada_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_loc_contratos_filial_devolucao_id_filiais FOREIGN KEY(filial_devolucao_id) REFERENCES filiais (id) ON DELETE RESTRICT
);

CREATE INDEX ix_loc_contratos_tenant_id ON loc_contratos (tenant_id);

CREATE INDEX ix_loc_contratos_tenant_status ON loc_contratos (tenant_id, status);

CREATE INDEX ix_loc_contratos_veiculo_id ON loc_contratos (veiculo_id);

CREATE INDEX ix_loc_contratos_cliente_id ON loc_contratos (cliente_id);

CREATE INDEX ix_loc_contratos_reserva_id ON loc_contratos (reserva_id);

CREATE UNIQUE INDEX uq_loc_contratos_tenant_numero_active ON loc_contratos (tenant_id, numero) WHERE deleted_at IS NULL;

CREATE TABLE loc_contrato_motoristas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    contrato_id UUID NOT NULL, 
    motorista_id UUID NOT NULL, 
    principal BOOLEAN DEFAULT 'false' NOT NULL, 
    CONSTRAINT pk_loc_contrato_motoristas PRIMARY KEY (id), 
    CONSTRAINT fk_loc_contrato_motoristas_contrato_id_loc_contratos FOREIGN KEY(contrato_id) REFERENCES loc_contratos (id) ON DELETE CASCADE, 
    CONSTRAINT fk_loc_contrato_motoristas_motorista_id_motoristas FOREIGN KEY(motorista_id) REFERENCES motoristas (id) ON DELETE RESTRICT
);

CREATE INDEX ix_loc_contrato_motoristas_tenant_id ON loc_contrato_motoristas (tenant_id);

CREATE INDEX ix_loc_contrato_motoristas_contrato_id ON loc_contrato_motoristas (contrato_id);

CREATE INDEX ix_loc_contrato_motoristas_motorista_id ON loc_contrato_motoristas (motorista_id);

CREATE UNIQUE INDEX uq_loc_contrato_motoristas_active ON loc_contrato_motoristas (tenant_id, contrato_id, motorista_id) WHERE deleted_at IS NULL;

CREATE TABLE loc_contrato_itens (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    contrato_id UUID NOT NULL, 
    tipo VARCHAR(20) NOT NULL, 
    referencia_id UUID, 
    descricao VARCHAR(200) NOT NULL, 
    quantidade NUMERIC(10, 2) DEFAULT '1' NOT NULL, 
    valor_unitario NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    CONSTRAINT pk_loc_contrato_itens PRIMARY KEY (id), 
    CONSTRAINT fk_loc_contrato_itens_contrato_id_loc_contratos FOREIGN KEY(contrato_id) REFERENCES loc_contratos (id) ON DELETE CASCADE
);

CREATE INDEX ix_loc_contrato_itens_tenant_id ON loc_contrato_itens (tenant_id);

CREATE INDEX ix_loc_contrato_itens_contrato_id ON loc_contrato_itens (contrato_id);

CREATE TABLE loc_contrato_aditivos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    contrato_id UUID NOT NULL, 
    versao INTEGER NOT NULL, 
    devolucao_anterior TIMESTAMP WITH TIME ZONE NOT NULL, 
    devolucao_nova TIMESTAMP WITH TIME ZONE NOT NULL, 
    dias_extra INTEGER NOT NULL, 
    valor_aditivo NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    pricing_snapshot TEXT DEFAULT '{}' NOT NULL, 
    aprovado BOOLEAN DEFAULT 'false' NOT NULL, 
    motivo VARCHAR(255), 
    CONSTRAINT pk_loc_contrato_aditivos PRIMARY KEY (id), 
    CONSTRAINT fk_loc_contrato_aditivos_contrato_id_loc_contratos FOREIGN KEY(contrato_id) REFERENCES loc_contratos (id) ON DELETE CASCADE
);

CREATE INDEX ix_loc_contrato_aditivos_tenant_id ON loc_contrato_aditivos (tenant_id);

CREATE INDEX ix_loc_contrato_aditivos_contrato_id ON loc_contrato_aditivos (contrato_id);

CREATE INDEX ix_loc_contrato_aditivos_tenant_contrato ON loc_contrato_aditivos (tenant_id, contrato_id);

CREATE TABLE loc_vistorias (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    contrato_id UUID NOT NULL, 
    tipo VARCHAR(15) NOT NULL, 
    km INTEGER NOT NULL, 
    combustivel_nivel INTEGER NOT NULL, 
    observacoes TEXT, 
    realizado_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    realizado_por_user_id UUID, 
    checklist_json TEXT DEFAULT '{}' NOT NULL, 
    CONSTRAINT pk_loc_vistorias PRIMARY KEY (id), 
    CONSTRAINT ck_loc_vistorias_ck_loc_vistorias_combustivel_nivel CHECK (combustivel_nivel >= 0 AND combustivel_nivel <= 8), 
    CONSTRAINT fk_loc_vistorias_contrato_id_loc_contratos FOREIGN KEY(contrato_id) REFERENCES loc_contratos (id) ON DELETE CASCADE, 
    CONSTRAINT fk_loc_vistorias_realizado_por_user_id_users FOREIGN KEY(realizado_por_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_loc_vistorias_tenant_id ON loc_vistorias (tenant_id);

CREATE INDEX ix_loc_vistorias_contrato_id ON loc_vistorias (contrato_id);

CREATE INDEX ix_loc_vistorias_tenant_tipo ON loc_vistorias (tenant_id, tipo);

CREATE TABLE loc_vistoria_fotos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    vistoria_id UUID NOT NULL, 
    storage_key VARCHAR(500) NOT NULL, 
    angulo VARCHAR(30) NOT NULL, 
    ordem INTEGER DEFAULT '0' NOT NULL, 
    CONSTRAINT pk_loc_vistoria_fotos PRIMARY KEY (id), 
    CONSTRAINT fk_loc_vistoria_fotos_vistoria_id_loc_vistorias FOREIGN KEY(vistoria_id) REFERENCES loc_vistorias (id) ON DELETE CASCADE
);

CREATE INDEX ix_loc_vistoria_fotos_tenant_id ON loc_vistoria_fotos (tenant_id);

CREATE INDEX ix_loc_vistoria_fotos_vistoria_id ON loc_vistoria_fotos (vistoria_id);

CREATE TABLE loc_avarias (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    veiculo_id UUID NOT NULL, 
    contrato_id UUID, 
    vistoria_id UUID, 
    origem VARCHAR(15) NOT NULL, 
    localizacao VARCHAR(100) NOT NULL, 
    severidade VARCHAR(10) NOT NULL, 
    responsabilidade VARCHAR(15), 
    laudo TEXT, 
    valor_reparo NUMERIC(14, 2), 
    status VARCHAR(30) DEFAULT 'registrada' NOT NULL, 
    os_id UUID, 
    observacoes TEXT, 
    CONSTRAINT pk_loc_avarias PRIMARY KEY (id), 
    CONSTRAINT fk_loc_avarias_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_loc_avarias_contrato_id_loc_contratos FOREIGN KEY(contrato_id) REFERENCES loc_contratos (id) ON DELETE SET NULL, 
    CONSTRAINT fk_loc_avarias_vistoria_id_loc_vistorias FOREIGN KEY(vistoria_id) REFERENCES loc_vistorias (id) ON DELETE SET NULL, 
    CONSTRAINT fk_loc_avarias_os_id_man_ordens_servico FOREIGN KEY(os_id) REFERENCES man_ordens_servico (id) ON DELETE SET NULL
);

CREATE INDEX ix_loc_avarias_tenant_id ON loc_avarias (tenant_id);

CREATE INDEX ix_loc_avarias_veiculo_id ON loc_avarias (veiculo_id);

CREATE INDEX ix_loc_avarias_contrato_id ON loc_avarias (contrato_id);

CREATE INDEX ix_loc_avarias_tenant_status ON loc_avarias (tenant_id, status);

CREATE TABLE loc_avaria_fotos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    avaria_id UUID NOT NULL, 
    storage_key VARCHAR(500) NOT NULL, 
    legenda VARCHAR(200), 
    CONSTRAINT pk_loc_avaria_fotos PRIMARY KEY (id), 
    CONSTRAINT fk_loc_avaria_fotos_avaria_id_loc_avarias FOREIGN KEY(avaria_id) REFERENCES loc_avarias (id) ON DELETE CASCADE
);

CREATE INDEX ix_loc_avaria_fotos_tenant_id ON loc_avaria_fotos (tenant_id);

CREATE INDEX ix_loc_avaria_fotos_avaria_id ON loc_avaria_fotos (avaria_id);

CREATE TABLE loc_multas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    veiculo_id UUID NOT NULL, 
    contrato_id UUID, 
    cliente_id UUID, 
    motorista_id UUID, 
    ocorrido_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    orgao VARCHAR(120) NOT NULL, 
    codigo_infracao VARCHAR(20) NOT NULL, 
    valor NUMERIC(14, 2) NOT NULL, 
    pontuacao INTEGER DEFAULT '0' NOT NULL, 
    ait VARCHAR(40), 
    status VARCHAR(15) DEFAULT 'recebida' NOT NULL, 
    taxa_admin NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_loc_multas PRIMARY KEY (id), 
    CONSTRAINT fk_loc_multas_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_loc_multas_contrato_id_loc_contratos FOREIGN KEY(contrato_id) REFERENCES loc_contratos (id) ON DELETE SET NULL, 
    CONSTRAINT fk_loc_multas_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE SET NULL, 
    CONSTRAINT fk_loc_multas_motorista_id_motoristas FOREIGN KEY(motorista_id) REFERENCES motoristas (id) ON DELETE SET NULL
);

CREATE INDEX ix_loc_multas_tenant_id ON loc_multas (tenant_id);

CREATE INDEX ix_loc_multas_veiculo_id ON loc_multas (veiculo_id);

CREATE INDEX ix_loc_multas_contrato_id ON loc_multas (contrato_id);

CREATE INDEX ix_loc_multas_tenant_status ON loc_multas (tenant_id, status);

CREATE INDEX ix_loc_multas_ocorrido_em ON loc_multas (ocorrido_em);

ALTER TABLE loc_contratos ENABLE ROW LEVEL SECURITY;

ALTER TABLE loc_contratos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON loc_contratos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE loc_contrato_motoristas ENABLE ROW LEVEL SECURITY;

ALTER TABLE loc_contrato_motoristas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON loc_contrato_motoristas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE loc_contrato_itens ENABLE ROW LEVEL SECURITY;

ALTER TABLE loc_contrato_itens FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON loc_contrato_itens
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE loc_contrato_aditivos ENABLE ROW LEVEL SECURITY;

ALTER TABLE loc_contrato_aditivos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON loc_contrato_aditivos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE loc_vistorias ENABLE ROW LEVEL SECURITY;

ALTER TABLE loc_vistorias FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON loc_vistorias
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE loc_vistoria_fotos ENABLE ROW LEVEL SECURITY;

ALTER TABLE loc_vistoria_fotos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON loc_vistoria_fotos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE loc_avarias ENABLE ROW LEVEL SECURITY;

ALTER TABLE loc_avarias FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON loc_avarias
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE loc_avaria_fotos ENABLE ROW LEVEL SECURITY;

ALTER TABLE loc_avaria_fotos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON loc_avaria_fotos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE loc_multas ENABLE ROW LEVEL SECURITY;

ALTER TABLE loc_multas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON loc_multas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0009_locacoes' WHERE alembic_version.version_num = '0008_reservas';

INSERT INTO alembic_version (version_num) VALUES ('0009_locacoes') ON CONFLICT (version_num) DO NOTHING;
