CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT false NOT NULL;

ALTER TABLE users ADD COLUMN totp_secret_encrypted TEXT;

ALTER TABLE users ADD COLUMN totp_enabled_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE users ADD COLUMN recovery_codes_encrypted TEXT;

UPDATE alembic_version SET version_num='0021_user_2fa' WHERE alembic_version.version_num = '0020_notificacoes';

INSERT INTO alembic_version (version_num) VALUES ('0021_user_2fa') ON CONFLICT (version_num) DO NOTHING;
