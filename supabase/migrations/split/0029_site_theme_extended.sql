-- Cores estendidas do site público
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_header_bg_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_header_text_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_topbar_bg_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_button_bg_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_button_text_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_link_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_border_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_surface_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_text_muted_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_footer_bg_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_footer_text_color VARCHAR(7);

UPDATE alembic_version SET version_num = '0029_site_theme_extended'
WHERE version_num = '0028_site_theme_colors';

INSERT INTO alembic_version (version_num)
VALUES ('0029_site_theme_extended')
ON CONFLICT DO NOTHING;
