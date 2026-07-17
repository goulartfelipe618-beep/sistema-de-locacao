CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE tenants (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    slug VARCHAR(63) NOT NULL, 
    legal_name VARCHAR(200) NOT NULL, 
    trade_name VARCHAR(200), 
    cnpj VARCHAR(14), 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    plan VARCHAR(50) DEFAULT 'standard' NOT NULL, 
    email VARCHAR(255), 
    phone VARCHAR(20), 
    CONSTRAINT pk_tenants PRIMARY KEY (id), 
    CONSTRAINT uq_tenants_slug UNIQUE (slug), 
    CONSTRAINT uq_tenants_cnpj UNIQUE (cnpj)
);

CREATE TABLE filiais (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    code VARCHAR(20) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    cnpj VARCHAR(14), 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    is_headquarters BOOLEAN DEFAULT false NOT NULL, 
    zip_code VARCHAR(8), 
    address VARCHAR(255), 
    number VARCHAR(20), 
    complement VARCHAR(100), 
    district VARCHAR(100), 
    city VARCHAR(100), 
    state VARCHAR(2), 
    phone VARCHAR(20), 
    CONSTRAINT pk_filiais PRIMARY KEY (id), 
    CONSTRAINT fk_filiais_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT uq_filiais_tenant_id_code UNIQUE (tenant_id, code)
);

CREATE INDEX ix_filiais_tenant_id ON filiais (tenant_id);

CREATE TABLE permissions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    code VARCHAR(150) NOT NULL, 
    module VARCHAR(60) NOT NULL, 
    resource VARCHAR(60) NOT NULL, 
    action VARCHAR(40) NOT NULL, 
    description VARCHAR(255) NOT NULL, 
    CONSTRAINT pk_permissions PRIMARY KEY (id), 
    CONSTRAINT uq_permissions_code UNIQUE (code)
);

CREATE INDEX ix_permissions_module ON permissions (module);

CREATE TABLE roles (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    slug VARCHAR(60) NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    description VARCHAR(255), 
    is_system BOOLEAN DEFAULT false NOT NULL, 
    CONSTRAINT pk_roles PRIMARY KEY (id), 
    CONSTRAINT fk_roles_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT uq_roles_tenant_id_slug UNIQUE (tenant_id, slug)
);

CREATE INDEX ix_roles_tenant_id ON roles (tenant_id);

CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    full_name VARCHAR(200) NOT NULL, 
    hashed_password VARCHAR(255) NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    is_superuser BOOLEAN DEFAULT false NOT NULL, 
    last_login_at TIMESTAMP WITH TIME ZONE, 
    failed_login_attempts INTEGER DEFAULT '0' NOT NULL, 
    locked_until TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_users PRIMARY KEY (id), 
    CONSTRAINT fk_users_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT uq_users_tenant_id_email UNIQUE (tenant_id, email)
);

CREATE INDEX ix_users_tenant_id ON users (tenant_id);

CREATE INDEX ix_users_email ON users (email);

CREATE TABLE role_permissions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    role_id UUID NOT NULL, 
    permission_id UUID NOT NULL, 
    CONSTRAINT pk_role_permissions PRIMARY KEY (id), 
    CONSTRAINT fk_role_permissions_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT fk_role_permissions_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
    CONSTRAINT fk_role_permissions_permission_id_permissions FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE, 
    CONSTRAINT uq_role_permissions_role_perm UNIQUE (role_id, permission_id)
);

CREATE INDEX ix_role_permissions_tenant_id ON role_permissions (tenant_id);

CREATE INDEX ix_role_permissions_role_id ON role_permissions (role_id);

CREATE INDEX ix_role_permissions_permission_id ON role_permissions (permission_id);

CREATE TABLE user_roles (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    role_id UUID NOT NULL, 
    CONSTRAINT pk_user_roles PRIMARY KEY (id), 
    CONSTRAINT fk_user_roles_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
    CONSTRAINT uq_user_roles_user_role UNIQUE (user_id, role_id)
);

CREATE INDEX ix_user_roles_tenant_id ON user_roles (tenant_id);

CREATE INDEX ix_user_roles_user_id ON user_roles (user_id);

CREATE INDEX ix_user_roles_role_id ON user_roles (role_id);

CREATE TABLE user_filiais (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    tenant_id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    filial_id UUID NOT NULL, 
    CONSTRAINT pk_user_filiais PRIMARY KEY (id), 
    CONSTRAINT fk_user_filiais_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_filiais_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_filiais_filial_id_filiais FOREIGN KEY(filial_id) REFERENCES filiais (id) ON DELETE CASCADE, 
    CONSTRAINT uq_user_filiais_user_filial UNIQUE (user_id, filial_id)
);

CREATE INDEX ix_user_filiais_tenant_id ON user_filiais (tenant_id);

CREATE INDEX ix_user_filiais_user_id ON user_filiais (user_id);

CREATE INDEX ix_user_filiais_filial_id ON user_filiais (filial_id);

CREATE TABLE audit_logs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID, 
    user_id UUID, 
    action VARCHAR(50) NOT NULL, 
    entity VARCHAR(100), 
    entity_id UUID, 
    description VARCHAR(500), 
    changes JSONB, 
    ip_address VARCHAR(64), 
    user_agent VARCHAR(400), 
    correlation_id VARCHAR(64), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_audit_logs PRIMARY KEY (id)
);

CREATE INDEX ix_audit_logs_tenant_id ON audit_logs (tenant_id);

CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_entity ON audit_logs (entity);

CREATE INDEX ix_audit_logs_correlation_id ON audit_logs (correlation_id);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

ALTER TABLE filiais ENABLE ROW LEVEL SECURITY;

ALTER TABLE filiais FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON filiais
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE roles ENABLE ROW LEVEL SECURITY;

ALTER TABLE roles FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON roles
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

ALTER TABLE users FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON users
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;

ALTER TABLE role_permissions FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON role_permissions
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

ALTER TABLE user_roles FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON user_roles
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

ALTER TABLE user_filiais ENABLE ROW LEVEL SECURITY;

ALTER TABLE user_filiais FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON user_filiais
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

INSERT INTO alembic_version (version_num) VALUES ('0001_foundation') RETURNING alembic_version.version_num;
