CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE crm_oportunidades (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    titulo VARCHAR(200) NOT NULL, 
    estagio VARCHAR(20) DEFAULT 'lead' NOT NULL, 
    origem_lead VARCHAR(20) DEFAULT 'outro' NOT NULL, 
    vendedor_id UUID, 
    cliente_id UUID, 
    cotacao_id UUID, 
    proposta_id UUID, 
    reserva_id UUID, 
    valor_estimado NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    data_prevista_fechamento DATE, 
    motivo_perda VARCHAR(255), 
    estagio_changed_at TIMESTAMP WITH TIME ZONE, 
    ultima_interacao_em TIMESTAMP WITH TIME ZONE, 
    observacoes TEXT, 
    CONSTRAINT pk_crm_oportunidades PRIMARY KEY (id), 
    CONSTRAINT fk_crm_oportunidades_vendedor_id_vendedores FOREIGN KEY(vendedor_id) REFERENCES vendedores (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_oportunidades_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_oportunidades_cotacao_id_res_cotacoes FOREIGN KEY(cotacao_id) REFERENCES res_cotacoes (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_oportunidades_reserva_id_res_reservas FOREIGN KEY(reserva_id) REFERENCES res_reservas (id) ON DELETE SET NULL
);

CREATE INDEX ix_crm_oportunidades_tenant_id ON crm_oportunidades (tenant_id);

CREATE INDEX ix_crm_oportunidades_tenant_estagio ON crm_oportunidades (tenant_id, estagio);

CREATE INDEX ix_crm_oportunidades_cliente_id ON crm_oportunidades (cliente_id);

CREATE INDEX ix_crm_oportunidades_cotacao_id ON crm_oportunidades (cotacao_id);

CREATE INDEX ix_crm_oportunidades_vendedor_id ON crm_oportunidades (vendedor_id);

CREATE UNIQUE INDEX uq_crm_oportunidades_tenant_numero_active ON crm_oportunidades (tenant_id, numero) WHERE deleted_at IS NULL;

CREATE TABLE crm_oportunidade_interacoes (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    oportunidade_id UUID NOT NULL, 
    tipo VARCHAR(12) DEFAULT 'nota' NOT NULL, 
    descricao TEXT NOT NULL, 
    ocorrido_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    user_id UUID, 
    CONSTRAINT pk_crm_oportunidade_interacoes PRIMARY KEY (id), 
    CONSTRAINT fk_crm_opp_inter_opp_id FOREIGN KEY(oportunidade_id) REFERENCES crm_oportunidades (id) ON DELETE CASCADE, 
    CONSTRAINT fk_crm_oportunidade_interacoes_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_crm_oportunidade_interacoes_tenant_id ON crm_oportunidade_interacoes (tenant_id);

CREATE INDEX ix_crm_oportunidade_interacoes_oportunidade_id ON crm_oportunidade_interacoes (oportunidade_id);

CREATE TABLE crm_campanhas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    codigo VARCHAR(20) NOT NULL, 
    nome VARCHAR(160) NOT NULL, 
    inicio_em DATE, 
    fim_em DATE, 
    status VARCHAR(12) DEFAULT 'rascunho' NOT NULL, 
    canal VARCHAR(12) DEFAULT 'email' NOT NULL, 
    publico_alvo VARCHAR(20) DEFAULT 'todos' NOT NULL, 
    categoria_cliente VARCHAR(60), 
    dias_inativo INTEGER DEFAULT '90' NOT NULL, 
    desconto_percentual NUMERIC(5, 2), 
    desconto_valor NUMERIC(14, 2), 
    cupom_id UUID, 
    enviados INTEGER DEFAULT '0' NOT NULL, 
    abertos INTEGER DEFAULT '0' NOT NULL, 
    convertidos INTEGER DEFAULT '0' NOT NULL, 
    mensagem_assunto VARCHAR(200), 
    mensagem_corpo TEXT, 
    CONSTRAINT pk_crm_campanhas PRIMARY KEY (id)
);

CREATE INDEX ix_crm_campanhas_tenant_id ON crm_campanhas (tenant_id);

CREATE INDEX ix_crm_campanhas_tenant_status ON crm_campanhas (tenant_id, status);

CREATE UNIQUE INDEX uq_crm_campanhas_tenant_codigo_active ON crm_campanhas (tenant_id, codigo) WHERE deleted_at IS NULL;

CREATE TABLE crm_cupons (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    codigo VARCHAR(40) NOT NULL, 
    tipo VARCHAR(12) DEFAULT 'percentual' NOT NULL, 
    valor NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    categoria_id UUID, 
    valor_minimo NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    primeira_locacao_apenas BOOLEAN DEFAULT 'false' NOT NULL, 
    inicio_em DATE, 
    fim_em DATE, 
    limite_uso_total INTEGER, 
    limite_uso_cliente INTEGER, 
    usos_totais INTEGER DEFAULT '0' NOT NULL, 
    status VARCHAR(12) DEFAULT 'ativo' NOT NULL, 
    campanha_id UUID, 
    parceiro_id UUID, 
    descricao VARCHAR(255), 
    CONSTRAINT pk_crm_cupons PRIMARY KEY (id), 
    CONSTRAINT fk_crm_cupons_categoria_id_frota_categorias FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_cupons_campanha_id_crm_campanhas FOREIGN KEY(campanha_id) REFERENCES crm_campanhas (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_cupons_parceiro_id_parceiros FOREIGN KEY(parceiro_id) REFERENCES parceiros (id) ON DELETE SET NULL
);

CREATE INDEX ix_crm_cupons_tenant_id ON crm_cupons (tenant_id);

CREATE INDEX ix_crm_cupons_tenant_status ON crm_cupons (tenant_id, status);

CREATE UNIQUE INDEX uq_crm_cupons_tenant_codigo_active ON crm_cupons (tenant_id, codigo) WHERE deleted_at IS NULL;

ALTER TABLE crm_campanhas ADD CONSTRAINT fk_crm_campanhas_cupom_id_crm_cupons FOREIGN KEY(cupom_id) REFERENCES crm_cupons (id) ON DELETE SET NULL;

CREATE TABLE crm_cupom_usos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    cupom_id UUID NOT NULL, 
    cliente_id UUID, 
    reserva_id UUID, 
    desconto_aplicado NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    usado_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_crm_cupom_usos PRIMARY KEY (id), 
    CONSTRAINT fk_crm_cupom_usos_cupom_id_crm_cupons FOREIGN KEY(cupom_id) REFERENCES crm_cupons (id) ON DELETE CASCADE, 
    CONSTRAINT fk_crm_cupom_usos_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_cupom_usos_reserva_id_res_reservas FOREIGN KEY(reserva_id) REFERENCES res_reservas (id) ON DELETE SET NULL
);

CREATE INDEX ix_crm_cupom_usos_tenant_id ON crm_cupom_usos (tenant_id);

CREATE INDEX ix_crm_cupom_usos_cupom_id ON crm_cupom_usos (cupom_id);

CREATE INDEX ix_crm_cupom_usos_cliente_id ON crm_cupom_usos (cliente_id);

CREATE TABLE crm_propostas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    versao INTEGER DEFAULT '1' NOT NULL, 
    proposta_pai_id UUID, 
    cliente_id UUID, 
    oportunidade_id UUID, 
    status VARCHAR(15) DEFAULT 'rascunho' NOT NULL, 
    validade_em DATE, 
    condicoes_comerciais TEXT, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    vendedor_id UUID, 
    campanha_id UUID, 
    cupom_id UUID, 
    reserva_id UUID, 
    filial_id UUID, 
    enviada_em TIMESTAMP WITH TIME ZONE, 
    visualizada_em TIMESTAMP WITH TIME ZONE, 
    aceita_em TIMESTAMP WITH TIME ZONE, 
    observacoes TEXT, 
    CONSTRAINT pk_crm_propostas PRIMARY KEY (id), 
    CONSTRAINT fk_crm_propostas_proposta_pai_id_crm_propostas FOREIGN KEY(proposta_pai_id) REFERENCES crm_propostas (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_propostas_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_propostas_oportunidade_id_crm_oportunidades FOREIGN KEY(oportunidade_id) REFERENCES crm_oportunidades (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_propostas_vendedor_id_vendedores FOREIGN KEY(vendedor_id) REFERENCES vendedores (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_propostas_campanha_id_crm_campanhas FOREIGN KEY(campanha_id) REFERENCES crm_campanhas (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_propostas_cupom_id_crm_cupons FOREIGN KEY(cupom_id) REFERENCES crm_cupons (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_propostas_reserva_id_res_reservas FOREIGN KEY(reserva_id) REFERENCES res_reservas (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_propostas_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL
);

CREATE INDEX ix_crm_propostas_tenant_id ON crm_propostas (tenant_id);

CREATE INDEX ix_crm_propostas_tenant_status ON crm_propostas (tenant_id, status);

CREATE INDEX ix_crm_propostas_cliente_id ON crm_propostas (cliente_id);

CREATE UNIQUE INDEX uq_crm_propostas_tenant_numero_versao_active ON crm_propostas (tenant_id, numero, versao) WHERE deleted_at IS NULL;

CREATE TABLE crm_proposta_itens (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    proposta_id UUID NOT NULL, 
    categoria_id UUID, 
    veiculo_id UUID, 
    descricao VARCHAR(255) NOT NULL, 
    quantidade NUMERIC(10, 2) DEFAULT '1' NOT NULL, 
    periodo_inicio DATE, 
    periodo_fim DATE, 
    dias INTEGER DEFAULT '1' NOT NULL, 
    valor_unitario NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    CONSTRAINT pk_crm_proposta_itens PRIMARY KEY (id), 
    CONSTRAINT fk_crm_proposta_itens_proposta_id_crm_propostas FOREIGN KEY(proposta_id) REFERENCES crm_propostas (id) ON DELETE CASCADE, 
    CONSTRAINT fk_crm_proposta_itens_categoria_id_frota_categorias FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE SET NULL, 
    CONSTRAINT fk_crm_proposta_itens_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE SET NULL
);

CREATE INDEX ix_crm_proposta_itens_tenant_id ON crm_proposta_itens (tenant_id);

CREATE INDEX ix_crm_proposta_itens_proposta_id ON crm_proposta_itens (proposta_id);

CREATE TABLE crm_fidelidade_regras (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(120) DEFAULT 'Programa de Fidelidade' NOT NULL, 
    pontos_por_real NUMERIC(10, 4) DEFAULT '1' NOT NULL, 
    pontos_por_diaria NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    valor_por_ponto NUMERIC(10, 4) DEFAULT '0.10' NOT NULL, 
    validade_meses INTEGER DEFAULT '12' NOT NULL, 
    ativo BOOLEAN DEFAULT 'true' NOT NULL, 
    CONSTRAINT pk_crm_fidelidade_regras PRIMARY KEY (id)
);

CREATE INDEX ix_crm_fidelidade_regras_tenant_id ON crm_fidelidade_regras (tenant_id);

CREATE INDEX ix_crm_fidelidade_regras_tenant_ativo ON crm_fidelidade_regras (tenant_id, ativo);

CREATE TABLE crm_fidelidade_tiers (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(60) NOT NULL, 
    pontos_minimos INTEGER DEFAULT '0' NOT NULL, 
    beneficio_descricao VARCHAR(255), 
    ordem INTEGER DEFAULT '0' NOT NULL, 
    CONSTRAINT pk_crm_fidelidade_tiers PRIMARY KEY (id)
);

CREATE INDEX ix_crm_fidelidade_tiers_tenant_id ON crm_fidelidade_tiers (tenant_id);

CREATE INDEX ix_crm_fidelidade_tiers_tenant_ordem ON crm_fidelidade_tiers (tenant_id, ordem);

CREATE TABLE crm_fidelidade_contas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    cliente_id UUID NOT NULL, 
    pontos_saldo INTEGER DEFAULT '0' NOT NULL, 
    pontos_historico_total INTEGER DEFAULT '0' NOT NULL, 
    tier_id UUID, 
    CONSTRAINT pk_crm_fidelidade_contas PRIMARY KEY (id), 
    CONSTRAINT fk_crm_fidelidade_contas_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE CASCADE, 
    CONSTRAINT fk_crm_fidelidade_contas_tier_id_crm_fidelidade_tiers FOREIGN KEY(tier_id) REFERENCES crm_fidelidade_tiers (id) ON DELETE SET NULL
);

CREATE INDEX ix_crm_fidelidade_contas_tenant_id ON crm_fidelidade_contas (tenant_id);

CREATE INDEX ix_crm_fidelidade_contas_cliente_id ON crm_fidelidade_contas (cliente_id);

CREATE UNIQUE INDEX uq_crm_fidelidade_contas_cliente_active ON crm_fidelidade_contas (tenant_id, cliente_id) WHERE deleted_at IS NULL;

CREATE TABLE crm_fidelidade_movimentos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    conta_id UUID NOT NULL, 
    tipo VARCHAR(12) NOT NULL, 
    pontos INTEGER DEFAULT '0' NOT NULL, 
    origem VARCHAR(12) DEFAULT 'ajuste' NOT NULL, 
    origem_id UUID, 
    descricao VARCHAR(255), 
    saldo_restante INTEGER DEFAULT '0' NOT NULL, 
    expira_em TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_crm_fidelidade_movimentos PRIMARY KEY (id), 
    CONSTRAINT fk_crm_fidelidade_movimentos_conta_id_crm_fidelidade_contas FOREIGN KEY(conta_id) REFERENCES crm_fidelidade_contas (id) ON DELETE CASCADE
);

CREATE INDEX ix_crm_fidelidade_movimentos_tenant_id ON crm_fidelidade_movimentos (tenant_id);

CREATE INDEX ix_crm_fidelidade_movimentos_conta_id ON crm_fidelidade_movimentos (conta_id);

CREATE INDEX ix_crm_fidelidade_movimentos_expira_em ON crm_fidelidade_movimentos (expira_em);

ALTER TABLE crm_oportunidades ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_oportunidades FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_oportunidades
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE crm_oportunidade_interacoes ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_oportunidade_interacoes FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_oportunidade_interacoes
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE crm_campanhas ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_campanhas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_campanhas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE crm_cupons ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_cupons FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_cupons
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE crm_cupom_usos ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_cupom_usos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_cupom_usos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE crm_propostas ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_propostas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_propostas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE crm_proposta_itens ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_proposta_itens FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_proposta_itens
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE crm_fidelidade_regras ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_fidelidade_regras FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_fidelidade_regras
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE crm_fidelidade_tiers ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_fidelidade_tiers FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_fidelidade_tiers
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE crm_fidelidade_contas ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_fidelidade_contas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_fidelidade_contas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE crm_fidelidade_movimentos ENABLE ROW LEVEL SECURITY;

ALTER TABLE crm_fidelidade_movimentos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON crm_fidelidade_movimentos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0011_crm' WHERE alembic_version.version_num = '0010_financeiro';

INSERT INTO alembic_version (version_num) VALUES ('0011_crm') ON CONFLICT (version_num) DO NOTHING;
