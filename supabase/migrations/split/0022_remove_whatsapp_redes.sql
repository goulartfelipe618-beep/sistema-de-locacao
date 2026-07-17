CREATE EXTENSION IF NOT EXISTS pgcrypto;

UPDATE crm_oportunidades SET origem_lead = 'outro' WHERE origem_lead = 'redes_sociais';

UPDATE crm_campanhas SET canal = 'email' WHERE canal = 'whatsapp';

UPDATE notificacao_envios SET canal = 'sms' WHERE canal = 'whatsapp';

ALTER TABLE clientes DROP COLUMN whatsapp;

UPDATE alembic_version SET version_num='0022_remove_whatsapp_redes' WHERE alembic_version.version_num = '0021_user_2fa';

INSERT INTO alembic_version (version_num) VALUES ('0022_remove_whatsapp_redes') ON CONFLICT (version_num) DO NOTHING;
