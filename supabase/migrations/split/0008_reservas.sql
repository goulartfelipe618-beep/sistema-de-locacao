CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE res_reservas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL, 
    alocacao VARCHAR(20) DEFAULT 'categoria' NOT NULL, 
    origem VARCHAR(20) DEFAULT 'balcao' NOT NULL, 
    cliente_id UUID NOT NULL, 
    categoria_id UUID NOT NULL, 
    veiculo_id UUID, 
    filial_retirada_id UUID NOT NULL, 
    filial_devolucao_id UUID NOT NULL, 
    retirada_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    devolucao_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    endereco_entrega TEXT, 
    vendedor_id UUID, 
    parceiro_id UUID, 
    politica_cancelamento_id UUID, 
    forma_pagamento_prevista VARCHAR(60), 
    cupom_codigo VARCHAR(40), 
    diaria_unitaria NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    dias INTEGER DEFAULT '1' NOT NULL, 
    subtotal NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    total_taxas NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    total_protecoes NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    total_acessorios NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    desconto NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    pricing_snapshot TEXT DEFAULT '{}' NOT NULL, 
    politica_snapshot TEXT, 
    motivo_cancelamento VARCHAR(255), 
    valor_retencao NUMERIC(14, 2), 
    observacoes TEXT, 
    requer_aprovacao BOOLEAN DEFAULT 'false' NOT NULL, 
    CONSTRAINT pk_res_reservas PRIMARY KEY (id), 
    CONSTRAINT fk_res_reservas_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_res_reservas_categoria_id_frota_categorias FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_res_reservas_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE SET NULL, 
    CONSTRAINT fk_res_reservas_filial_retirada_id_filiais FOREIGN KEY(filial_retirada_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_res_reservas_filial_devolucao_id_filiais FOREIGN KEY(filial_devolucao_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_res_reservas_vendedor_id_vendedores FOREIGN KEY(vendedor_id) REFERENCES vendedores (id) ON DELETE SET NULL, 
    CONSTRAINT fk_res_reservas_parceiro_id_parceiros FOREIGN KEY(parceiro_id) REFERENCES parceiros (id) ON DELETE SET NULL, 
    CONSTRAINT fk_res_res_pol_cancel_id FOREIGN KEY(politica_cancelamento_id) REFERENCES tar_politicas_cancelamento (id) ON DELETE SET NULL
);

CREATE INDEX ix_res_reservas_tenant_id ON res_reservas (tenant_id);

CREATE INDEX ix_res_reservas_tenant_status ON res_reservas (tenant_id, status);

CREATE INDEX ix_res_reservas_tenant_retirada ON res_reservas (tenant_id, retirada_em);

CREATE INDEX ix_res_reservas_veiculo_id ON res_reservas (veiculo_id);

CREATE UNIQUE INDEX uq_res_reservas_tenant_numero_active ON res_reservas (tenant_id, numero) WHERE deleted_at IS NULL;

CREATE TABLE res_cotacoes (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    status VARCHAR(20) DEFAULT 'aberta' NOT NULL, 
    validade_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    filial_retirada_id UUID NOT NULL, 
    filial_devolucao_id UUID NOT NULL, 
    categoria_id UUID NOT NULL, 
    veiculo_id UUID, 
    retirada_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    devolucao_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    cliente_id UUID, 
    converted_reserva_id UUID, 
    origem VARCHAR(20) DEFAULT 'balcao' NOT NULL, 
    parceiro_id UUID, 
    diaria_unitaria NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    dias INTEGER DEFAULT '1' NOT NULL, 
    subtotal NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    total_taxas NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    total_protecoes NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    total_acessorios NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    desconto NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    pricing_snapshot TEXT DEFAULT '{}' NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_res_cotacoes PRIMARY KEY (id), 
    CONSTRAINT fk_res_cotacoes_filial_retirada_id_filiais FOREIGN KEY(filial_retirada_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_res_cotacoes_filial_devolucao_id_filiais FOREIGN KEY(filial_devolucao_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_res_cotacoes_categoria_id_frota_categorias FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_res_cotacoes_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE SET NULL, 
    CONSTRAINT fk_res_cotacoes_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE SET NULL, 
    CONSTRAINT fk_res_cotacoes_converted_reserva_id_res_reservas FOREIGN KEY(converted_reserva_id) REFERENCES res_reservas (id) ON DELETE SET NULL, 
    CONSTRAINT fk_res_cotacoes_parceiro_id_parceiros FOREIGN KEY(parceiro_id) REFERENCES parceiros (id) ON DELETE SET NULL
);

CREATE INDEX ix_res_cotacoes_tenant_id ON res_cotacoes (tenant_id);

CREATE INDEX ix_res_cotacoes_tenant_status ON res_cotacoes (tenant_id, status);

CREATE INDEX ix_res_cotacoes_validade ON res_cotacoes (validade_em);

CREATE UNIQUE INDEX uq_res_cotacoes_tenant_numero_active ON res_cotacoes (tenant_id, numero) WHERE deleted_at IS NULL;

CREATE TABLE res_reserva_motoristas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    reserva_id UUID NOT NULL, 
    motorista_id UUID NOT NULL, 
    principal BOOLEAN DEFAULT 'false' NOT NULL, 
    CONSTRAINT pk_res_reserva_motoristas PRIMARY KEY (id), 
    CONSTRAINT fk_res_reserva_motoristas_reserva_id_res_reservas FOREIGN KEY(reserva_id) REFERENCES res_reservas (id) ON DELETE CASCADE, 
    CONSTRAINT fk_res_reserva_motoristas_motorista_id_motoristas FOREIGN KEY(motorista_id) REFERENCES motoristas (id) ON DELETE RESTRICT
);

CREATE INDEX ix_res_reserva_motoristas_tenant_id ON res_reserva_motoristas (tenant_id);

CREATE INDEX ix_res_reserva_motoristas_reserva_id ON res_reserva_motoristas (reserva_id);

CREATE INDEX ix_res_reserva_motoristas_motorista_id ON res_reserva_motoristas (motorista_id);

CREATE UNIQUE INDEX uq_res_reserva_motoristas_active ON res_reserva_motoristas (tenant_id, reserva_id, motorista_id) WHERE deleted_at IS NULL;

CREATE TABLE res_reserva_itens (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    reserva_id UUID NOT NULL, 
    tipo VARCHAR(20) NOT NULL, 
    referencia_id UUID, 
    descricao VARCHAR(200) NOT NULL, 
    quantidade NUMERIC(10, 2) DEFAULT '1' NOT NULL, 
    valor_unitario NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    CONSTRAINT pk_res_reserva_itens PRIMARY KEY (id), 
    CONSTRAINT fk_res_reserva_itens_reserva_id_res_reservas FOREIGN KEY(reserva_id) REFERENCES res_reservas (id) ON DELETE CASCADE
);

CREATE INDEX ix_res_reserva_itens_tenant_id ON res_reserva_itens (tenant_id);

CREATE INDEX ix_res_reserva_itens_reserva_id ON res_reserva_itens (reserva_id);

ALTER TABLE res_reservas ENABLE ROW LEVEL SECURITY;

ALTER TABLE res_reservas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON res_reservas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE res_cotacoes ENABLE ROW LEVEL SECURITY;

ALTER TABLE res_cotacoes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON res_cotacoes
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE res_reserva_motoristas ENABLE ROW LEVEL SECURITY;

ALTER TABLE res_reserva_motoristas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON res_reserva_motoristas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE res_reserva_itens ENABLE ROW LEVEL SECURITY;

ALTER TABLE res_reserva_itens FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON res_reserva_itens
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0008_reservas' WHERE alembic_version.version_num = '0007_tarifario';

INSERT INTO alembic_version (version_num) VALUES ('0008_reservas') ON CONFLICT (version_num) DO NOTHING;
