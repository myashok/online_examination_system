-- Least-privilege accounts for the local ONLINE EXAMINATION SYSTEM database.
-- oes_migrator applies DDL (Django migrations and this schema).
-- oes_app is the account used by the running application: DML only.
-- These passwords are for the local demonstration database.

CREATE DATABASE IF NOT EXISTS oes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'oes_migrator'@'localhost' IDENTIFIED BY 'oes_migrator_pass';
CREATE USER IF NOT EXISTS 'oes_migrator'@'127.0.0.1' IDENTIFIED BY 'oes_migrator_pass';
CREATE USER IF NOT EXISTS 'oes_app'@'localhost' IDENTIFIED BY 'oes_app_pass';
CREATE USER IF NOT EXISTS 'oes_app'@'127.0.0.1' IDENTIFIED BY 'oes_app_pass';

GRANT ALL PRIVILEGES ON oes.* TO 'oes_migrator'@'localhost';
GRANT ALL PRIVILEGES ON oes.* TO 'oes_migrator'@'127.0.0.1';
GRANT ALL PRIVILEGES ON `test\_oes`.* TO 'oes_migrator'@'localhost';
GRANT ALL PRIVILEGES ON `test\_oes`.* TO 'oes_migrator'@'127.0.0.1';
GRANT CREATE, DROP ON *.* TO 'oes_migrator'@'localhost';
GRANT CREATE, DROP ON *.* TO 'oes_migrator'@'127.0.0.1';

GRANT SELECT, INSERT, UPDATE, DELETE ON oes.* TO 'oes_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON oes.* TO 'oes_app'@'127.0.0.1';

FLUSH PRIVILEGES;
