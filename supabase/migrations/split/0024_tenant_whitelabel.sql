-- White label: identidade do sistema, endereço e onboarding obrigatório
-- Espelha alembic/versions/0024_tenant_whitelabel.py

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS app_display_name VARCHAR(200);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS setup_completed_at TIMESTAMPTZ;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS ie VARCHAR(20);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS website VARCHAR(255);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS document_footer_text TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS zip_code VARCHAR(8);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS address VARCHAR(255);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS number VARCHAR(20);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS complement VARCHAR(100);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS district VARCHAR(100);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS state VARCHAR(2);

ALTER TABLE tenants ALTER COLUMN logo_url TYPE TEXT;

UPDATE tenants
SET setup_completed_at = NOW() AT TIME ZONE 'UTC'
WHERE setup_completed_at IS NULL
  AND deleted_at IS NULL
  AND cnpj IS NOT NULL
  AND email IS NOT NULL
  AND phone IS NOT NULL
  AND legal_name IS NOT NULL;
