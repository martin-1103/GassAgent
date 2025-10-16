-- Create user_roles junction table
-- Phase 3: Role System
-- This table links users to roles

CREATE TABLE user_roles (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    role_id BIGINT UNSIGNED NOT NULL,
    assigned_by BIGINT UNSIGNED NULL,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT NULL,

    PRIMARY KEY (id),
    UNIQUE KEY uk_user_roles_user_role (user_id, role_id),
    KEY idx_user_roles_user_id (user_id),
    KEY idx_user_roles_role_id (role_id),
    KEY idx_user_roles_assigned_by (assigned_by),
    KEY idx_user_roles_is_active (is_active),
    KEY idx_user_roles_expires_at (expires_at),
    KEY idx_user_roles_user_active (user_id, is_active),
    KEY idx_user_roles_role_active (role_id, is_active),
    KEY idx_user_roles_expiry_active (expires_at, is_active),
    KEY idx_user_roles_user_active_assigned (user_id, is_active, assigned_at),
    KEY idx_user_roles_permission_check (user_id, is_active, expires_at),

    CONSTRAINT fk_user_roles_user_id FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_user_roles_role_id FOREIGN KEY (role_id) REFERENCES roles(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_user_roles_assigned_by FOREIGN KEY (assigned_by) REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT ck_user_roles_expiry_future CHECK (
        expires_at IS NULL OR expires_at > assigned_at
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create triggers for role assignment audit logging
DELIMITER //
CREATE TRIGGER after_user_role_insert
AFTER INSERT ON user_roles
FOR EACH ROW
BEGIN
    INSERT INTO user_activities (user_id, activity_type, description, ip_address, user_agent, created_at)
    VALUES (NEW.user_id, 'role_assignment',
            CONCAT('Role assigned: ', (SELECT display_name FROM roles WHERE id = NEW.role_id)),
            NULL, NULL, NOW());
END//
DELIMITER ;

DELIMITER //
CREATE TRIGGER after_user_role_update
AFTER UPDATE ON user_roles
FOR EACH ROW
BEGIN
    IF OLD.is_active <> NEW.is_active THEN
        INSERT INTO user_activities (user_id, activity_type, description, ip_address, user_agent, created_at)
        VALUES (NEW.user_id, 'role_status_change',
                CONCAT('Role status changed to ', IF(NEW.is_active, 'active', 'inactive'),
                       ' for role: ', (SELECT display_name FROM roles WHERE id = NEW.role_id)),
                NULL, NULL, NOW());
    END IF;
END//
DELIMITER ;

DELIMITER //
CREATE TRIGGER after_user_role_delete
AFTER DELETE ON user_roles
FOR EACH ROW
BEGIN
    INSERT INTO user_activities (user_id, activity_type, description, ip_address, user_agent, created_at)
    VALUES (OLD.user_id, 'role_removal',
            CONCAT('Role removed: ', (SELECT display_name FROM roles WHERE id = OLD.role_id)),
            NULL, NULL, NOW());
END//
DELIMITER ;