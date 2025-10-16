-- Initial database setup for RBAC User Panel
-- This script creates the database and sets up basic configuration

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS rbac_user_panel
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- Use the database
USE rbac_user_panel;

-- Set SQL mode for strict data handling
SET SQL_MODE = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION';

-- Set time zone
SET time_zone = '+00:00';

-- Create default user for application (if needed)
-- CREATE USER IF NOT EXISTS 'rbac_app'@'%' IDENTIFIED BY 'your_secure_password';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON rbac_user_panel.* TO 'rbac_app'@'%';
-- FLUSH PRIVILEGES;

-- Log initial setup
INSERT INTO system_settings (key_name, value, description, data_type, is_public, is_system, created_at, updated_at)
VALUES (
    'database_initialized',
    'true',
    'Flag indicating database has been initialized',
    'boolean',
    false,
    true,
    NOW(),
    NOW()
) ON DUPLICATE KEY UPDATE value = 'true', updated_at = NOW();

COMMIT;