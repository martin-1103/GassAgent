-- Create audit_logs table
-- Phase 4: Testing & Deployment
-- This table logs all system activities for security audit

CREATE TABLE audit_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id BIGINT UNSIGNED NULL,
    old_values JSON NULL,
    new_values JSON NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    session_id VARCHAR(255) NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_audit_logs_user_id (user_id),
    KEY idx_audit_logs_action (action),
    KEY idx_audit_logs_resource_type (resource_type),
    KEY idx_audit_logs_resource_id (resource_id),
    KEY idx_audit_logs_created_at (created_at),
    KEY idx_audit_logs_success (success),
    KEY idx_audit_logs_user_action (user_id, action),
    KEY idx_audit_logs_resource_action (resource_type, action),
    KEY idx_audit_logs_user_time (user_id, created_at),
    KEY idx_audit_logs_action_time (action, created_at),
    KEY idx_audit_logs_security (action, success, created_at),

    CONSTRAINT fk_audit_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create system_settings table
-- Phase 4: Testing & Deployment
-- This table stores system-wide configuration

CREATE TABLE system_settings (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    key_name VARCHAR(100) NOT NULL,
    value TEXT NULL,
    description TEXT NULL,
    data_type ENUM('string', 'number', 'boolean', 'json') NOT NULL DEFAULT 'string',
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    created_by BIGINT UNSIGNED NULL,
    updated_by BIGINT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_system_settings_key_name (key_name),
    KEY idx_system_settings_is_public (is_public),
    KEY idx_system_settings_is_system (is_system),
    KEY idx_system_settings_data_type (data_type),
    KEY idx_system_settings_created_by (created_by),

    CONSTRAINT fk_system_settings_created_by FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT fk_system_settings_updated_by FOREIGN KEY (updated_by) REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;