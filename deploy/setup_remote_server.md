# Remote Server Setup Guide for CNPERP

This guide helps you set up a remote server (Linux or Windows) to run CNPERP and deploy via Git + VS Code Remote SSH.

---

## Part 1: Server Prerequisites

### For Linux (Ubuntu 20.04/22.04 recommended):
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install python3 python3-pip python3-venv -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Git
sudo apt install git -y

# Install Node.js (for PM2 if needed)
sudo apt install nodejs npm -y

# Install nginx (reverse proxy)
sudo apt install nginx -y
```

### For Windows Server:
```powershell
# Install Python from https://www.python.org/downloads/
# Install PostgreSQL from https://www.postgresql.org/download/windows/
# Install Git from https://git-scm.com/download/win
```

---

## Part 2: SSH Setup

### On Your LOCAL Machine:

#### Generate SSH Key (if you don't have one):
```bash
# Windows (PowerShell)
ssh-keygen -t ed25519 -C "your_email@example.com"
# Press Enter to save to default location: C:\Users\YourName\.ssh\id_ed25519

# Linux/Mac
ssh-keygen -t ed25519 -C "your_email@example.com"
# Press Enter to save to default location: ~/.ssh/id_ed25519
```

#### Copy Public Key to Server:
```bash
# Linux/Mac
ssh-copy-id username@your-server-ip

# Windows (PowerShell) - Manual method:
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh username@your-server-ip "cat >> ~/.ssh/authorized_keys"
```

#### Test SSH Connection:
```bash
ssh username@your-server-ip
```

---

## Part 3: VS Code Remote SSH Setup

### 1. Install VS Code Extension:
- Open VS Code
- Go to Extensions (Ctrl+Shift+X)
- Search for "Remote - SSH"
- Install the extension by Microsoft

### 2. Configure SSH Config File:

**Windows:** `C:\Users\YourName\.ssh\config`
**Linux/Mac:** `~/.ssh/config`

Add this configuration:
```
Host cnperp-server
    HostName your-server-ip-or-domain
    User your-username
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    ForwardAgent yes
```

### 3. Connect to Remote Server:
1. Press `F1` or `Ctrl+Shift+P`
2. Type: "Remote-SSH: Connect to Host"
3. Select "cnperp-server"
4. VS Code will open a new window connected to your server

### 4. Open Remote Folder:
- File → Open Folder
- Navigate to `/home/username/cnperp-python` (Linux)
- Or `C:\apps\cnperp-python` (Windows)

---

## Part 4: Deploy Application to Server

### Initial Deployment (First Time):

#### On Remote Server (via SSH):
```bash
# Create application directory
mkdir -p ~/apps
cd ~/apps

# Clone repository
git clone https://github.com/cassidymug/cnperp-python.git
cd cnperp-python

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux
# or
.\.venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
nano .env  # or vim .env
```

#### Configure .env file:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/cnperp_db
SECRET_KEY=your-secret-key-here
ENVIRONMENT=production
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-server-ip

# PostgreSQL Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=cnperp_user
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=cnperp_db
```

#### Set up PostgreSQL database:
```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE cnperp_db;
CREATE USER cnperp_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE cnperp_db TO cnperp_user;
\q

# Run migrations (if using Alembic)
# alembic upgrade head
```

---

## Part 5: Set Up Systemd Service (Linux)

Create service file:
```bash
sudo nano /etc/systemd/system/cnperp.service
```

Add this content:
```ini
[Unit]
Description=CNPERP FastAPI Application
After=network.target postgresql.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/apps/cnperp-python
Environment="PATH=/home/your-username/apps/cnperp-python/.venv/bin"
ExecStart=/home/your-username/apps/cnperp-python/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8010 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cnperp
sudo systemctl start cnperp
sudo systemctl status cnperp
```

---

## Part 6: Configure Nginx Reverse Proxy (Linux)

