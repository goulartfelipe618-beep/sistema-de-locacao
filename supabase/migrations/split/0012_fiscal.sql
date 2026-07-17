CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE fis_imposto_configs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    filial_id UUID, 
    regime VARCHAR(20) DEFAULT 'simples_nacional' NOT NULL, 
    vigencia_inicio DATE NOT NULL, 
    vigencia_fim DATE, 
    nfse_automatica BOOLEAN DEFAULT 'false' NOT NULL, 
    ativo BOOLEAN DEFAULT 'true' NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_fis_imposto_configs PRIMARY KEY (id), 
    CONSTRAINT fk_fis_imposto_configs_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL
);

CREATE INDEX ix_fis_imposto_configs_tenant_id ON fis_imposto_configs (tenant_id);

CREATE INDEX ix_fis_imposto_configs_tenant_ativo ON fis_imposto_configs (tenant_id, ativo);

CREATE INDEX ix_fis_imposto_configs_filial_id ON fis_imposto_configs (filial_id);

CREATE TABLE fis_aliquotas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    config_id UUID NOT NULL, 
    tipo VARCHAR(10) NOT NULL, 
    servico_produto_codigo VARCHAR(40), 
    descricao VARCHAR(200), 
    aliquota_percentual NUMERIC(7, 4) DEFAULT '0' NOT NULL, 
    retencao BOOLEAN DEFAULT 'false' NOT NULL, 
    vigencia_inicio DATE NOT NULL, 
    vigencia_fim DATE, 
    CONSTRAINT pk_fis_aliquotas PRIMARY KEY (id), 
    CONSTRAINT fk_fis_aliquotas_config_id_fis_imposto_configs FOREIGN KEY(config_id) REFERENCES fis_imposto_configs (id) ON DELETE CASCADE
);

CREATE INDEX ix_fis_aliquotas_tenant_id ON fis_aliquotas (tenant_id);

CREATE INDEX ix_fis_aliquotas_config_id ON fis_aliquotas (config_id);

CREATE INDEX ix_fis_aliquotas_tenant_tipo ON fis_aliquotas (tenant_id, tipo);

CREATE TABLE fis_xml_arquivos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    tipo VARCHAR(15) DEFAULT 'outro' NOT NULL, 
    direcao VARCHAR(10) DEFAULT 'emitido' NOT NULL, 
    chave_acesso VARCHAR(60), 
    hash_sha256 VARCHAR(64) NOT NULL, 
    conteudo_xml TEXT NOT NULL, 
    documento_tipo VARCHAR(10), 
    documento_id UUID, 
    filial_id UUID, 
    periodo_ref DATE, 
    filename VARCHAR(200) NOT NULL, 
    tamanho_bytes INTEGER DEFAULT '0' NOT NULL, 
    fornecedor_cnpj VARCHAR(20), 
    titulo_pagar_id UUID, 
    CONSTRAINT pk_fis_xml_arquivos PRIMARY KEY (id), 
    CONSTRAINT fk_fis_xml_arquivos_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL, 
    CONSTRAINT fk_fis_xml_arquivos_titulo_pagar_id_fin_contas_pagar FOREIGN KEY(titulo_pagar_id) REFERENCES fin_contas_pagar (id) ON DELETE SET NULL
);

CREATE INDEX ix_fis_xml_arquivos_tenant_id ON fis_xml_arquivos (tenant_id);

CREATE INDEX ix_fis_xml_arquivos_tenant_tipo ON fis_xml_arquivos (tenant_id, tipo);

CREATE INDEX ix_fis_xml_arquivos_chave_acesso ON fis_xml_arquivos (chave_acesso);

CREATE INDEX ix_fis_xml_arquivos_periodo_ref ON fis_xml_arquivos (periodo_ref);

CREATE INDEX ix_fis_xml_arquivos_filial_id ON fis_xml_arquivos (filial_id);

CREATE UNIQUE INDEX uq_fis_xml_arquivos_tenant_hash_active ON fis_xml_arquivos (tenant_id, hash_sha256) WHERE deleted_at IS NULL;

