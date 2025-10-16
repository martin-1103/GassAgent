-- Create roles table
-- Phase 3: Role System
-- This table defines roles in the RBAC system

CREATE TABLE roles (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    level INT UNSIGNED NOT NULL DEFAULT 1,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    max_users INT UNSIGNED NULL,
    created_by BIGINT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_roles_name (name),
    KEY idx_roles_level (level),
    KEY idx_roles_is_active (is_active),
    KEY idx_roles_is_system (is_system),
    KEY idx_roles_created_by (created_by),
    KEY idx_roles_active_level (is_active, level),
    KEY idx_roles_system_active (is_system, is_active),
    KEY idx_roles_level_name (level, name),
    KEY idx_roles_hierarchy_query (level, is_active, is_system),

    CONSTRAINT fk_roles_created_by FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT ck_roles_level_positive CHECK (level > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create permissions table
-- Phase 3: Role System
-- This table defines permissions in the RBAC system

CREATE TABLE permissions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    description TEXT NULL,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    module VARCHAR(50) NULL,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    risk_level ENUM('low', 'medium', 'high', 'critical') NOT NULL DEFAULT 'medium',
    created_by BIGINT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_permissions_name (name),
    UNIQUE KEY uk_permissions_resource_action (resource, action),
    KEY idx_permissions_resource (resource),
    KEY idx_permissions_action (action),
    KEY idx_permissions_module (module),
    KEY idx_permissions_is_active (is_active),
    KEY idx_permissions_risk_level (risk_level),
    KEY idx_permissions_is_system (is_system),
    KEY idx_permissions_resource_action_active (resource, action, is_active),
    KEY idx_permissions_module_active (module, is_active),
    KEY idx_permissions_risk_active (risk_level, is_active),
    KEY idx_permissions_system_active (is_system, is_active),
    KEY idx_permissions_lookup_optimized (resource, action, is_active, is_system),

    CONSTRAINT fk_permissions_created_by FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT ck_permissions_name_format CHECK (name REGEXP '^[a-zA-Z0-9_\\.]+$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create role_permissions junction table
-- Phase 3: Role System
-- This table links roles to permissions

CREATE TABLE role_permissions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    role_id BIGINT UNSIGNED NOT NULL,
    permission_id BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_role_permissions_role_permission (role_id, permission_id),
    KEY idx_role_permissions_role_id (role_id),
    KEY idx_role_permissions_permission_id (permission_id),

    CONSTRAINT fk_role_permissions_role_id FOREIGN KEY (role_id) REFERENCES roles(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_role_permissions_permission_id FOREIGN KEY (permission_id) REFERENCES permissions(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;