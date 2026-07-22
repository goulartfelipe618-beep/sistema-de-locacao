-- Cores das abas da topbar do site
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_topbar_tab_bg_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_topbar_tab_text_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_topbar_tab_active_bg_color VARCHAR(7);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS site_topbar_tab_active_text_color VARCHAR(7);

UPDATE alembic_version SET version_num = '0030_site_topbar_tabs'
WHERE version_num = '0029_site_theme_extended';

INSERT INTO alembic_version (version_num)
VALUES ('0030_site_topbar_tabs')
ON CONFLICT DO NOTHING;