CREATE TABLE fis_nfse (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    serie VARCHAR(10) DEFAULT 'A' NOT NULL, 
    status VARCHAR(20) DEFAULT 'a_emitir' NOT NULL, 
    contrato_id UUID, 
    fatura_id UUID, 
    cliente_id UUID, 
    filial_id UUID NOT NULL, 
    municipio_ibge VARCHAR(10), 
    municipio_nome VARCHAR(120), 
    valor_servico NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    aliquota_iss NUMERIC(7, 4) DEFAULT '0' NOT NULL, 
    valor_iss NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_iss_retido NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    retencao_iss BOOLEAN DEFAULT 'false' NOT NULL, 
    discriminacao TEXT, 
    chave_acesso VARCHAR(60), 
    protocolo VARCHAR(60), 
    pdf_url VARCHAR(500), 
    xml_arquivo_id UUID, 
    emitida_em TIMESTAMP WITH TIME ZONE, 
    autorizada_em TIMESTAMP WITH TIME ZONE, 
    rejeicao_motivo VARCHAR(255), 
    provedor VARCHAR(60) DEFAULT 'simulador' NOT NULL, 
    automatica BOOLEAN DEFAULT 'false' NOT NULL, 
    CONSTRAINT pk_fis_nfse PRIMARY KEY (id), 
    CONSTRAINT fk_fis_nfse_contrato_id_loc_contratos FOREIGN KEY(contrato_id) REFERENCES loc_contratos (id) ON DELETE SET NULL, 
    CONSTRAINT fk_fis_nfse_fatura_id_fin_faturas FOREIGN KEY(fatura_id) REFERENCES fin_faturas (id) ON DELETE SET NULL, 
    CONSTRAINT fk_fis_nfse_cliente_id_clientes FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE SET NULL, 
    CONSTRAINT fk_fis_nfse_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_fis_nfse_xml_arquivo_id_fis_xml_arquivos FOREIGN KEY(xml_arquivo_id) REFERENCES fis_xml_arquivos (id) ON DELETE SET NULL
);

CREATE INDEX ix_fis_nfse_tenant_id ON fis_nfse (tenant_id);

CREATE INDEX ix_fis_nfse_tenant_status ON fis_nfse (tenant_id, status);

CREATE INDEX ix_fis_nfse_contrato_id ON fis_nfse (contrato_id);

CREATE INDEX ix_fis_nfse_fatura_id ON fis_nfse (fatura_id);

CREATE INDEX ix_fis_nfse_cliente_id ON fis_nfse (cliente_id);

CREATE INDEX ix_fis_nfse_filial_id ON fis_nfse (filial_id);

CREATE UNIQUE INDEX uq_fis_nfse_tenant_serie_numero_active ON fis_nfse (tenant_id, serie, numero) WHERE deleted_at IS NULL;

CREATE TABLE fis_nfe (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    serie VARCHAR(10) DEFAULT '1' NOT NULL, 
    status VARCHAR(20) DEFAULT 'a_emitir' NOT NULL, 
    operacao VARCHAR(15) DEFAULT 'venda' NOT NULL, 
    destinatario_nome VARCHAR(160) NOT NULL, 
    destinatario_doc VARCHAR(20), 
    destinatario_id UUID, 
    filial_id UUID NOT NULL, 
    veiculo_id UUID, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    natureza_operacao VARCHAR(120), 
    cfop_padrao VARCHAR(10), 
    chave_acesso VARCHAR(60), 
    protocolo VARCHAR(60), 
    pdf_url VARCHAR(500), 
    xml_arquivo_id UUID, 
    emitida_em TIMESTAMP WITH TIME ZONE, 
    autorizada_em TIMESTAMP WITH TIME ZONE, 
    rejeicao_motivo VARCHAR(255), 
    provedor VARCHAR(60) DEFAULT 'simulador' NOT NULL, 
    CONSTRAINT pk_fis_nfe PRIMARY KEY (id), 
    CONSTRAINT fk_fis_nfe_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_fis_nfe_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE SET NULL, 
    CONSTRAINT fk_fis_nfe_xml_arquivo_id_fis_xml_arquivos FOREIGN KEY(xml_arquivo_id) REFERENCES fis_xml_arquivos (id) ON DELETE SET NULL
);

CREATE INDEX ix_fis_nfe_tenant_id ON fis_nfe (tenant_id);

CREATE INDEX ix_fis_nfe_tenant_status ON fis_nfe (tenant_id, status);

CREATE INDEX ix_fis_nfe_filial_id ON fis_nfe (filial_id);

CREATE INDEX ix_fis_nfe_veiculo_id ON fis_nfe (veiculo_id);

CREATE UNIQUE INDEX uq_fis_nfe_tenant_serie_numero_active ON fis_nfe (tenant_id, serie, numero) WHERE deleted_at IS NULL;

