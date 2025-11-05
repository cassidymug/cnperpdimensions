# Quick LAN Installation - Linux/Ubuntu Server

## 🎯 Goal
Install CNPERP on your Linux server so all computers on your network can access it.

---

## ⚡ Super Quick Install (Copy & Paste)

### Step 1: Connect to Your Server

```bash
# From your PC (Windows/Mac/Linux)
ssh username@192.168.1.100
# Replace with your server's IP and username
```

---

### Step 2: Update System & Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y git python3.11 python3.11-venv python3-pip postgresql postgresql-contrib build-essential libpq-dev curl

# Verify installations
python3.11 --version
psql --version
git --version
```

---

### Step 3: Configure PostgreSQL

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql <<'SQL'
CREATE DATABASE cnperp_db;
CREATE USER cnperp_user WITH PASSWORD 'CNP3rp@2025';
GRANT ALL PRIVILEGES ON DATABASE cnperp_db TO cnperp_user;
ALTER DATABASE cnperp_db OWNER TO cnperp_user;
\q
SQL

# Allow network connections (optional, for remote DB access)
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/*/main/postgresql.conf

# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

### Step 4: Clone Repository

```bash
# Create app directory
mkdir -p ~/apps && cd ~/apps

# Clone from GitHub
git clone https://github.com/cassidymug/cnperpdimensions.git
cd cnperpdimensions
```

---

### Step 5: Setup Python Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate it
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

---

### Step 6: Configure Environment Variables

```bash
# Create .env file
nano .env
```

**Paste this configuration:**

```env
# Database Configuration
DATABASE_URL=postgresql://cnperp_user:CNP3rp@2025@localhost:5432/cnperp_db

# Security
SECRET_KEY=your-secret-key-change-this-in-production
ENVIRONMENT=production

# Server Configuration
ALLOWED_HOSTS=0.0.0.0,localhost,192.168.1.100
DEBUG=False

# CORS (Allow all network devices)
CORS_ORIGINS=*
```

**Save:** Press `Ctrl+X`, then `Y`, then `Enter`

---

### Step 7: Run Database Migrations

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Run migrations
alembic upgrade head
```

---

### Step 8: Configure Firewall

```bash
# Allow port 8010 (API)
sudo ufw allow 8010/tcp

# Allow SSH (if not already allowed)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status
```

---

### Step 9: Test the Application

```bash
# Start application (test mode)
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

**Press Ctrl+C to stop after testing**

---

### Step 10: Install as Systemd Service (Production)

**Create service file:**

```bash
sudo nano /etc/systemd/system/cnperp.service
```

**Paste this configuration (REPLACE 'your-username' with your actual username):**

```ini
[Unit]
Description=CNPERP ERP Application
After=network.target postgresql.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/apps/cnperpdimensions
Environment="PATH=/home/your-username/apps/cnperpdimensions/.venv/bin"
ExecStart=/home/your-username/apps/cnperpdimensions/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8010 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Save:** Press `Ctrl+X`, then `Y`, then `Enter`

**Enable and start service:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable cnperp

# Start service now
sudo systemctl start cnperp

# Check status
sudo systemctl status cnperp
```

---

### Step 11: Test from Another Computer

**On any computer in your network:**

1. Open browser
2. Go to: `http://192.168.1.100:8010/static/login.html`
3. Login with:
   - Username: `admin`
   - Password: `adminpassword`

**API Docs:** `http://192.168.1.100:8010/docs`

---

## 🌐 Setup Nginx Reverse Proxy (Optional)

**This allows access via port 80 instead of 8010:**

```bash
# Install Nginx
sudo apt install -y nginx

# Create configuration
sudo nano /etc/nginx/sites-available/cnperp
```

**Paste this:**

```nginx
server {
    listen 80;
    server_name _;

    # Increase client body size for file uploads
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Enable and start:**

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/cnperp /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Allow port 80
sudo ufw allow 80/tcp

# Restart Nginx
sudo systemctl restart nginx
```

**Now access via:** `http://192.168.1.100` (no port needed!)

---

## 🔄 Update Application (Future Updates)

```bash
# Navigate to app directory
cd ~/apps/cnperpdimensions

# Pull latest code
git pull origin main

# Activate virtual environment
source .venv/bin/activate

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart cnperp

# Check status
sudo systemctl status cnperp
```

**Or use the automated script:**
```bash
./deploy/update_app.sh
```

---

## 📊 Useful Commands

