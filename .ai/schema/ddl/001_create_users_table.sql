-- Create users table
-- Phase 1: Authentication Setup
-- This table stores user authentication data and account status

CREATE TABLE users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status ENUM('active', 'inactive', 'suspended', 'pending_verification') NOT NULL DEFAULT 'pending_verification',
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    email_verification_token VARCHAR(255) NULL,
    last_login_at TIMESTAMP NULL,
    login_attempts INT UNSIGNED NOT NULL DEFAULT 0,
    locked_until TIMESTAMP NULL,
    password_changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_users_username (username),
    UNIQUE KEY uk_users_email (email),
    KEY idx_users_status (status),
    KEY idx_users_email_verified (email_verified),
    KEY idx_users_last_login_at (last_login_at),
    KEY idx_users_status_email_verified (status, email_verified),
    KEY idx_users_status_last_login (status, last_login_at),
    KEY idx_users_created_at_status (created_at, status),
    KEY idx_users_email_verification_token (email_verification_token),
    KEY idx_users_locked_until (locked_until),
    KEY idx_users_login_optimization (email, status, locked_until),

    CONSTRAINT ck_users_email_format CHECK (email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'),
    CONSTRAINT ck_users_username_format CHECK (username REGEXP '^[a-zA-Z0-9_]{3,50}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create trigger for user insert
DELIMITER //
CREATE TRIGGER before_user_insert
BEFORE INSERT ON users
FOR EACH ROW
BEGIN
    -- Validate password format (basic length check)
    IF LENGTH(NEW.password_hash) < 60 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid password hash format';
    END IF;

    -- Set email verification token if not provided and email not verified
    IF NEW.email_verified = FALSE AND NEW.email_verification_token IS NULL THEN
        SET NEW.email_verification_token = SHA2(CONCAT(NEW.email, NOW(), RAND()), 256);
    END IF;
END//
DELIMITER ;

-- Create trigger for user update audit logging
DELIMITER //
CREATE TRIGGER after_user_update
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    -- Log important status changes
    IF OLD.status <> NEW.status THEN
        INSERT INTO user_activities (user_id, activity_type, description, ip_address, user_agent, created_at)
        VALUES (NEW.id, 'status_change',
                CONCAT('Status changed from ', OLD.status, ' to ', NEW.status),
                NULL, NULL, NOW());
    END IF;

    -- Log password changes
    IF OLD.password_hash <> NEW.password_hash THEN
        SET NEW.password_changed_at = NOW();
        INSERT INTO user_activities (user_id, activity_type, description, ip_address, user_agent, created_at)
        VALUES (NEW.id, 'password_change', 'Password was changed',
                NULL, NULL, NOW());
    END IF;
END//
DELIMITER ;