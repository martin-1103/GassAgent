-- Seed initial data for RBAC system
-- This script should be run after all tables are created

-- Insert default system roles
INSERT INTO roles (name, display_name, description, level, is_system, is_active) VALUES
('super_admin', 'Super Administrator', 'Super administrator dengan akses penuh ke sistem', 100, TRUE, TRUE),
('admin', 'Administrator', 'Administrator dengan akses ke user dan role management', 80, TRUE, TRUE),
('moderator', 'Moderator', 'Moderator dengan akses terbatas untuk user management', 50, FALSE, TRUE),
('user', 'Regular User', 'Regular user dengan akses dasar', 10, TRUE, TRUE);

-- Insert default system permissions
INSERT INTO permissions (name, display_name, description, resource, action, module, is_system, risk_level) VALUES
-- System permissions
('system.admin', 'System Administration', 'Full system administration access', 'system', 'admin', 'system', TRUE, 'critical'),
('system.settings', 'System Settings', 'Access to system settings', 'system', 'settings', 'system', TRUE, 'high'),
('system.audit', 'System Audit', 'Access to system audit logs', 'system', 'audit', 'system', TRUE, 'high'),

-- User management permissions
('users.create', 'Create Users', 'Permission to create new users', 'users', 'create', 'user_management', TRUE, 'high'),
('users.read', 'View Users', 'Permission to view user information', 'users', 'read', 'user_management', TRUE, 'medium'),
('users.update', 'Update Users', 'Permission to update user information', 'users', 'update', 'user_management', TRUE, 'high'),
('users.delete', 'Delete Users', 'Permission to delete users', 'users', 'delete', 'user_management', TRUE, 'critical'),
('users.activate', 'Activate Users', 'Permission to activate user accounts', 'users', 'activate', 'user_management', TRUE, 'high'),
('users.deactivate', 'Deactivate Users', 'Permission to deactivate user accounts', 'users', 'deactivate', 'user_management', TRUE, 'high'),

-- Role management permissions
('roles.create', 'Create Roles', 'Permission to create new roles', 'roles', 'create', 'role_management', TRUE, 'high'),
('roles.read', 'View Roles', 'Permission to view role information', 'roles', 'read', 'role_management', TRUE, 'medium'),
('roles.update', 'Update Roles', 'Permission to update role information', 'roles', 'update', 'role_management', TRUE, 'high'),
('roles.delete', 'Delete Roles', 'Permission to delete roles', 'roles', 'delete', 'role_management', TRUE, 'critical'),
('roles.assign', 'Assign Roles', 'Permission to assign roles to users', 'roles', 'assign', 'role_management', TRUE, 'high'),
('roles.revoke', 'Revoke Roles', 'Permission to revoke roles from users', 'roles', 'revoke', 'role_management', TRUE, 'high'),

-- Authentication permissions
('auth.login', 'Login', 'Permission to login to system', 'auth', 'login', 'authentication', TRUE, 'low'),
('auth.logout', 'Logout', 'Permission to logout from system', 'auth', 'logout', 'authentication', TRUE, 'low'),
('auth.register', 'Register', 'Permission to register new account', 'auth', 'register', 'authentication', TRUE, 'low'),
('auth.reset_password', 'Reset Password', 'Permission to reset password', 'auth', 'reset_password', 'authentication', TRUE, 'medium'),

-- Profile permissions
('profile.read', 'View Profile', 'Permission to view user profile', 'profile', 'read', 'profile', TRUE, 'low'),
('profile.update', 'Update Profile', 'Permission to update user profile', 'profile', 'update', 'profile', TRUE, 'low'),
('profile.update_own', 'Update Own Profile', 'Permission to update own profile', 'profile', 'update_own', 'profile', TRUE, 'low');

-- Assign permissions to Super Admin role (all permissions)
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'super_admin'),
    p.id
FROM permissions p;

-- Assign permissions to Admin role
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'admin'),
    p.id
FROM permissions p
WHERE p.name NOT IN ('system.admin', 'system.settings');

-- Assign basic permissions to Moderator role
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'moderator'),
    p.id
FROM permissions p
WHERE p.name IN (
    'users.read', 'users.update', 'users.activate', 'users.deactivate',
    'roles.read', 'auth.login', 'auth.logout',
    'profile.read', 'profile.update'
);

-- Assign basic permissions to User role
INSERT INTO role_permissions (role_id, permission_id)
SELECT
    (SELECT id FROM roles WHERE name = 'user'),
    p.id
FROM permissions p
WHERE p.name IN (
    'auth.login', 'auth.logout', 'auth.register', 'auth.reset_password',
    'profile.read', 'profile.update_own'
);

-- Insert default system settings
INSERT INTO system_settings (key_name, value, description, data_type, is_public, is_system) VALUES
('app_name', 'RBAC User Panel', 'Application name displayed to users', 'string', TRUE, TRUE),
('app_version', '1.0.0', 'Current application version', 'string', TRUE, TRUE),
('max_login_attempts', '5', 'Maximum failed login attempts before account lockout', 'number', FALSE, TRUE),
('account_lockout_duration', '15', 'Account lockout duration in minutes', 'number', FALSE, TRUE),
('password_min_length', '8', 'Minimum password length requirement', 'number', FALSE, TRUE),
('password_require_uppercase', 'true', 'Require uppercase letters in password', 'boolean', FALSE, TRUE),
('password_require_lowercase', 'true', 'Require lowercase letters in password', 'boolean', FALSE, TRUE),
('password_require_numbers', 'true', 'Require numbers in password', 'boolean', FALSE, TRUE),
('password_require_special_chars', 'true', 'Require special characters in password', 'boolean', FALSE, TRUE),
('session_timeout_hours', '24', 'Session timeout duration in hours', 'number', FALSE, TRUE),
('email_verification_required', 'true', 'Require email verification for new accounts', 'boolean', FALSE, TRUE),
('two_factor_enabled', 'false', 'Enable two-factor authentication', 'boolean', FALSE, TRUE),
('default_timezone', 'UTC', 'Default timezone for the application', 'string', TRUE, TRUE),
('default_language', 'en', 'Default language for the application', 'string', TRUE, TRUE);