**View logs:**
```bash
# Real-time logs
sudo journalctl -u cnperp -f

# Last 100 lines
sudo journalctl -u cnperp -n 100

# Today's logs
sudo journalctl -u cnperp --since today
```

**Service management:**
```bash
# Start
sudo systemctl start cnperp

# Stop
sudo systemctl stop cnperp

# Restart
sudo systemctl restart cnperp

# Status
sudo systemctl status cnperp
```

**Check if app is running:**
```bash
# Check process
ps aux | grep uvicorn

# Check port
netstat -tulpn | grep 8010
```

**Database access:**
```bash
# Connect to database
psql -U cnperp_user -d cnperp_db -h localhost
# Password: CNP3rp@2025
```

---

## 💾 Setup Automated Backups

**Create backup script:**

```bash
sudo nano /usr/local/bin/cnperp_backup.sh
```

**Paste this:**

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/cnperp"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
sudo -u postgres pg_dump -Fc cnperp_db > "$BACKUP_DIR/cnperp_${DATE}.dump"

# Delete backups older than 30 days
find "$BACKUP_DIR" -type f -name "*.dump" -mtime +30 -delete

echo "Backup completed: cnperp_${DATE}.dump"
```

**Make executable:**
```bash
sudo chmod +x /usr/local/bin/cnperp_backup.sh
```

**Schedule daily backup (2 AM):**
```bash
sudo crontab -e
```

**Add this line:**
```
0 2 * * * /usr/local/bin/cnperp_backup.sh >> /var/log/cnperp_backup.log 2>&1
```

**Test backup:**
```bash
sudo /usr/local/bin/cnperp_backup.sh
ls -lh /var/backups/cnperp/
```

---

## 🔒 Security Recommendations

**1. Change default passwords:**
```bash
# Login to application and change admin password
# Also change PostgreSQL password
```

**2. Setup UFW firewall properly:**
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8010/tcp
sudo ufw allow 80/tcp
sudo ufw enable
```

**3. Keep system updated:**
```bash
# Setup automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## 🆘 Troubleshooting

### Can't access from other computers

**1. Check if service is running:**
```bash
sudo systemctl status cnperp
```

**2. Check if port is listening:**
```bash
netstat -tulpn | grep 8010
```

**3. Check firewall:**
```bash
sudo ufw status
```

**4. Test from server itself:**
```bash
curl http://localhost:8010/docs
```

**5. Check server IP:**
```bash
ip addr show
# or
hostname -I
```

### Database connection errors

**Test database connection:**
```bash
psql -U cnperp_user -d cnperp_db -h localhost
```

**Check PostgreSQL is running:**
```bash
sudo systemctl status postgresql
```

### Service won't start

**Check logs:**
```bash
sudo journalctl -u cnperp -n 50
```

**Check permissions:**
```bash
ls -la ~/apps/cnperpdimensions
```

**Manually test:**
```bash
cd ~/apps/cnperpdimensions
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8010
```

---

## ✅ Success Checklist

- [ ] System updated
- [ ] PostgreSQL installed and configured
- [ ] Database created (cnperp_db)
- [ ] Repository cloned
- [ ] Python virtual environment created
- [ ] Dependencies installed
- [ ] .env file configured
- [ ] Database migrations run
- [ ] Firewall configured (port 8010)
- [ ] Systemd service created and started
- [ ] Can access from server (localhost:8010)
- [ ] Can access from another computer (server-ip:8010)
- [ ] Nginx reverse proxy configured (optional)
- [ ] Automated backups scheduled (optional)

---

## 📞 Default Access Information

**With Nginx (port 80):** `http://<server-ip>`
**Direct access (port 8010):** `http://<server-ip>:8010`

**Login Page:** `/static/login.html`
**API Docs:** `/docs`

**Default Credentials:**
- Username: `admin`
- Password: `adminpassword`

**⚠️ Change default password immediately after first login!**

---

**Installation Time:** ~20 minutes
**Future Updates:** ~2 minutes with automated script

## 🎯 Quick Reference

**Find your server IP:**
```bash
hostname -I | awk '{print $1}'
```

**Restart everything:**
```bash
sudo systemctl restart postgresql
sudo systemctl restart cnperp
sudo systemctl restart nginx  # if installed
```

**Complete uninstall:**
```bash
sudo systemctl stop cnperp
sudo systemctl disable cnperp
sudo rm /etc/systemd/system/cnperp.service
sudo systemctl daemon-reload
rm -rf ~/apps/cnperpdimensions
```

