CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE role_permissions DROP COLUMN deleted_at;

ALTER TABLE user_roles DROP COLUMN deleted_at;

ALTER TABLE user_filiais DROP COLUMN deleted_at;

ALTER TABLE users DROP CONSTRAINT uq_users_tenant_id_email;

CREATE UNIQUE INDEX uq_users_tenant_id_email_active
        ON users (tenant_id, email)
        WHERE deleted_at IS NULL;

ALTER TABLE filiais DROP CONSTRAINT uq_filiais_tenant_id_code;

CREATE UNIQUE INDEX uq_filiais_tenant_id_code_active
        ON filiais (tenant_id, code)
        WHERE deleted_at IS NULL;

ALTER TABLE roles DROP CONSTRAINT uq_roles_tenant_id_slug;

CREATE UNIQUE INDEX uq_roles_tenant_id_slug_active
        ON roles (tenant_id, slug)
        WHERE deleted_at IS NULL;

ALTER TABLE tenants DROP CONSTRAINT uq_tenants_slug;

CREATE UNIQUE INDEX uq_tenants_slug_active
        ON tenants (slug)
        WHERE deleted_at IS NULL;

ALTER TABLE tenants DROP CONSTRAINT uq_tenants_cnpj;

CREATE UNIQUE INDEX uq_tenants_cnpj_active
        ON tenants (cnpj)
        WHERE deleted_at IS NULL AND cnpj IS NOT NULL;

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON audit_logs
        USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
        WITH CHECK (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            OR (
                tenant_id IS NULL
                AND COALESCE(current_setting('app.current_tenant_id', true), '') = ''
            )
        );

UPDATE alembic_version SET version_num='0002_foundation_hardening' WHERE alembic_version.version_num = '0001_foundation';

INSERT INTO alembic_version (version_num) VALUES ('0002_foundation_hardening') ON CONFLICT (version_num) DO NOTHING;
