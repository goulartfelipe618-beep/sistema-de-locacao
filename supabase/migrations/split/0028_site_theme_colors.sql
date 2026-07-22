-- Cores do site público (tenant white-label)
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_primary_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_background_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_text_color VARCHAR(7);

UPDATE alembic_version SET version_num = '0028_site_theme_colors'
WHERE version_num = '0027_site_slides';

INSERT INTO alembic_version (version_num)
VALUES ('0028_site_theme_colors')
ON CONFLICT DO NOTHING;
