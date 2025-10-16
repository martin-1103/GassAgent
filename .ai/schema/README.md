# RBAC User Panel Database Schema

## Overview

Database schema yang komprehensif untuk sistem RBAC (Role-Based Access Control) User Panel yang dibangun dengan Node.js, Express, Next.js, dan MySQL.

## Database Structure

### Engine Configuration
- **Database Engine**: MySQL 8.0+
- **Character Set**: utf8mb4
- **Collation**: utf8mb4_unicode_ci
- **Storage Engine**: InnoDB

## Phase-Based Development

### Phase 1: Authentication Setup (Week 1)
**Tables**: `users`, `user_sessions`, `password_resets`

Fokus pada:
- User registration dan login
- JWT token management
- Password security dengan bcrypt
- Email verification
- Password reset

**Key Features**:
- Account lockout setelah 5 failed attempts
- Email verification required
- Secure password hashing (bcrypt cost 12)
- Session management dengan refresh token rotation

### Phase 2: User Management (Week 2)
**Tables**: `user_profiles`, `user_activities`

Fokus pada:
- CRUD operations untuk users
- User profile management
- Activity logging
- Basic admin functionality

**Key Features**:
- Extensive user profile fields
- Activity audit trail
- Profile privacy controls
- Multi-language support

### Phase 3: Role System (Week 3)
**Tables**: `roles`, `permissions`, `role_permissions`, `user_roles`

Fokus pada:
- RBAC implementation
- Role management
- Permission system
- Role assignment

**Key Features**:
- Hierarchical role system
- Granular permission control
- System role protection
- Temporary role assignments

### Phase 4: Testing & Deployment (Week 4)
**Tables**: `audit_logs`, `system_settings`

Fokus pada:
- Performance optimization
- Security hardening
- Audit system
- Production deployment

**Key Features**:
- Comprehensive audit logging
- System configuration management
- Security compliance
- Performance monitoring

## Security Features

### Password Security
- Bcrypt hashing dengan cost 12
- Minimum 8 characters
- Require uppercase, lowercase, numbers, dan special characters
- Password history tracking
- Password rotation policy (90 days)

### Session Management
- JWT tokens dengan 24-hour expiration
- Refresh token rotation
- Maximum 3 concurrent sessions
- IP address dan user agent tracking
- Automatic session cleanup

### Access Control
- Role-based access control (RBAC)
- Hierarchical role system
- Granular permissions
- Self-assignment prevention
- Least privilege principle

### Audit & Compliance
- Comprehensive activity logging
- Immutable audit trails
- 90-day retention policy
- Security event tracking
- Data change tracking

## Default Roles & Permissions

### System Roles
1. **Super Administrator** (Level 100)
   - Full system access
   - All permissions

2. **Administrator** (Level 80)
   - User dan role management
   - Most system permissions

3. **Moderator** (Level 50)
   - Limited user management
   - Read access to most resources

4. **Regular User** (Level 10)
   - Basic self-service permissions
   - Profile management

### Permission Categories
- **System**: System administration dan configuration
- **User Management**: CRUD operations pada users
- **Role Management**: CRUD operations pada roles dan permissions
- **Authentication**: Login, logout, registration, password reset
- **Profile**: Profile management

## Performance Optimizations

### Indexes
- Unique indexes untuk data integrity
- Composite indexes untuk query optimization
- Security-specific indexes untuk access control
- Audit-specific indexes untuk log retrieval

### Caching Strategy
- User sessions: Redis dengan TTL
- Permissions: Memory cache (1 hour TTL)
- Roles: Memory cache (6 hour TTL)
- User profiles: Optional cache

### Cleanup Jobs
- Expired session cleanup (daily)
- Old activity log cleanup (monthly)
- Temporary role expiration check (hourly)

## Data Migration

### Migration Order
1. `001_create_users_table.sql`
2. `002_create_user_profiles_table.sql`
3. `003_create_roles_permissions_tables.sql`
4. `004_create_user_roles_table.sql`
5. `005_create_support_tables.sql`
6. `006_create_audit_system_tables.sql`
7. `007_seed_initial_data.sql`

### Seed Data
- 4 default roles (Super Admin, Admin, Moderator, User)
- 20+ default permissions
- System configuration settings
- Default role-permission assignments

## API Endpoints

### Authentication (Phase 1)
- POST /auth/register
- POST /auth/login
- POST /auth/logout
- POST /auth/verify-email
- POST /auth/forgot-password
- POST /auth/reset-password

### User Management (Phase 2)
- GET /users
- GET /users/:id
- PUT /users/:id
- DELETE /users/:id
- GET /users/profile
- PUT /users/profile

### Role Management (Phase 3)
- GET /roles
- GET /roles/:id
- POST /roles
- PUT /roles/:id
- DELETE /roles/:id
- GET /permissions
- POST /users/:userId/roles/:roleId
- DELETE /users/:userId/roles/:roleId

### System (Phase 4)
- GET /audit/logs
- GET /system/settings
- PUT /system/settings
- GET /system/health

## Testing Strategy

### Unit Testing
- Password hashing verification
- JWT token validation
- Permission checking logic
- Data validation rules

### Integration Testing
- User registration dan login flow
- Role assignment dan permission checking
- Session management
- Audit logging

### Security Testing
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting
- Account lockout testing

### Performance Testing
- Load testing dengan concurrent users
- Permission checking performance
- Audit log performance
- Session management performance

## Deployment Considerations

### Environment Variables
- Database connection strings
- JWT secret keys
- Email configuration
- Redis configuration
- Security settings

### Database Configuration
- Connection pooling
- Query timeout settings
- Backup strategy
- Replication setup

### Monitoring
- Database performance metrics
- Security event monitoring
- Audit log monitoring
- User activity tracking

## File Structure

```
.ai/schema/
├── index.json                           # Project overview
├── implementation_plan.json             # Phase-by-phase implementation
├── README.md                           # This file
├── ddl/                                # SQL migration scripts
│   ├── 001_create_users_table.sql
│   ├── 002_create_user_profiles_table.sql
│   ├── 003_create_roles_permissions_tables.sql
│   ├── 004_create_user_roles_table.sql
│   ├── 005_create_support_tables.sql
│   ├── 006_create_audit_system_tables.sql
│   └── 007_seed_initial_data.sql
├── users/                              # User table schema
│   ├── entity.json
│   ├── relationships.json
│   └── indexes.json
├── user_profiles/                      # User profile schema
├── roles/                              # Role management schema
├── permissions/                        # Permission schema
├── user_roles/                         # User-role junction
├── user_sessions/                      # Session management
├── user_activities/                    # Activity logging
└── audit_logs/                         # System audit
```

## Usage Instructions

1. **Setup Database**: Create MySQL database dengan utf8mb4 charset
2. **Run Migrations**: Execute SQL files dalam urutan yang benar
3. **Seed Data**: Run seed script untuk default roles dan permissions
4. **Configure Application**: Setup environment variables
5. **Implement API**: Build API endpoints sesuai dengan phase development
6. **Testing**: Jalankan comprehensive testing untuk setiap phase

## Security Best Practices

1. **Never commit** sensitive data atau credentials
2. **Use environment variables** untuk semua configuration
3. **Implement proper error handling** tanpa exposing sensitive information
4. **Regular security audits** dan penetration testing
5. **Keep dependencies updated** dan security patches
6. **Monitor audit logs** untuk suspicious activities
7. **Implement rate limiting** untuk API endpoints
8. **Use HTTPS** untuk semua communications

## Support

Untuk pertanyaan atau issues, refer ke documentation masing-masing phase atau contact development team.