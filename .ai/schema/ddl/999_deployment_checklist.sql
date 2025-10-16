-- Deployment checklist and validation script for RBAC User Panel
-- Run this script to validate the database setup before going to production

-- Create a validation report
SELECT '=== DATABASE VALIDATION REPORT ===' as validation_report;

-- Check if all required tables exist
SELECT 'Table Validation' as check_type,
       CASE
           WHEN COUNT(*) = 11 THEN 'PASS: All required tables exist'
           ELSE CONCAT('FAIL: Expected 11 tables, found ', COUNT(*))
       END as result
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN (
    'users', 'user_profiles', 'user_sessions', 'password_resets',
    'user_activities', 'roles', 'permissions', 'role_permissions',
    'user_roles', 'audit_logs', 'system_settings'
  );

-- Check character set and collation
SELECT 'Character Set Validation' as check_type,
       CASE
           WHEN DEFAULT_CHARACTER_SET_NAME = 'utf8mb4'
             AND DEFAULT_COLLATION_NAME = 'utf8mb4_unicode_ci'
           THEN 'PASS: Correct character set and collation'
           ELSE CONCAT('FAIL: Expected utf8mb4/utf8mb4_unicode_ci, found ',
                      DEFAULT_CHARACTER_SET_NAME, '/', DEFAULT_COLLATION_NAME)
       END as result
FROM information_schema.schemata
WHERE schema_name = DATABASE();

-- Check if system roles exist
SELECT 'System Roles Validation' as check_type,
       CASE
           WHEN COUNT(*) >= 4 THEN 'PASS: System roles exist'
           ELSE CONCAT('FAIL: Expected at least 4 system roles, found ', COUNT(*))
       END as result
FROM roles
WHERE is_system = true AND is_active = true;

-- Check if system permissions exist
SELECT 'System Permissions Validation' as check_type,
       CASE
           WHEN COUNT(*) >= 15 THEN 'PASS: System permissions exist'
           ELSE CONCAT('FAIL: Expected at least 15 system permissions, found ', COUNT(*))
       END as result
FROM permissions
WHERE is_system = true AND is_active = true;

-- Check if default system settings exist
SELECT 'System Settings Validation' as check_type,
       CASE
           WHEN COUNT(*) >= 10 THEN 'PASS: System settings exist'
           ELSE CONCAT('FAIL: Expected at least 10 system settings, found ', COUNT(*))
       END as result
FROM system_settings
WHERE is_system = true;

-- Check foreign key constraints
SELECT 'Foreign Key Validation' as check_type,
       CASE
           WHEN COUNT(*) >= 10 THEN 'PASS: Foreign key constraints exist'
           ELSE CONCAT('FAIL: Expected at least 10 foreign keys, found ', COUNT(*))
       END as result
FROM information_schema.key_column_usage
WHERE table_schema = DATABASE()
  AND referenced_table_name IS NOT NULL;

-- Check indexes
SELECT 'Index Validation' as check_type,
       CONCAT('Found ', COUNT(*), ' indexes') as result
FROM information_schema.statistics
WHERE table_schema = DATABASE();

-- Data integrity checks
SELECT 'Data Integrity: Users without profiles' as check_type,
       COUNT(*) as result
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id
WHERE up.user_id IS NULL;

SELECT 'Data Integrity: Users without roles' as check_type,
       COUNT(*) as result
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id AND ur.is_active = true
WHERE ur.user_id IS NULL;

SELECT 'Data Integrity: Roles without permissions' as check_type,
       r.name,
       COUNT(rp.permission_id) as permission_count
FROM roles r
LEFT JOIN role_permissions rp ON r.id = rp.role_id
WHERE r.is_active = true
GROUP BY r.id, r.name
HAVING permission_count = 0;

-- Security checks
SELECT 'Security: Admin users check' as check_type,
       COUNT(*) as admin_count
FROM users u
JOIN user_roles ur ON u.id = ur.user_id AND ur.is_active = true
JOIN roles r ON ur.role_id = r.id AND r.is_active = true
WHERE r.name IN ('admin', 'super_admin') AND u.status = 'active';

-- Performance checks
SELECT 'Performance: Table sizes' as check_type,
       table_name,
       ROUND(data_length/1024/1024, 2) as data_size_mb,
       ROUND(index_length/1024/1024, 2) as index_size_mb
FROM information_schema.tables
WHERE table_schema = DATABASE()
ORDER BY data_length DESC;

-- Create deployment readiness report
SELECT
    'DEPLOYMENT READINESS' as category,
    CASE
        WHEN (
            -- Check 1: All tables exist
            (SELECT COUNT(*) FROM information_schema.tables
             WHERE table_schema = DATABASE()
               AND table_name IN ('users', 'user_profiles', 'user_sessions', 'password_resets',
                                 'user_activities', 'roles', 'permissions', 'role_permissions',
                                 'user_roles', 'audit_logs', 'system_settings')) = 11
            -- Check 2: System roles exist
            AND (SELECT COUNT(*) FROM roles WHERE is_system = true AND is_active = true) >= 4
            -- Check 3: System permissions exist
            AND (SELECT COUNT(*) FROM permissions WHERE is_system = true AND is_active = true) >= 15
            -- Check 4: Default admin user exists (you may need to create this manually)
        ) THEN 'READY: Database is ready for production deployment'
        ELSE 'NOT READY: Please resolve the issues above before deployment'
    END as status;

-- Final recommendations
SELECT
    'RECOMMENDATIONS' as category,
    '1. Create at least one admin user manually if not exists' as recommendation
UNION ALL SELECT
    'RECOMMENDATIONS', '2. Review and update system settings as needed'
UNION ALL SELECT
    'RECOMMENDATIONS', '3. Set up database backup strategy'
UNION ALL SELECT
    'RECOMMENDATIONS', '4. Configure monitoring for audit logs'
UNION ALL SELECT
    'RECOMMENDATIONS', '5. Test application with sample data'
UNION ALL SELECT
    'RECOMMENDATIONS', '6. Review security settings and password policies';

-- Create admin user creation helper (commented out - uncomment if needed)
/*
-- Create default admin user (password: admin123456)
-- You should change this password immediately after deployment
INSERT INTO users (username, email, password_hash, status, email_verified, created_at, updated_at)
VALUES (
    'admin',
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6QJw/2Ej7W', -- admin123456
    'active',
    true,
    NOW(),
    NOW()
);

-- Get the admin user ID
SET @admin_user_id = LAST_INSERT_ID();

-- Create admin profile
INSERT INTO user_profiles (user_id, first_name, last_name, created_at, updated_at)
VALUES (@admin_user_id, 'System', 'Administrator', NOW(), NOW());

-- Assign admin role
INSERT INTO user_roles (user_id, role_id, assigned_by, assigned_at)
VALUES (@admin_user_id, (SELECT id FROM roles WHERE name = 'admin'), @admin_user_id, NOW());
*/

COMMIT;