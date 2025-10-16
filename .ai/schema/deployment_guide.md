# RBAC User Panel - Database Deployment Guide

## Quick Start Guide

### 1. Database Setup
```bash
# MySQL 8.0+ required
mysql -u root -p

# Create database
CREATE DATABASE rbac_user_panel CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE rbac_user_panel;
```

### 2. Run Migration Scripts
```bash
# Execute in order
mysql -u root -p rbac_user_panel < 000_initial_setup.sql
mysql -u root -p rbac_user_panel < 001_create_users_table.sql
mysql -u root -p rbac_user_panel < 002_create_user_profiles_table.sql
mysql -u root -p rbac_user_panel < 003_create_roles_permissions_tables.sql
mysql -u root -p rbac_user_panel < 004_create_user_roles_table.sql
mysql -u root -p rbac_user_panel < 005_create_support_tables.sql
mysql -u root -p rbac_user_panel < 006_create_audit_system_tables.sql
mysql -u root -p rbac_user_panel < 007_seed_initial_data.sql
mysql -u root -p rbac_user_panel < 998_performance_optimizations.sql
mysql -u root -p rbac_user_panel < 999_deployment_checklist.sql
```

### 3. Create First Admin User
```sql
-- After running migrations, create your first admin
INSERT INTO users (username, email, password_hash, status, email_verified)
VALUES ('admin', 'admin@yourcompany.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6QJw/2Ej7W', 'active', true);

-- Get admin user ID
SET @admin_id = LAST_INSERT_ID();

-- Create admin profile
INSERT INTO user_profiles (user_id, first_name, last_name) VALUES (@admin_id, 'System', 'Administrator');

-- Assign admin role
INSERT INTO user_roles (user_id, role_id) VALUES (@admin_id, (SELECT id FROM roles WHERE name = 'admin'));
```

## Phase-by-Phase Implementation

### Phase 1: Authentication (Week 1)
- **Focus**: User registration, login, JWT tokens
- **Tables**: `users`, `user_sessions`, `password_resets`
- **API Endpoints**: `/auth/*`

### Phase 2: User Management (Week 2)
- **Focus**: CRUD operations, profiles, activity logging
- **Tables**: `user_profiles`, `user_activities`
- **API Endpoints**: `/users/*`

### Phase 3: Role System (Week 3)
- **Focus**: RBAC implementation, role management
- **Tables**: `roles`, `permissions`, `role_permissions`, `user_roles`
- **API Endpoints**: `/roles/*`, `/permissions/*`

### Phase 4: Testing & Deployment (Week 4)
- **Focus**: Performance, security, audit system
- **Tables**: `audit_logs`, `system_settings`
- **API Endpoints**: `/audit/*`, `/system/*`

## Configuration

### Environment Variables
```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=rbac_user_panel
DB_USER=rbac_app
DB_PASSWORD=your_secure_password

# JWT
JWT_SECRET=your_very_long_and_secure_jwt_secret_key_here
JWT_EXPIRES_IN=24h
REFRESH_TOKEN_EXPIRES_IN=7d

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password

# Security
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION=15
SESSION_TIMEOUT_HOURS=24
```

### Security Best Practices
1. Change default admin password immediately
2. Use environment variables for all sensitive data
3. Enable SSL/TLS for database connections
4. Set up regular database backups
5. Monitor audit logs regularly
6. Keep all dependencies updated

## Performance Monitoring

### Key Metrics to Monitor
- Database connection pool usage
- Query execution times
- Session cleanup efficiency
- Audit log growth rate
- Role permission check performance

### Maintenance Tasks
- Daily: Expired session cleanup
- Weekly: Database optimization
- Monthly: Audit log review
- Quarterly: Performance tuning

## Troubleshooting

### Common Issues
1. **Migration fails**: Check MySQL version (8.0+ required)
2. **Permission denied**: Verify database user permissions
3. **Performance issues**: Check indexes and query plans
4. **Login problems**: Verify JWT secret and session settings

### Health Check Queries
```sql
-- Check database health
SELECT * FROM database_health;

-- Check active users
SELECT COUNT(*) FROM users WHERE status = 'active';

-- Check role assignments
SELECT u.username, r.display_name
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE ur.is_active = true;
```

## Support

For issues or questions, refer to the main README.md file or contact the development team.