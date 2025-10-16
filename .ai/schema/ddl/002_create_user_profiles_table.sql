-- Create user_profiles table
-- Phase 2: User Management
-- This table stores user profile information

CREATE TABLE user_profiles (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    first_name VARCHAR(50) NULL,
    last_name VARCHAR(50) NULL,
    full_name VARCHAR(100) GENERATED ALWAYS AS (CONCAT(IFNULL(first_name, ''), ' ', IFNULL(last_name, ''))) VIRTUAL,
    phone VARCHAR(20) NULL,
    avatar_url VARCHAR(255) NULL,
    bio TEXT NULL,
    date_of_birth DATE NULL,
    gender ENUM('male', 'female', 'other', 'prefer_not_to_say') NULL,
    address VARCHAR(255) NULL,
    city VARCHAR(100) NULL,
    country VARCHAR(100) NULL,
    postal_code VARCHAR(20) NULL,
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    notification_email BOOLEAN NOT NULL DEFAULT TRUE,
    notification_push BOOLEAN NOT NULL DEFAULT TRUE,
    two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_user_profiles_user_id (user_id),
    KEY idx_user_profiles_first_name (first_name),
    KEY idx_user_profiles_last_name (last_name),
    KEY idx_user_profiles_full_name (full_name),
    KEY idx_user_profiles_city (city),
    KEY idx_user_profiles_country (country),
    KEY idx_user_profiles_timezone (timezone),

    CONSTRAINT fk_user_profiles_user_id FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT ck_user_profiles_date_of_birth_reasonable CHECK (
        date_of_birth IS NULL OR
        date_of_birth BETWEEN '1900-01-01' AND CURRENT_DATE
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;