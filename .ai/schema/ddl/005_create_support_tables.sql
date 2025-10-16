-- Create user_sessions table
-- Phase 1: Authentication Setup
-- This table manages user login sessions

CREATE TABLE user_sessions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    session_token VARCHAR(255) NOT NULL,
    refresh_token VARCHAR(255) NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_user_sessions_session_token (session_token),
    UNIQUE KEY uk_user_sessions_refresh_token (refresh_token),
    KEY idx_user_sessions_user_id (user_id),
    KEY idx_user_sessions_is_active (is_active),
    KEY idx_user_sessions_expires_at (expires_at),
    KEY idx_user_sessions_user_active (user_id, is_active),
    KEY idx_user_sessions_cleanup (is_active, expires_at),

    CONSTRAINT fk_user_sessions_user_id FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create password_resets table
-- Phase 1: Authentication Setup
-- This table manages password reset requests

CREATE TABLE password_resets (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    token VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP NULL,

    PRIMARY KEY (id),
    UNIQUE KEY uk_password_resets_token (token),
    KEY idx_password_resets_user_id (user_id),
    KEY idx_password_resets_email (email),
    KEY idx_password_resets_is_used (is_used),
    KEY idx_password_resets_expires_at (expires_at),
    KEY idx_password_resets_cleanup (is_used, expires_at),

    CONSTRAINT fk_password_resets_user_id FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create user_activities table
-- Phase 2: User Management
-- This table logs user activities for audit purposes

CREATE TABLE user_activities (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NULL,
    activity_type VARCHAR(50) NOT NULL,
    description TEXT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    metadata JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_user_activities_user_id (user_id),
    KEY idx_user_activities_activity_type (activity_type),
    KEY idx_user_activities_created_at (created_at),
    KEY idx_user_activities_user_activity (user_id, activity_type),
    KEY idx_user_activities_user_time (user_id, created_at),
    KEY idx_user_activities_activity_time (activity_type, created_at),

    CONSTRAINT fk_user_activities_user_id FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;