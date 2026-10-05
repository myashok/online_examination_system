-- Runs once, the first time the Compose MySQL volume is created.
-- Connections from other containers arrive on the Docker network, so the
-- accounts are granted to '%' inside this private database. oes_app still
-- has DML only. oes_migrator is used only by the migrate step.

CREATE USER IF NOT EXISTS 'oes_migrator'@'%' IDENTIFIED BY 'oes_migrator_pass';
CREATE USER IF NOT EXISTS 'oes_app'@'%' IDENTIFIED BY 'oes_app_pass';

GRANT ALL PRIVILEGES ON oes.* TO 'oes_migrator'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON oes.* TO 'oes_app'@'%';

FLUSH PRIVILEGES;
