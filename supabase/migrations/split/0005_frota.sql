CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE frota_categorias (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    descricao TEXT, 
    capacidade_passageiros INTEGER DEFAULT '5' NOT NULL, 
    capacidade_porta_malas VARCHAR(60), 
    transmissao_tipica VARCHAR(40), 
    imagem_url VARCHAR(500), 
    ordem INTEGER DEFAULT '0' NOT NULL, 
    grupo_tarifario VARCHAR(60), 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    CONSTRAINT pk_frota_categorias PRIMARY KEY (id)
);

CREATE INDEX ix_frota_categorias_tenant_id ON frota_categorias (tenant_id);

CREATE INDEX ix_frota_categorias_tenant_nome ON frota_categorias (tenant_id, nome);

CREATE INDEX ix_frota_categorias_tenant_ordem ON frota_categorias (tenant_id, ordem);

CREATE TABLE frota_marcas (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    logo_url VARCHAR(500), 
    pais_origem VARCHAR(60), 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    CONSTRAINT pk_frota_marcas PRIMARY KEY (id)
);

CREATE INDEX ix_frota_marcas_tenant_id ON frota_marcas (tenant_id);

CREATE INDEX ix_frota_marcas_tenant_nome ON frota_marcas (tenant_id, nome);

CREATE TABLE frota_combustiveis (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(100) NOT NULL, 
    unidade VARCHAR(10) DEFAULT 'litro' NOT NULL, 
    preco_referencia NUMERIC(14, 4) DEFAULT '0' NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    CONSTRAINT pk_frota_combustiveis PRIMARY KEY (id)
);

CREATE INDEX ix_frota_combustiveis_tenant_id ON frota_combustiveis (tenant_id);

CREATE INDEX ix_frota_combustiveis_tenant_nome ON frota_combustiveis (tenant_id, nome);

CREATE TABLE frota_modelos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    marca_id UUID NOT NULL, 
    categoria_padrao_id UUID, 
    nome VARCHAR(200) NOT NULL, 
    versao VARCHAR(100), 
    motorizacao VARCHAR(100), 
    cambio VARCHAR(40), 
    portas INTEGER, 
    capacidade_tanque NUMERIC(8, 2), 
    consumo_medio_km_l NUMERIC(6, 2), 
    codigo_fipe VARCHAR(20), 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    CONSTRAINT pk_frota_modelos PRIMARY KEY (id), 
    CONSTRAINT fk_frota_modelos_marca_id_frota_marcas FOREIGN KEY(marca_id) REFERENCES frota_marcas (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_frota_modelos_categoria_padrao_id_frota_categorias FOREIGN KEY(categoria_padrao_id) REFERENCES frota_categorias (id) ON DELETE SET NULL
);

CREATE INDEX ix_frota_modelos_tenant_id ON frota_modelos (tenant_id);

CREATE INDEX ix_frota_modelos_marca_id ON frota_modelos (marca_id);

CREATE INDEX ix_frota_modelos_categoria_padrao_id ON frota_modelos (categoria_padrao_id);

CREATE INDEX ix_frota_modelos_tenant_nome ON frota_modelos (tenant_id, nome);

CREATE TABLE frota_acessorios (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    nome VARCHAR(200) NOT NULL, 
    descricao TEXT, 
    tipo VARCHAR(10) DEFAULT 'fixo' NOT NULL, 
    valor_diaria NUMERIC(14, 2) DEFAULT '0' NOT NULL, 
    estoque_disponivel INTEGER DEFAULT '0' NOT NULL, 
    foto_url VARCHAR(500), 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    CONSTRAINT pk_frota_acessorios PRIMARY KEY (id)
);

CREATE INDEX ix_frota_acessorios_tenant_id ON frota_acessorios (tenant_id);

CREATE INDEX ix_frota_acessorios_tenant_nome ON frota_acessorios (tenant_id, nome);

