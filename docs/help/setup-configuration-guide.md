# System Setup & Configuration Guide

## Overview
This guide will help you set up and configure your CNPERP ERP system from initial installation to full operational status.

## Table of Contents
1. [Initial System Setup](#initial-system-setup)
2. [Branch Management](#branch-management)
3. [User Management](#user-management)
4. [Application Settings](#application-settings)
5. [Role-Based Access Control](#role-based-access-control)
6. [Database Configuration](#database-configuration)
7. [API Configuration](#api-configuration)
8. [Troubleshooting](#troubleshooting)

---

## Initial System Setup

### Prerequisites
Before starting, ensure you have:
- PostgreSQL 12 or higher installed
- Python 3.8 or higher
- Git (for version control)
- 4GB RAM minimum (8GB recommended)
- 20GB free disk space

### Step 1: Database Setup

1. **Create the Database:**
   ```bash
   # Connect to PostgreSQL
   psql -U postgres
   
   # Create database
   CREATE DATABASE cnperp_db;
   
   # Create user
   CREATE USER cnperp_user WITH PASSWORD 'your_secure_password';
   
   # Grant privileges
   GRANT ALL PRIVILEGES ON DATABASE cnperp_db TO cnperp_user;
   ```

2. **Configure Environment:**
   ```bash
   # Copy example environment file
   cp env.example .env
   
   # Edit .env file with your settings
   DATABASE_URL=postgresql://cnperp_user:your_password@localhost/cnperp_db
   SECRET_KEY=your_secret_key_here
   ```

3. **Run Database Migrations:**
   ```bash
   # Activate virtual environment
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   
   # Run migrations
   python run_migrations.py
   
   # Seed initial data
   python seed_database.py
   ```

### Step 2: Create Super Admin

```bash
python create_superadmin.py
```

Follow the prompts to create your first administrator account.

### Step 3: Start the Application

```bash
# For development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8010

# For production (use with gunicorn)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8010
```

Access the application at: `http://localhost:8010/static/index.html`

---

## Branch Management

### Creating a Branch

1. **Navigate to Setup → Branches**
2. Click **"Add Branch"**
3. Fill in required information:
   - **Branch Code**: Unique identifier (e.g., "HQ", "BR001")
   - **Branch Name**: Full name (e.g., "Head Office")
   - **Address**: Physical location
   - **Contact Information**: Phone, email
   - **Is Active**: Enable/disable branch

4. Click **"Save"**

### Branch Settings

Each branch can have:
- **Default Currency**: Set local currency
- **Default VAT Rate**: Configure tax rate
- **Operating Hours**: Set business hours
- **Default Accounts**: Link to accounting codes

### Assigning Users to Branches

```bash
# Use the branch assignment script
python assign_users_to_branches.py
```

Or through the UI:
1. Go to **Users** page
2. Edit user profile
3. Select **Branch** from dropdown
4. Save changes

### Assigning Products to Branches

Products can be assigned to specific branches for inventory tracking:

```bash
python assign_products_to_branch.py
```

Or through Products page:
1. Edit product
2. Select **Available Branches**
3. Save changes

---

## User Management

### Creating Users

1. **Navigate to Setup → Users**
2. Click **"Add User"**
3. Enter user details:
   - **Username**: Unique login name
   - **Full Name**: Employee full name
   - **Email**: Contact email
   - **Password**: Initial password (user should change)
   - **Branch**: Assign to branch
   - **Role**: Select user role

4. Click **"Create User"**

### User Roles

Default roles include:
- **Super Admin**: Full system access
- **Admin**: Administrative access
- **Accountant**: Finance and accounting
- **Manager**: Branch management
- **Sales**: Sales and POS access
- **Inventory**: Stock management
- **Cashier**: POS only

### Password Management

**Reset User Password:**
1. Go to Users page
2. Click user's action menu
3. Select "Reset Password"
4. Enter new password
5. Option to force password change on next login

**User Self-Service:**
Users can change their own password from Profile settings.

### User Permissions

Permissions are managed through roles. To customize:
1. Go to **Settings → Role Management**
2. Select role to edit
3. Check/uncheck permissions
4. Save changes

---

## Application Settings

### Accessing Settings

Navigate to **Settings → System Settings**

### General Settings

- **Company Name**: Your business name
- **Company Logo**: Upload company logo
- **Fiscal Year Start**: Set fiscal year beginning
- **Date Format**: Choose date display format
- **Time Zone**: Set system timezone

### Currency Settings

- **Base Currency**: Primary currency (BWP, USD, EUR, etc.)
- **Currency Symbol**: Display symbol (P, $, €)
- **Decimal Places**: Number of decimal places (usually 2)
- **Exchange Rate Source**: Manual or automated

### VAT/Tax Settings

- **VAT Enabled**: Enable/disable VAT
- **Default VAT Rate**: Standard VAT percentage
- **VAT Number**: Your business VAT registration
- **VAT Account Mapping**: Link to GL accounts

### Invoice Settings

- **Invoice Prefix**: Default prefix (e.g., "INV-")
- **Invoice Numbering**: Sequential numbering format
- **Default Payment Terms**: Net 30, Net 60, etc.
- **Default Notes**: Standard invoice footer

### Email Settings

Configure SMTP for sending invoices and reports:
- **SMTP Server**: mail.example.com
- **SMTP Port**: 587 (TLS) or 465 (SSL)
- **Username**: email@example.com
- **Password**: SMTP password
- **From Address**: noreply@example.com

---

## Role-Based Access Control

### Understanding Roles

Roles define what users can do in the system. Each role has:
- **Name**: Role identifier
- **Description**: What this role does
- **Permissions**: List of allowed actions

### Permission Types

- **Read**: View data
- **Create**: Add new records
- **Update**: Edit existing records
- **Delete**: Remove records
- **Export**: Download data
- **Print**: Print reports

### Creating Custom Roles

1. Go to **Settings → Role Management**
2. Click **"Create Role"**
3. Enter role details:
   - **Role Name**: e.g., "Store Manager"
   - **Description**: Brief description
4. Select permissions by module:
   - Sales permissions
   - Inventory permissions
   - Accounting permissions
   - etc.
5. Click **"Save"**

### Permission Matrix

View all roles and permissions in grid format:
1. Go to **Settings → Permission Matrix**
2. See all roles vs. all permissions
3. Quickly identify access levels

---

## Database Configuration

### Connection Settings

Edit `.env` file:
```
DATABASE_URL=postgresql://user:password@host:port/database
```

### Database Backup

**Manual Backup:**
```bash
pg_dump cnperp_db > backup_$(date +%Y%m%d).sql
```

**Automated Backup:**
1. Go to **Settings → Backup Management**
2. Configure backup schedule
3. Choose backup location
4. Enable automated backups

### Database Maintenance

**Regular maintenance tasks:**
```sql
-- Vacuum database
VACUUM ANALYZE;

-- Reindex
REINDEX DATABASE cnperp_db;

-- Check database size
SELECT pg_size_pretty(pg_database_size('cnperp_db'));
```

---

## API Configuration

### API Endpoints

All API endpoints follow REST conventions:
- Base URL: `http://localhost:8010/api/v1/`
- Authentication: Token-based (JWT)
- Format: JSON

### API Authentication

1. **Get Token:**
   ```bash
   curl -X POST http://localhost:8010/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"password"}'
   ```

2. **Use Token:**
   ```bash
   curl http://localhost:8010/api/v1/products \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

### API Rate Limiting

Default limits:
- 100 requests per minute per user
- 1000 requests per hour per IP

Configure in `app/core/config.py`

### API Documentation

Access interactive API docs at:
- Swagger UI: `http://localhost:8010/docs`
- ReDoc: `http://localhost:8010/redoc`

---

## Troubleshooting

### Common Issues

**Issue: Cannot connect to database**
- Check PostgreSQL is running: `sudo service postgresql status`
- Verify connection string in `.env`
- Check firewall settings
- Verify user permissions

**Issue: Application won't start**
- Check Python version: `python --version`
- Verify virtual environment activated
- Check for port conflicts: `netstat -ano | findstr :8010`
- Review logs: `tail -f logs/app.log`

**Issue: Users cannot login**
- Verify user exists: Check Users page
- Reset password if needed
- Check user is active and not locked
- Verify branch assignment

**Issue: Slow performance**
- Check database indices
- Review query performance
- Increase server resources
- Enable caching

### Getting Help

1. **Check Documentation**: Review this guide and related docs
2. **Check Logs**: `logs/app.log` for errors
3. **Community Support**: GitHub issues
4. **Email Support**: support@cnperp.com

### Log Files

Important log locations:
- Application logs: `logs/app.log`
- Error logs: `logs/error.log`
- Access logs: `logs/access.log`
- Database logs: Check PostgreSQL log directory

---

## Best Practices

### Security
- ✅ Use strong passwords (min 12 characters)
- ✅ Enable two-factor authentication
- ✅ Regular security audits
- ✅ Keep system updated
- ✅ Limit super admin accounts
- ✅ Regular password rotation

### Performance
- ✅ Regular database maintenance
- ✅ Monitor disk space
- ✅ Archive old transactions
- ✅ Optimize images and files
- ✅ Use CDN for static assets

### Backup
- ✅ Daily automated backups
- ✅ Test restore procedures monthly
- ✅ Keep offsite backup copies
- ✅ Document backup procedures
- ✅ Encrypt backup files

### Updates
- ✅ Review changelog before updates
- ✅ Test in staging environment
- ✅ Backup before updates
- ✅ Schedule during low-traffic periods
- ✅ Have rollback plan ready

---

## Next Steps

After completing initial setup:
1. ✅ Configure Chart of Accounts
2. ✅ Set up bank accounts
3. ✅ Add products/services
4. ✅ Create customer records
5. ✅ Configure invoice templates
6. ✅ Train users
7. ✅ Begin transactions

## Related Documentation
- [Accounting Codes Setup](accounting-codes-guide.md)
- [Banking Configuration](banking-guide.md)
- [User Management Guide](user-management-guide.md)
- [API Documentation](api-guide.md)