Create nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/cnperp
```

Add this content:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support (if needed)
    location /ws {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable site and restart nginx:
```bash
sudo ln -s /etc/nginx/sites-available/cnperp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Part 7: Set Up SSL/HTTPS (Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
# Test renewal:
sudo certbot renew --dry-run
```

---

## Part 8: Daily Workflow - Updating Application

### Method 1: Using Update Script (Recommended)

**From your LOCAL machine via VS Code Remote:**
1. Connect to server via VS Code Remote SSH
2. Open terminal in VS Code (Ctrl+`)
3. Run update script:
   ```bash
   cd ~/apps/cnperp-python
   ./deploy/update_app.sh  # Linux
   # or
   .\deploy\update_app.ps1  # Windows
   ```

### Method 2: Manual Git Pull

**Via SSH:**
```bash
ssh cnperp-server
cd ~/apps/cnperp-python
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart cnperp
```

### Method 3: Via VS Code Remote

1. Open VS Code
2. Press F1 → "Remote-SSH: Connect to Host" → "cnperp-server"
3. Open folder: `/home/username/apps/cnperp-python`
4. Use Source Control panel (Ctrl+Shift+G) to pull latest changes
5. Open terminal (Ctrl+`) and run:
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt --upgrade
   sudo systemctl restart cnperp
   ```

---

## Part 9: Monitoring & Logs

### View application logs:
```bash
# Systemd service logs
sudo journalctl -u cnperp -f

# Or if using log files
tail -f /var/log/cnperp.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Check application status:
```bash
sudo systemctl status cnperp
curl http://localhost:8010/health  # If you have a health endpoint
```

---

## Part 10: Firewall Setup

```bash
# Ubuntu (UFW)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable
sudo ufw status
```

---

## Part 11: Backup Strategy

### Set up automated backups:
```bash
# Create backup script
sudo nano /usr/local/bin/backup-cnperp.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/cnperp"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U cnperp_user cnperp_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup uploaded files (if any)
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /home/username/apps/cnperp-python/uploads

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup-cnperp.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
```
Add line:
```
0 2 * * * /usr/local/bin/backup-cnperp.sh >> /var/log/cnperp-backup.log 2>&1
```

---

## Quick Reference Commands

```bash
# Connect via SSH
ssh cnperp-server

# Pull latest code
cd ~/apps/cnperp-python && git pull origin main

# Restart application
sudo systemctl restart cnperp

# View logs
sudo journalctl -u cnperp -f

# Check status
sudo systemctl status cnperp

# Update dependencies
source .venv/bin/activate && pip install -r requirements.txt --upgrade

# Run backup
python -c "from app.services.backup_service import BackupService; from app.core.database import SessionLocal; db = SessionLocal(); BackupService(db).create_backup(); db.close()"
```

---

## Troubleshooting

### Application won't start:
```bash
sudo systemctl status cnperp
sudo journalctl -u cnperp -n 50
```

### Database connection issues:
```bash
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT 1"
```

### Port already in use:
```bash
sudo lsof -i :8010
sudo kill -9 <PID>
```

### Permission issues:
```bash
sudo chown -R your-username:your-username ~/apps/cnperp-python
chmod +x deploy/update_app.sh
```

---

## Security Best Practices

1. **Change default PostgreSQL password**
2. **Use strong SECRET_KEY in .env**
3. **Keep SSH keys secure** (never share private key)
4. **Enable firewall** (ufw or firewalld)
5. **Set up fail2ban** to prevent brute-force SSH attacks
6. **Regular security updates**: `sudo apt update && sudo apt upgrade`
7. **Use HTTPS** (SSL certificate via Certbot)
8. **Disable root SSH login** in `/etc/ssh/sshd_config`
9. **Use environment variables** for secrets (never commit .env to git)
10. **Regular backups** (automated daily)

---

## Support

For issues or questions:
- Check logs: `sudo journalctl -u cnperp -f`
- Review documentation in this repository
- Contact system administrator