CREATE TABLE frota_veiculos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    placa VARCHAR(10) NOT NULL, 
    renavam VARCHAR(11), 
    chassi VARCHAR(17), 
    ano_fabricacao INTEGER NOT NULL, 
    ano_modelo INTEGER NOT NULL, 
    cor VARCHAR(40), 
    categoria_id UUID NOT NULL, 
    marca_id UUID NOT NULL, 
    modelo_id UUID NOT NULL, 
    combustivel_id UUID NOT NULL, 
    filial_id UUID, 
    fornecedor_id UUID, 
    status VARCHAR(20) DEFAULT 'disponivel' NOT NULL, 
    propriedade VARCHAR(20) DEFAULT 'propria' NOT NULL, 
    data_compra DATE, 
    valor_aquisicao NUMERIC(14, 2), 
    km_inicial INTEGER, 
    km_atual INTEGER, 
    valor_fipe NUMERIC(14, 2), 
    valor_mercado NUMERIC(14, 2), 
    proprietario_nome VARCHAR(200), 
    observacoes TEXT, 
    motivo_bloqueio VARCHAR(255), 
    data_baixa DATE, 
    motivo_baixa VARCHAR(255), 
    nivel_combustivel_atual INTEGER DEFAULT '8' NOT NULL, 
    CONSTRAINT pk_frota_veiculos PRIMARY KEY (id), 
    CONSTRAINT ck_frota_veiculos_ck_frota_veiculos_nivel_combustivel CHECK (nivel_combustivel_atual >= 0 AND nivel_combustivel_atual <= 8), 
    CONSTRAINT fk_frota_veiculos_categoria_id_frota_categorias FOREIGN KEY(categoria_id) REFERENCES frota_categorias (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_frota_veiculos_marca_id_frota_marcas FOREIGN KEY(marca_id) REFERENCES frota_marcas (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_frota_veiculos_modelo_id_frota_modelos FOREIGN KEY(modelo_id) REFERENCES frota_modelos (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_frota_veiculos_combustivel_id_frota_combustiveis FOREIGN KEY(combustivel_id) REFERENCES frota_combustiveis (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_frota_veiculos_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE SET NULL, 
    CONSTRAINT fk_frota_veiculos_fornecedor_id_fornecedores FOREIGN KEY(fornecedor_id) REFERENCES fornecedores (id) ON DELETE SET NULL
);

CREATE INDEX ix_frota_veiculos_tenant_id ON frota_veiculos (tenant_id);

CREATE INDEX ix_frota_veiculos_categoria_id ON frota_veiculos (categoria_id);

CREATE INDEX ix_frota_veiculos_marca_id ON frota_veiculos (marca_id);

CREATE INDEX ix_frota_veiculos_modelo_id ON frota_veiculos (modelo_id);

CREATE INDEX ix_frota_veiculos_combustivel_id ON frota_veiculos (combustivel_id);

CREATE INDEX ix_frota_veiculos_filial_id ON frota_veiculos (filial_id);

CREATE INDEX ix_frota_veiculos_fornecedor_id ON frota_veiculos (fornecedor_id);

CREATE INDEX ix_frota_veiculos_tenant_status ON frota_veiculos (tenant_id, status);

CREATE INDEX ix_frota_veiculos_tenant_filial ON frota_veiculos (tenant_id, filial_id);

CREATE UNIQUE INDEX uq_frota_veiculos_tenant_placa_active ON frota_veiculos (tenant_id, placa) WHERE deleted_at IS NULL AND placa IS NOT NULL;

CREATE UNIQUE INDEX uq_frota_veiculos_tenant_renavam_active ON frota_veiculos (tenant_id, renavam) WHERE deleted_at IS NULL AND renavam IS NOT NULL;

CREATE UNIQUE INDEX uq_frota_veiculos_tenant_chassi_active ON frota_veiculos (tenant_id, chassi) WHERE deleted_at IS NULL AND chassi IS NOT NULL;

CREATE TABLE frota_veiculo_acessorios (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    veiculo_id UUID NOT NULL, 
    acessorio_id UUID NOT NULL, 
    data_instalacao DATE, 
    observacoes TEXT, 
    CONSTRAINT pk_frota_veiculo_acessorios PRIMARY KEY (id), 
    CONSTRAINT fk_frota_veiculo_acessorios_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE CASCADE, 
    CONSTRAINT fk_frota_veiculo_acessorios_acessorio_id_frota_acessorios FOREIGN KEY(acessorio_id) REFERENCES frota_acessorios (id) ON DELETE RESTRICT
);

CREATE INDEX ix_frota_veiculo_acessorios_tenant_id ON frota_veiculo_acessorios (tenant_id);

CREATE INDEX ix_frota_veiculo_acessorios_veiculo_id ON frota_veiculo_acessorios (veiculo_id);

CREATE INDEX ix_frota_veiculo_acessorios_acessorio_id ON frota_veiculo_acessorios (acessorio_id);

CREATE UNIQUE INDEX uq_frota_veiculo_acessorios_active ON frota_veiculo_acessorios (tenant_id, veiculo_id, acessorio_id) WHERE deleted_at IS NULL;

CREATE TABLE frota_veiculo_fotos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    veiculo_id UUID NOT NULL, 
    storage_key VARCHAR(500) NOT NULL, 
    legenda VARCHAR(255), 
    tirada_em DATE, 
    ordem INTEGER DEFAULT '0' NOT NULL, 
    CONSTRAINT pk_frota_veiculo_fotos PRIMARY KEY (id), 
    CONSTRAINT fk_frota_veiculo_fotos_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE CASCADE
);

CREATE INDEX ix_frota_veiculo_fotos_tenant_id ON frota_veiculo_fotos (tenant_id);

CREATE INDEX ix_frota_veiculo_fotos_veiculo_id ON frota_veiculo_fotos (veiculo_id);

CREATE INDEX ix_frota_veiculo_fotos_veiculo_ordem ON frota_veiculo_fotos (veiculo_id, ordem);

CREATE TABLE frota_documentos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    veiculo_id UUID NOT NULL, 
    tipo VARCHAR(30) NOT NULL, 
    numero VARCHAR(60), 
    orgao_emissor VARCHAR(60), 
    data_emissao DATE, 
    data_validade DATE, 
    arquivo_key VARCHAR(500), 
    status VARCHAR(20) DEFAULT 'regular' NOT NULL, 
    versao INTEGER DEFAULT '1' NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_frota_documentos PRIMARY KEY (id), 
    CONSTRAINT fk_frota_documentos_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE CASCADE
);

CREATE INDEX ix_frota_documentos_tenant_id ON frota_documentos (tenant_id);

CREATE INDEX ix_frota_documentos_veiculo_id ON frota_documentos (veiculo_id);

CREATE INDEX ix_frota_documentos_veiculo_tipo ON frota_documentos (veiculo_id, tipo);

CREATE INDEX ix_frota_documentos_validade ON frota_documentos (data_validade);

CREATE TABLE frota_telemetria_dispositivos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    veiculo_id UUID NOT NULL, 
    provedor VARCHAR(100) NOT NULL, 
    equipamento_id VARCHAR(100) NOT NULL, 
    conn_status VARCHAR(20) DEFAULT 'offline' NOT NULL, 
    lat NUMERIC(10, 7), 
    lng NUMERIC(10, 7), 
    ultima_posicao_em TIMESTAMP WITH TIME ZONE, 
    km_telemetria INTEGER, 
    bloqueio_remoto BOOLEAN DEFAULT false NOT NULL, 
    observacoes TEXT, 
    CONSTRAINT pk_frota_telemetria_dispositivos PRIMARY KEY (id), 
    CONSTRAINT fk_frota_telemetria_dispositivos_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE CASCADE
);