CREATE TABLE fis_nfe_itens (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nfe_id UUID NOT NULL, 
    descricao VARCHAR(255) NOT NULL, 
    codigo VARCHAR(40), 
    ncm VARCHAR(10), 
    cfop VARCHAR(10), 
    quantidade NUMERIC(12, 3) DEFAULT '1' NOT NULL, 
    valor_unitario NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    valor_total NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    icms_aliquota NUMERIC(7, 4) DEFAULT '0' NOT NULL, 
    icms_valor NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    ipi_aliquota NUMERIC(7, 4) DEFAULT '0' NOT NULL, 
    ipi_valor NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    produto_ref_tipo VARCHAR(20), 
    produto_ref_id UUID, 
    CONSTRAINT pk_fis_nfe_itens PRIMARY KEY (id), 
    CONSTRAINT fk_fis_nfe_itens_nfe_id_fis_nfe FOREIGN KEY(nfe_id) REFERENCES fis_nfe (id) ON DELETE CASCADE
);

CREATE INDEX ix_fis_nfe_itens_tenant_id ON fis_nfe_itens (tenant_id);

CREATE INDEX ix_fis_nfe_itens_nfe_id ON fis_nfe_itens (nfe_id);

CREATE TABLE fis_cancelamentos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    numero VARCHAR(20) NOT NULL, 
    documento_tipo VARCHAR(10) NOT NULL, 
    documento_id UUID NOT NULL, 
    tipo_evento VARCHAR(15) DEFAULT 'cancelamento' NOT NULL, 
    motivo VARCHAR(255) NOT NULL, 
    justificativa_completa TEXT, 
    solicitado_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    processado_em TIMESTAMP WITH TIME ZONE, 
    protocolo_retorno VARCHAR(60), 
    status VARCHAR(12) DEFAULT 'solicitado' NOT NULL, 
    fora_do_prazo BOOLEAN DEFAULT 'false' NOT NULL, 
    user_id UUID, 
    CONSTRAINT pk_fis_cancelamentos PRIMARY KEY (id), 
    CONSTRAINT fk_fis_cancelamentos_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_fis_cancelamentos_tenant_id ON fis_cancelamentos (tenant_id);

CREATE INDEX ix_fis_cancelamentos_tenant_status ON fis_cancelamentos (tenant_id, status);

CREATE INDEX ix_fis_cancelamentos_documento ON fis_cancelamentos (documento_tipo, documento_id);

CREATE INDEX ix_fis_cancelamentos_user_id ON fis_cancelamentos (user_id);

CREATE UNIQUE INDEX uq_fis_cancelamentos_tenant_numero_active ON fis_cancelamentos (tenant_id, numero) WHERE deleted_at IS NULL;

CREATE TABLE fis_prazos_cancelamento (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    tipo_documento VARCHAR(10) NOT NULL, 
    uf VARCHAR(2), 
    municipio_ibge VARCHAR(10), 
    horas_limite INTEGER DEFAULT '24' NOT NULL, 
    ativo BOOLEAN DEFAULT 'true' NOT NULL, 
    descricao VARCHAR(200), 
    CONSTRAINT pk_fis_prazos_cancelamento PRIMARY KEY (id)
);

CREATE INDEX ix_fis_prazos_cancelamento_tenant_id ON fis_prazos_cancelamento (tenant_id);

CREATE INDEX ix_fis_prazos_cancelamento_tenant_tipo ON fis_prazos_cancelamento (tenant_id, tipo_documento);

CREATE INDEX ix_fis_prazos_cancelamento_ativo ON fis_prazos_cancelamento (tenant_id, ativo);

ALTER TABLE fis_imposto_configs ENABLE ROW LEVEL SECURITY;

ALTER TABLE fis_imposto_configs FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fis_imposto_configs
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fis_aliquotas ENABLE ROW LEVEL SECURITY;

ALTER TABLE fis_aliquotas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fis_aliquotas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fis_xml_arquivos ENABLE ROW LEVEL SECURITY;

ALTER TABLE fis_xml_arquivos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fis_xml_arquivos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fis_nfse ENABLE ROW LEVEL SECURITY;

ALTER TABLE fis_nfse FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fis_nfse
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fis_nfe ENABLE ROW LEVEL SECURITY;

ALTER TABLE fis_nfe FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fis_nfe
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fis_nfe_itens ENABLE ROW LEVEL SECURITY;

ALTER TABLE fis_nfe_itens FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fis_nfe_itens
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fis_cancelamentos ENABLE ROW LEVEL SECURITY;

ALTER TABLE fis_cancelamentos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fis_cancelamentos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE fis_prazos_cancelamento ENABLE ROW LEVEL SECURITY;

ALTER TABLE fis_prazos_cancelamento FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON fis_prazos_cancelamento
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0012_fiscal' WHERE alembic_version.version_num = '0011_crm';

INSERT INTO alembic_version (version_num) VALUES ('0012_fiscal') ON CONFLICT (version_num) DO NOTHING;
