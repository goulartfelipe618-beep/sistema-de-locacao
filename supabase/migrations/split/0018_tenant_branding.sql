CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE tenants ADD COLUMN logo_storage_key VARCHAR(500);

ALTER TABLE tenants ADD COLUMN logo_url VARCHAR(500);

ALTER TABLE tenants ADD COLUMN brand_primary_color VARCHAR(7) DEFAULT '#1e5a8a';

ALTER TABLE tenants ADD COLUMN cert_a1_encrypted TEXT;

ALTER TABLE tenants ADD COLUMN cert_a1_password_encrypted TEXT;

ALTER TABLE tenants ADD COLUMN cert_a1_valid_until DATE;

ALTER TABLE tenants ADD COLUMN cert_a1_subject VARCHAR(255);

UPDATE alembic_version SET version_num='0018_tenant_branding' WHERE alembic_version.version_num = '0017_documentos';

INSERT INTO alembic_version (version_num) VALUES ('0018_tenant_branding') ON CONFLICT (version_num) DO NOTHING;