CREATE INDEX ix_frota_telemetria_dispositivos_tenant_id ON frota_telemetria_dispositivos (tenant_id);

CREATE INDEX ix_frota_telemetria_dispositivos_veiculo_id ON frota_telemetria_dispositivos (veiculo_id);

CREATE UNIQUE INDEX uq_frota_telemetria_dispositivos_veiculo_active ON frota_telemetria_dispositivos (tenant_id, veiculo_id) WHERE deleted_at IS NULL;

CREATE TABLE frota_telemetria_eventos (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    dispositivo_id UUID NOT NULL, 
    veiculo_id UUID NOT NULL, 
    tipo VARCHAR(30) NOT NULL, 
    descricao TEXT, 
    lat NUMERIC(10, 7), 
    lng NUMERIC(10, 7), 
    velocidade NUMERIC(6, 2), 
    ocorrido_em TIMESTAMP WITH TIME ZONE NOT NULL, 
    payload_json TEXT, 
    CONSTRAINT pk_frota_telemetria_eventos PRIMARY KEY (id), 
    CONSTRAINT fk_frota_tel_evt_dispositivo_id FOREIGN KEY(dispositivo_id) REFERENCES frota_telemetria_dispositivos (id) ON DELETE CASCADE, 
    CONSTRAINT fk_frota_telemetria_eventos_veiculo_id_frota_veiculos FOREIGN KEY(veiculo_id) REFERENCES frota_veiculos (id) ON DELETE CASCADE
);

CREATE INDEX ix_frota_telemetria_eventos_tenant_id ON frota_telemetria_eventos (tenant_id);

CREATE INDEX ix_frota_telemetria_eventos_dispositivo_id ON frota_telemetria_eventos (dispositivo_id);

CREATE INDEX ix_frota_telemetria_eventos_veiculo_id ON frota_telemetria_eventos (veiculo_id);

CREATE INDEX ix_frota_telemetria_eventos_veiculo_ocorrido ON frota_telemetria_eventos (veiculo_id, ocorrido_em);

ALTER TABLE frota_categorias ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_categorias FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_categorias
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_marcas ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_marcas FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_marcas
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_combustiveis ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_combustiveis FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_combustiveis
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_modelos ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_modelos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_modelos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_acessorios ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_acessorios FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_acessorios
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_veiculos ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_veiculos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_veiculos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_veiculo_acessorios ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_veiculo_acessorios FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_veiculo_acessorios
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_veiculo_fotos ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_veiculo_fotos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_veiculo_fotos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_documentos ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_documentos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_documentos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_telemetria_dispositivos ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_telemetria_dispositivos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_telemetria_dispositivos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE frota_telemetria_eventos ENABLE ROW LEVEL SECURITY;

ALTER TABLE frota_telemetria_eventos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON frota_telemetria_eventos
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

UPDATE alembic_version SET version_num='0005_frota' WHERE alembic_version.version_num = '0004_cadastros_completos';

INSERT INTO alembic_version (version_num) VALUES ('0005_frota') ON CONFLICT (version_num) DO NOTHING;
