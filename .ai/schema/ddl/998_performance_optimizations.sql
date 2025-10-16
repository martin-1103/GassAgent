-- Performance optimizations for RBAC User Panel
-- This script should be run after all data is seeded

-- Create optimized views for common queries

-- View for active users with their roles
CREATE OR REPLACE VIEW active_users_with_roles AS
SELECT
    u.id,
    u.username,
    u.email,
    u.status,
    u.last_login_at,
    up.first_name,
    up.last_name,
    up.full_name,
    GROUP_CONCAT(DISTINCT r.name ORDER BY r.level DESC SEPARATOR ', ') as role_names,
    GROUP_CONCAT(DISTINCT r.display_name ORDER BY r.level DESC SEPARATOR ', ') as role_display_names,
    MAX(r.level) as max_role_level
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id
LEFT JOIN user_roles ur ON u.id = ur.user_id AND ur.is_active = true
LEFT JOIN roles r ON ur.role_id = r.id AND r.is_active = true
WHERE u.status = 'active' AND u.email_verified = true
GROUP BY u.id, u.username, u.email, u.status, u.last_login_at, up.first_name, up.last_name, up.full_name;

-- View for user permissions (aggregated through roles)
CREATE OR REPLACE VIEW user_permissions AS
SELECT DISTINCT
    ur.user_id,
    p.name as permission_name,
    p.display_name,
    p.resource,
    p.action,
    p.module,
    r.level as role_level
FROM user_roles ur
JOIN roles r ON ur.role_id = r.id AND ur.is_active = true AND r.is_active = true
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id AND p.is_active = true
WHERE ur.expires_at IS NULL OR ur.expires_at > NOW();

-- Materialized view alternative for role hierarchy (using stored procedure)
DELIMITER //
CREATE PROCEDURE refresh_role_hierarchy_cache()
BEGIN
    DROP TEMPORARY TABLE IF EXISTS temp_role_hierarchy;

    CREATE TEMPORARY TABLE temp_role_hierarchy AS
    SELECT
        r1.id as role_id,
        r1.name as role_name,
        r1.level as role_level,
        COUNT(r2.id) as higher_roles_count
    FROM roles r1
    LEFT JOIN roles r2 ON r2.level > r1.level AND r2.is_active = true
    WHERE r1.is_active = true
    GROUP BY r1.id, r1.name, r1.level
    ORDER BY r1.level DESC;

    -- Create cache table if not exists
    CREATE TABLE IF NOT EXISTS role_hierarchy_cache (
        role_id BIGINT UNSIGNED PRIMARY KEY,
        role_name VARCHAR(50) NOT NULL,
        role_level INT UNSIGNED NOT NULL,
        higher_roles_count INT UNSIGNED NOT NULL,
        last_refreshed TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_role_hierarchy_level (role_level),
        INDEX idx_role_hierarchy_name (role_name)
    ) ENGINE=InnoDB;

    -- Replace cache data
    REPLACE INTO role_hierarchy_cache (role_id, role_name, role_level, higher_roles_count)
    SELECT * FROM temp_role_hierarchy;

    DROP TEMPORARY TABLE temp_role_hierarchy;
END//
DELIMITER ;

-- Create stored procedure for permission checking
DELIMITER //
CREATE PROCEDURE check_user_permission(
    IN p_user_id BIGINT UNSIGNED,
    IN p_resource VARCHAR(50),
    IN p_action VARCHAR(50)
)
BEGIN
    SELECT
        COUNT(*) as has_permission,
        GROUP_CONCAT(DISTINCT r.name ORDER BY r.level DESC) as roles_granting_access
    FROM user_roles ur
    JOIN roles r ON ur.role_id = r.id AND ur.is_active = true AND r.is_active = true
    JOIN role_permissions rp ON r.id = rp.role_id
    JOIN permissions p ON rp.permission_id = p.id AND p.is_active = true
    WHERE ur.user_id = p_user_id
      AND p.resource = p_resource
      AND p.action = p_action
      AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
      AND u.status = 'active'
      AND u.email_verified = true;
END//
DELIMITER ;

-- Create function to get user max role level
DELIMITER //
CREATE FUNCTION get_user_max_role_level(p_user_id BIGINT UNSIGNED)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE max_level INT DEFAULT 0;

    SELECT COALESCE(MAX(r.level), 0) INTO max_level
    FROM user_roles ur
    JOIN roles r ON ur.role_id = r.id
    WHERE ur.user_id = p_user_id
      AND ur.is_active = true
      AND r.is_active = true
      AND (ur.expires_at IS NULL OR ur.expires_at > NOW());

    RETURN max_level;
END//
DELIMITER ;

-- Create indexes for performance if they don't exist
CREATE INDEX IF NOT EXISTS idx_users_email_status_verified ON users(email, status, email_verified);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_active_expiry ON user_roles(user_id, is_active, expires_at);
CREATE INDEX IF NOT EXISTS idx_permissions_resource_action_active ON permissions(resource, action, is_active);
CREATE INDEX IF NOT EXISTS idx_audit_logs_security ON audit_logs(action, success, created_at);
CREATE INDEX IF NOT EXISTS idx_user_activities_user_type_time ON user_activities(user_id, activity_type, created_at);

-- Create partitioning for audit_logs (if table is large)
-- This is optional and should be done based on actual data size
/*
ALTER TABLE audit_logs
PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
*/

-- Schedule event for periodic maintenance (MySQL 8.0+)
SET GLOBAL event_scheduler = ON;

DELIMITER //
CREATE EVENT IF NOT EXISTS cleanup_expired_sessions
ON SCHEDULE EVERY 1 HOUR
DO
BEGIN
    DELETE FROM user_sessions
    WHERE is_active = false
       OR expires_at < NOW()
       OR (is_active = true AND last_accessed_at < DATE_SUB(NOW(), INTERVAL 7 DAY));
END//

CREATE EVENT IF NOT EXISTS cleanup_expired_password_resets
ON SCHEDULE EVERY 6 HOUR
DO
BEGIN
    DELETE FROM password_resets
    WHERE is_used = true
       OR expires_at < NOW();
END//

CREATE EVENT IF NOT EXISTS deactivate_expired_user_roles
ON SCHEDULE EVERY 1 HOUR
DO
BEGIN
    UPDATE user_roles
    SET is_active = false
    WHERE is_active = true
      AND expires_at IS NOT NULL
      AND expires_at < NOW();
END//

CREATE EVENT IF NOT EXISTS refresh_role_hierarchy
ON SCHEDULE EVERY 30 MINUTE
DO
BEGIN
    CALL refresh_role_hierarchy_cache();
END//
DELIMITER ;

-- Create database health check view
CREATE OR REPLACE VIEW database_health AS
SELECT
    'users' as table_name,
    COUNT(*) as total_records,
    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_records,
    MAX(created_at) as latest_record,
    MIN(created_at) as oldest_record
FROM users
UNION ALL
SELECT
    'roles' as table_name,
    COUNT(*) as total_records,
    SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END) as active_records,
    MAX(created_at) as latest_record,
    MIN(created_at) as oldest_record
FROM roles
UNION ALL
SELECT
    'permissions' as table_name,
    COUNT(*) as total_records,
    SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END) as active_records,
    MAX(created_at) as latest_record,
    MIN(created_at) as oldest_record
FROM permissions
UNION ALL
SELECT
    'user_roles' as table_name,
    COUNT(*) as total_records,
    SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END) as active_records,
    MAX(assigned_at) as latest_record,
    MIN(assigned_at) as oldest_record
FROM user_roles;

COMMIT;